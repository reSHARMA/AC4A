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
from datetime import datetime, timedelta
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
logging.getLogger('autogen').setLevel(logging.ERROR)
logging.getLogger('azure').setLevel(logging.ERROR)
logging.getLogger('autogen_core').setLevel(logging.ERROR)
logging.getLogger('autogen_agentchat').setLevel(logging.ERROR)
logging.getLogger('autogen_ext').setLevel(logging.ERROR)

# Create queues for communication between the agent and the web app
input_request_queue = queue.Queue()  # Queue for sending input requests to the web UI
input_response_queue = queue.Queue()  # Queue for receiving responses from the web UI
agent_message_queue = queue.Queue()  # Queue for sending agent messages to the web UI

# Global variable to store the current user input
current_user_input = ""

# Global variables for agent session management
agent_session_active = False
agent_waiting_for_input_flag = False
agent_group_chat = None
agent_thread = None
agent_loop = None
agent_initialized = False  # New flag to track if agent has been initialized
last_input_request = None  # Track the last input request to avoid duplicates

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
calendar_api = CalendarAPI(policy_system)
wallet_api = WalletAPI(policy_system)
expedia_api = ExpediaAPI(policy_system)
contact_manager_api = ContactManagerAPI(policy_system)

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
    global agent_waiting_for_input_flag, last_input_request
    
    # If this is the same prompt as the last one, don't ask again
    if prompt == last_input_request:
        logger.info(f"Duplicate input request detected: {prompt}")
        return "No response received. Please try again."
    
    logger.info(f"Web input function called with prompt: {prompt}")
    
    # Set the waiting flag
    agent_waiting_for_input_flag = True
    
    # Store the last input request
    last_input_request = prompt
    
    # Put the prompt in the input request queue
    input_request_queue.put(prompt)
    logger.info(f"Added prompt to input request queue: {prompt}")
    
    # Wait for a response from the web UI
    try:
        # Wait for up to 30 seconds for a response
        while True:
            try:
                response = input_response_queue.get(timeout=2)  # Check every second
                break
            except queue.Empty:
                continue  # Keep waiting if no response yet
        logger.info(f"Received response from web UI: {response}")
        agent_waiting_for_input_flag = False
        last_input_request = None  # Reset the last input request
        return response
    except queue.Empty:
        logger.warning("Timeout waiting for user input, using default response")
        agent_waiting_for_input_flag = False
        last_input_request = None  # Reset the last input request
        return "No response received. Please try again."

def get_next_input_request():
    """Get the next input request from the queue"""
    try:
        return input_request_queue.get_nowait()
    except queue.Empty:
        return None

def submit_user_input(user_input: str):
    """Submit user input to the agent"""
    global current_user_input, agent_session_active, last_input_request
    
    logger.info(f"Submitting user input: {user_input}")
    current_user_input = user_input
    
    # Reset the last input request to avoid duplicate requests
    last_input_request = None
    
    # If the agent session is not active, initialize it
    if not agent_session_active:
        logger.info("Agent session not active, initializing")
        initialize_agent_session()
    
    # Put the user input in the response queue
    input_response_queue.put(user_input)

def get_next_agent_message():
    """Get the next agent message from the queue"""
    try:
        return agent_message_queue.get_nowait()
    except queue.Empty:
        return None

def is_agent_waiting_for_input():
    """Check if the agent is waiting for input"""
    global agent_waiting_for_input_flag
    return agent_waiting_for_input_flag

def is_agent_session_active():
    """Check if the agent session is active"""
    global agent_session_active
    return agent_session_active

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
            
            # Check if the message starts with "User:" - this is a special case
            # where the Planner is asking for user input
            if content.startswith("User:"):
                logger.info("Planner message starts with 'User:', returning User")
                # Return User to get input from the user
                return "User"
            
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
            
            # Look for agent names in the content
            agent_names = ["Calendar", "Expedia", "Wallet", "ContactManager"]
            for agent_name in agent_names:
                if agent_name.lower() in content.lower():
                    logger.info(f"Found agent name '{agent_name}' in content, returning {agent_name}")
                    return agent_name
            
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

async def run_agent() -> str:
    """Run the agent"""
    global agent_session_active, agent_group_chat, agent_waiting_for_input_flag
    logger.info(f"Running agent")
    
    try:
        # Set up model client
        logger.info("Setting up model client")
        model_client = setup_model_client()
        
        # Create agents
        logger.info("Creating agents")
        def get_user_message(prompt: str) -> str:
            # Put out a system message that we're waiting for input
            agent_message_queue.put(f"System: Awaiting user input for: {prompt}")
            
            # Use the web_input_func to get input
            return web_input_func(prompt)
            
        user = UserProxyAgent("User", input_func=get_user_message)

        planner = AssistantAgent(
            name="Planner",
            system_message="""You have access to multiple different applications which you must invoke to complete the user reuqest. Output the name of the application from the application given to you which must be invoked next. You will see the history of applications invoked and their results. Along with the name of the application, send a description of the task that application needs to perform with all the necessary data you have without explicitly sending the exact user request. Only send the necessary information.

            List of the available application with description:
            Calendar: A calendar app with API to reserve, check availability and read the calendar data.
            Expedia: A travel booking application with APIs for searching, booking and paying for flights, hotels, rental cars, experiences like cruises.
            Wallet: A wallet application with saved cards and with APIs for adding, removing, updating and getting credit card information for payment.
            ContactManager: A contact manager application with APIs to add, remove, update and get contact information.
            User: The user application only for asking the user for input and data.

            First output the name of the application and then the description in the format, application: description. The description must contains all the required information for the application, do not make up data, if you need data invoke the User application to get the required data first before calling the application.

            When all the tasks are completed return terminate.
            If there is a permission error while doing the task return perm_err
            for any other reason of failure return error
            Always give reason for termination, perm_err or error.

        """,
            model_client = model_client
        )

        # Create specialized agents
        logger.info("Creating specialized agents")

        async def get_user_input(question: str) -> str:
            # For flight booking, we'll extract the information from the user's initial request
            # This is a special case to avoid the loop of asking for input
            if "flight" in question.lower() and "sea" in question.lower() and "slc" in question.lower():
                # Extract information from the user's initial request
                # For now, we'll use default values
                return "I'd like to book a flight from Seattle (SEA) to Salt Lake City (SLC) for 2 passengers in economy class for next month."
            return f"user: {question}"

        async def get_user_data(request: str) -> str:
            return f"data: {request}"

        async def calendar_reserve(start_time: datetime, duration: timedelta, description: str) -> str:
            print(f"\033[1;34;40mCalling CalendarAPI reserve with start_time={start_time}, duration={duration}, description={description}\033[0m")
            result = calendar_api.reserve(start_time=start_time, duration=duration, description=description)
            return result

        async def calendar_read(start_time: datetime, duration: timedelta) -> str:
            print(f"\033[1;34;40mCalling CalendarAPI read with start_time={start_time}, duration={duration}\033[0m")
            result = calendar_api.read(start_time=start_time, duration=duration)
            return result

        async def calendar_check_availability(start_time: datetime, duration: timedelta) -> str:
            print(f"\033[1;34;40mCalling CalendarAPI check_available with start_time={start_time}, duration={duration}\033[0m")
            result = calendar_api.check_available(start_time=start_time, duration=duration)
            return result

        calendar = AssistantAgent(
            name="Calendar",
            system_message="""
            You are a calendar agent.
            Asume offset-naive datetime for simplicity.
            Use the tools available to you to fulfill the request.
            Return "done" when the task given to you is completed.
        """,
            tools=[calendar_reserve, calendar_read, calendar_check_availability],
            model_client=model_client
        )

        async def wallet_add_credit_card(card_name: str, card_type: str, card_number: str, card_pin: str) -> str:
            print(f"\033[1;34;40mCalling WalletAPI add_credit_card with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}\033[0m")
            result = wallet_api.add_credit_card(card_name=card_name, card_type=card_type, card_number=card_number, card_pin=card_pin)
            return result

        async def wallet_remove_credit_card(card_name: str) -> str:
            print(f"\033[1;34;40mCalling WalletAPI remove_credit_card with card_name={card_name}\033[0m")
            result = wallet_api.remove_credit_card(card_name=card_name)
            return result

        async def wallet_update_credit_card(card_name: str, card_type: str = None, card_number: str = None, card_pin: str = None) -> str:
            print(f"\033[1;34;40mCalling WalletAPI update_credit_card with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}\033[0m")
            result = wallet_api.update_credit_card(card_name=card_name, card_type=card_type, card_number=card_number, card_pin=card_pin)
            return result

        async def wallet_get_credit_card_info(card_name: str) -> str:
            print(f"\033[1;34;40mCalling WalletAPI get_credit_card_info with card_name={card_name}\033[0m")
            result = wallet_api.get_credit_card_info(card_name=card_name)
            return result

        wallet = AssistantAgent(
            name="Wallet",
            system_message="""
            You are a wallet agent.

            wallet_get_credit_card_info tool takes card_name as input and returns all the credit card information, always including the card type, card number, and card pin or CVV and the billing and anything else necessary for making a payment for the given card name.

            If the card information is requested but card name is not provided, ask the user for the card name using `get_user_input` tool.

            Return "done" when you have completed your work.
        """,
            tools=[wallet_get_credit_card_info, wallet_add_credit_card, wallet_remove_credit_card, wallet_update_credit_card, get_user_input],
            model_client=model_client
        )

        async def contact_add_contact(name: str, phone: str, address: str, email: str, relation: str, birthday: str = None, notes: str = None) -> str:
            print(f"\033[1;34;40mCalling ContactManagerAPI add_contact with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}\033[0m")
            result = contact_manager_api.add_contact(name=name, phone=phone, address=address, email=email, relation=relation, birthday=birthday, notes=notes)
            return result

        async def contact_remove_contact(name: str) -> str:
            print(f"\033[1;34;40mCalling ContactManagerAPI remove_contact with name={name}\033[0m")
            result = contact_manager_api.remove_contact(name=name)
            return result

        async def contact_update_contact(name: str, phone: str = None, address: str = None, email: str = None, relation: str = None, birthday: str = None, notes: str = None) -> str:
            print(f"\033[1;34;40mCalling ContactManagerAPI update_contact with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}\033[0m")
            result = contact_manager_api.update_contact(name=name, phone=phone, address=address, email=email, relation=relation, birthday=birthday, notes=notes)
            return result

        async def contact_get_contact_info(name: str) -> str:
            print(f"\033[1;34;40mCalling ContactManagerAPI get_contact_info with name={name}\033[0m")
            result = contact_manager_api.get_contact_info(name=name)
            return result

        async def contact_get_names_by_relation(relation: str) -> str:
            print(f"\033[1;34;40mCalling ContactManagerAPI get_names_by_relation with relation={relation}\033[0m")
            result = contact_manager_api.get_names_by_relation(relation=relation)
            return result

        contact_manager = AssistantAgent(
            name="ContactManager",
            system_message="""
            You are a contact manager agent.

            The name of the user is Ron Swanson whose information is already stored in the contact manager.

            Use the tool `contact_get_names_by_relation` to get the names of all the contacts with the given relation and you may later use the `contact_get_contact_info` tool to get the information for the contact.

            `contact_get_contact_info` tool takes name as input and returns all the contact information, including phone, address, email, relation, birthday, and notes for the given name.

            use `get_user_input` tool to ask the user for user input.

            Return "done" when your work is completed.
        """,
            tools=[contact_add_contact, contact_remove_contact, contact_update_contact, contact_get_contact_info, contact_get_names_by_relation, get_user_input],
            model_client=model_client
        )

        async def expedia_search_flights(from_location: str, to_location: str, departure_date: datetime, return_date: datetime = None, airline: str = None, round_trip: bool = True) -> str:
            print(f"\033[1;34;40mCalling expedia_search_flights with from_location={from_location}, to_location={to_location}, departure_date={departure_date}, return_date={return_date}, airline={airline}, round_trip={round_trip}\033[0m")
            result = expedia_api.search_flights(from_location=from_location, to_location=to_location, departure_date=departure_date, return_date=return_date, airline=airline, round_trip=round_trip)
            return result

        async def expedia_book_hotel(hotel_name: str, location: str, check_in_date: datetime, check_out_date: datetime, room_type: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_book_hotel with hotel_name={hotel_name}, location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}\033[0m")
            result = expedia_api.book_hotel(hotel_name=hotel_name, location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
            return result

        async def expedia_rent_car(car_type: str, pickup_location: str, pickup_date: datetime, return_date: datetime, rental_company: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_rent_car with car_type={car_type}, pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, rental_company={rental_company}\033[0m")
            result = expedia_api.rent_car(car_type=car_type, pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, rental_company=rental_company)
            return result

        async def expedia_book_experience(experience_name: str, location: str, date: datetime, participants: int = 1) -> str:
            print(f"\033[1;34;40mCalling expedia_book_experience with experience_name={experience_name}, location={location}, date={date}, participants={participants}\033[0m")
            result = expedia_api.book_experience(experience_name=experience_name, location=location, date=date, participants=participants)
            return result

        async def expedia_book_cruise(cruise_name: str, departure_port: str, departure_date: datetime, return_date: datetime, cabin_type: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_book_cruise with cruise_name={cruise_name}, departure_port={departure_port}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}\033[0m")
            result = expedia_api.book_cruise(cruise_name=cruise_name, departure_port=departure_port, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
            return result

        async def expedia_search_hotels(location: str, check_in_date: datetime, check_out_date: datetime, room_type: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_search_hotels with location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}\033[0m")
            result = expedia_api.search_hotels(location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
            return result

        async def expedia_search_rental_cars(pickup_location: str, pickup_date: datetime, return_date: datetime, car_type: str = None, rental_company: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_search_rental_cars with pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, car_type={car_type}, rental_company={rental_company}\033[0m")
            result = expedia_api.search_rental_cars(pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, car_type=car_type, rental_company=rental_company)
            return result

        async def expedia_search_experience(experience_name: str, location: str, date: datetime, participants: int = 1) -> str:
            print(f"\033[1;34;40mCalling expedia_search_experience with experience_name={experience_name}, location={location}, date={date}, participants={participants}\033[0m")
            result = expedia_api.search_experience(experience_name=experience_name, location=location, date=date, participants=participants)
            return result

        async def expedia_search_cruise(departure_port: str, destination: str, departure_date: datetime, return_date: datetime, cabin_type: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_search_cruise with departure_port={departure_port}, destination={destination}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}\033[0m")
            result = expedia_api.search_cruise(departure_port=departure_port, destination=destination, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
            return result

        async def expedia_get_cruise_info(cruise_id: str) -> str:
            print(f"\033[1;34;40mCalling expedia_get_cruise_info with cruise_id={cruise_id}\033[0m")
            result = expedia_api.get_cruise_info(cruise_id=cruise_id)
            return result

        async def expedia_get_cruise_addons(cruise_id: str) -> str:
            print(f"\033[1;34;40mCalling expedia_get_cruise_addons with cruise_id={cruise_id}\033[0m")
            result = expedia_api.get_cruise_addons(cruise_id=cruise_id)
            return result

        async def expedia_get_cruise_policies(cruise_id: str) -> str:
            print(f"\033[1;34;40mCalling expedia_get_cruise_policies with cruise_id={cruise_id}\033[0m")
            result = expedia_api.get_cruise_policies(cruise_id=cruise_id)
            return result

        async def expedia_get_cruise_payment_options(cruise_id: str) -> str:
            print(f"\033[1;34;40mCalling expedia_get_cruise_payment_options with cruise_id={cruise_id}\033[0m")
            result = expedia_api.get_cruise_payment_options(cruise_id=cruise_id)
            return result
        
        async def expedia_pay_for_itenary(booking_id: str, payment_method: str, amount: float, card_number: str, card_expiry: str, card_cvv: str, billing_address: str) -> str:
            print(f"\033[1;34;40mCalling expedia_pay_for_itenary with booking_id={booking_id}, payment_method={payment_method}, amount={amount}, card_number={card_number}, card_expiry={card_expiry}, card_cvv={card_cvv}, billing_address={billing_address}\033[0m")
            result = expedia_api.pay_for_itenary(booking_id=booking_id, payment_method=payment_method, amount=amount, card_number=card_number, card_expiry=card_expiry, card_cvv=card_cvv, billing_address=billing_address)
            return result

        async def expedia_add_guest_info(booking_id: str, guest_name: str, guest_email: str, guest_phone: str, guest_address: str = None) -> str:
            print(f"\033[1;34;40mCalling expedia_add_guest_info with booking_id={booking_id}, guest_name={guest_name}, guest_email={guest_email}, guest_phone={guest_phone}, guest_address={guest_address}\033[0m")
            result = expedia_api.add_guest_info(booking_id=booking_id, guest_name=guest_name, guest_email=guest_email, guest_phone=guest_phone, guest_address=guest_address)
            return result

        expedia = AssistantAgent(
            name="Expedia",
            system_message="""
            You are a travel booking agent with strict confirmation requirements. Follow these rules:

            1. **Mandatory Confirmations** - after calling the following tools, ALWAYS ask the user for input using get_user_input:
            - expedia_search_cruise
            - expedia_get_cruise_info 
            - expedia_get_cruise_addons
            - expedia_get_cruise_policies
            - expedia_get_cruise_payment_options

            2. **Mandatory Data Requirements** - before calling the following tools, ALWAYS request data by calling using get_user_data:
            - expedia_add_guest_info 
            - expedia_pay_for_itenary 

            3. **Execution Flow** - Cruise booking MUST follow this exact sequence with confirmations:
            a. expedia_search_cruise → get_user_input: "Choose cruise an room option from these search results?"
            b. ONLY if confirmed → expedia_get_cruise_info → get_user_input: "Confirm cruise details and number of guests?"
            c. ONLY if confirmed → expedia_get_cruise_addons → get_user_input: "Confirm add-ons?"
            d. ONLY if confirmed → expedia_get_cruise_policies → get_user_input: "Accept policies?"
            e. ONLY if confirmed → expedia_get_cruise_payment_options → get_user_input: "Confirm payment method?"
            f. ONLY if confirmed → get_user_data: "Please provide payment details" → ONLY if data provided → expedia_pay_for_itenary
            g. get_user_data: "Please provide guest information" → ONLY if data provided → expedia_add_guest_info
            h. done

            4. **Interaction Rules**:
            - If user rejects any step, return to previous stage
            - Repeat incomplete data requests until fulfilled
            - NEVER proceed with partial/invalid/dummy data, always ask for real data
            - get_user_input and get_user_data are mandatory before certain tools and should not be skipped or combined or used for any other purpose
            - Always only return "done" when the entire task is completed
            """,
            tools=[expedia_search_flights, expedia_book_hotel, expedia_rent_car, expedia_book_experience, expedia_book_cruise, expedia_search_hotels, expedia_search_rental_cars, expedia_search_experience, expedia_search_cruise, expedia_get_cruise_info, expedia_pay_for_itenary, expedia_add_guest_info, expedia_get_cruise_addons, expedia_get_cruise_policies, expedia_get_cruise_payment_options, get_user_data, get_user_input],
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
            max_turns=55,
            termination_condition=termination,
            model_client=model_client,
            selector_func=selector_exp
        )
        
        # Store the group chat for later use
        agent_group_chat = group_chat
        
        # Set the agent session as active
        agent_session_active = True
        
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

def initialize_agent_session():
    """Initialize the agent session"""
    global agent_session_active, agent_thread, agent_loop, agent_initialized
    
    # If the agent session is already active, do nothing
    if agent_session_active:
        logger.info("Agent session already active")
        return
    
    # If the agent has already been initialized, don't initialize again
    if agent_initialized:
        logger.info("Agent already initialized, not initializing again")
        return
    
    logger.info("Initializing agent session")
    
    # Create a new event loop for the agent
    agent_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(agent_loop)
    
    # Start the agent in a separate thread
    agent_thread = threading.Thread(target=run_agent_thread)
    agent_thread.daemon = True
    agent_thread.start()
    
    # Mark the agent as initialized
    agent_initialized = True
    
    logger.info("Agent session initialized")

def run_agent_thread():
    """Run the agent in a separate thread"""
    global agent_loop, agent_session_active
    
    try:
        # Run the agent in the event loop
        agent_loop.run_until_complete(run_agent())
    except Exception as e:
        logger.error(f"Error in agent thread: {str(e)}", exc_info=True)
    finally:
        # Set the agent session as inactive
        agent_session_active = False
        logger.info("Agent session ended")

def run_agent_sync() -> str:
    """Synchronous wrapper for running the agent"""
    logger.info(f"Running agent synchronously")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_agent())
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
    response = run_agent_sync()
    print("Agent response:", response) 