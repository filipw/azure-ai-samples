# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
import sys
import requests
from typing import Any, Dict

from dotenv import load_dotenv
from agent_framework.azure import AzureAIAgentClient
from azure.ai.agents.models import OpenApiAnonymousAuthDetails, OpenApiTool
from azure.identity.aio import AzureCliCredential

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

"""
Azure AI Agent with OpenAPI Tool Example

This sample demonstrates OpenAPI tool integration with Azure AI Agent Framework,
showing how to create an agent that can call external APIs through OpenAPI specifications.
"""


def load_openapi_spec_from_server(tunnel_url: str) -> Dict[str, Any]:
    """Load OpenAPI specification from the running FastAPI server via tunnel."""
    openapi_url = f"{tunnel_url}/openapi.json"
    
    try:
        response = requests.get(openapi_url)
        if response.status_code == 200:
            openapi_dict = response.json()
            print(f"✅ Successfully fetched OpenAPI spec from {openapi_url}")
            return openapi_dict
        else:
            raise Exception(f"Failed to fetch OpenAPI spec: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching OpenAPI spec from {openapi_url}: {e}")
        print(f"Make sure the FastAPI server is running and accessible at {tunnel_url}")
        raise


async def main() -> None:
    """Main function demonstrating Azure AI agent with OpenAPI tools."""
    print("\n🤖 Initializing Weather Forecast Agent...")
    
    tunnel_url = os.environ.get("DEV_TUNNEL_URL")
    if not tunnel_url:
        print("⚠️  Error: DEV_TUNNEL_URL environment variable is not set")
        print("   Please set DEV_TUNNEL_URL to your tunnel endpoint")
        return
    else:
        print(f"🔗 Using tunnel URL: {tunnel_url}")
    
    weather_openapi_spec = load_openapi_spec_from_server(tunnel_url)
    print(f"📋 Available endpoints: {list(weather_openapi_spec.get('paths', {}).keys())}")
    
    auth = OpenApiAnonymousAuthDetails()
    
    openapi_weather = OpenApiTool(
        name="WeatherForecastApi",
        spec=weather_openapi_spec,
        description="Provides access to the weather forecast",
        auth=auth,
    )
    print("✅ Created OpenAPI weather tool")
    
    async with (
        AzureCliCredential() as credential,
        AzureAIAgentClient(async_credential=credential).create_agent(
            name="WeatherAgent",
            instructions=(
                "You are a helpful weather expert. Use the OpenAPI tool to provide weather forecasts. "
                "When asked about weather, use the WeatherForecastApi tool to get the 5-day forecast. "
                "Provide clear, informative answers based on the API results."
            ),
            tools=openapi_weather.definitions,
        ) as agent,
    ):
        print("✅ Created weather forecast agent with OpenAPI tool")
        
        user_input = "Get me the weather forecast for Zurich"
        print(f"\n💬 User: {user_input}")
        response = await agent.run(user_input)
        print(f"🤖 Agent: {response.text}")
        
        print(f"\n✅ Weather forecast interaction completed!")


if __name__ == "__main__":
    asyncio.run(main())