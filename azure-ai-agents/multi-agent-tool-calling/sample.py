import sys, os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from helpers import print_json

import time, json
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    FunctionTool,
    RequiredFunctionToolCall,
    SubmitToolOutputsAction,
    ToolOutput,
)
from dotenv import load_dotenv
from app_functions import *

load_dotenv()

def execute_run_with_tools(project_client, thread_id, run_id):
    """Execute a run and handle tool calling interactions"""
    run = project_client.agents.get_run(thread_id=thread_id, run_id=run_id)
    previous_status = None

    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1)
        run = project_client.agents.get_run(thread_id=thread_id, run_id=run_id)

        if run.status == "requires_action" and isinstance(
            run.required_action, SubmitToolOutputsAction
        ):
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            if not tool_calls:
                print("❌ No tool calls provided - cancelling run")
                project_client.agents.cancel_run(thread_id=thread_id, run_id=run_id)
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
                            print(
                                f"🔍 Searching for concerts by {function_args.get('band')} in {function_args.get('location')}"
                            )
                        elif function_name == "book_ticket":
                            output = book_ticket(**function_args)
                            print(
                                f"🎫 Booking ticket for concert ID: {function_args.get('id')}"
                            )
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
                    thread_id=thread_id, run_id=run_id, tool_outputs=tool_outputs
                )

        # only print status changes to avoid spamming the console
        if run.status != previous_status:
            print(f"⏳ Run status: {run.status}")
            previous_status = run.status

    return run


def print_conversation_summary(project_client, thread_id):
    """Print a summary of the conversation"""
    print(f"\n***********\n")
    print(f"\n💬 Conversation summary:")
    messages = project_client.agents.list_messages(thread_id=thread_id)

    for msg in reversed(messages.data):
        role_emoji = "🧑" if msg.role == "user" else "🤖"

        print(f"\n{role_emoji} {msg.role.upper()}:")

        if msg.content and len(msg.content) > 0 and hasattr(msg.content[0], "text"):
            content = msg.content[0].text.value
            print(f"{content}")

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"],
)

model = "gpt-4o-mini"
user_query = "I want to book tickets for a Dropkick Murphys concert in Toronto"

with project_client:
    # participant 1: Concert Search agent
    print("\n🔍 Initializing Concert Search Agent...")
    search_functions = FunctionTool(functions={search_concerts})
    search_agent = project_client.agents.create_agent(
        model=model,
        name="concert-search-agent",
        instructions="You are a specialized agent focused on finding concerts. Help users find concerts by specific bands or artists in their preferred locations. Your only task is to search for concerts and provide the information to the user or the booking agent.",
        tools=search_functions.definitions,
    )
    print(f"✅ Created search agent, ID: {search_agent.id}")
    # participant 2: Concert Booking agent
    print("\n🎫 Initializing Concert Booking Agent...")
    booking_functions = FunctionTool(functions={book_ticket})
    booking_agent = project_client.agents.create_agent(
        model=model,
        name="concert-booking-agent",
        instructions="You are a specialized agent focused on booking concert tickets. You'll receive concert information and help users complete their bookings. Your only task is to book tickets for concerts that the search agent has already found.",
        tools=booking_functions.definitions,
    )
    print(f"✅ Created booking agent, ID: {booking_agent.id}")

    thread = project_client.agents.create_thread()
    print(f"📝 Created thread, ID: {thread.id}")

    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=(user_query),
    )
    print(f"💬 User query: {user_query}")
    print(f"📤 Created message, ID: {message.id}")

    # 1. use search agent to find concerts
    print("\n🔍 Starting concert search with the search agent...")
    search_run = project_client.agents.create_run(
        thread_id=thread.id, agent_id=search_agent.id
    )
    print(f"🚀 Started search agent run, ID: {search_run.id}")

    search_run = execute_run_with_tools(project_client, thread.id, search_run.id)
    print(f"\n✅ Search agent completed with status: {search_run.status}")

    # 2. use booking agent to book a ticket
    print("\n🎫 Starting ticket booking with the booking agent...")
    booking_message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content="Please book a ticket for one of these concerts.",
    )

    print(f"📤 Created booking request message, ID: {booking_message.id}")
    booking_run = project_client.agents.create_run(
        thread_id=thread.id, agent_id=booking_agent.id
    )
    print(f"🚀 Started booking agent run, ID: {booking_run.id}")

    booking_run = execute_run_with_tools(project_client, thread.id, booking_run.id)
    print(f"\n✅ Booking agent completed with status: {booking_run.status}")

    # 3. print conversation summary
    print_conversation_summary(project_client, thread.id)

    project_client.agents.delete_agent(search_agent.id)
    project_client.agents.delete_agent(booking_agent.id)
    print(f"\n🧹 Cleaned up: Agents deleted")