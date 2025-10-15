import logging
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree
from src.utils.dummy_data import generate_dummy_data
from config import WILDCARD
from typing import Annotated

# Set up logging
logger = logging.getLogger(__name__)


class CalendarAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        # Define resources with metadata and edges: Calendar:Year -> Calendar:Month -> Calendar:Day -> Calendar:Hour
        calendar_year = ResourceTypeTree.create_resource('Calendar:Year', description='The year of the calendar', examples=['2025', '2026', '2027'])
        calendar_month = ResourceTypeTree.create_resource('Calendar:Month', parent=calendar_year, description='The month of the calendar', examples=['January', 'February', 'December'])
        calendar_day = ResourceTypeTree.create_resource('Calendar:Day', parent=calendar_month, description='The day of the calendar must be a number between 1 and 31', examples=['1', '2', '31'])
        calendar_hour = ResourceTypeTree.create_resource('Calendar:Hour', parent=calendar_day, description='The hour of the calendar must be a number between 0 and 23', examples=['0', '1', '23'])

        # New three-argument init: [granular_data], [data_access], omit position (default applies)
        super().__init__(
            "Calendar",
            [calendar_year],
            [ResourceTypeTree('Read'), ResourceTypeTree('Write'), ResourceTypeTree('Create')]
        )

    def get_hierarchy(self, start_time, duration, use_wildcard):
        end_time = start_time + duration
        
        # Define month names
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        
        # Create time hierarchies for start and end times
        start_hierarchy = [
            (365, 'Year', start_time.year),
            (30, 'Month', month_names[start_time.month - 1]),
            (1, 'Day', start_time.day),
            (0, 'Hour', start_time.hour)
        ]
        
        end_hierarchy = [
            (365, 'Year', end_time.year),
            (30, 'Month', month_names[end_time.month - 1]),
            (1, 'Day', end_time.day),
            (0, 'Hour', end_time.hour)
        ]

        # Find the first differing node and build complete path
        composite_data = []
        for (days, label, start_value), (_, _, end_value) in zip(start_hierarchy, end_hierarchy):
            if use_wildcard:
                composite_data.append(f'{self.namespace}:{label}(*)')
            else:
                composite_data.append(f'{self.namespace}:{label}({start_value})')
            
            if start_value != end_value:
                break

        return '::'.join(composite_data)

    def get_access_level(self, endpoint_name):
        if 'reserve' in endpoint_name or 'create' in endpoint_name or 'add' in endpoint_name:
            return 'Create'
        elif 'update' in endpoint_name or 'edit' in endpoint_name or 'modify' in endpoint_name:
            return 'Write'
        else:
            return 'Read'

    def get_time_period(self, start_time, duration, use_wildcard):
        end_time = start_time + duration
        logger.error(f"Start time: {start_time}, End time: {end_time}")
        
        # Define month names
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        
        # Create time hierarchies for start and end times
        start_hierarchy = [
            (365, 'Year', start_time.year),
            (30, 'Month', month_names[start_time.month - 1]),
            (1, 'Day', start_time.day),
            (0, 'Hour', start_time.hour)
        ]
        
        end_hierarchy = [
            (365, 'Year', end_time.year),
            (30, 'Month', month_names[end_time.month - 1]),
            (1, 'Day', end_time.day),
            (0, 'Hour', end_time.hour)
        ]

        # Find the first differing node and calculate difference
        for (days, label, start_value), (_, _, end_value) in zip(start_hierarchy, end_hierarchy):
            if start_value != end_value:
                # Calculate difference based on the type of value
                if label == 'Year':
                    diff = int(end_value) - int(start_value)
                elif label == 'Month':
                    diff = month_names.index(end_value) - month_names.index(start_value)
                elif label == 'Day':
                    diff = int(end_value) - int(start_value)
                else:  # Hour
                    diff = int(end_value) - int(start_value)
                
                # Return position based on difference
                if -1 <= diff <= 1:  # If difference is within 1 unit, consider it Current
                    return "Current"
                elif diff > 1:
                    if use_wildcard:
                        return "Next(*)"
                    return f"Next({abs(diff)})"
                else:  # diff < -1
                    if use_wildcard:
                        return "Previous(*)"
                    return f"Previous({abs(diff)})"
        
        # If all values are same, return Current
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        start_time = kwargs['start_time']
        duration = kwargs['duration']
        return [{
            'granular_data': self.get_hierarchy(start_time, duration, wildcard),
            'data_access': self.get_access_level(endpoint_name)
        }]

class CalendarAPI:
    def __init__(self, policy_system):
        self.annotation = CalendarAPIAnnotation()
        self.policy_system = policy_system

    @CalendarAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

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

        Output "done" when the task given to you is completed. Do not suggest any other actions to the user.
        If you are given a task which is not related to calendar, also return "done"
        """
        policy_system.register_api(CalendarAPI)
        self.calendar_api = CalendarAPI(policy_system)
        
        tools = [
            self.calendar_reserve,
            self.calendar_read,
            self.calendar_check_availability,
            get_user_input
        ]
        
        super().__init__("Calendar", system_message, tools, model_client)
        
    async def calendar_reserve(self, start_time: Annotated[datetime, "The start time of the reservation as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the reservation as timedelta"], description: Annotated[str, "The description of the reservation, can also be empty"]) -> str:
        """
        Reserve a time slot in the calendar
        """
        logger.info(f"Calling CalendarAPI reserve with start_time={start_time}, duration={duration}, description={description}")
        result = self.calendar_api.reserve(start_time=start_time, duration=duration, description=description)
        return result
        
    async def calendar_read(self, start_time: Annotated[datetime, "The start time of data to be read as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the reading as timedelta"]) -> str:
        """
        Read calendar entries
        """
        logger.info(f"Calling CalendarAPI read with start_time={start_time}, duration={duration}")
        result = self.calendar_api.read(start_time=start_time, duration=duration)
        return result
        
    async def calendar_check_availability(self, start_time: Annotated[datetime, "The start time of the availability check as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the availability check as timedelta"]) -> str:
        """
        Check availability for a time slot
        """
        logger.info(f"Calling CalendarAPI check_available with start_time={start_time}, duration={duration}")
        result = self.calendar_api.check_available(start_time=start_time, duration=duration)
        return result 