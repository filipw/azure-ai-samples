import asyncio
import os
import sys

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from shared_plugins import ConcertPlugin

from semantic_kernel.agents import AzureAIAgent

load_dotenv()

async def main():
    concert_plugin = ConcertPlugin()
    
    async with DefaultAzureCredential() as creds:
        async with AzureAIAgent.create_client(
            credential=creds,
            conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
        ) as client:
            agent_definition = await client.agents.create_agent(
                model="gpt-4o-mini",
                name="ConcertAgent",
                instructions="You are a helpful assistant that helps users find concerts and book tickets."
            )
            
            agent = AzureAIAgent(
                client=client,
                definition=agent_definition,
                plugins=[concert_plugin],
            )
            print(f"✅ Created agent with ID: {agent.id}")
            
            thread = None
            
            user_input = "I want to book tickets for a Dropkick Murphys concert in Toronto"
            print(f"\n💬 User: {user_input}")
                    
            async for response in agent.invoke(
                messages=user_input,
                thread=thread,
            ):
                print(f"\n🤖 Agent: {response}")
                thread = response.thread
                        
            print("\n🧹 Cleaning up resources...")
            if thread:
                try:
                    await thread.delete()
                    print("✅ Thread deleted")
                except Exception as e:
                    print(f"⚠️ Error deleting thread: {e}")
            
            try:
                await client.agents.delete_agent(agent.id)
                print("✅ Agent deleted")
            except Exception as e:
                    print(f"⚠️ Error deleting agent: {e}")

if __name__ == "__main__":
    asyncio.run(main())