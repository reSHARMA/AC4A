from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console

from app.calendar import CalendarAPI
from src.policy_system.policy_system import PolicySystem

import os, asyncio
from datetime import datetime, timedelta

policy_system = PolicySystem()

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

    user = UserProxyAgent("user")

    planner = AssistantAgent(
        name="Planner",
        system_message="""You have access to multiple different applications which you must invoke to complete the user reuqest. Output the name of the application from the application given to you which must be invoked next. You will see the history of applications invoked and their results. Along with the name of the application, send a description of the task that application needs to perform with all the necessary data you have without explicitly sending the exact user request. 

        List of the available application with description:
        Calendar: A normal calendar app with API to reserve, check availability and read the calendar data.

        If the task is completed return terminate.
    """,
        model_client = model_client
    )

    calendar_api = CalendarAPI(policy_system)

    async def append_policy(code: str) -> str:
        import re
        print("Debug: Starting append_policy function")
        print(f"Debug: Received code:\n{code}")
        
        eval(code, {"policy_system": policy_system})
        print("Debug: Evaluation complete")
            
    permission = AssistantAgent(
        name="Permission",
        system_message="""You are a permission agent, your task is to understand the user request carefully and think about what are the data the user is implcitly giving permission to the system to access. Based on the data implicitly allowed by the user based on the request, you are requested to create policies which allows for the use of the data restricted by various attributes.

        The policy is made of up three attributes, granular_data, data_access and time.
        granular_data represents the data which is allowed to be used by the user request and is required in the policy.
        data_access is used for restricting the read or write access to the granular_data
        time is used to restrict the temporal aspect of the granular_data

        For the calendar application, the following are the available data and attributes
        'granular_data': [AttributeTree(f'Calendar:Year', [
            AttributeTree(f'Calendar:Month', [
                AttributeTree(f'Calendar:Week', [
                    AttributeTree(f'Calendar:Day', [
                        AttributeTree(f'Calendar:Hour')
                    ])
                ])
            ])
        ])],
        'data_access': [
            AttributeTree('Read'),
            AttributeTree('Write')
        ],
        'time': ['Past', 'Present', 'Future']

        The data and the attributes can be a tree or a list or a list of tree nodes. 
        '*' can be used to represent wildcard
        data_access: '*' would imply any data acess
        Calendar:Month means Calendar:Month(*) would imply access to any month
        Calendar:Month(Oct) would imply access to calendar month october

        Since the data can sometimes be a tree, it is possible to represent access to calendar for 2026 Oct month by doing
        Calendar:Year(2026)::Calendar:Month(Oct) where :: represents sub-data.

        Return a list of such policies as python code, for example:

        # read only access to the calendar for Oct 2025 (note that time future is redundant here and is not needed)
        policy_system.add_policy({
            "granular_data": "Calendar:Year(2025)::Calendar:Month(Oct)",
            "data_access": "r",
            "time": "Future"
        })

        After creating the policies, call the tool function append_policy to register them with the policy engine.
    """,
        model_client = model_client,
        tools=[append_policy]
    )

    async def calendar_reserve(start_time: datetime, duration: timedelta, description: str) -> str:
        calendar_api.reserve(start_time=start_time, duration=duration, description=description)
        return "ok"

    async def calendar_read(start_time: datetime, duration: timedelta) -> str:
        calendar_api.read(start_time=start_time, duration=duration)
        return "ok"

    async def calendar_check_availability(start_time: datetime, duration: timedelta) -> str:
        calendar_api.check_available(start_time=start_time, duration=duration)
        return "ok"

    calendar = AssistantAgent(
        name="Calendar",
        system_message="""
        You are a calendar app with access to calendar APIs as tools, you will be given a request to fulfill. Call the tools available to you to fulfill the request. 
    """,
        tools=[calendar_reserve, calendar_read, calendar_check_availability],
        model_client=model_client
    )

    termination = TextMentionTermination("terminate")

    selector_prompt = """You are an expert personal assistant given a task to be fulfilled. There are multiple agents available to you which you can invoke to complete the given task. The following are the agents available to you:
    {roles}
    Follow these guidelines while selecting the next agent for the task:
    1. For the first time always select the permission agent
    2. Once the permission agent is done, that is, the second time, always select the planner agent.
    3. The planner agent will select an application agent, select that application agent. 
    4. Once the application agent is done, select the planner agent again so that the planner agent can either choose another application or check if the task is completed. 
    5. Loop between the planner and application agents until the planner terminates.
    6. Only output the name of the next agent and nothing else. 
    7. Under any circumstances the permission agent must not be called more than once after the start.

    {history}
    
    Read the above conversation. Then select the next role from {participants} to complete the task as per the guidelines. Only return the name of the agent aka role.
"""

    groupchat = SelectorGroupChat([permission, planner, calendar], termination_condition=termination, max_turns=10, model_client=model_client, selector_prompt=selector_prompt)
    stream = groupchat.run_stream(task="Schedule a meeting for next Monday 8am with MSR folks. Today's date is 15th Jan 2025")
    await Console(stream)

asyncio.run(main())