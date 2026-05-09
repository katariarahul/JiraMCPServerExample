# Jira & Gmail MCP Servers with Opik & Kubernetes

This repository contains agent code for Jira & Gmail MCP servers featuring Opik configuration and Kubernetes deployment.

---

## 🚀 Features

### 1. Simple Agent
- Custom agent designed to call a locally running Jira MCP Server.
- Automates the creation of Jira tickets via simple commands.

### 2. Gmail MCP Server
- Exposed as a streamable HTTP service for local integration.
- Handles authentication and mail processing logic.

### 3. Jira MCP Server
#### Connection Testing
- Scripts to verify Jira API connectivity.

#### HTTP Interface
- MCP Server exposed via HTTP for local web access.

#### Stdio Interface
- Standard I/O exposure for local tool integration.

### 4. Opik Integration
- Integrated Opik for observability and tracing of Jira MCP server actions.

### 5. DevOps & Deployment
- Dockerized: Optimized Dockerfiles for all server components.
- Kubernetes: Full deployment manifests for k3d and local K8s clusters.

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Language | Python |
| Environment | UV, Conda |
| Containerization | Docker |
| Orchestration | Kubernetes (k3d) |
| Observability | Opik |
| MCP SERVER | HTTP | STDIO

---

## 📖 Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <repo-name>
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Update `.env` with your credentials and configuration.

### 3. Install Dependencies

```bash
uv sync
```

### 4. Deploy to Kubernetes

```bash
kubectl apply -f Docker/k8s/phase1/
```

---

## 🧪 Local Development

Run services locally for testing and development purposes.

Example:

```bash
uv run python main.py
```

---

## 💡 Notes

- This project is intended for local development and testing of Model Context Protocol (MCP) implementations.
- k3d is recommended for lightweight local Kubernetes testing.
- Opik tracing is enabled for observability and debugging workflows.

---

## 🔍 Observability

Opik integration provides:
- Request tracing
- Agent execution visibility
- MCP interaction monitoring
- Debugging support for workflows

---

# 📄 Disclaimer

This project is intended for learning, experimentation, and local development purposes only.

Credentials, secrets, and sensitive configurations are excluded from the repository.

