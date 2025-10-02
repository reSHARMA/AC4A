import logging
from datetime import datetime, timedelta
from typing import Annotated

from ..base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree
from src.utils.dummy_data import generate_dummy_data

logger = logging.getLogger(__name__)


class CalendarEventTypesAPIAnnotation(APIAnnotationBase):
    """Calendar API annotation using Events with Meeting/Reminder/AllDay types as the resource model."""
    
    def __init__(self):
        # Define resources: Event -> (Meeting | Reminder | AllDay)
        event = ResourceTypeTree.create_resource(
            'Calendar:Event',
            description='A calendar event',
            examples=['Team_Meeting', 'Doctor_Appointment', 'Birthday_Reminder']
        )
        ResourceTypeTree.create_resource('Calendar:Meeting', parent=event, description='A meeting event', examples=['Team_Standup', 'Client_Call', 'Board_Meeting'])
        ResourceTypeTree.create_resource('Calendar:Reminder', parent=event, description='A reminder event', examples=['Birthday_Reminder', 'Deadline_Alert', 'Medication_Reminder'])
        ResourceTypeTree.create_resource('Calendar:AllDay', parent=event, description='An all-day event', examples=['Holiday', 'Vacation', 'Conference'])

        super().__init__(
            "CalendarEventTypes",
            [event],
            [ResourceTypeTree('Read'), ResourceTypeTree('Write'), ResourceTypeTree('Create')]
        )

    def get_hierarchy(self, resource_type, title_or_message, use_wildcard):
        """Build simple resource hierarchy."""
        identifier = '*' if use_wildcard else title_or_message.replace(' ', '_')
        return f'{self.namespace}:{resource_type}({identifier})'

    def get_access_level(self, endpoint_name):
        """Get access level for endpoint using dictionary mapping."""
        access_map = {
            'schedule_meeting': 'Create',
            'create_reminder': 'Create', 
            'add_all_day_event': 'Create',
            'add_event': 'Create',
            'get_events_by_type': 'Read',
            'check_meeting_exists': 'Read',
            'check_reminder_exists': 'Read',
            'remove_event': 'Write'
        }
        return access_map.get(endpoint_name, 'Read')

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        """Generate attributes based on endpoint and parameters."""
        # Endpoint-specific resource type and parameter mappings
        endpoint_config = {
            'schedule_meeting': ('Meeting', 'title'),
            'create_reminder': ('Reminder', 'message'),
            'add_all_day_event': ('AllDay', 'title'),
            'get_events_by_type': (kwargs.get('event_type', 'Event'), '*'),
            'check_meeting_exists': ('Meeting', '*'),
            'check_reminder_exists': ('Reminder', '*'),
            'remove_event': ('Event', '*')
        }
        
        # Category to resource type mapping for add_event
        category_map = {
            'meeting': 'Meeting', 'appointment': 'Meeting',
            'reminder': 'Reminder', 'alert': 'Reminder', 
            'holiday': 'AllDay', 'vacation': 'AllDay', 'allday': 'AllDay'
        }
        
        if endpoint_name in endpoint_config:
            resource_type, param_key = endpoint_config[endpoint_name]
            if param_key == '*':
                granular_data = self.get_hierarchy(resource_type, '*', True)
            else:
                value = kwargs.get(param_key, '')
                granular_data = self.get_hierarchy(resource_type, value, wildcard)
        elif endpoint_name == 'add_event':
            title = kwargs.get('title', '')
            category = kwargs.get('category')
            resource_type = category_map.get(category.lower(), 'Event') if category else 'Event'
            granular_data = self.get_hierarchy(resource_type, title, wildcard)
        else:
            granular_data = self.get_hierarchy('Event', '*', True)
            
        return [{
            'granular_data': granular_data,
            'data_access': self.get_access_level(endpoint_name)
        }]


class CalendarEventTypesAPI:
    """Calendar API using Events with Meeting/Reminder/AllDay types for resource modeling."""
    
    def __init__(self, policy_system):
        self.annotation = CalendarEventTypesAPIAnnotation()
        self.policy_system = policy_system

    def resource_difference(self, needs, have):
        """Returns what's still needed after subtracting what we have."""
        if not needs:
            return set()
        if not have:
            return needs
        
        # Extract resource info: [{"Calendar:Meeting": "*"}] -> ("Meeting", "*")
        def extract_info(parsed_list):
            if not parsed_list:
                return None, None
            resource_dict = parsed_list[0]
            key, value = next(iter(resource_dict.items()))
            return (key[9:], value) if key.startswith('Calendar:') else (None, None)
        
        needs_type, needs_id = extract_info(needs)
        have_type, have_id = extract_info(have)
        
        if not needs_type or not have_type:
            return needs
        
        # Type compatibility: Event > {Meeting, Reminder, AllDay}
        type_ok = (needs_type == have_type or 
                  (have_type == 'Event' and needs_type in ['Meeting', 'Reminder', 'AllDay']))
        
        # ID compatibility: * means "all", exact match or have *
        id_ok = (needs_id == have_id or have_id == '*')
        
        return set() if (type_ok and id_ok) else needs

    @CalendarEventTypesAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarEventTypesAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    def _api_method(self, description):
        """Factory method for creating API methods."""
        @CalendarEventTypesAPIAnnotation.annotate
        def method(*args, **kwargs):
            return generate_dummy_data(description, **kwargs)
        return method

    # API methods using factory pattern
    schedule_meeting = _api_method("schedule_meeting: Schedule a meeting event.")
    create_reminder = _api_method("create_reminder: Create a reminder event.")
    add_all_day_event = _api_method("add_all_day_event: Add an all-day event.")
    add_event = _api_method("add_event: Add an event with optional category.")
    get_events_by_type = _api_method("get_events_by_type: Get events filtered by type (Meeting/Reminder/AllDay).")
    check_meeting_exists = _api_method("check_meeting_exists: Check if a meeting exists.")
    check_reminder_exists = _api_method("check_reminder_exists: Check if a reminder exists.")
    remove_event = _api_method("remove_event: Remove an event.")


class CalendarEventTypesAgent(BaseAgent):
    """Calendar agent using Events with Meeting/Reminder/AllDay types for resource modeling."""
    
    def __init__(self, model_client, policy_system):
        system_message = """
        You are a calendar agent that works with Events and their types (Meeting, Reminder, AllDay).
        Assume offset-naive datetime for simplicity.

        Output "done" when the task given to you is completed. Do not suggest any other actions to the user.
        If you are given a task which is not related to calendar, also return "done"
        """
        policy_system.register_api(CalendarEventTypesAPI)
        self.calendar_api = CalendarEventTypesAPI(policy_system)
        
        tools = [
            self.schedule_meeting,
            self.create_reminder,
            self.add_all_day_event,
            self.add_event,
            self.get_events_by_type,
            self.check_meeting_exists,
            self.check_reminder_exists,
            self.remove_event,
            get_user_input
        ]
        
        super().__init__("CalendarEventTypes", system_message, tools, model_client)
        
    async def _call_api(self, method_name: str, **kwargs) -> str:
        """Generic method to call API methods with logging."""
        logger.info(f"Calling CalendarEventTypesAPI {method_name} with {kwargs}")
        method = getattr(self.calendar_api, method_name)
        return method(**kwargs)

    async def schedule_meeting(self, start_time: Annotated[datetime, "The start time of the meeting as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the meeting as timedelta"], title: Annotated[str, "The title of the meeting"], attendees: Annotated[str, "The attendees of the meeting"]) -> str:
        """Schedule a meeting event."""
        return await self._call_api('schedule_meeting', start_time=start_time, duration=duration, title=title, attendees=attendees)
        
    async def create_reminder(self, start_time: Annotated[datetime, "The start time of the reminder as offset-naive datetime"], message: Annotated[str, "The reminder message"], priority: Annotated[str, "The priority of the reminder (High/Medium/Low)"]) -> str:
        """Create a reminder event."""
        return await self._call_api('create_reminder', start_time=start_time, message=message, priority=priority)
        
    async def add_all_day_event(self, date: Annotated[datetime, "The date of the all-day event as offset-naive datetime"], title: Annotated[str, "The title of the all-day event"], category: Annotated[str, "The category of the all-day event"]) -> str:
        """Add an all-day event."""
        return await self._call_api('add_all_day_event', date=date, title=title, category=category)
        
    async def add_event(self, start_time: Annotated[datetime, "The start time of the event as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the event as timedelta"], title: Annotated[str, "The title of the event"], attendees: Annotated[str, "The attendees of the event"], event_type: Annotated[str, "The type of the event (Meeting/Reminder/AllDay)"] = None) -> str:
        """Add an event."""
        return await self._call_api('add_event', start_time=start_time, duration=duration, title=title, attendees=attendees, event_type=event_type)
        
    async def get_events_by_type(self, start_time: Annotated[datetime, "The start time of the query as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the query as timedelta"], event_type: Annotated[str, "The event type to filter by (Meeting/Reminder/AllDay)"]) -> str:
        """Get events filtered by type."""
        return await self._call_api('get_events_by_type', start_time=start_time, duration=duration, event_type=event_type)
        
    async def check_meeting_exists(self, start_time: Annotated[datetime, "The start time of the meeting as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the meeting as timedelta"], title: Annotated[str, "The title of the meeting"]) -> str:
        """Check if a meeting exists."""
        return await self._call_api('check_meeting_exists', start_time=start_time, duration=duration, title=title)
        
    async def check_reminder_exists(self, start_time: Annotated[datetime, "The start time of the reminder as offset-naive datetime"], message: Annotated[str, "The reminder message"]) -> str:
        """Check if a reminder exists."""
        return await self._call_api('check_reminder_exists', start_time=start_time, message=message)
    
    async def remove_event(self, start_time: Annotated[datetime, "The start time of the event as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the event as timedelta"], title: Annotated[str, "The title of the event"]) -> str:
        """Remove an event."""
        return await self._call_api('remove_event', start_time=start_time, duration=duration, title=title)