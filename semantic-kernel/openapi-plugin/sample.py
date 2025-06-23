import asyncio
import os
import sys
import requests

from dotenv import load_dotenv
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

async def main():
    kernel = Kernel()
    
    api_host = os.environ.get("API_HOST", "http://localhost:5270")
    openapi_url = f"{api_host}/openapi.json"
    
    # option 1: pre-fetch OpenAPI specification dynamically from the running server
    # try:
    #     response = requests.get(openapi_url)
    #     if response.status_code == 200:
    #         swagger_dict = response.json()
    #         print(f"✅ Successfully fetched OpenAPI spec from {openapi_url}")
    #     else:
    #         raise Exception(f"Failed to fetch OpenAPI spec: HTTP {response.status_code}")
    # except Exception as e:
    #     print(f"❌ Error fetching OpenAPI spec from {openapi_url}: {e}")
    #     print(f"Make sure the FastAPI server is running on {api_host}")
    #     return

    # # add the plugin to the kernel
    # weather_plugin = kernel.add_plugin_from_openapi(
    #     plugin_name="WeatherPlugin",
    #     openapi_parsed_spec=swagger_dict
    # )
    # print("✅ Created OpenAPI plugin")

    # option 2: create a plugin from a URL directly
    weather_plugin = kernel.add_plugin_from_openapi(
        plugin_name="WeatherPlugin",
        openapi_document_path=openapi_url,
    )
    print("✅ Created OpenAPI plugin from URL")
    
    # set up an agent that uses the plugin
    agent = ChatCompletionAgent(
        service=AzureChatCompletion(
            deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        ),
        name="WeatherAgent",
        instructions="You are a helpful assistant that provides weather forecasts using the OpenAPI plugin.",
        plugins=[weather_plugin]
    )
    print("✅ Created weather forecast agent with plugin")
    
    thread = None
    
    user_input = "What's the weather forecast for today?"
    print(f"\n💬 User: {user_input}")
            
    response = await agent.get_response(
        messages=user_input,
        thread=thread,
    )
    print(f"\n🤖 Agent: {response}")
    thread = response.thread
    
    user_input = "Will it be cold tomorrow?"
    print(f"\n💬 User: {user_input}")
    
    response = await agent.get_response(
        messages=user_input,
        thread=thread,
    )
    print(f"\n🤖 Agent: {response}")
            
    print("\n🧹 Cleaning up resources...")
    if thread:
        try:
            await thread.delete()
            print("✅ Thread deleted")
        except Exception as e:
            print(f"⚠️ Error deleting thread: {e}")

if __name__ == "__main__":
    asyncio.run(main())