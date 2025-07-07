import asyncio
import os
import sys
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass

from dotenv import load_dotenv
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureTextEmbedding
from semantic_kernel.functions import kernel_function
from typing import Annotated

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

@dataclass
class Document:
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: np.ndarray = None

class SimpleVectorStore:
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings_service = None
    
    def set_embeddings_service(self, service):
        self.embeddings_service = service
    
    async def add_documents(self, documents: List[Document]):
        for doc in documents:
            if self.embeddings_service and doc.embedding is None:
                embeddings = await self.embeddings_service.generate_embeddings([doc.content])
                doc.embedding = np.array(embeddings[0])
            self.documents.append(doc)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Document]:
        if not self.documents or len(self.documents) == 0:
            return []
        
        similarities = []
        for doc in self.documents:
            if doc.embedding is not None:
                similarity = np.dot(query_embedding, doc.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc.embedding)
                )
                similarities.append((similarity, doc))
        
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in similarities[:top_k]]

class QuantumProjectsPlugin:
    """Plugin for searching quantum project information using RAG"""
    
    def __init__(self, vector_store: SimpleVectorStore, embeddings_service):
        self.vector_store = vector_store
        self.embeddings_service = embeddings_service
    
    @kernel_function(description="Search quantum project information to answer questions about quantum research projects.")
    async def search_quantum_projects(
        self, 
        query: Annotated[str, "The search query about quantum projects"]
    ) -> Annotated[str, "Returns relevant information about quantum projects"]:
        """Search for quantum project information based on the query."""
        
        print(f"🔍 Searching quantum projects for: {query}")
        
        query_embeddings = await self.embeddings_service.generate_embeddings([query])
        query_embedding = np.array(query_embeddings[0])
        
        similar_docs = self.vector_store.search(query_embedding, top_k=3)
        
        if not similar_docs:
            return "No relevant quantum project information found."
        
        context = []
        for doc in similar_docs:
            context.append(f"From {doc.metadata.get('project', 'Unknown Project')}:\n{doc.content}")
        
        result = "\n\n---\n\n".join(context)
        print(f"📊 Found {len(similar_docs)} relevant document chunks")
        
        return result

def load_and_chunk_projects_data(file_path: str) -> List[Document]:
    """Load the projects.md file and chunk it into documents"""
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    projects = content.split('# Project')[1:]
    
    documents = []
    for i, project in enumerate(projects):
        project_content = f"# Project{project}"  # add back the heading
        
        # extract project name from the first line
        first_line = project_content.split('\n')[0]
        project_name = first_line.replace('# Project ', '').split(' (')[0]
        
        # split each project into sections
        sections = project_content.split('\n## ')
        
        for j, section in enumerate(sections):
            if j == 0:
                section_content = section
                section_name = "Overview"
            else:
                section_content = f"## {section}"
                section_name = section.split('\n')[0]
            
            # create a document for each section
            doc_id = f"project_{i}_section_{j}"
            doc = Document(
                id=doc_id,
                content=section_content.strip(),
                metadata={
                    'project': project_name,
                    'section': section_name,
                    'project_index': i,
                    'section_index': j
                }
            )
            documents.append(doc)
    
    return documents

async def main():
    print("🚀 Initializing Quantum Projects RAG Agent...")
    
    embeddings_service = AzureTextEmbedding(
        deployment_name=os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    )
    print("✅ Created embeddings service")
    
    vector_store = SimpleVectorStore()
    vector_store.set_embeddings_service(embeddings_service)
    
    # load and process the quantum projects data
    data_path = os.path.join(os.path.dirname(__file__), "data", "projects.md")
    print(f"📄 Loading quantum projects data from {data_path}")
    
    documents = load_and_chunk_projects_data(data_path)
    print(f"📚 Created {len(documents)} document chunks")
    
    # add documents to vector store (this will generate embeddings)
    print("🔄 Generating embeddings for documents...")
    await vector_store.add_documents(documents)
    print("✅ Documents indexed in vector store")
    
    # create the quantum projects plugin
    quantum_plugin = QuantumProjectsPlugin(vector_store, embeddings_service)
    
    agent = ChatCompletionAgent(
        service=AzureChatCompletion(
            deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        ),
        name="QuantumProjectsAgent",
        instructions="""You are a helpful assistant that provides information about quantum research projects. 
        Use the search_quantum_projects function to find relevant information from the quantum projects database.
        Always base your answers on the retrieved information and cite which projects the information comes from.
        If you can't find relevant information, say so clearly.""",
        plugins=[quantum_plugin],
    )
    print("✅ Created Quantum Projects RAG agent")
    
    print("\nWelcome to the Quantum Projects Chat!")
    print("Ask me anything about quantum research projects. Type 'quit' or 'exit' to end the conversation.")
    print("Example questions:")
    print("  - What is Project Mousetrap and what are its goals?")
    print("  - Which quantum projects have the largest budgets?")
    print("  - Tell me about quantum key distribution research")
    
    thread = None
    
    try:
        while True:
            user_input = (await async_input("\n💬 User: ")).strip()
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
            if not user_input:
                continue
            
            try:
                response = await agent.get_response(
                    messages=user_input,
                    thread=thread,
                )
                print(f"\n🤖 Agent: {response}")
                thread = response.thread
                
            except Exception as e:
                print(f"❌ Error getting response: {e}")
                
    except KeyboardInterrupt:
        print("\n\n👋 Chat interrupted. Goodbye!")
    
    print("\n🧹 Cleaning up resources...")
    if thread:
        try:
            await thread.delete()
            print("✅ Thread deleted")
        except Exception as e:
            print(f"⚠️ Error deleting thread: {e}")

if __name__ == "__main__":
    asyncio.run(main())