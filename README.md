# Azure AI Samples

A collection of various interesting Azure AI Samples.

## Installation

Create the Python environment of your choice and install the required packages:

```bash
pip install -r requirements.txt
```

Create an [Azure AI Foundry project](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/create-projects?tabs=ai-studio) in Azure. Once ready, set the following environment variable (using `.env` file or directly in your shell):

```bash
AZURE_AI_PROJECT_CONNECTION_STRING=<Azure AI Project connection string>
```

> The Azure AI Inference samples may require additional environment variables. Those are documented in the code.

## Contents

| Sample Name | Description | Blog Post | Type |
|-------------|-------------|-----------|------|
| 💻 [AI Inference: Switching between models](./azure-ai-inference-model-switching/) | 📝 Using Azure AI Inference to easily switch between models running in Azure OpenAI, OpenAI, Github Models, Azure AI Serverless and local endpoints. | [Link](https://www.strathweb.com/2024/11/simplifying-the-ai-workflow-access-different-types-of-model-deployments-with-azure-ai-inference/) | Notebook |
| 💻 [AI Inference: Tool calling](./azure-ai-inference-model-switching/) | 📝 Using Azure AI Inference for tool calling. | N/A | Program |
| 💻 [AI Agents: Single agent tool calling](./azure-ai-agents-tool-calling/) | 📝 Using Azure AI Agents for tool calling (single agent). | N/A | Program |
| 💻 [AI Agents: Multi agent tool calling](./azure-ai-agents-multi-agent-tool-calling/) | 📝 Using Azure AI Agents for tool calling (multi-agent). | N/A | Program |
| 💻 [AI Agents: Orchestrated agents with tools](./azure-ai-agents-multi-agent-orchestrated-tool-calling/) | 📝 Using Azure AI Agents (multi-agent) with a coordinating orchestrator agent. | N/A | Program |
| 💻 [AI Agents: OpenAPI tool calling](./azure-ai-agents-openapi-tool/) | 📝 Using Azure AI Agents for calling tools defined via OpenAPI HTTP contract. | N/A | Program |