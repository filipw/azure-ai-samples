import json
import time
from typing import Annotated

from semantic_kernel.functions import kernel_function

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