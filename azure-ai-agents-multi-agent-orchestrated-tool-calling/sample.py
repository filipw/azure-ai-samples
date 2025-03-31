import os, time, json, re
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


def print_json(json_obj):
    """Pretty print JSON data"""
    if isinstance(json_obj, str):
        try:
            json_obj = json.loads(json_obj)
        except:
            pass
    print(json.dumps(json_obj, indent=2))


def process_agent_run(project_client, thread_id, agent_id, message=None):
    """Process a run for an agent with the specified message"""
    # add a 25-second pause before every run to avoid rate limits in constrained quota environments
    print("⏱️ Pausing for 25 seconds to avoid rate limits...")
    time.sleep(25)
    
    if message:
        print(f"📄 Adding message for agent {agent_id}: {message}")
        # we can't set agent_id on the message creation directly so we will use a user message
        project_client.agents.create_message(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
    print(f"🚀 Starting run for agent {agent_id}")
    run = project_client.agents.create_run(thread_id=thread_id, agent_id=agent_id)
    print(f"✨ Created run with ID: {run.id}")
    
    # process the run and handle any tool calls
    run = process_run_with_tools(project_client, thread_id, run.id)
    print(f"🏁 Run {run.id} completed with status: {run.status}")
    
    return run


def process_run_with_tools(project_client, thread_id, run_id):
    """Process a run and handle any tool calls"""
    print(f"Processing run {run_id}")
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

                        # search concerts should be offloaded to the search concerts function
                        if function_name == "search_concerts":
                            output = search_concerts(**function_args)
                            print(
                                f"🔍 Searching for concerts by {function_args.get('band')} in {function_args.get('location')}"
                            )
                        # book tickets should be offloaded to the book ticket function
                        elif function_name == "book_ticket":
                            output = book_ticket(**function_args)
                            print(
                                f"🎫 Booking ticket for concert ID: {function_args.get('id')}"
                            )
                        # delegation tasks are added to the task queue for later execution
                        elif function_name == "create_task":
                            recipient = function_args.get("recipient")
                            request = function_args.get("request")
                            requestor = function_args.get("requestor")
                            
                            print(f"📋 Delegation request from {requestor} to {recipient}: {request}")
                            
                            # First finish this run normally
                            output = json.dumps({"success": True, "message": f"Task sent to {recipient}"})
                            
                            # Store the task for later execution after this run completes
                            add_task(recipient, request, requestor)
                            
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
                        tool_outputs.append(
                            ToolOutput(
                                tool_call_id=tool_call.id,
                                output=json.dumps({"error": str(e)}),
                            )
                        )

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


def print_conversation_summary(project_client, thread_id, agent_ids):
    """Print a summary of the conversation with proper agent attributions

    Args:
        project_client: The AI Project client
        thread_id: ID of the thread to summarize
        agent_ids: Dictionary mapping agent IDs to agent names
    """
    print(f"\n***********\n")
    print(f"\n💬 Conversation summary:")
    messages = project_client.agents.list_messages(thread_id=thread_id)

    for msg in reversed(messages.data):
        role_emoji = "🧑"
        role_name = msg.role.upper()
        
        # check if this message was generated by an agent
        if msg.agent_id and msg.agent_id in agent_ids:
            role_emoji = "🤖"
            role_name = f"{agent_ids[msg.agent_id]}"
        elif msg.role == "agent":
            role_emoji = "🤖"
        
        print(f"\n{role_emoji} {role_name}:")

        if msg.content and len(msg.content) > 0 and hasattr(msg.content[0], "text"):
            content = msg.content[0].text.value
            print(f"{content}")


tasks = []

def add_task(recipient, request, requestor):
    """Add a task to the task queue"""
    tasks.append({
        "recipient": recipient,
        "request": request,
        "requestor": requestor
    })
    print(f"📋 Task added: Recipient={recipient}, Requestor={requestor}, Request={request}")
    print(f"📊 Current task queue: {len(tasks)} tasks")


def create_task(recipient, request, requestor):
    """Function for agents to create tasks for other agents"""
    print(f"🔄 Creating task: {requestor} -> {recipient}: {request}")
    add_task(recipient, request, requestor)
    return json.dumps({"success": True})


project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"],
)

model = "gpt-4o-mini"
user_query = "I want to book tickets for a Dropkick Murphys concert in Toronto"

# we will track the agent IDs and names for cleanup and summary
agent_ids = {}

with project_client:
    print("\n🔍 Initializing Concert Search Agent...")
    search_functions = FunctionTool(functions={search_concerts})
    search_agent = project_client.agents.create_agent(
        model=model,
        name="concert-search-agent",
        instructions="""You are a specialized agent for finding concerts.
        
Help users find concerts by specific bands or artists in their preferred locations. 
When asked for concerts, always call the search_concerts function with the appropriate band name and location.
Provide detailed information about the concerts you find.""",
        tools=search_functions.definitions,
    )
    print(f"✅ Created search agent, ID: {search_agent.id}")
    agent_ids[search_agent.id] = "Concert Search Agent"
    
    print("\n🎫 Initializing Concert Booking Agent...")
    booking_functions = FunctionTool(functions={book_ticket})
    booking_agent = project_client.agents.create_agent(
        model=model,
        name="concert-booking-agent",
        instructions="""You are a specialized agent for booking concert tickets.
        
You'll receive concert information and help users complete their bookings.
When asked to book tickets, always call the book_ticket function with the appropriate concert ID.
After booking, confirm the details of the booking with the user.""",
        tools=booking_functions.definitions,
    )
    print(f"✅ Created booking agent, ID: {booking_agent.id}")
    agent_ids[booking_agent.id] = "Concert Booking Agent"
    
    # set up the orchestrator agent with delegation capabilities
    print("\n🎭 Initializing Orchestrator Agent...")
    orchestration_functions = FunctionTool(functions={create_task})
    
    orchestrator_agent = project_client.agents.create_agent(
        model="gpt-4o", # we use a "smarter" model for the orchestrator
        name="orchestrator-agent",
        instructions=f"""You are an orchestrator agent responsible for planning and coordinating specialized agents.

Your role:
1. Analyze the user's request to understand what they want
2. Break down the request into sequential tasks for specialized agents
3. Delegate tasks to the appropriate specialized agents using the create_task function
4. After all tasks are complete, provide a coherent final response to the user

Available specialized agents:
- concert-search-agent: Specialized in finding concerts for specific artists/bands in locations
- concert-booking-agent: Specialized in booking tickets for specific concerts

IMPORTANT - Task Sequence:
First, search for concerts: When a user asks for concert tickets, your first step should ALWAYS be to delegate to the concert-search-agent to find available concerts.

Only after receiving search results: After the search agent has completed its task and returned concert information, THEN delegate to the concert-booking-agent with the specific concert ID found.

DO NOT create a booking task until after you can see the search results.

Always use the create_task function to delegate work to the specialized agents.
DO NOT attempt to directly search for concerts or book tickets yourself as you do not have appropriate tools.
""",
        tools=orchestration_functions.definitions,
    )
    print(f"✅ Created orchestrator agent, ID: {orchestrator_agent.id}")
    agent_ids[orchestrator_agent.id] = "Orchestrator Agent"

    # set up our thread
    thread = project_client.agents.create_thread()
    print(f"📝 Created thread, ID: {thread.id}")

    # initial user query to the thread, which triggers our orchestrator agent 
    # and hopefully kicks off the autonomous orchestration process
    project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_query,
    )
    print(f"💬 User query: {user_query}")
    print("\n🎭 Starting orchestration...")
    
    # first let the orchestrator process the request and create tasks
    # this should now only create the search task
    process_agent_run(project_client, thread.id, orchestrator_agent.id)
    
    # process tasks until no more remain
    print(f"\n🔄 Starting task processing loop. Initial task count: {len(tasks)}")
    processed_tasks = []
    
    while tasks:
        task = tasks.pop(0)
        task_id = f"{task['requestor']}-{task['recipient']}-{task['request']}"
        
        if task_id in processed_tasks:
            print(f"⏭️ Skipping already processed task: {task_id[:50]}...")
            continue
            
        processed_tasks.append(task_id)
        recipient_name = task["recipient"]
        request = task["request"]
        requestor = task["requestor"]
        
        print(f"\n📋 Processing task from {requestor} to {recipient_name}: {request}")
        print(f"   Tasks remaining in queue: {len(tasks)}")
        
        agent_id = None
        if recipient_name == "concert-search-agent":
            agent_id = search_agent.id
            print(f"🔍 Delegating to search agent: {agent_id}")
        elif recipient_name == "concert-booking-agent":
            agent_id = booking_agent.id
            print(f"🎫 Delegating to booking agent: {agent_id}")
        elif recipient_name == "orchestrator-agent":
            agent_id = orchestrator_agent.id
            print(f"🎭 Delegating to orchestrator: {agent_id}")
        
        if agent_id:
            agent_result = process_agent_run(project_client, thread.id, agent_id, request)
            
            # after each task completes, let the orchestrator evaluate the situation
            # unless - of course - the task was already for the orchestrator
            if recipient_name != "orchestrator-agent" and agent_result and agent_result.status == "completed":
                print(f"\n🔄 Task completed by {recipient_name}. Notifying orchestrator for next steps.")
                
                process_agent_run(
                    project_client, 
                    thread.id, 
                    orchestrator_agent.id, 
                    f"The {recipient_name} has completed the task. Please review and determine next steps."
                )
        else:
            print(f"⚠️ Unknown recipient: {recipient_name}")
            
        print(f"\n📊 Current task queue status: {len(tasks)} tasks remaining")
    
    # add a final message triggering our orchestrator to summarize the conversation
    print("\n🏁 All tasks completed, requesting final summary...")
    process_agent_run(
        project_client, 
        thread.id, 
        orchestrator_agent.id,
        "Can you provide a final summary of the concert search and booking process?"
    )
    
    # print conversation summary
    print_conversation_summary(project_client, thread.id, agent_ids)

    # clean up our agents, thank you Azure!
    project_client.agents.delete_agent(search_agent.id)
    project_client.agents.delete_agent(booking_agent.id)
    project_client.agents.delete_agent(orchestrator_agent.id)
    print(f"\n🧹 Cleaned up: Agents deleted")