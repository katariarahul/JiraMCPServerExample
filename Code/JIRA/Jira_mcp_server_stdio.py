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
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

# Initialize FastMCP - This automatically handles tool discovery
mcp = FastMCP("Jira-Helper")

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

    response = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        auth=(JIRA_EMAIL, JIRA_TOKEN),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=payload
    )

    if response.status_code == 201:
        return f"Success! Issue created: {response.json().get('key')}"
    else:
        # Truncate error to avoid exceeding 1MB MCP limit
        error_text = response.text[:500] if response.text else "No response body"
        return f"Failed with status {response.status_code}: {error_text}"

if __name__ == "__main__":
    # Standard MCP entry point
    mcp.run(transport="stdio")
    #mcp.run(transport="streamable-http")
