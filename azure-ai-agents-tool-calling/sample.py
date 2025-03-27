import os, time, json
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import FunctionTool, RequiredFunctionToolCall, SubmitToolOutputsAction, ToolOutput
from dotenv import load_dotenv
from app_functions import *

load_dotenv()

def print_json(json_obj):
    """Pretty print JSON data"""
    if isinstance(json_obj, str):
        try:
            json_obj = json.loads(json_obj)
        except:
            pass
    print(json.dumps(json_obj, indent=2))

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(), conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
)

with project_client:
    print("\n🤖 Initializing Concert Booking Agent...")
    functions = FunctionTool(functions=app_functions)
    
    agent = project_client.agents.create_agent(
        model="gpt-4o-mini",
        name="concert-booking-assistant",
        instructions="You are a helpful concert booking agent. Help users find and book tickets for concerts.",
        tools=functions.definitions,
    )
    print(f"✅ Created agent, ID: {agent.id}")

    thread = project_client.agents.create_thread()
    print(f"📝 Created thread, ID: {thread.id}")

    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content="I want to book tickets for a Dropkick Murphys concert in Toronto",
    )
    print(f"💬 User request: I want to book tickets for a Dropkick Murphys concert in Toronto")
    print(f"📤 Created message, ID: {message.id}")

    run = project_client.agents.create_run(thread_id=thread.id, agent_id=agent.id)
    print(f"🚀 Started agent run, ID: {run.id}")
    print("\n⏳ Processing request...")

    previous_status = None
    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1)
        run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)

        if run.status == "requires_action" and isinstance(run.required_action, SubmitToolOutputsAction):
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            if not tool_calls:
                print("❌ No tool calls provided - cancelling run")
                project_client.agents.cancel_run(thread_id=thread.id, run_id=run.id)
                break

            print("\n🛠️  Agent needs to use tools to complete the request")
            tool_outputs = []
            for tool_call in tool_calls:
                if isinstance(tool_call, RequiredFunctionToolCall):
                    try:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        print(f"⚙️  Executing function: {function_name}")
                        print("📥 Arguments:")
                        print_json(function_args)
                        
                        if function_name == "search_concerts":
                            output = search_concerts(**function_args)
                            print(f"🔍 Searching for concerts by {function_args.get('band')} in {function_args.get('location')}")
                        elif function_name == "book_ticket":
                            output = book_ticket(**function_args)
                            print(f"🎫 Booking ticket for concert ID: {function_args.get('id')}")
                        else:
                            raise ValueError(f"Unknown function: {function_name}")
                        
                        tool_outputs.append(
                            ToolOutput(
                                tool_call_id=tool_call.id,
                                output=output,
                            )
                        )
                        
                        print("✅ Function executed successfully")
                        print("📤 Result:")
                        print_json(output)
                        
                    except Exception as e:
                        print(f"❌ Error executing tool_call {tool_call.id}: {e}")

            if tool_outputs:
                print("⏳ Sending tool outputs back to agent...")
                project_client.agents.submit_tool_outputs_to_run(
                    thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
                )

        # only print status changes to avoid spamming the console
        if run.status != previous_status:
            print(f"⏳ Run status: {run.status}")
            previous_status = run.status

    print(f"\n✅ Run completed with final status: {run.status}")

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