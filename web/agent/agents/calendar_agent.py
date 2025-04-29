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
        
        # Define month and day names
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                    'Friday', 'Saturday', 'Sunday']
        
        time_hierarchy = [
            (365, 'Year', start_time.year),
            (30, 'Month', month_names[start_time.month - 1]),
            (7, 'Week', start_time.isocalendar()[1]),
            (1, 'Day', day_names[start_time.weekday()]),
            (0, 'Hour', start_time.hour)
        ]

        composite_data = None
        for days, label, value in time_hierarchy:
            if (end_time - start_time).days >= days:
                # Handle value ranges and promote to next level if needed
                if label == 'Day' and value > 7:
                    # If day > 7, promote to week
                    if use_wildcard:
                        composite_data = f'{self.namespace}:Week(*)'
                    else:
                        composite_data = f'{self.namespace}:Week({start_time.isocalendar()[1]})'
                    break
                elif label == 'Week' and value > 4:
                    # If week > 4, promote to month
                    if use_wildcard:
                        composite_data = f'{self.namespace}:Month(*)'
                    else:
                        composite_data = f'{self.namespace}:Month({month_names[start_time.month - 1]})'
                    break
                elif label == 'Month' and value > 12:
                    # If month > 12, promote to year
                    if use_wildcard:
                        composite_data = f'{self.namespace}:Year(*)'
                    else:
                        composite_data = f'{self.namespace}:Year({start_time.year})'
                    break
                
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

        # First get the hierarchy for start time
        start_hierarchy = self.get_hierarchy(start_time, duration, False)
        if not start_hierarchy:
            return "Current"

        # Extract the label and value from start hierarchy
        label = start_hierarchy.split('(')[0].split(':')[-1]
        start_value = start_hierarchy.split('(')[1].rstrip(')')

        # Get the corresponding value for end time
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                    'Friday', 'Saturday', 'Sunday']
        
        time_hierarchy = [
            (365, 'Year', end_time.year),
            (30, 'Month', month_names[end_time.month - 1]),
            (7, 'Week', end_time.isocalendar()[1]),
            (1, 'Day', day_names[end_time.weekday()]),
            (0, 'Hour', end_time.hour)
        ]

        end_value = None
        for days, h_label, value in time_hierarchy:
            if h_label == label:
                end_value = value
                break

        if end_value is None:
            return "Current"

        # Calculate the difference
        if label == 'Year':
            diff = int(end_value) - int(start_value)
        elif label == 'Month':
            diff = month_names.index(end_value) - month_names.index(start_value)
        elif label == 'Week':
            diff = int(end_value) - int(start_value)
        elif label == 'Day':
            diff = day_names.index(end_value) - day_names.index(start_value)
        else:
            diff = 0

        if diff == 0:
            return "Current"
        elif current_time < start_time:
            if use_wildcard:
                return "Next(*)"
            return f"Next({abs(diff)})"
        else:
            if use_wildcard:
                return "Previous(*)"
            return f"Previous({abs(diff)})"

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