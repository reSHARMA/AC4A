from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_core import CancellationToken
from autogen_ext.auth.azure import AzureTokenProvider
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential


from app.calendar import CalendarAPI
from app.expedia import ExpediaAPI
from app.wallet import WalletAPI
from app.contact_manager import ContactManagerAPI

from src.policy_system.policy_system import PolicySystem
from src.utils.dummy_data import call_openai_api
from src.prompts import *

import os, asyncio, json, re, pprint
from typing import Sequence
from datetime import datetime, timedelta
from dotenv import load_dotenv

from config import debug_print
import streamlit as st

# Load environment variables from .env file
load_dotenv()

# Conditional import for Streamlit
USE_STREAMLIT = True
DEMO = False

if not DEMO:
    USE_STREAMLIT = False

default_agent = ["Planner"]

policy_system = PolicySystem()
user_input = ""

if USE_STREAMLIT:
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    if 'policies' not in st.session_state:
        st.session_state['policies'] = []

async def main() -> None:
    # Register CalendarAPI with the policy system
    policy_system.register_api(CalendarAPI)
    policy_system.register_api(ExpediaAPI)
    policy_system.register_api(WalletAPI)
    policy_system.register_api(ContactManagerAPI)

    # Try OpenAI configuration first
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        config = {
            "provider": "OpenAIChatCompletionClient",
            "config": {
                "model": "gpt-4o",
                "api_key": openai_api_key
            }
        }
        model_client = ChatCompletionClient.load_component(config)
    else:
        # Fallback to Azure OpenAI
        debug_print("OpenAI API key not found, using Azure OpenAI client")
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        if not endpoint:
            raise ValueError("Azure OpenAI endpoint not found in environment variables")
        
        # Extract API version from endpoint URL if not provided
        api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        if not api_version:
            raise ValueError("Azure OpenAI API version not found in environment variables")
        
        scope = os.getenv('AZURE_OPENAI_TOKEN_SCOPES')
        if not scope:
            raise ValueError("Azure OpenAI token scope not found in environment variables")
        
        # Get deployment from environment variable
        deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        if not deployment:
            raise ValueError("Azure OpenAI deployment not found in environment variables")
        
        # Create the Azure token provider
        token_provider = AzureTokenProvider(
            DefaultAzureCredential(),
            scope,
        )
        
        # Create the Azure OpenAI client
        model_client = AzureOpenAIChatCompletionClient(
            azure_deployment=deployment,
            model="gpt-4o",
            api_version=api_version,
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
        )

    def web_input_func(prompt: str) -> str:
        global user_input
        user_input = prompt
        return user_input

    def web_input_func1(prompt: str) -> str:
        global user_input
        temp = user_input
        user_input = ""
        return temp 

    def get_task(prompt : str) -> str:
            task = input("User: ")
            return task
            return task + " Today's date is 25th Jan 2025 PST."

    user = None

    if USE_STREAMLIT:
        user = UserProxyAgent("User", input_func=web_input_func1) 
    else:
        user = UserProxyAgent("User", input_func=get_task)

    # User: The user who is interacting with you. Must be asked for confirmation for irreversible tasks or when there are options available.
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

    calendar_api = CalendarAPI(policy_system)
    expedia_api = ExpediaAPI(policy_system)
    wallet_api = WalletAPI(policy_system)
    contact_manager_api = ContactManagerAPI(policy_system)

    def append_policy(code: str) -> str:
        debug_print(code)
        import re
        def extract_code_blocks(code: str) -> list:
            pattern = r"```python(.*?)```"
            code_blocks = re.findall(pattern, code, re.DOTALL)
            return [block.strip() for block in code_blocks]

        snippets = []
        if "```python" in code:
            snippets = extract_code_blocks(code)

        num_policies = sum(snp.count("policy_system") for snp in snippets)

        debug_print("Number of policies: ", num_policies)
        error = False
        for snp in snippets:
            debug_print(f"Policy: {snp}")
            if USE_STREAMLIT:
                st.session_state["policies"].append(snp)
            try:
                exec(snp, {"policy_system": policy_system})
            except Exception as e:
                debug_print(f"Error: {e}")
                error = True
        return "policy_err" if error else "policies deployed!"
            
    class PermissionAgent(AssistantAgent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.message_sent = False

        async def process_request(self, request):
            if not self.message_sent:
                # Logic to process the request and generate a message
                message = self.create_policy_message(request)
                self.send_message(message)
                self.message_sent = True
            else:
                debug_print("Debug: Message already sent, skipping.")

        def create_policy_message(self, request):
            # Logic to create the policy message based on the request
            return "Generated policy message"

        def send_message(self, message):
            # Logic to send the message
            debug_print(f"Sending message: {message}")

    permission = PermissionAgent(
        name="Permission",
        system_message=POLICY_GENERATOR_WILDCARD,
        model_client = model_client,
        tools=[]
    )

    async def get_user_input(question: str) -> str:
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

    termination = TextMentionTermination("terminate") | TextMentionTermination("perm_err") | TextMentionTermination("error")
    agents = [user, planner, calendar, wallet, expedia, contact_manager]

    def selector_demo(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        if (len(messages) > 0):
            debug_print("==>", messages[-1].content)
        if USE_STREAMLIT:
            if len(messages) == 0:
                messages = st.session_state['messages'] 

            debug_print(f"Debug: Number of messages received: {len(messages)}")
            debug_print("****", messages)

            if len(messages) > 0:
                name = messages[-1].source
                debug_print("*******", name)
                avatar = "🤖"
                if name == "User":
                    avatar = "🧑‍💼"
                if name == "Permission":
                    avatar = "👮‍♀️"
                if name == "Planner":
                    avatar = "🤔"
        
                message = st.chat_message(name=name, avatar=avatar)

                text = messages[-1].content
                message.write(text)

        agent = ""

        if len(messages) == 0:
            debug_print("Debug: No messages, waiting for user input.")

            if USE_STREAMLIT:
                user_input = st.chat_input("Say something")
                debug_print(f"Debug: User input received: {user_input}")
                web_input_func(user_input)
                st.session_state["policies"] = []

            agent = "User"
        
        if len(messages) == 1: 
            debug_print("Debug: Only one message, returning 'Permission'.")
            agent = "Permission"
        
        if len(messages) > 0 and "policy_err" in messages[-1].content:
            debug_print("Debug: 'policy_err' found in the last message, returning 'Permission'.")

            messages = [message for message in messages if message.source != "Permission"]
            agent = "Permission"
        
        if len(messages) > 0 and messages[-1].source == "Permission":
            debug_print("Debug: Last message from 'Permission', filtering messages and returning 'Planner'.")

            append_policy(messages[-1].content)
            
            if USE_STREAMLIT:
                with st.sidebar:
                    st.header("Policies")
                    for policy in st.session_state["policies"]:
                        st.code(pprint.pformat(policy, width=40), language="python")

            messages = [message for message in messages if message.source != "Permission"]
            debug_print("=====>", messages)
            agent = "Planner"
        
        if len(messages) > 0 and messages[-1].source == "Planner":
            next_agent = messages[-1].content.split(":")[0]
            debug_print(f"Debug: Last message from 'Planner', next agent determined as: {next_agent}")
            agent =  next_agent

            if agent == "terminate":
                agent = "Planner"
        
        if agent == "":
            debug_print("Debug: Default case, returning 'Planner'.")
            agent = "Planner"

        debug_print(f"Debug: Returning agent: {agent}")
        return agent


    
    def selector_exp(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        if (len(messages) > 0):
            debug_print("==>", messages[-1].content)
        
        global default_agent
        agent = ""

        if len(messages) == 0:
            debug_print("Debug: No messages, waiting for user input.")
            agent = "User"
        
        elif messages[-1].source == "User": 
            # print(f"\033[92mUser: {messages[-1].content}\033[0m")
            debug_print(f"Debug: Last message from User, returning {default_agent}.")
            agent = default_agent[-1]
        
        elif len(messages) > 0 and messages[-1].source == "Planner":
            print(f"\033[93mPlanner: {messages[-1].content}\033[0m")
            next_agent = messages[-1].content.split(":")[0]

            granted = policy_system.text()
            granted_txt = f"The system is already initialized with the following permissions: {granted}"
            policies = call_openai_api(POLICY_GENERATOR_WILDCARD_V2, messages[-1].content + "\n" + granted_txt)
            status = append_policy(policies)
            if "err" in status:
                print("error in inferring data policies")

            debug_print(f"Debug: Last message from 'Planner', next agent determined as: {next_agent}")
            agent =  next_agent
            
            if agent == "terminate":
                agent = "Planner"

        elif len(messages) > 0:    
            if messages[-1].content.lower() == "done":
                agent = "Planner"
            elif messages[-1].content.lower().startswith("user"):
                print(f"\033[92mUser: {messages[-1].content}\033[0m")
                agent = "User"
            elif messages[-1].content.lower().startswith("data"):
                print(f"\033[92mNeed data: {messages[-1].content}\033[0m")
                agent = "Planner"
            elif messages[-1].content.lower().startswith("done"):
                agent = "Planner"
            else:
                agent = messages[-1].source

        debug_print(f"Debug: Returning agent: {agent}")
        
        if agent != "User":
            default_agent.append(agent)

        return agent

    async def msr():
        policy_system.reset()
        
        policy_system.add_policy({
            "granular_data": "Expedia:Destination",
            "data_access": "Read"
        })
        
        policy_system.add_policy({
            "granular_data": "Expedia:Experience",
            "data_access": "Read"
        })

        granted = policy_system.text()
        granted_txt = f"The system is initialized with the following permissions:\n{granted}"
        print(f"\033[95m{granted_txt}\033[0m")

        policy_system.ask()

        stream_log = []
        run_task = SelectorGroupChat(agents, max_turns=70, termination_condition=termination, model_client=model_client, selector_func=selector_exp, allow_repeated_speaker=False)
        stream = run_task.run_stream()
        async for log_entry in stream:
            stream_log.append(log_entry)

        print(stream_log[-1].stop_reason)
        
        
    async def experiment():
        policy_system.disable()
        print("Running task to check if it works natively")
        task = "Search a cruise from Seattle for July 2026 and book the cheapest option for two people. Add it into my calendar."
        # RQ1 how good are the auto generated policies 
        # task completed / total task * 100 
        def get_task(prompt : str) -> str:
            return task + " Today's date is 25th Jan 2025 PST."

        user = UserProxyAgent("User", input_func=get_task) 
        run_task = SelectorGroupChat(agents, max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_exp)

        stream_log = []
        stream = run_task.run_stream()
        async for log_entry in stream:
            stream_log.append(log_entry)

        print(stream_log[-1].stop_reason)

        await run_task.reset()

        policy_system.enable()
        print("Policies deployed to check if the generated policies are good")
        policies = call_openai_api(POLICY_GENERATOR_WILDCARD, task)
        status = append_policy(policies)

        if "err" in status:
            debug_print("RQ1: Policy error") 
            return 
        
        run_task = SelectorGroupChat(agents, max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_exp)
        stream = run_task.run_stream()
        async for log_entry in stream:
            stream_log.append(log_entry)

        print(stream_log[-1].stop_reason)

        await run_task.reset()

        print("Augumenting tasks to check if the policies can catch the changes")
        augment_task = call_openai_api("Given a input task, change it such that the task remains same but the data is changed. Only output the changed task and nothing else.", task)
        debug_print(f"\033[94m{augment_task}\033[0m")  # Prints in blue color

        def get_augmented_task(prompt: str) -> str:
            return augment_task  + " Today's date is 25th Jan 2025 PST."

        user = UserProxyAgent("User", input_func=get_augmented_task)

        run_task = SelectorGroupChat(agents, max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_exp)
        stream = run_task.run_stream()
        async for log_entry in stream:
            stream_log.append(log_entry)

        print(stream_log[-1].stop_reason)

        await run_task.reset()

        print("Generating policies with values")
        policy_system.reset()
        policies = call_openai_api(POLICY_GENERATOR_VALUE, task)
        status = append_policy(policies)
        
        user = UserProxyAgent("User", input_func=get_task) 
        
        run_task = SelectorGroupChat(agents, max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_exp)
        stream = run_task.run_stream()
        async for log_entry in stream:
            stream_log.append(log_entry)

        print(stream_log[-1].stop_reason)

        await run_task.reset()

        print("Augumenting tasks to check if the policies can catch the changes")

        user = UserProxyAgent("User", input_func=get_augmented_task)

        run_task = SelectorGroupChat(agents, max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_exp)
        stream = run_task.run_stream()
        async for log_entry in stream:
            stream_log.append(log_entry)

        print(stream_log[-1].stop_reason)
       
        # debug_print(stream_log)

    async def demo():
        groupchat = SelectorGroupChat(agents, max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_demo)
        stream = groupchat.run_stream()
        if USE_STREAMLIT:
            async for _ in stream:
                pass
        else:
            await Console(stream)


    if DEMO:
        await demo()
    else:
        # # paper eval
        # await experiment()
        await msr()

asyncio.run(main())