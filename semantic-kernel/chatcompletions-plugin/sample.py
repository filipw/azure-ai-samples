import asyncio
import os
import sys

from dotenv import load_dotenv
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from shared_plugins import ConcertPlugin

load_dotenv()

async def main():
    concert_plugin = ConcertPlugin()
    
    agent = ChatCompletionAgent(
        service=AzureChatCompletion(
            deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        ),
        name="ConcertAgent",
        instructions="You are a helpful assistant that helps users find concerts and book tickets.",
        plugins=[concert_plugin],
    )
    print("✅ Created concert agent")
    
    thread = None
    
    user_input = "I want to book tickets for a Dropkick Murphys concert in Toronto"
    print(f"\n💬 User: {user_input}")
            
    response = await agent.get_response(
        messages=user_input,
        thread=thread,
    )
    print(f"\n🤖 Agent: {response}")
    thread = response.thread
            
    print("\n🧹 Cleaning up resources...")
    if thread:
        try:
            await thread.delete()
            print("✅ Thread deleted")
        except Exception as e:
            print(f"⚠️ Error deleting thread: {e}")

if __name__ == "__main__":
    asyncio.run(main())