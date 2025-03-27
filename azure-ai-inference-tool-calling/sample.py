import os
import json
import enum
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import (
    ChatCompletionsToolDefinition,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    FunctionDefinition
)
from azure.core.credentials import AzureKeyCredential

load_dotenv()

AZURE_AI_URL = os.environ["AZURE_AI_URL"]
AZURE_AI_KEY = os.environ["AZURE_AI_KEY"]

try:
    endpoint = os.environ["AZURE_AI_URL"]
    key = os.environ["AZURE_AI_KEY"]
except KeyError:
    print("Missing environment variables 'AZURE_AI_URL' or 'AZURE_AI_KEY'")
    raise SystemExit("Ensure these variables are set")

client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

class Location(enum.Enum):
    Zurich = "Zurich" 
    Basel = "Basel"
    Toronto = "Toronto"
    NewYork = "NewYork"

class Concert:
    def __init__(self, id: int, timestamp: datetime, band: str, location: Location, price: float, currency: str):
        self.id = id
        self.timestamp = timestamp
        self.band = band
        self.location = location
        self.price = price
        self.currency = currency
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "band": self.band,
            "location": self.location.value,
            "price": self.price,
            "currency": self.currency
        }

class ConcertApi:
    def __init__(self):
        self.concerts = [
            Concert(1, datetime(2025, 6, 11), "Iron Maiden", Location.Zurich, 150, "CHF"),
            Concert(2, datetime(2024, 6, 12), "Iron Maiden", Location.Basel, 135, "CHF"),
            Concert(3, datetime(2025, 8, 15), "Dropkick Murphys", Location.Toronto, 145, "CAD"),
            Concert(4, datetime(2026, 1, 11), "Green Day", Location.NewYork, 200, "USD"),
        ]

    def search_concerts(self, band: str, location: Location) -> str:
        matches = [
            concert.to_dict() for concert in self.concerts 
            if concert.band.lower() == band.lower() and concert.location == location
        ]
        return json.dumps(matches)

    def book_ticket(self, id: int) -> str:
        if not any(concert.id == id for concert in self.concerts):
            raise Exception("No such concert!")

        return "Success!"

class ToolResult:
    def __init__(self, output: str, back_to_model: bool = False, is_error: bool = False):
        self.output = output
        self.back_to_model = back_to_model
        self.is_error = is_error

class ExecutionHelper:
    def __init__(self, concert_api: ConcertApi):
        self.concert_api = concert_api

    def get_available_functions(self) -> List[FunctionDefinition]:
        return [
            FunctionDefinition(
                name="search_concerts",
                description="Searches for concerts by a specific band name and location. Returns a list of concerts, each one with its ID, date, band, location, ticket prices and currency.",
                parameters={
                    "type": "object",
                    "properties": {
                        "band": {"type": "string"},
                        "location": {
                            "type": "string",
                            "enum": ["Zurich", "Basel", "Toronto", "NewYork"]
                        },
                    },
                    "required": ["band", "location"]
                }
            ),
            FunctionDefinition(
                name="book_ticket",
                description="Books a concert ticket to a concert, using the concert's ID.",
                parameters={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                    },
                    "required": ["id"]
                }
            )
        ]

    def invoke_function(self, function_name: str, function_arguments: str) -> ToolResult:
        try:
            if function_name == "search_concerts":
                args = json.loads(function_arguments)
                location = Location(args["location"])
                band = args["band"]
                result = self.concert_api.search_concerts(band, location)
                return ToolResult(result, back_to_model=True)
            
            elif function_name == "book_ticket":
                args = json.loads(function_arguments)
                id = args["id"]
                self.concert_api.book_ticket(id)
                return ToolResult("Success!")
        
        except Exception as e:
            print(f"Error executing function: {e}")
            return ToolResult(None, is_error=True)
        
        return ToolResult(None, is_error=True)

def main():
    system_instructions = f"""
You are an AI assistant designed to support users in searching and booking concert tickets. Adhere to the following rules rigorously:

1.  **Direct Parameter Requirement:** 
When a user requests an action, directly related to the functions, you must never infer or generate parameter values, especially IDs, band names or locations on your own. 
If a parameter is needed for a function call and the user has not provided it, you must explicitly ask the user to provide this specific information.

2.  **Avoid Assumptions:** 
Do not make assumptions about parameter values. 
If the user's request lacks clarity or omits necessary details for function execution, you are required to ask follow-up questions to clarify parameter values.

3.  **User Clarification:** 
If a user's request is ambiguous or incomplete, you should not proceed with function invocation. 
Instead, ask for the missing information to ensure the function can be executed accurately and effectively.

4. **Grounding in Time:**
Today is {datetime.now().strftime("%B %d, %Y")}
Yesterday was {(datetime.now() - timedelta(days=1)).strftime("%B %d, %Y")}. You will correctly infer past dates.
Tomorrow will be {(datetime.now() + timedelta(days=1)).strftime("%B %d, %Y")}.
"""

    intro_message = "I'm a Concert Booking AI assistant! Ask me concerts and I can help you find them and book tickets!"
    print(f"🤖 {intro_message}")

    concert_api = ConcertApi()
    execution_helper = ExecutionHelper(concert_api)
    
    messages = [
        SystemMessage(system_instructions),
        AssistantMessage(intro_message)
    ]

    skip_user_prompt = False
    while True:
        if not skip_user_prompt:
            prompt = input("> ")
            messages.append(UserMessage(prompt))

        tools = [
            ChatCompletionsToolDefinition(function=function)
            for function in execution_helper.get_available_functions()
        ]

        response = client.complete(
            messages=messages,
            tools=tools,
            temperature=0,
            max_tokens=400
        )

        print("🤖 ", end="", flush=True)
        model_response = response.choices[0].message.content or ""
        print(model_response)
        
        if response.choices[0].message.tool_calls:
            assistant_message = response.choices[0].message
            messages.append(assistant_message)
            
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = tool_call.function.arguments
            
            print(f"I'm calling a function called {function_name} with arguments {function_args}... Stay tuned...")
            function_result = execution_helper.invoke_function(function_name, function_args)
            
            if function_result.output:
                # add tool message in response to the assistant message with tool_calls
                tool_message = ToolMessage(function_result.output, tool_call_id=tool_call.id)
                messages.append(tool_message)
                
                skip_user_prompt = function_result.back_to_model
                
                if not function_result.back_to_model:
                    print(function_result.output)
                
                continue
        else:
            # no tool calls, just a regular message
            assistant_message = AssistantMessage(model_response)
            messages.append(assistant_message)
            
        skip_user_prompt = False
        print()

if __name__ == "__main__":
    main()