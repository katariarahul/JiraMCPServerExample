import os
import requests
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
# This will be used for Langchain Trace
#from opik.integrations.langchain import OpikTracer
from opik import track
import opik
#import time
#from opik.opik_context import get_current_opik_span
# Initialize the tracer
#opik_tracer  = OpikTracer(project_name="JIRA_MCP_Server")

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

# Initialize FastMCP - This automatically handles tool discovery
mcp = FastMCP("Jira-Helper")

@track(name="prepare_payload", project_name="JIRA_Agent")
async def prepare_payload(project_key, summary, adf_description,issue_type):
    payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": adf_description, # Corrected for v3 API
                "issuetype": {"name": issue_type}
            }
        }
    return payload


@track(name="jira_api_call", project_name="JIRA_Agent")
async def call_jira(payload):
    response = requests.post(
            f"{JIRA_URL}/rest/api/3/issue",
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload
        )
    return response

@track(name="format_response", project_name="JIRA_Agent")
async def format_response(response):
    if response.status_code == 201:
        result =  f"Success! Issue created: {response.json().get('key')}"
    else:
        # Truncate error to avoid exceeding 1MB MCP limit
        error_text = response.text[:500] if response.text else "No response body"
        result = f"Failed with status {response.status_code}: {error_text}"
    return result

# ---- MCP tool: jira.create_issue ----
@mcp.tool()
@track(name="JIRA_create_issue", project_name="JIRA_Agent")
async def create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task") -> str:
    try:    
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
        print(" $$$$$$$$$$$$$$$$ Before payload &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        payload = await prepare_payload(project_key, summary, adf_description, issue_type)

        response = await call_jira(payload)

        result = await format_response(response=response)

        return result 

    except Exception as e:
        return f"Exception occurred: {str(e)}"   # ✅ FIX

if __name__ == "__main__":
    # Standard MCP entry point
    mcp.run(transport="stdio")
    #mcp.run(transport="streamable-http")
