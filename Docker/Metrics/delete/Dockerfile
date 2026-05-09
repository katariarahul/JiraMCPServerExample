FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY Jira_mcp_server_http_k8s_metrics.py .

# FastMCP streamable-http defaults to port 8000
EXPOSE 8000

CMD ["python", "Jira_mcp_server_http_k8s metrics.py"]