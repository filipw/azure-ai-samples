import asyncio
import os
import sys

from dotenv import load_dotenv
import json
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    swagger_path = os.path.join(current_dir, "fastapi_swagger.json")
    
    kernel = Kernel()
    
    # assuming you already run the FastAPI server on localhost:5270
    api_host = os.environ.get("API_HOST", "http://localhost:5270")
    with open(swagger_path, 'r') as file:
        swagger_content = file.read().replace("{TUNNEL_URL}", api_host)
    
    swagger_dict = json.loads(swagger_content)

    # add the plugin to the kernel
    weather_plugin = kernel.add_plugin_from_openapi(
        plugin_name="WeatherPlugin",
        openapi_parsed_spec=swagger_dict
    )
    print("✅ Created OpenAPI plugin")
    
    # now set up an agent that uses the plugin
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