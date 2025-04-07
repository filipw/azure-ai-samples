import asyncio
import json
import os
import time
from typing import Annotated

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from semantic_kernel.agents import AzureAIAgent
from semantic_kernel.functions import kernel_function

load_dotenv()

class ConcertPlugin:
    CONCERT_DATA = [
        {
            "id": 123,
            "date": "2025-12-15",
            "band": "Dropkick Murphys",
            "location": "Toronto",
            "venue": "Scotiabank Arena",
            "ticket_prices": 145,
            "currency": "CAD"
        },
        {
            "id": 124,
            "date": "2025-12-20",
            "band": "Green Day",
            "location": "Toronto",
            "venue": "Rogers Centre",
            "ticket_prices": 140,
            "currency": "CAD"
        },
        {
            "id": 125,
            "date": "2026-01-15",
            "band": "Dropkick Murphys",
            "location": "Zurich",
            "venue": "Hallenstadion",
            "ticket_prices": 60,
            "currency": "CHF"
        }
    ]

    @kernel_function(description="Search for concerts by band name and location.")
    def search_concerts(
        self, 
        band: Annotated[str, "The name of the band or artist"],
        location: Annotated[str, "The city or location of the concert"]
    ) -> Annotated[str, "Returns JSON with concert search results"]:
        """Search for concerts by band name and location."""
        print(f"🔍 Searching for concerts by {band} in {location}")

        results = []
        for concert in self.CONCERT_DATA:
            if (band.lower() in concert["band"].lower() and
                location.lower() == concert["location"].lower()):
                results.append(concert)

        print(f"🎤 Found {len(results)} concerts for {band} in {location}")
        return json.dumps({"concerts": results})

    @kernel_function(description="Book tickets for a specific concert.")
    def book_ticket(
        self, 
        id: Annotated[int, "The concert ID"]
    ) -> Annotated[str, "Returns JSON with booking confirmation"]:
        """Book tickets for a specific concert."""

        print(f"🎫 Booking tickets for concert ID: {id}")
    
        concert = next((c for c in self.CONCERT_DATA if c["id"] == id), None)
        
        if not concert:
            return json.dumps({"error": "Concert not found"})
        
        booking_id = f"BK-{id}-{int(time.time())}"
        confirmation = {
            "booking_id": booking_id,
            "concert_id": id,
            "concert_info": concert,
            "ticket_confirmed": True,
            "seat": f"GA{int(time.time()) % 100}",  # Generate a fake seat number
        }

        print(f"✅ Booking confirmed! Booking ID: {booking_id}")
        
        return json.dumps({"confirmation": confirmation})

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