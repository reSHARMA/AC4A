from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import AgentEvent, ChatMessage

from app.calendar import CalendarAPI
from app.expedia import ExpediaAPI
from src.policy_system.policy_system import PolicySystem

import os, asyncio, json, re, pprint
from typing import Sequence
from datetime import datetime, timedelta

import streamlit as st

# Conditional import for Streamlit
USE_STREAMLIT = True

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

    config = {
        "provider": "OpenAIChatCompletionClient",
        "config": {
            "model": "gpt-4o",
            "api_key": os.environ["OPENAI_API_KEY"]
        }
    }

    model_client = ChatCompletionClient.load_component(config)

    def web_input_func(prompt: str) -> str:
        global user_input
        user_input = prompt
        return user_input

    def web_input_func1(prompt: str) -> str:
        global user_input
        temp = user_input
        user_input = ""
        return temp 

    user = None

    if USE_STREAMLIT:
        user = UserProxyAgent("User", input_func=web_input_func1) 
    else:
        user = UserProxyAgent("User", input_func=input)

    # User: The user who is interacting with you. Must be asked for confirmation for irreversible tasks or when there are options available.
    planner = AssistantAgent(
        name="Planner",
        system_message="""You have access to multiple different applications which you must invoke to complete the user reuqest. Output the name of the application from the application given to you which must be invoked next. You will see the history of applications invoked and their results. Along with the name of the application, send a description of the task that application needs to perform with all the necessary data you have without explicitly sending the exact user request. Only send the necessary information.

        List of the available application with description:
        Calendar: A normal calendar app with API to reserve, check availability and read the calendar data.
        Expedia: An application to search flights, book hotels, rent cars, and book experiences and cruises with a comprehensive travel API.
        
        First output the name of the application and then the description in the format, application: description.

        If the task is completed or if you are not able to complete the task return terminate.
        Always give reason for termination.
        You work fully autonomously, take best decision without disturbing the user with confirmation or clarification. 
    """,
        model_client = model_client
    )

    calendar_api = CalendarAPI(policy_system)
    expedia_api = ExpediaAPI(policy_system)

    def append_policy(code: str) -> str:
        print(code)
        import re
        def extract_code_blocks(code: str) -> list:
            pattern = r"```python(.*?)```"
            code_blocks = re.findall(pattern, code, re.DOTALL)
            return [block.strip() for block in code_blocks]

        if "```python" in code:
            snippets = extract_code_blocks(code)
        else:
            snippets = [code]

        num_policies = sum(1 for snp in snippets if "policy_system" in snp)
        print("Number of policies: ", num_policies)
        error = False
        for snp in snippets:
            print(f"Policy: {snp}")
            if USE_STREAMLIT:
                st.session_state["policies"].append(snp)
            try:
                eval(snp, {"policy_system": policy_system})
            except Exception as e:
                print(f"Error: {e}")
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
                print("Debug: Message already sent, skipping.")

        def create_policy_message(self, request):
            # Logic to create the policy message based on the request
            return "Generated policy message"

        def send_message(self, message):
            # Logic to send the message
            print(f"Sending message: {message}")

    POLICY_GENERATOR_WILDCARD = """
You are a data access policy generator agent. You are expected to generate policies in an embedded DSL in Python based on the data access allowed by the user request.

Each policy is made up of three components: `granular_data`, `data_access`, and `position`.

### Granular Data
- **Identify the highest granularity of data** that is sufficient to complete the user request.
  - Example: If the user requests calendar data covering more than 7 days, provide access to an entire month of data instead of a week or individual days.

### Available Data Hierarchy:
- **Calendar:Year**
  - **Calendar:Month**
    - **Calendar:Week**
      - **Calendar:Day**
        - **Calendar:Hour**

- **Expedia:Destination**
  - **Expedia:Flight**
  - **Expedia:Hotel**
  - **Expedia:CarRental**
- **Expedia:Experience**
  - **Expedia:Cruise**

- **Contact:Name**
  - **Contact:Email**
  - **Contact:Phone**

- **Wallet:CreditCard**
  - **Wallet:CreditCardType**
  - **Wallet:CreditCardNumber**
  - **Wallet:CreditCardPin**

- **User:Profile**
  - **User:Name**
  - **User:Address**
  - **User:Phone**
  - **User:SSN**

### Data Access
- The `data_access` component indicates if granular_data can be read or written (allowed values: `Read` / `Write`).
  - Determine this by assessing whether the data should be accessed for reading existing information or writing new information.

### Position
- The `position` attribute represents the data's position within its sequence (allowed values: `Previous` / `Current` / `Next`) with respect to the temporal context.
- **Determine the temporal context**: Start by establishing a temporal reference point, such as today's date or another specified date in the user request.
- **Assess the position** by comparing the established temporal reference against the requested data:
  - For calendar data: Determine if the data is in the `Current`, `Next`, or `Previous` temporal sequence unit (e.g., month, year) relative to the current reference.
    - If today's date is January 2025 and the request is for Oct 2025, `Month` should be marked as `Next` while `Year` should be `Current`.
  - For non-sequential data or when not applicable, mark the `position` field as `Current`.

### Format of Policy
Policies must be added to the policy_system using the `add_policy` method. This method accepts a dictionary input consisting of only three keys: `granular_data`, `data_access`, and `position`.

Example Policy Format:
```python
policy_system.add_policy({
    "granular_data": "Calendar:Month",
    "data_access": "Read",
    "position": "Next"
})
```

### Additional Instructions
- **Generate only permissive policies** for data whose access can be reasonably inferred from the request and is essential for completing the task.
- **Minimize data exposure**: Provide access to the minimal required data.
- **No assumptions about sensitive data**: Allow access if the user action implicitly necessitates it.
- **First, output the reasoning for each policy, and then output the generated policy in individual code blocks.
"""

    permission = PermissionAgent(
        name="Permission",
        system_message=POLICY_GENERATOR_WILDCARD,
        model_client = model_client,
        tools=[]
    )

    async def calendar_reserve(start_time: datetime, duration: timedelta, description: str) -> str:
        print("\033[1;34;40mCalling CalendarAPI reserve\033[0m")
        result = calendar_api.reserve(start_time=start_time, duration=duration, description=description)
        return result

    async def calendar_read(start_time: datetime, duration: timedelta) -> str:
        print("\033[1;34;40mCalling CalendarAPI read\033[0m")
        result = calendar_api.read(start_time=start_time, duration=duration)
        return result

    async def calendar_check_availability(start_time: datetime, duration: timedelta) -> str:
        print("\033[1;34;40mCalling CalendarAPI check_available\033[0m")
        result = calendar_api.check_available(start_time=start_time, duration=duration)
        return result

    calendar = AssistantAgent(
        name="Calendar",
        system_message="""
        You are a calendar agent with access to calendar APIs as tools, you will be given a request to fulfill.
        Call the tools available to you to fulfill the request. Asume offset-naive datetime for simplicity.
    """,
        tools=[calendar_reserve, calendar_read, calendar_check_availability],
        model_client=model_client
    )

    async def expedia_search_flights(from_location: str, to_location: str, departure_date: datetime, return_date: datetime = None, airline: str = None, round_trip: bool = True) -> str:
        print("\033[1;34;40mCalling expedia_search_flights\033[0m")
        result = expedia_api.search_flights(from_location=from_location, to_location=to_location, departure_date=departure_date, return_date=return_date, airline=airline, round_trip=round_trip)
        return result

    async def expedia_book_hotel(hotel_name: str, location: str, check_in_date: datetime, check_out_date: datetime, room_type: str = None) -> str:
        print("\033[1;34;40mCalling expedia_book_hotel\033[0m")
        result = expedia_api.book_hotel(hotel_name=hotel_name, location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
        return result

    async def expedia_rent_car(car_type: str, pickup_location: str, pickup_date: datetime, return_date: datetime, rental_company: str = None) -> str:
        print("\033[1;34;40mCalling expedia_rent_car\033[0m")
        result = expedia_api.rent_car(car_type=car_type, pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, rental_company=rental_company)
        return result

    async def expedia_book_experience(experience_name: str, location: str, date: datetime, participants: int = 1) -> str:
        print("\033[1;34;40mCalling expedia_book_experience\033[0m")
        result = expedia_api.book_experience(experience_name=experience_name, location=location, date=date, participants=participants)
        return result

    async def expedia_book_cruise(cruise_name: str, departure_port: str, departure_date: datetime, return_date: datetime, cabin_type: str = None) -> str:
        print("\033[1;34;40mCalling expedia_book_cruise\033[0m")
        result = expedia_api.book_cruise(cruise_name=cruise_name, departure_port=departure_port, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
        return result

    async def expedia_search_hotels(location: str, check_in_date: datetime, check_out_date: datetime, room_type: str = None) -> str:
        print("\033[1;34;40mCalling expedia_search_hotels\033[0m")
        result = expedia_api.search_hotels(location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
        return result

    async def expedia_search_rental_cars(pickup_location: str, pickup_date: datetime, return_date: datetime, car_type: str = None, rental_company: str = None) -> str:
        print("\033[1;34;40mCalling expedia_search_rental_cars\033[0m")
        result = expedia_api.search_rental_cars(pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, car_type=car_type, rental_company=rental_company)
        return result

    async def expedia_search_experience(experience_name: str, location: str, date: datetime, participants: int = 1) -> str:
        print("\033[1;34;40mCalling expedia_search_experience\033[0m")
        result = expedia_api.search_experience(experience_name=experience_name, location=location, date=date, participants=participants)
        return result

    async def expedia_search_cruise(departure_port: str, departure_date: datetime, return_date: datetime, cabin_type: str = None) -> str:
        print("\033[1;34;40mCalling expedia_search_cruise\033[0m")
        result = expedia_api.search_cruise(departure_port=departure_port, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
        return result

    expedia = AssistantAgent(
        name="Expedia",
        system_message="""
        You are an Expedia app (a travel and experience booking app) with access to Expedia APIs as tools, you will be given a request to fulfill.
        Call the tools available to you to fulfill the request.
        Asume offset-naive datetime for simplicity.
    """,
        tools=[expedia_search_flights, expedia_book_hotel, expedia_rent_car, expedia_book_experience, expedia_book_cruise, expedia_search_hotels, expedia_search_rental_cars, expedia_search_experience, expedia_search_cruise],
        model_client=model_client
    )

    termination = TextMentionTermination("terminate")

    def selector_func(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        print("+++++>", messages)
        if USE_STREAMLIT:
            if len(messages) == 0:
                messages = st.session_state['messages'] 

            print(f"Debug: Number of messages received: {len(messages)}")
            print("****", messages)

            if len(messages) > 0:
                name = messages[-1].source
                print("*******", name)
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
            print("Debug: No messages, waiting for user input.")

            if USE_STREAMLIT:
                user_input = st.chat_input("Say something")
                print(f"Debug: User input received: {user_input}")
                web_input_func(user_input)
                st.session_state["policies"] = []

            agent = "User"
        
        if len(messages) == 1: 
            print("Debug: Only one message, returning 'Permission'.")
            agent = "Permission"
        
        if len(messages) > 0 and "policy_err" in messages[-1].content:
            print("Debug: 'policy_err' found in the last message, returning 'Permission'.")

            messages = [message for message in messages if message.source != "Permission"]
            agent = "Permission"
        
        if len(messages) > 0 and messages[-1].source == "Permission":
            print("Debug: Last message from 'Permission', filtering messages and returning 'Planner'.")

            append_policy(messages[-1].content)
            
            if USE_STREAMLIT:
                with st.sidebar:
                    st.header("Policies")
                    for policy in st.session_state["policies"]:
                        st.code(pprint.pformat(policy, width=40), language="python")

            messages = [message for message in messages if message.source != "Permission"]
            print("=====>", messages)
            agent = "Planner"
        
        if len(messages) > 0 and messages[-1].source == "Planner":
            next_agent = messages[-1].content.split(":")[0]
            print(f"Debug: Last message from 'Planner', next agent determined as: {next_agent}")
            agent =  next_agent

            if agent == "terminate":
                agent = "Planner"
        
        if agent == "":
            print("Debug: Default case, returning 'Planner'.")
            agent = "Planner"

        print(f"Debug: Returning agent: {agent}")
        return agent

    groupchat = SelectorGroupChat([user, permission, planner, calendar, expedia], max_turns=25, termination_condition=termination, model_client=model_client, selector_func=selector_func)

    task = "Schedule a meeting for next Monday 8am with MSR folks. Today's date is 15th Jan 2025"
    task = "Use Expedia to compare travel itineraries for a cruise to Alaska around mid-July, considering existing constraints on my calendar."

    task += "Today's date is 15th Jan 2025"

    stream = groupchat.run_stream()
    if USE_STREAMLIT:
        async for _ in stream:
            pass
    else:
        await Console(stream)

asyncio.run(main())