import sys
import os
import asyncio
import threading
import queue
import io
import contextlib
import importlib.util
import logging
import re
from typing import Sequence
from typing import Dict, List, Any
from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core import CancellationToken
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_ext.auth.azure import AzureTokenProvider
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Import mock APIs
from mock_app import CalendarAPI, ExpediaAPI, WalletAPI, ContactManagerAPI

# Set up logging - change level to INFO to reduce logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable autogen debug logs
logging.getLogger('autogen').setLevel(logging.WARNING)
logging.getLogger('azure').setLevel(logging.WARNING)

# Create queues for communication between the agent and the web app
input_request_queue = queue.Queue()  # Queue for sending input requests to the web UI
input_response_queue = queue.Queue()  # Queue for receiving responses from the web UI
agent_message_queue = queue.Queue()  # Queue for sending agent messages to the web UI

# Global variable to store the current user input
current_user_input = ""

# Mock policy system
class MockPolicySystem:
    def __init__(self):
        self.policies = []
        logger.info("Mock policy system initialized")
    
    def add_policy(self, policy):
        self.policies.append(policy)
        logger.info(f"Added policy: {policy}")
    
    def reset(self):
        self.policies = []
        logger.info("Policy system reset")
    
    def enable(self):
        logger.info("Policy system enabled")
    
    def disable(self):
        logger.info("Policy system disabled")
    
    def text(self):
        return "Mock policy system text"
    
    def ask(self):
        logger.info("Policy system ask called")
        return True

# Create a mock policy system
policy_system = MockPolicySystem()

def setup_model_client():
    """Set up the model client for autogen"""
    logger.info("Setting up model client")
    load_dotenv()
    
    # Try OpenAI configuration first
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        logger.info("Using OpenAI configuration")
        return OpenAIChatCompletionClient(
            model="gpt-4",
            api_key=openai_api_key
        )
    else:
        # Fallback to Azure OpenAI
        logger.info("Using Azure OpenAI configuration")
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        scope = os.getenv('AZURE_OPENAI_TOKEN_SCOPES')
        deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        
        if not all([endpoint, api_version, scope, deployment]):
            logger.error("Missing required Azure OpenAI configuration")
            logger.error(f"endpoint: {endpoint}")
            logger.error(f"api_version: {api_version}")
            logger.error(f"scope: {scope}")
            logger.error(f"deployment: {deployment}")
            raise ValueError("Missing required Azure OpenAI configuration")
        
        # Use the Azure OpenAI client with Azure AD authentication
        scope = "api://trapi/.default"
        credential = get_bearer_token_provider(ChainedTokenCredential(
            AzureCliCredential(),
            DefaultAzureCredential(
                exclude_cli_credential=True,
                # Exclude other credentials we are not interested in.
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_developer_cli_credential=True,
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_visual_studio_code_credentials=True,
                # DEFAULT_IDENTITY_CLIENT_ID is a variable exposed in
                # Azure ML Compute jobs that has the client id of the
                # user-assigned managed identity in it.
                managed_identity_client_id=os.environ.get("DEFAULT_IDENTITY_CLIENT_ID"),
            )
        ), scope)

        api_version = '2024-10-21' 
        model_name = 'gpt-4o'
        model_version = '2024-11-20'
        deployment_name = re.sub(r'[^a-zA-Z0-9-_]', '', f'{model_name}_{model_version}') 
        instance = 'redmond/interactive'
        endpoint = f'https://trapi.research.microsoft.com/{instance}'

        # Define model info for the custom model
        model_info = {
            "context_length": 128000,
            "max_tokens": 4096,
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
            "model_type": "chat",
            "supports_functions": True,
            "supports_vision": False,
            "supports_streaming": True,
            "vision": False,
            "json_output": True,
            "function_calling": True
        }

        # Create the Azure OpenAI client using autogen's AzureOpenAIChatCompletionClient
        return AzureOpenAIChatCompletionClient(
            model=deployment_name,
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_ad_token_provider=credential,
            model_info=model_info
        )

def web_input_func(prompt: str) -> str:
    """Function to handle web input"""
    global current_user_input
    logger.info(f"Web input function called with prompt: {prompt}")
    
    # Put the prompt in the input request queue
    input_request_queue.put(prompt)
    logger.info(f"Added prompt to input request queue: {prompt}")
    
    # Wait for a response from the web UI
    try:
        # Wait for up to 30 seconds for a response
        response = input_response_queue.get(timeout=30)
        logger.info(f"Received response from web UI: {response}")
        return response
    except queue.Empty:
        logger.warning("Timeout waiting for user input, using default response")
        return "No response received. Please try again."

def get_next_input_request():
    """Get the next input request from the queue"""
    try:
        return input_request_queue.get_nowait()
    except queue.Empty:
        return None

def submit_user_input(user_input: str):
    """Submit user input to the agent"""
    logger.info(f"Submitting user input: {user_input}")
    input_response_queue.put(user_input)

def get_next_agent_message():
    """Get the next agent message from the queue"""
    try:
        return agent_message_queue.get_nowait()
    except queue.Empty:
        return None

def selector_exp(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
    """Selector function for the group chat"""
    if len(messages) == 0:
        logger.info("No messages, returning User")
        return "User"
    
    last_message = messages[-1]
    
    # Handle different message types
    try:
        if isinstance(last_message, dict):
            source = last_message.get('source', 'Unknown')
            content = last_message.get('content', '')
        else:
            # For TaskResult objects or other types
            source = getattr(last_message, 'source', 'Unknown')
            content = getattr(last_message, 'content', str(last_message))
        
        if source == "User":
            logger.info("Last message from User, returning Planner")
            return "Planner"
        
        if source == "Planner":
            # Clean up markdown formatting
            content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
            
            # Extract the next agent from the content
            # Look for "Next Agent: [AgentName]" pattern
            next_agent_match = re.search(r'Next Agent:\s*([^\n]+)', content)
            if next_agent_match:
                next_agent = next_agent_match.group(1).strip()
                logger.info(f"Last message from Planner, next agent: {next_agent}")
                return next_agent if next_agent != "terminate" else "Planner"
            
            # Look for "Agent: [AgentName]" pattern (alternative format)
            agent_match = re.search(r'Agent:\s*([^\n]+)', content)
            if agent_match:
                next_agent = agent_match.group(1).strip()
                logger.info(f"Last message from Planner, next agent: {next_agent}")
                return next_agent if next_agent != "terminate" else "Planner"
            
            # Fallback to the old method
            next_agent = content.split(":")[0]
            logger.info(f"Last message from Planner, next agent: {next_agent}")
            return next_agent if next_agent != "terminate" else "Planner"
        
        if content.lower() == "done":
            logger.info("Message content is 'done', returning Planner")
            return "Planner"
        elif content.lower().startswith("user"):
            logger.info("Message content starts with 'user', returning User")
            return "User"
        elif content.lower().startswith("data"):
            logger.info("Message content starts with 'data', returning Planner")
            return "Planner"
        elif source == "Agent":
            # If the message is from an Agent, return the appropriate specialized agent
            # Extract the agent name from the content
            agent_match = re.search(r'Agent:\s*([^\n]+)', content)
            if agent_match:
                agent_name = agent_match.group(1).strip()
                logger.info(f"Last message from Agent, returning specialized agent: {agent_name}")
                return agent_name
            else:
                logger.info("Last message from Agent, returning Planner")
                return "Planner"
        
        logger.info(f"Default case, returning {source}")
        return source
    except Exception as e:
        logger.error(f"Error in selector_exp: {str(e)}", exc_info=True)
        return "Planner"  # Default to Planner on error

async def run_agent_with_input(user_input: str) -> str:
    """Run the agent with the given user input"""
    logger.info(f"Running agent with input: {user_input}")
    global current_user_input
    current_user_input = user_input
    
    try:
        # Set up model client
        logger.info("Setting up model client")
        model_client = setup_model_client()
        
        # Create agents
        logger.info("Creating agents")
        def get_user_message(prompt: str) -> str:
            return user_input
            
        user = UserProxyAgent("User", input_func=get_user_message)
        planner = AssistantAgent(
            name="Planner",
            system_message="""You are a planner agent that coordinates between different specialized agents.
            Your role is to understand the user's request and delegate tasks to the appropriate agent.
            Always return the name of the next agent to handle the request, followed by a description of what needs to be done.
            
            IMPORTANT: Do NOT use markdown formatting (like ** or __) in your responses.
            Format your response exactly like this:
            Next Agent: [AgentName]
            Task: [Description of the task]
            
            For example:
            Next Agent: Expedia
            Task: Help the user book a flight ticket from Seattle (SEA) to Salt Lake City (SLC), ensuring the best available options for their travel needs.""",
            model_client=model_client
        )
        
        # Create specialized agents
        logger.info("Creating specialized agents")
        calendar = AssistantAgent(
            name="Calendar",
            system_message="""You are a calendar agent that can reserve, check availability, and read calendar data.
            Use the tools available to you to fulfill the request.
            Return "done" when the task given to you is completed.""",
            model_client=model_client
        )
        
        wallet = AssistantAgent(
            name="Wallet",
            system_message="""You are a wallet agent that can add, remove, update, and get credit card information.
            Use the tools available to you to fulfill the request.
            Return "done" when the task given to you is completed.""",
            model_client=model_client
        )
        
        expedia = AssistantAgent(
            name="Expedia",
            system_message="""You are a travel booking agent that can search and book flights, hotels, rental cars, and experiences.
            Use the tools available to you to fulfill the request.
            Return "done" when the task given to you is completed.""",
            model_client=model_client
        )
        
        contact_manager = AssistantAgent(
            name="ContactManager",
            system_message="""You are a contact manager agent that can add, remove, update, and get contact information.
            Use the tools available to you to fulfill the request.
            Return "done" when the task given to you is completed.""",
            model_client=model_client
        )
        
        # Set up termination condition
        logger.info("Setting up termination condition")
        termination = TextMentionTermination("terminate") | TextMentionTermination("perm_err") | TextMentionTermination("error")
        
        # Create group chat
        logger.info("Creating group chat")
        agents = [user, planner, calendar, wallet, expedia, contact_manager]
        group_chat = SelectorGroupChat(
            agents,
            max_turns=5,
            termination_condition=termination,
            model_client=model_client,
            selector_func=selector_exp
        )
        
        # Run the chat
        logger.info("Running chat")
        responses = []
        termination_reason = "Conversation completed"
        
        async for message in group_chat.run_stream():
            try:
                # Handle different message types
                if hasattr(message, 'source') and hasattr(message, 'content'):
                    source = message.source
                    content = message.content
                elif isinstance(message, dict):
                    source = message.get('source', 'Unknown')
                    content = message.get('content', '')
                else:
                    # For TaskResult objects or other types
                    source = getattr(message, 'source', 'Unknown')
                    content = getattr(message, 'content', str(message))
                
                logger.info(f"Received message: {source}: {content}")
                
                # Check for termination reason
                if source == "Group chat manager" and "Maximum number of turns" in content:
                    termination_reason = "Maximum number of turns reached"
                elif "Maximum number of turns" in content:
                    termination_reason = "Maximum number of turns reached"
                elif "terminate" in content.lower():
                    termination_reason = "Agent requested termination"
                elif "error" in content.lower():
                    termination_reason = "An error occurred"
                
                # Skip TaskResult messages that contain all previous messages
                if source == "Unknown" and "TaskResult" in str(message) and "messages=" in str(message):
                    logger.info("Skipping concatenated TaskResult message")
                    continue
                
                # Skip user messages to prevent duplication
                if source == "User":
                    logger.info("Skipping user message to prevent duplication")
                    continue
                
                # Format the message for display
                formatted_message = ""
                
                if source == "Planner":
                    # Clean up markdown formatting
                    content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                    
                    # Extract the task description
                    task_match = re.search(r'Task:\s*([^\n]+)', content)
                    if task_match:
                        task = task_match.group(1).strip()
                        formatted_message = f"{source}: {task}"
                    else:
                        # Look for Description: pattern
                        desc_match = re.search(r'Description:\s*([^\n]+)', content)
                        if desc_match:
                            desc = desc_match.group(1).strip()
                            formatted_message = f"{source}: {desc}"
                        else:
                            formatted_message = f"{source}: {content}"
                elif source == "User":
                    # Skip user messages to prevent duplication
                    continue
                elif source == "Agent":
                    # Handle messages from the Agent source
                    # Clean up markdown formatting
                    content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                    
                    # Extract the task description if available
                    task_match = re.search(r'Task:\s*([^\n]+)', content)
                    if task_match:
                        task = task_match.group(1).strip()
                        formatted_message = f"Agent: {task}"
                    else:
                        # Look for Description: pattern
                        desc_match = re.search(r'Description:\s*([^\n]+)', content)
                        if desc_match:
                            desc = desc_match.group(1).strip()
                            formatted_message = f"Agent: {desc}"
                        else:
                            formatted_message = f"Agent: {content}"
                elif source == "Expedia" or source == "Calendar" or source == "Wallet" or source == "ContactManager":
                    # Handle messages from specialized agents
                    # Clean up markdown formatting
                    content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                    formatted_message = f"{source}: {content}"
                else:
                    # Handle messages from other sources
                    # Clean up markdown formatting
                    content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                    formatted_message = f"{source}: {content}"
                
                # Add the formatted message to the responses
                if formatted_message:
                    responses.append(formatted_message)
                    
                    # Put the formatted message in the agent message queue
                    agent_message_queue.put(formatted_message)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                responses.append(f"Error: {str(e)}")
        
        logger.info(f"Chat completed with {len(responses)} responses")
        
        # Return the termination reason
        return f"Termination reason: {termination_reason}"
    except Exception as e:
        logger.error(f"Error in run_agent_with_input: {str(e)}", exc_info=True)
        # Return a fallback response
        return f"Assistant: I apologize, but I encountered an error while processing your request: {str(e)}. This might be due to API connectivity issues. Please try again later or contact support if the problem persists."

def run_agent_sync(user_input: str) -> str:
    """Synchronous wrapper for running the agent"""
    logger.info(f"Running agent synchronously with input: {user_input}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_agent_with_input(user_input))
        logger.info(f"Agent run completed with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}", exc_info=True)
        # Return a fallback response
        return f"Assistant: I apologize, but I encountered an error while processing your request: {str(e)}. This might be due to API connectivity issues. Please try again later or contact support if the problem persists."
    finally:
        loop.close()

# Example usage
if __name__ == "__main__":
    # Test the wrapper
    response = run_agent_sync("Hello, agent!")
    print("Agent response:", response) 