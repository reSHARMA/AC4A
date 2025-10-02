import logging
from datetime import datetime, timedelta
from typing import Annotated

from ..base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree
from src.utils.dummy_data import generate_dummy_data

logger = logging.getLogger(__name__)


class CalendarUnixAPIAnnotation(APIAnnotationBase):
    """Calendar API annotation using Unix timestamps as the primary resource model."""
    
    def __init__(self):
        # Define Unix timestamp as the main resource
    unix_timestamp = ResourceTypeTree.create_resource(
            'Calendar:UnixTimestamp', 
            description='Unix timestamp representing a specific moment in time',
            examples=['1704067200', '1735689600', '1767225600']  # 2024-01-01, 2025-01-01, 2026-01-01
        )
        
        super().__init__(
            "CalendarUnix",
            [unix_timestamp],
            [ResourceTypeTree('Read'), ResourceTypeTree('Write'), ResourceTypeTree('Create')]
        )

    def get_timestamp(self, start_time, use_wildcard):
        """Convert datetime to Unix timestamp."""
        if use_wildcard:
            return f'{self.namespace}:UnixTimestamp(*)'
        else:
            timestamp = int(start_time.timestamp())
            return f'{self.namespace}:UnixTimestamp({timestamp})'

    def get_access_level(self, endpoint_name):
        """Get access level for endpoint using dictionary mapping."""
        access_map = {
            'schedule_at_timestamp': 'Create',
            'query_timestamp': 'Read',
            'check_timestamp_availability': 'Read',
            'update_timestamp_event': 'Write',
            'delete_timestamp_event': 'Write'
        }
        return access_map.get(endpoint_name, 'Read')

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        """Generate attributes for Unix timestamp operations."""
        # Handle different parameter patterns for Unix timestamp operations
        if 'start_time' in kwargs:
            start_time = kwargs['start_time']
            granular_data = self.get_timestamp(start_time, wildcard)
        elif 'timestamp' in kwargs:
            # For operations with specific timestamp
            timestamp = kwargs['timestamp']
            granular_data = f'{self.namespace}:UnixTimestamp({timestamp})'
        else:
            # Default fallback
            granular_data = f'{self.namespace}:UnixTimestamp(*)'
            
        return [{
            'granular_data': granular_data,
            'data_access': self.get_access_level(endpoint_name)
        }]


class CalendarUnixAPI:
    """Calendar API using Unix timestamps for resource modeling."""
    
    def __init__(self, policy_system):
        self.annotation = CalendarUnixAPIAnnotation()
        self.policy_system = policy_system

    def resource_difference(self, needs, have):
        """Returns what's still needed after subtracting what we have."""
        if not needs:
            return set()
        if not have:
            return needs
        
        # Extract resource info: [{"Calendar:UnixTimestamp": "1704067200"}] -> ("UnixTimestamp", "1704067200")
        def extract_info(parsed_list):
            if not parsed_list:
                return None, None
            resource_dict = parsed_list[0]
            key, value = next(iter(resource_dict.items()))
            return (key[9:], value) if key.startswith('Calendar:') else (None, None)
        
        needs_type, needs_timestamp = extract_info(needs)
        have_type, have_timestamp = extract_info(have)
        
        if not needs_type or not have_type:
            return needs
        
        # Type compatibility
        type_ok = (needs_type == have_type)
        
        # Timestamp compatibility: * means "all", exact match or have *
        timestamp_ok = (needs_timestamp == have_timestamp or have_timestamp == '*')
        
        return set() if (type_ok and timestamp_ok) else needs

    @CalendarUnixAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarUnixAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    def _api_method(self, description):
        """Factory method for creating API methods."""
        @CalendarUnixAPIAnnotation.annotate
        def method(*args, **kwargs):
            return generate_dummy_data(description, **kwargs)
        return method

    # API methods using factory pattern
    schedule_at_timestamp = _api_method("schedule_at_timestamp: Schedule an event at a specific Unix timestamp.")
    query_timestamp = _api_method("query_timestamp: Query events at a specific Unix timestamp.")
    check_timestamp_availability = _api_method("check_timestamp_availability: Check availability at a Unix timestamp.")
    update_timestamp_event = _api_method("update_timestamp_event: Update an event at a Unix timestamp.")
    delete_timestamp_event = _api_method("delete_timestamp_event: Delete an event at a Unix timestamp.")


class CalendarUnixAgent(BaseAgent):
    """Calendar agent using Unix timestamps for resource modeling."""
    
    def __init__(self, model_client, policy_system):
        system_message = """
        You are a calendar agent that works with Unix timestamps.
        Assume offset-naive datetime for simplicity.

        Output "done" when the task given to you is completed. Do not suggest any other actions to the user.
        If you are given a task which is not related to calendar, also return "done"
        """
        policy_system.register_api(CalendarUnixAPI)
        self.calendar_api = CalendarUnixAPI(policy_system)
        
        tools = [
            self.schedule_at_timestamp,
            self.query_timestamp,
            self.check_timestamp_availability,
            self.update_timestamp_event,
            self.delete_timestamp_event,
            get_user_input
        ]
        
        super().__init__("CalendarUnix", system_message, tools, model_client)
        
    async def _call_api(self, method_name: str, **kwargs) -> str:
        """Generic method to call API methods with logging."""
        logger.info(f"Calling CalendarUnixAPI {method_name} with {kwargs}")
        method = getattr(self.calendar_api, method_name)
        return method(**kwargs)

    async def schedule_at_timestamp(self, start_time: Annotated[datetime, "The start time of the event as offset-naive datetime"], description: Annotated[str, "The description of the event, can also be empty"]) -> str:
        """Schedule an event at a specific Unix timestamp."""
        return await self._call_api('schedule_at_timestamp', start_time=start_time, description=description)
        
    async def query_timestamp(self, start_time: Annotated[datetime, "The timestamp to query events for as offset-naive datetime"]) -> str:
        """Query events at a specific Unix timestamp."""
        return await self._call_api('query_timestamp', start_time=start_time)
        
    async def check_timestamp_availability(self, start_time: Annotated[datetime, "The timestamp to check availability for as offset-naive datetime"]) -> str:
        """Check availability at a Unix timestamp."""
        return await self._call_api('check_timestamp_availability', start_time=start_time)
        
    async def update_timestamp_event(self, timestamp: Annotated[int, "The Unix timestamp of the event to update"], description: Annotated[str, "The new description for the event"]) -> str:
        """Update an event at a Unix timestamp."""
        return await self._call_api('update_timestamp_event', timestamp=timestamp, description=description)
        
    async def delete_timestamp_event(self, timestamp: Annotated[int, "The Unix timestamp of the event to delete"]) -> str:
        """Delete an event at a Unix timestamp."""
        return await self._call_api('delete_timestamp_event', timestamp=timestamp)

