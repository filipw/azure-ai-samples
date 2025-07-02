# Sample demonstrating HyPE (Hypothetical Prompt Embeddings) with Semantic Kernel
#
# based on: 
# Vake, Domen and Vičič, Jernej and Tošić, Aleksandar, Bridging the Question-Answer Gap in Retrieval-Augmented Generation: Hypothetical Prompt Embeddings. Available at SSRN: https://ssrn.com/abstract=5139335 or http://dx.doi.org/10.2139/ssrn.5139335

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

@dataclass
class Document:
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: np.ndarray = None

@dataclass
class HypotheticalQuestion:
    question: str
    question_embedding: np.ndarray
    original_chunk_id: str
    original_chunk_content: str
    original_chunk_metadata: Dict[str, Any]

class HyPEVectorStore:
    def __init__(self):
        self.hypothetical_questions: List[HypotheticalQuestion] = []
        self.embeddings_service = None
        self.llm_service = None
    
    def set_services(self, embeddings_service, llm_service):
        self.embeddings_service = embeddings_service
        self.llm_service = llm_service
    
    async def generate_hypothetical_questions(self, chunk_content: str, chunk_metadata: Dict[str, Any]) -> List[str]:
        try:
            kernel = Kernel()
            kernel.add_service(self.llm_service)
            
            question_generator = kernel.add_function(
                plugin_name="HyPE",
                function_name="GenerateQuestions",
                prompt="""You are an expert at generating hypothetical questions from document content for information retrieval.

Analyze the following text and generate 3-5 essential questions that, when answered, would capture the main points and core meaning of the content.

These questions should:
- Be specific and detailed enough to retrieve this exact content
- Cover different aspects of the information presented  
- Be phrased as natural questions a user might ask
- Focus on key facts, numbers, goals, and important details
- Be the type of questions that would lead someone to search for this specific information

Text to analyze:
{{$chunk_content}}

Generate only the questions, one per line, without numbering or bullet points:""",
                template_format="semantic-kernel"
            )
            
            kernel_arguments = KernelArguments(chunk_content=chunk_content)
            response = await kernel.invoke(
                plugin_name="HyPE", 
                function_name="GenerateQuestions", 
                arguments=kernel_arguments
            )
            
            if not response or not str(response).strip():
                print(f"⚠️ Empty response from LLM for chunk {chunk_metadata.get('project', 'Unknown')}")
                return []
            
            questions_text = str(response).strip()
            questions = [q.strip() for q in questions_text.split('\n') if q.strip() and not q.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*', '•'))]
            
            # clean up any remaining numbering or formatting
            cleaned_questions = []
            for q in questions:
                q = q.strip()
                if q:
                    # remove common prefixes
                    for prefix in ['1. ', '2. ', '3. ', '4. ', '5. ', '- ', '* ', '• ']:
                        if q.startswith(prefix):
                            q = q[len(prefix):].strip()
                    
                    # only add if it's a "reasonable" question
                    if len(q) > 10 and '?' in q:
                        cleaned_questions.append(q)
            
            project = chunk_metadata.get('project', 'Unknown')
            section = chunk_metadata.get('section', 'Unknown')
            
            print(f"💡 Generated {len(cleaned_questions)} hypothetical questions for chunk: {project}/{section}")
            for i, q in enumerate(cleaned_questions[:3], 1):
                print(f"   {i}. {q[:80]}{'...' if len(q) > 80 else ''}")
            
            return cleaned_questions[:5]  # 5 questions max in this sample
            
        except Exception as e:
            print(f"⚠️ Error generating hypothetical questions: {e}")
            return []
    
    async def add_documents_with_hype(self, documents: List[Document]):
        print(f"\n🔬 Starting HyPE indexing for {len(documents)} document chunks...")
        
        for i, doc in enumerate(documents):
            print(f"\n📄 Processing chunk {i+1}/{len(documents)}: {doc.metadata.get('project', 'Unknown')}/{doc.metadata.get('section', 'Unknown')}")
            
            # generate hypothetical questions for this chunk
            questions = await self.generate_hypothetical_questions(doc.content, doc.metadata)
            
            if not questions:
                print(f"⚠️ No questions generated for chunk {doc.id}, skipping...")
                continue
            
            # create an embedding for each question
            print(f"🔮 Embedding {len(questions)} hypothetical questions...")
            question_texts = questions
            embeddings = await self.embeddings_service.generate_embeddings(question_texts)
            
            # store each question with its embedding and link to original content
            for question, embedding in zip(questions, embeddings):
                hyp_question = HypotheticalQuestion(
                    question=question,
                    question_embedding=np.array(embedding),
                    original_chunk_id=doc.id,
                    original_chunk_content=doc.content,
                    original_chunk_metadata=doc.metadata
                )
                self.hypothetical_questions.append(hyp_question)
        
        print(f"\n✅ HyPE indexing complete! Created {len(self.hypothetical_questions)} hypothetical question embeddings")
    
    def search_by_question_similarity(self, query_embedding: np.ndarray, top_k: int = 3) -> List[HypotheticalQuestion]:
        if not self.hypothetical_questions:
            return []
        
        similarities = []
        for hyp_q in self.hypothetical_questions:
            similarity = np.dot(query_embedding, hyp_q.question_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(hyp_q.question_embedding)
            )
            similarities.append((similarity, hyp_q))
        
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [hyp_q for _, hyp_q in similarities[:top_k]]

class QuantumProjectsHyPEPlugin:
    """HyPE-enhanced plugin for searching quantum project information"""
    
    def __init__(self, hype_store: HyPEVectorStore, embeddings_service):
        self.hype_store = hype_store
        self.embeddings_service = embeddings_service
    
    @kernel_function(description="Search quantum project information using HyPE (Hypothetical Prompt Embeddings) to answer questions about quantum research projects.")
    async def search_quantum_projects_hype(
        self, 
        query: Annotated[str, "The search query about quantum projects"]
    ) -> Annotated[str, "Returns relevant information about quantum projects"]:
        """Search for quantum project information using HyPE question-to-question matching."""
        
        print(f"\n🔍 HyPE Search: {query}")
        
        query_embeddings = await self.embeddings_service.generate_embeddings([query])
        query_embedding = np.array(query_embeddings[0])
        
        # find similar hypothetical questions
        similar_questions = self.hype_store.search_by_question_similarity(query_embedding, top_k=3)
        
        if not similar_questions:
            return "No relevant quantum project information found."
        
        # extract original chunks from matching questions
        context = []
        seen_chunks = set()  # avoid duplicate chunks
        
        print("🎯 Question-to-Question Matches Found:")
        for i, hyp_q in enumerate(similar_questions):
            chunk_id = hyp_q.original_chunk_id
            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                project = hyp_q.original_chunk_metadata.get('project', 'Unknown Project')
                section = hyp_q.original_chunk_metadata.get('section', 'Unknown Section')
                
                print(f"   {i+1}. Matched Question: \"{hyp_q.question[:100]}{'...' if len(hyp_q.question) > 100 else ''}\"")
                print(f"      From: {project} → {section}")
                
                context.append(f"From {project} - {section}:\n{hyp_q.original_chunk_content}")
        
        if not context:
            return "No relevant quantum project information found."
        
        result = "\n\n---\n\n".join(context)
        print(f"📊 Retrieved {len(context)} unique document chunks via HyPE")
        
        return result

def load_and_chunk_projects_data(file_path: str) -> List[Document]:
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

def save_hype_index(hype_store: HyPEVectorStore, file_path: str):
    index_data = []
    for hyp_q in hype_store.hypothetical_questions:
        index_data.append({
            'question': hyp_q.question,
            'question_embedding': hyp_q.question_embedding.tolist(),
            'original_chunk_id': hyp_q.original_chunk_id,
            'original_chunk_content': hyp_q.original_chunk_content,
            'original_chunk_metadata': hyp_q.original_chunk_metadata
        })
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    
    print(f"💾 Saved HyPE index with {len(index_data)} questions to {file_path}")

def load_hype_index(file_path: str) -> HyPEVectorStore:
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        hype_store = HyPEVectorStore()
        
        for item in index_data:
            hyp_q = HypotheticalQuestion(
                question=item['question'],
                question_embedding=np.array(item['question_embedding']),
                original_chunk_id=item['original_chunk_id'],
                original_chunk_content=item['original_chunk_content'],
                original_chunk_metadata=item['original_chunk_metadata']
            )
            hype_store.hypothetical_questions.append(hyp_q)
        
        print(f"📥 Loaded HyPE index with {len(hype_store.hypothetical_questions)} questions from {file_path}")
        return hype_store
        
    except Exception as e:
        print(f"⚠️ Error loading HyPE index: {e}")
        return None

async def main():
    print("🚀 HyPE-Enhanced Quantum Projects RAG Demo")
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
    
    # initialize HyPE vector store
    hype_store = HyPEVectorStore()
    hype_store.set_services(embeddings_service, chat_completion_service)
    
    # load and process the demo data
    data_path = os.path.join(os.path.dirname(__file__), "data", "projects.md")
    print(f"\n📄 Loading quantum projects data from {data_path}")
    
    documents = load_and_chunk_projects_data(data_path)
    print(f"📚 Created {len(documents)} document chunks")
    
    # HyPE INDEXING PHASE
    print("\n🧠 Starting HyPE indexing phase...")
    print("=" * 60)
    
    index_file_path = os.path.join(os.path.dirname(__file__), "data", "hype_index.json")
    if os.path.exists(index_file_path):
        existing_hype_store = load_hype_index(index_file_path)
        if existing_hype_store and existing_hype_store.hypothetical_questions:
            hype_store = existing_hype_store
            hype_store.set_services(embeddings_service, chat_completion_service)
            print("✅ Loaded existing HyPE index")
        else:
            print("🔨 Creating new HyPE index...")
            await hype_store.add_documents_with_hype(documents)
            save_hype_index(hype_store, index_file_path)
    else:
        print("🔨 Creating new HyPE index...")
        await hype_store.add_documents_with_hype(documents)
        save_hype_index(hype_store, index_file_path)
    
    print("=" * 60)
    print("✅ HyPE indexing complete!")
    
    # create the HyPE-enhanced quantum projects plugin
    quantum_plugin = QuantumProjectsHyPEPlugin(hype_store, embeddings_service)
    
    # create agent using the proper ChatCompletionAgent pattern like the reference sample
    agent = ChatCompletionAgent(
        service=chat_completion_service,
        name="QuantumProjectsHyPEAgent",
        instructions="""You are a helpful assistant specializing in quantum research projects. 
        You have access to information about various quantum computing projects through HyPE (Hypothetical Prompt Embeddings).
        
        Use the search_quantum_projects_hype function to find relevant information from the quantum projects database.
        This system uses advanced question-to-question matching for improved retrieval accuracy.
        
        Always base your answers on the retrieved information and cite which projects the information comes from.
        If you can't find relevant information, say so clearly.""",
        plugins=[quantum_plugin],
    )
    print("✅ Created HyPE-Enhanced Quantum Projects Agent")
    
    # test queries to demonstrate HyPE capabilities
    test_queries = [
        "What is Project Mousetrap and what are its goals?",
        "Which quantum projects have the largest budgets?",
        "Tell me about quantum key distribution research",
    ]
    
    print("\n" + "="*80)
    print("🎯 HyPE RETRIEVAL DEMO - Question-to-Question Matching")
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
    if thread:
        try:
            await thread.delete()
            print("✅ Thread deleted")
        except Exception as e:
            print(f"⚠️ Error deleting thread: {e}")

if __name__ == "__main__":
    asyncio.run(main())