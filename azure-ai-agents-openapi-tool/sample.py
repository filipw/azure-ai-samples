import os
import time
import json
import jsonref
import re
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import OpenApiTool, OpenApiAnonymousAuthDetails
from dotenv import load_dotenv

load_dotenv()

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(), conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
)

tunnel_url = os.environ.get("DEV_TUNNEL_URL")
if not tunnel_url:
    print("⚠️  Warning: DEV_TUNNEL_URL environment variable is not set")
    print("   Using {TUNNEL_URL} placeholder directly, which may cause issues")
    tunnel_url = "{TUNNEL_URL}"
else:
    print(f"🔗 Using tunnel URL: {tunnel_url}")

try:
    with open('./fastapi_swagger.json', 'r') as f:
        swagger_content = f.read()
        swagger_content = swagger_content.replace("{TUNNEL_URL}", tunnel_url)
        openapi_spec = jsonref.loads(swagger_content)
except FileNotFoundError:
    print("❌ Error: swagger.json file not found. Please ensure it exists in the current directory - ideally you run the sample from the azure-ai-agents-openapi-tool folder.")
    exit(1)

auth = OpenApiAnonymousAuthDetails()

openapi = OpenApiTool(name="WeatherForecastApi", spec=openapi_spec, description="Provides access to the weather forecast", auth=auth)

user_query = "Get me the weather forecast for Zurich"

with project_client:
    print("\n🤖 Initializing Weather Forecast Agent...")
    agent = project_client.agents.create_agent(
        model="gpt-4o-mini",
        name="weather-assistant",
        instructions="You are a helpful weather expert. Use the OpenAPI tool to provide weather forecasts.",
        tools=openapi.definitions
    )
    print(f"✅ Created agent, ID: {agent.id}")

    thread = project_client.agents.create_thread()
    print(f"📝 Created thread, ID: {thread.id}")

    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_query,
    )
    print(f"💬 User request: {user_query}")
    print(f"📤 Created message, ID: {message.id}")

    print("\n⏳ Processing request...")
    run = project_client.agents.create_run(thread_id=thread.id, agent_id=agent.id)
    print(f"🚀 Started agent run, ID: {run.id}")
    
    previous_status = None
    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1)
        run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
        
        if run.status != previous_status:
            print(f"⏳ Run status: {run.status}")
            previous_status = run.status
            
            if run.status == "requires_action":
                print("🛠️  Agent is making API requests...")

    print(f"\n✅ Run completed with final status: {run.status}")
    
    if run.status == "failed":
        print(f"❌ Run failed: {run.last_error}")

    project_client.agents.delete_agent(agent.id)
    print(f"🧹 Cleaned up: Agent deleted")

    print(f"\n💬 Conversation summary:")
    messages = project_client.agents.list_messages(thread_id=thread.id)
    
    for msg in reversed(messages.data):
        role_emoji = "🧑" if msg.role == "user" else "🤖"
        
        print(f"\n{role_emoji} {msg.role.upper()}:")
        
        if msg.content and len(msg.content) > 0 and hasattr(msg.content[0], 'text'):
            content = msg.content[0].text.value
            print(f"{content}")