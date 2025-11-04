# Azure AI Agents Samples

A collection of various interesting Azure AI Agents Samples.

## Installation

Create the Python environment of your choice and install the required packages:

```bash
pip install -r requirements.txt
```

### AI Foundry Project

Create an [Azure AI Foundry project](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/create-projects?tabs=ai-studio) in Azure. Once ready, set the following environment variable (using `.env` file or directly in your shell):

```bash
AZURE_AI_PROJECT_CONNECTION_STRING=<Azure AI Project connection string>
```

### Azure OpenAI

Sample using Azure OpenAI directly require the following variables:

```bash
AZURE_OPENAI_DEPLOYMENT_NAME=<deployment name>
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=<chat deployment name> # for Agent Framework samples
AZURE_OPENAI_ENDPOINT=<endpoint root>
AZURE_OPENAI_API_KEY=<key>
```

> Some samples may require additional environment variables. Those are documented in the code.

## AI Inference

| Sample Name | Description | Blog Post | Type |
|-------------|-------------|-----------|------|
| 💻 [AI Inference: Switching between models](./azure-ai-inference/model-switching/) | 📝 Using Azure AI Inference to easily switch between models running in Azure OpenAI, OpenAI, Github Models, Azure AI Serverless and local endpoints. | [Link](https://www.strathweb.com/2024/11/simplifying-the-ai-workflow-access-different-types-of-model-deployments-with-azure-ai-inference/) | Notebook |
| 💻 [AI Inference: Tool calling](./azure-ai-inference/model-switching/) | 📝 Using Azure AI Inference for tool calling. | N/A | Program |

## Azure AI Agents

| Sample Name | Description | Blog Post | Type |
|-------------|-------------|-----------|------|
| 💻 [Azure AI Agents: Single agent tool calling](./azure-ai-agents/tool-calling/) | 📝 Using Azure AI Agents for tool calling (single agent). | N/A | Program |
| 💻 [Azure AI Agents: Multi agent tool calling](./azure-ai-agents/multi-agent-tool-calling/) | 📝 Using Azure AI Agents for tool calling (multi-agent). | N/A | Program |
| 💻 [Azure AI Agents: Orchestrated agents with tools](./azure-ai-agents/multi-agent-orchestrated-tool-calling/) | 📝 Using Azure AI Agents (multi-agent) with a coordinating orchestrator agent. | N/A | Program |
| 💻 [Azure AI Agents: OpenAPI tool calling](./azure-ai-agents/openapi-tool/) | 📝 Using Azure AI Agents for calling tools defined via OpenAPI HTTP contract. | [Link](https://www.strathweb.com/2025/06/ai-agents-with-openapi-tools-part-2-azure-ai-foundry/) | Program |

## Semantic Kernel Agents

| Sample Name | Description | Blog Post | Type |
|-------------|-------------|-----------|------|
| 💻 [Semantic Kernel: Single agent tool calling](./semantic-kernel/chatcompletions-plugin/) | 📝 Using Semantic Kernal with Chat Completion Agents for tool calling (plugin) | N/A | Program |
| 💻 [Semantic Kernel + AI Agents: Single agent tool calling](./semantic-kernel/azure-ai-agents-plugin/) | 📝 Using Semantic Kernal with Azure AI Agents for tool calling (plugin) | N/A | Program |
| 💻 [Semantic Kernel: OpenAPI Plugin](./semantic-kernel/openapi-plugin/) | 📝 Using Semantic Kernel for calling tools (plugin) defined via OpenAPI HTTP contract. | [Link](https://www.strathweb.com/2025/06/ai-agents-with-openapi-tools-part-1-semantic-kernel/) | Program |
| 💻 [Semantic Kernel: RAG with local vector store](./semantic-kernel/chatcompletions-agent-rag/) | 📝 Using Semantic Kernel with a simple local vector store for Retrieval-Augmented Generation (RAG) on sample data | N/A | Program |
| 💻 [Semantic Kernel: HyPE (Hypothetical Prompt Embeddings)](./semantic-kernel/chatcompletions-agent-hype-rag/) | 📝 Using Semantic Kernel with a local vector store for Retrieval-Augmented Generation (RAG) using the HyPE (Hypothetical Prompt Embeddings) pattern | [Link](https://www.strathweb.com/2025/07/rag-agent-with-hype-pattern-using-semantic-kernel/) | Program | 
| 💻 [Semantic Kernel: HyDE (Hypothetical Document Embeddings)](./semantic-kernel/chatcompletions-agent-hyde-rag/) | 📝 Using Semantic Kernel with a local vector store for Retrieval-Augmented Generation (RAG) using the HyDE (Hypothetical Document Embeddings) pattern | N/A | Program | 

## Agent Framework Agents

| Sample Name | Description | Blog Post | Type |
|-------------|-------------|-----------|------|
| 💻 [Agent Framework: Single chat agent tool calling](./agent-framework/tool-calling/) | 📝 Using Agent Framework for tool calling (single AzureOpenAIChatClient agent). | N/A | Program |
| 💻 [Agent Framework: OpenAPI tool calling with Azure AI Agent](./agent-framework/openapi-tool/) | 📝 Using Agent Framework with Azure AI Agents for calling tools defined via OpenAPI HTTP contract. | N/A | Program |