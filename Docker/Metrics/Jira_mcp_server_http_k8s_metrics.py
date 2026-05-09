"""
If you try to point a LangChain 1.0+ agent at this, it won't see any tools. In 2026, a
"Model Context Protocol" (MCP) server must implement a specific JSON-RPC handshake so the LLM can "discover" what tools you have and what arguments they need.

Why this version works:
Auto-Discovery: By using @mcp.tool(), the server automatically tells LangChain: "I have a tool called 'create_issue' and it requires these 4 arguments."

Type Safety: The LLM sees the type hints (str) and the docstrings to understand how to use the tool.

ADF Support: The adf_description block prevents Jira from throwing a 400 Bad Request.

Protocol Compliance: mcp.run() starts the server in a way that LangChain's McpToolkit can actually communicate with.

How to run it with your new uv setup:
Save the code above as server.py and run:

uv run python server.py


"""
import os
import requests
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import uvicorn
from dotenv import load_dotenv
import time
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    make_asgi_app,
    REGISTRY
)

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

# Read ALLOWED_HOSTS from environment variable (injected via ConfigMap)
# Split by comma to get list
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,localhost:8000,127.0.0.1"   # ← default fallback for local dev
).split(",")

print(f"Starting MCP server with ALLOWED_HOSTS: {ALLOWED_HOSTS}")

# ── Prometheus Metrics ────────────────────────────────────────
ticket_creation_total = Counter(
    "mcp_ticket_creation_total",
    "Total number of Jira tickets created",
    ["status", "project"]          # labels: success/failure, project key
)

ticket_creation_failures = Counter(
    "mcp_ticket_creation_failures_total",
    "Total number of failed Jira ticket creations",
    ["reason"]                     # label: api_error, validation_error
)

tool_call_duration = Histogram(
    "mcp_tool_call_duration_seconds",
    "Time spent executing MCP tools",
    ["tool_name"],                 # label: create_issue
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

active_sessions = Gauge(
    "mcp_active_sessions",
    "Number of active MCP sessions"
)

jira_api_duration = Histogram(
    "mcp_jira_api_duration_seconds",
    "Time spent calling Jira REST API",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# ── FastMCP Setup ─────────────────────────────────────────────
# Initialize FastMCP - This automatically handles tool discovery
# Pass allowed hosts directly to FastMCP
mcp = FastMCP(
    "Jira-Helper",
    transport_security=TransportSecuritySettings(
        allowed_hosts=ALLOWED_HOSTS    # ← from ConfigMap now
    )
)

# Create FastAPI app
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── MCP Tool ──────────────────────────────────────────────────
# ---- MCP tool: jira.create_issue ----
@mcp.tool()
def create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task") -> str:
    """
    Create a new Jira issue.
    :param project_key: The project key (e.g., 'PROJ')
    :param summary: Brief title of the issue
    :param description: Detailed explanation
    :param issue_type: Type of issue (Task, Bug, etc.)
    """
    start_time = time.time()
    active_sessions.inc()          # increment active sessions

    try:
        # FIX: Convert string description to Atlassian Document Format (ADF)
        adf_description = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}]
                }
            ]
        }

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": adf_description, # Corrected for v3 API
                "issuetype": {"name": issue_type}
            }
        }

        # Measure Jira API call duration
        api_start = time.time()
        response = requests.post(
            f"{JIRA_URL}/rest/api/3/issue",
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload
        )
        jira_api_duration.observe(time.time() - api_start)

      
        if response.status_code == 201:
            issue_key = response.json().get("key")
            # Increment success counter
            ticket_creation_total.labels(
                status="success",
                project=project_key
            ).inc()
            return f"Success! Issue created: {issue_key}"
        else:
            # Truncate error to avoid exceeding 1MB MCP limit
            error_text = response.text[:500] 
            # Increment failure counters
            ticket_creation_total.labels(
                status="failure",
                project=project_key
            ).inc()
            ticket_creation_failures.labels(
                reason="api_error"
            ).inc()
            return f"Failed with status {response.status_code}: {error_text}"
    
    except Exception as e:
        ticket_creation_failures.labels(reason="exception").inc()
        ticket_creation_total.labels(
            status="failure",
            project=project_key
        ).inc()
        return f"Error: {str(e)}"

    finally:
        # Always record duration and decrement sessions
        duration = time.time() - start_time
        tool_call_duration.labels(tool_name="create_issue").observe(duration)
        active_sessions.dec()

"""if __name__ == "__main__":
    # Get the ASGI app from FastMCP and run via uvicorn directly
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)"""


from starlette.applications import Starlette
from starlette.routing import Mount
from prometheus_client import make_asgi_app

# Get MCP app
mcp_app = mcp.streamable_http_app()

# Create Prometheus metrics app
metrics_app = make_asgi_app()

# Wrap with custom routing
"""
This is what makes it an ASGI app. ASGI (Async Server Gateway Interface) is the protocol uvicorn uses to talk to Python web apps.
Every request calls __call__ with 3 arguments:
  scope   ← request metadata (path, headers, method)
  receive ← function to read request body
  send    ← function to send response back

  Starlette Mount:                CombinedApp:
────────────────                ────────────
Adds /metrics/ prefix          Manual path routing
Requires trailing slash        No trailing slash needed
Conflicts with MCP lifecycle   MCP runs at root ✅
307 redirects                  No redirects ✅
"""
class CombinedApp:
    def __init__(self, mcp_app, metrics_app):
        self.mcp_app = mcp_app
        self.metrics_app = metrics_app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if path.startswith("/metrics"):
            # Strip /metrics prefix for prometheus app
            scope = dict(scope)
            scope["path"] = path[len("/metrics"):] or "/"
            scope["raw_path"] = scope["path"].encode()
            await self.metrics_app(scope, receive, send)
        else:
            # Pass everything else to MCP app
            await self.mcp_app(scope, receive, send)

app = CombinedApp(mcp_app, metrics_app)


# ── App Setup ─────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)