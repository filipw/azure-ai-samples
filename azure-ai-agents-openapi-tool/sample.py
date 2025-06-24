import os
import time
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import OpenApiTool, OpenApiAnonymousAuthDetails
from dotenv import load_dotenv
import requests

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

# pre-fetch OpenAPI specification dynamically from the running server
try:
    openapi_url = f"{tunnel_url}/openapi.json"
    response = requests.get(openapi_url)
    if response.status_code == 200:
        openapi_spec = response.json()
        print(f"✅ Successfully fetched OpenAPI spec from {openapi_url}")
    else:
        raise Exception(f"Failed to fetch OpenAPI spec: HTTP {response.status_code}")
except Exception as e:
    print(f"❌ Error fetching OpenAPI spec from {openapi_url}: {e}")
    print(f"Make sure the FastAPI server is running and accessible at {tunnel_url}")
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
    print("🧹 Cleaned up: Agent deleted")
    print("\n💬 Conversation summary:")
    messages = project_client.agents.list_messages(thread_id=thread.id)
    
    for msg in reversed(messages.data):
        role_emoji = "🧑" if msg.role == "user" else "🤖"
        
        print(f"\n{role_emoji} {msg.role.upper()}:")
        
        if msg.content and len(msg.content) > 0 and hasattr(msg.content[0], 'text'):
            content = msg.content[0].text.value
            print(f"{content}")