import json, time
from typing import Any, Callable, Set, Annotated
from pydantic import Field

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

def search_concerts(
    band: Annotated[str, Field(description="Name of the band")],
    location: Annotated[str, Field(description="Location of the concert, one of ['Zurich', 'Basel', 'Toronto', 'NewYork']")]
) -> str:
    """Searches for concerts by a specific band name and location. Returns a list of concerts, each one with its ID, date, band, location, ticket prices and currency."""
    print(f"🔍 Searching for concerts by {band} in {location}")
    
    results = []
    for concert in CONCERT_DATA:
        if (band.lower() in concert["band"].lower() and
            location.lower() == concert["location"].lower()):
            results.append(concert)
    
    result = json.dumps({"concerts": results})
    print("📤 Search result:")
    print(json.dumps(json.loads(result), indent=2))
    return result

def book_ticket(
    id: Annotated[int, Field(description="ID of the concert")]
) -> str:
    """Books a concert ticket to a concert, using the concert's ID."""
    print(f"🎫 Booking ticket for concert ID: {id}")
    
    concert = next((c for c in CONCERT_DATA if c["id"] == id), None)
    
    if not concert:
        result = json.dumps({"error": "Concert not found"})
        print("❌ Concert not found")
        return result
    
    booking_id = f"BK-{id}-{int(time.time())}"
    confirmation = {
        "booking_id": booking_id,
        "concert_id": id,
        "concert_info": concert,
        "ticket_confirmed": True,
        "seat": f"GA{int(time.time()) % 100}",  # Generate a fake seat number
    }
    
    result = json.dumps({"confirmation": confirmation})
    print("✅ Ticket booked successfully:")
    print(json.dumps(json.loads(result), indent=2))
    return result

app_functions: Set[Callable[..., Any]] = {
    search_concerts,
    book_ticket
}