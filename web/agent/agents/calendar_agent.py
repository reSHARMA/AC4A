import logging
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from ..web_input import web_input_func
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data
from config import WILDCARD

# Set up logging
logger = logging.getLogger(__name__)


class CalendarAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("Calendar", {
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
            'position': [
                AttributeTree('Previous'),
                AttributeTree('Current'),
                AttributeTree('Next')
            ]
        })

    def get_hierarchy(self, start_time, duration, use_wildcard):
        end_time = start_time + duration
        
        time_hierarchy = [
            (365, 'Year', start_time.year),
            (30, 'Month', start_time.month),
            (7, 'Week', start_time.isocalendar()[1]),
            (1, 'Day', start_time.day),
            (0, 'Hour', start_time.hour)
        ]

        composite_data = None
        for days, label, value in time_hierarchy:
            if (end_time - start_time).days >= days:
                if use_wildcard:
                    composite_data = f'{self.namespace}:{label}(*)'
                else:
                    composite_data = f'{self.namespace}:{label}({value})'
                break

        return composite_data

    def get_access_level(self, endpoint_name):
        return 'Write' if 'reserve' in endpoint_name else 'Read'

    def get_time_period(self, start_time, duration, use_wildcard):
        current_time = datetime.now()
        end_time = start_time + duration

        if start_time < current_time < end_time:
            return "Current"
        
        time_hierarchy = [
            (365, 'Year', end_time.year - start_time.year),
            (30, 'Month', (end_time.year - start_time.year) * 12 + end_time.month - start_time.month),
            (7, 'Week', (end_time - start_time).days // 7),
            (1, 'Day', (end_time - start_time).days),
            (0, 'Hour', (end_time - start_time).seconds // 3600)
        ]

        composite_data = None
        for days, label, value in time_hierarchy:
            if (end_time - start_time).days >= days:
                if start_time < current_time and current_time < end_time:
                    composite_data = "Current"
                elif current_time < start_time:
                    if use_wildcard:
                        composite_data = f"Next(*)"
                    else:
                        composite_data = f"Next({value})"
                else:
                    if use_wildcard:
                        composite_data = f"Previous(*)"
                    else:
                        composite_data = f"Previous({value})"
                break

        result = composite_data if composite_data else "Current"
        return result

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        start_time = kwargs['start_time']
        duration = kwargs['duration']
        return {
            'granular_data': self.get_hierarchy(start_time, duration, wildcard),
            'data_access': self.get_access_level(endpoint_name),
            'position': self.get_time_period(start_time, duration, wildcard)
        }

class CalendarAPI:
    def __init__(self, policy_system):
        self.annotation = CalendarAPIAnnotation()
        self.policy_system = policy_system

    @CalendarAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarAPIAnnotation.annotate
    def reserve(self, *args, **kwargs):
        return generate_dummy_data("reserve: This method reserves a time slot in the calendar.", **kwargs)

    @CalendarAPIAnnotation.annotate
    def read(self, *args, **kwargs):
        return generate_dummy_data("read: This method reads calendar events within a specified time range.", **kwargs)

    @CalendarAPIAnnotation.annotate
    # start_time, duration
    def check_available(self, *args, **kwargs):
        return generate_dummy_data("check_availability: This method checks the availability of a time slot in the calendar.", **kwargs)

class CalendarAgent(BaseAgent):
    """Calendar agent for managing calendar operations"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the calendar agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a calendar agent.
        Asume offset-naive datetime for simplicity.
        Use the tools available to you to fulfill the request.
        Return "done" when the task given to you is completed.
        """
        policy_system.register_api(CalendarAPI)
        self.calendar_api = CalendarAPI(policy_system)
        
        tools = [
            self.calendar_reserve,
            self.calendar_read,
            self.calendar_check_availability,
            web_input_func
        ]
        
        super().__init__("Calendar", system_message, tools, model_client)
        
    async def calendar_reserve(self, start_time: datetime, duration: timedelta, description: str) -> str:
        """
        Reserve a time slot in the calendar
        
        Args:
            start_time: The start time of the reservation
            duration: The duration of the reservation
            description: The description of the reservation
            
        Returns:
            The result of the reservation
        """
        logger.info(f"Calling CalendarAPI reserve with start_time={start_time}, duration={duration}, description={description}")
        result = self.calendar_api.reserve(start_time=start_time, duration=duration, description=description)
        return result
        
    async def calendar_read(self, start_time: datetime, duration: timedelta) -> str:
        """
        Read calendar entries
        
        Args:
            start_time: The start time to read from
            duration: The duration to read for
            
        Returns:
            The calendar entries
        """
        logger.info(f"Calling CalendarAPI read with start_time={start_time}, duration={duration}")
        result = self.calendar_api.read(start_time=start_time, duration=duration)
        return result
        
    async def calendar_check_availability(self, start_time: datetime, duration: timedelta) -> str:
        """
        Check availability for a time slot
        
        Args:
            start_time: The start time to check
            duration: The duration to check for
            
        Returns:
            The availability status
        """
        logger.info(f"Calling CalendarAPI check_available with start_time={start_time}, duration={duration}")
        result = self.calendar_api.check_available(start_time=start_time, duration=duration)
        return result 