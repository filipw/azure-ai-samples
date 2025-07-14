# Sample demonstrating HyDE (Hypothetical Document Embeddings) with Semantic Kernel
#
# Based on:
# Luyu Gao and Xueguang Ma and Jimmy Lin and Jamie Callan, "Precise Zero-Shot Dense Retrieval without Relevance Labels." (2022)
# arXiv https://arxiv.org/abs/2212.10496

import asyncio
import os
import sys
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
import json

from dotenv import load_dotenv
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureTextEmbedding
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelArguments
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

@dataclass
class HypotheticalDocument:
    document: str
    document_embedding: np.ndarray
    original_query: str
    query_context: Dict[str, Any]

class HyDEVectorStore:
    def __init__(self):
        self.documents: List[Document] = []
        self.hypothetical_documents: List[HypotheticalDocument] = []
        self.embeddings_service = None
        self.llm_service = None
    
    def set_services(self, embeddings_service, llm_service):
        self.embeddings_service = embeddings_service
        self.llm_service = llm_service
    
    async def add_documents(self, documents: List[Document]):
        print(f"\n📄 Indexing {len(documents)} document chunks...")
        
        for doc in documents:
            if self.embeddings_service and doc.embedding is None:
                embeddings = await self.embeddings_service.generate_embeddings([doc.content])
                doc.embedding = np.array(embeddings[0])
            self.documents.append(doc)
        
        print(f"✅ Indexed {len(documents)} documents with embeddings")
    
    async def generate_hypothetical_document(self, query: str, task_instruction: str = None) -> str:
        """Generate a hypothetical document that would answer the query using HyDE approach."""
        
        try:
            kernel = Kernel()
            kernel.add_service(self.llm_service)
            
            if task_instruction is None:
                task_instruction = "Write a detailed, specific passage that directly answers the question with concrete details, facts, and specific information. Avoid generic introductions."
            
            kernel.add_function(
                plugin_name="HyDE",
                function_name="GenerateDocument",
                prompt=f"""{task_instruction}

Example:
Question: What is Project Lighthouse and what is its budget?
Passage: Project Lighthouse is dedicated to developing a secure communication system using Quantum Key Distribution (QKD). The primary objective is to create a QKD system that can securely transmit encryption keys over distances of up to 500 kilometers by 2025. Project Lighthouse is the most well-funded quantum project, with a budget of $50 million for 2024. Approximately 60% of the budget is dedicated to building the infrastructure required for large-scale QKD networks, including optical fiber installations, ground stations, and communication satellites.

Question: {{$query}}
Passage:""",
                template_format="semantic-kernel"
            )
            
            kernel_arguments = KernelArguments(query=query)
            response = await kernel.invoke(
                plugin_name="HyDE", 
                function_name="GenerateDocument", 
                arguments=kernel_arguments
            )
            
            if not response or not str(response).strip():
                print(f"⚠️ Empty response from LLM for query: {query}")
                return query  # fallback to original query
            
            hypothetical_doc = str(response).strip()
            print(f"📝 Generated hypothetical document ({len(hypothetical_doc)} chars) for query: {query[:50]}...")
            print(f"🔍 Hypothetical document preview: {hypothetical_doc[:200]}...")
            
            return hypothetical_doc
            
        except Exception as e:
            print(f"⚠️ Error generating hypothetical document: {e}")
            return query  # fallback to original query
    
    async def search_with_hyde(self, query: str, top_k: int = 3, task_instruction: str = None) -> List[Document]:
        """Search using HyDE: generate hypothetical document, embed it, find similar real documents."""
        
        print(f"\n🔍 HyDE Search: {query}")
        
        # step 1: Generate hypothetical document that would answer the query
        hypothetical_doc = await self.generate_hypothetical_document(query, task_instruction)
        
        # step 2: Embed the hypothetical document
        print("🔮 Embedding hypothetical document...")
        hyp_embeddings = await self.embeddings_service.generate_embeddings([hypothetical_doc])
        hyp_embedding = np.array(hyp_embeddings[0])
        
        # step 3: Search for similar real documents using document-document similarity
        print("🎯 Searching for similar real documents...")
        similar_docs = self._search_by_embedding(hyp_embedding, top_k)
        
        # we don't need to do this, but we can store the hypothetical document for later analysis
        # or debugging
        hyp_doc_entry = HypotheticalDocument(
            document=hypothetical_doc,
            document_embedding=hyp_embedding,
            original_query=query,
            query_context={"task_instruction": task_instruction}
        )
        self.hypothetical_documents.append(hyp_doc_entry)
        
        print(f"📊 Found {len(similar_docs)} similar documents via HyDE")
        return similar_docs
    
    def _search_by_embedding(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Document]:
        """Search documents by embedding similarity."""
        if not self.documents:
            return []
        
        similarities = []
        for doc in self.documents:
            if doc.embedding is not None:
                similarity = np.dot(query_embedding, doc.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc.embedding)
                )
                similarities.append((similarity, doc))
        
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # this is just for illustration purposes to show the top similarities
        print("🔍 Top similarities:")
        for i, (sim, doc) in enumerate(similarities[:5]):
            project = doc.metadata.get('project', 'Unknown')
            section = doc.metadata.get('section', 'Unknown')
            print(f"   {i+1}. {sim:.4f} - {project} → {section}")
        
        return [doc for _, doc in similarities[:top_k]]

class QuantumProjectsHyDEPlugin:
    """HyDE-enhanced plugin for searching quantum project information"""
    
    def __init__(self, hyde_store: HyDEVectorStore):
        self.hyde_store = hyde_store
    
    @kernel_function(description="Search quantum project information using HyDE (Hypothetical Document Embeddings) to answer questions about quantum research projects.")
    async def search_quantum_projects_hyde(
        self, 
        query: Annotated[str, "The search query about quantum projects"]
    ) -> Annotated[str, "Returns relevant information about quantum projects"]:
        """Search for quantum project information using HyDE document-to-document matching."""
        
        task_instruction = "Write a detailed scientific passage about specific quantum computing projects, including concrete details like project names, goals, technologies, budgets, timelines, and technical specifications. Focus on the specific details mentioned in the question. Use the same style and level of detail as the example provided."
        
        similar_docs = await self.hyde_store.search_with_hyde(
            query, 
            top_k=3, 
            task_instruction=task_instruction
        )
        
        if not similar_docs:
            return "No relevant quantum project information found."
        
        context = []
        for i, doc in enumerate(similar_docs):
            project = doc.metadata.get('project', 'Unknown Project')
            section = doc.metadata.get('section', 'Unknown Section')
            
            print(f"   {i+1}. Retrieved: {project} → {section}")
            context.append(f"From {project} - {section}:\n{doc.content}")
        
        return "\n\n---\n\n".join(context)

def load_and_chunk_projects_data(file_path: str) -> List[Document]:
    """Load the projects.md file and chunk it into documents"""
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    projects = content.split('# Project')[1:]
    
    documents = []
    for i, project in enumerate(projects):
        project_content = f"# Project{project}"
        
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

def save_hyde_index(hyde_store: HyDEVectorStore, file_path: str):
    """Save the document index (not the hypothetical documents)"""
    index_data = []
    for doc in hyde_store.documents:
        index_data.append({
            'id': doc.id,
            'content': doc.content,
            'metadata': doc.metadata,
            'embedding': doc.embedding.tolist() if doc.embedding is not None else None
        })
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    
    print(f"💾 Saved HyDE document index with {len(index_data)} documents to {file_path}")

def load_hyde_index(file_path: str) -> HyDEVectorStore:
    """Load the document index"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        hyde_store = HyDEVectorStore()
        
        for item in index_data:
            doc = Document(
                id=item['id'],
                content=item['content'],
                metadata=item['metadata'],
                embedding=np.array(item['embedding']) if item['embedding'] else None
            )
            hyde_store.documents.append(doc)
        
        print(f"📥 Loaded HyDE document index with {len(hyde_store.documents)} documents from {file_path}")
        return hyde_store
        
    except Exception as e:
        print(f"⚠️ Error loading HyDE index: {e}")
        return None

async def main():
    print("🚀 HyDE-Enhanced Quantum Projects RAG Demo")
    print("=" * 60)
    
    chat_completion_service = AzureChatCompletion(
        deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    )
    print("✅ Created chat completion service")
    
    embeddings_service = AzureTextEmbedding(
        deployment_name=os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    )
    print("✅ Created embeddings service")
    
    # initialize HyDE vector store
    hyde_store = HyDEVectorStore()
    hyde_store.set_services(embeddings_service, chat_completion_service)
    
    # load and process the demo data
    data_path = os.path.join(os.path.dirname(__file__), "..", "shared-data", "projects.md")
    print(f"\n📄 Loading quantum projects data from {data_path}")
    
    documents = load_and_chunk_projects_data(data_path)
    print(f"📚 Created {len(documents)} document chunks")
    
    # HyDE indexing is same as regular RAG indexing (only documents, not hypothetical docs!)
    print("\n🧠 Starting HyDE document indexing phase...")
    print("=" * 60)
    
    index_file_path = os.path.join(os.path.dirname(__file__), "data", "hyde_index.json")
    if os.path.exists(index_file_path):
        existing_hyde_store = load_hyde_index(index_file_path)
        if existing_hyde_store and existing_hyde_store.documents:
            hyde_store = existing_hyde_store
            hyde_store.set_services(embeddings_service, chat_completion_service)
            print("✅ Loaded existing HyDE document index")
        else:
            print("🔨 Creating new HyDE document index...")
            await hyde_store.add_documents(documents)
            save_hyde_index(hyde_store, index_file_path)
    else:
        print("🔨 Creating new HyDE document index...")
        await hyde_store.add_documents(documents)
        save_hyde_index(hyde_store, index_file_path)
    
    print("=" * 60)
    print("✅ HyDE document indexing complete!")
    
    # create the HyDE-enhanced quantum projects plugin
    quantum_plugin = QuantumProjectsHyDEPlugin(hyde_store)
    
    agent = ChatCompletionAgent(
        service=chat_completion_service,
        name="QuantumProjectsHyDEAgent",
        instructions="""You are a helpful assistant specializing in quantum research projects. 
        You have access to information about various quantum computing projects through HyDE (Hypothetical Document Embeddings).
        
        Use the search_quantum_projects_hyde function to find relevant information from the quantum projects database.
        This system uses advanced document-to-document matching via hypothetical document generation for improved retrieval accuracy.
        
        Always base your answers on the retrieved information and cite which projects the information comes from.
        If you can't find relevant information, say so clearly.""",
        plugins=[quantum_plugin],
    )
    print("✅ Created HyDE-Enhanced Quantum Projects Agent")
    
    # Test queries to demonstrate HyDE capabilities
    test_queries = [
        "What is Project Mousetrap and what are its goals?",
        "Which quantum projects have the largest budgets?",
        "Tell me about quantum key distribution research",
        "What are the timeline and milestones for quantum sensor development?",
    ]
    
    print("\n" + "="*80)
    print("🎯 HyDE RETRIEVAL DEMO - Document-to-Document Matching")
    print("="*80)
    
    thread = None
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"💬 Test Query {i}/{len(test_queries)}: {query}")
        print(f"{'='*60}")
        
        response = await agent.get_response(
            messages=query,
            thread=thread,
        )
        
        if response:
            print(f"\n🤖 Agent Response:\n{response}")
            thread = response.thread
        
        await asyncio.sleep(1)
    
    print(f"\n{'='*80}")
    print("💡 HyDE Summary:")
    print(f"📊 Generated {len(hyde_store.hypothetical_documents)} hypothetical documents during search")
    print(f"📄 Searched against {len(hyde_store.documents)} real document chunks")
    print("✨ HyDE enables zero-shot dense retrieval without relevance labels!")
    
    if thread:
        try:
            await thread.delete()
            print("✅ Thread deleted")
        except Exception as e:
            print(f"⚠️ Error deleting thread: {e}")

if __name__ == "__main__":
    asyncio.run(main())