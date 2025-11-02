import sys, os
import asyncio
from typing import Annotated

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from helpers import print_json
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from app_functions import search_concerts, book_ticket

load_dotenv()

async def main() -> None:
    print("\n🤖 Initializing Concert Booking Agent...")
    
    # Create agent with tools
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(credential=DefaultAzureCredential()),
        instructions="You are a helpful concert booking agent. Help users find and book tickets for concerts.",
        tools=[search_concerts, book_ticket],
    )
    
    print("✅ Created concert booking agent")
    
    # User query
    query = "I want to book tickets for a Dropkick Murphys concert in Toronto"
    print(f"💬 User request: {query}")
    print("\n⏳ Processing request...")
    
    # Run the agent
    result = await agent.run(query)
    
    print(f"\n🤖 Agent response:")
    print(f"{result}")
    
    print(f"\n✅ Concert booking interaction completed!")


if __name__ == "__main__":
    asyncio.run(main())