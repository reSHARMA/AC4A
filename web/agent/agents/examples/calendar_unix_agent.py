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
    """Calendar API annotation using Unix timestamp intervals as the primary resource model.

    Main resource model: Calendar:UnixTimestampInterval(start-end) where start and end are Unix epoch seconds.
    Wildcard: Calendar:UnixTimestampInterval(*) meaning any interval.
    If only start is known (no end provided) we'll represent as start-* to indicate an open-ended interval.
    """

    def __init__(self):
        # Define Unix timestamp interval as the main resource
        unix_timestamp_interval = ResourceTypeTree.create_resource(
            'Calendar:UnixTimestampInterval',
            description='Unix timestamp interval representing a time span start-end in epoch seconds',
            examples=[
                '1704067200-1704070800',  # 2024-01-01 00:00 to 01:00 UTC
                '1735689600-1735693200',  # 2025-01-01 00:00 to 01:00 UTC
                '1767225600-1767229200'   # 2026-01-01 00:00 to 01:00 UTC
            ]
        )

        super().__init__(
            "CalendarUnix",
            [unix_timestamp_interval],
            [ResourceTypeTree('Read'), ResourceTypeTree('Write'), ResourceTypeTree('Create')]
        )

    def get_interval(self, start_time=None, end_time=None, use_wildcard=False):
        """Build interval resource string.

        Cases:
        - wildcard -> Calendar:UnixTimestampInterval(*)
        - start & end -> Calendar:UnixTimestampInterval(start-end)
        - start only -> Calendar:UnixTimestampInterval(start-*) (open ended)
        - none -> wildcard
        """
        if use_wildcard or start_time is None:
            return f'{self.namespace}:UnixTimestampInterval(*)'
        start_epoch = int(start_time.timestamp())
        if end_time is None:
            return f'{self.namespace}:UnixTimestampInterval({start_epoch}-*)'
        end_epoch = int(end_time.timestamp())
        return f'{self.namespace}:UnixTimestampInterval({start_epoch}-{end_epoch})'

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
        """Generate attributes for Unix timestamp interval operations.

        Supported kwargs patterns:
        - start_time & end_time (datetime): produce closed interval
        - start_time only: open-ended interval start-*
        - timestamp_interval (str 'start-end'): directly used
        - timestamp (int) legacy single point -> treat as point interval start-start
        - none -> wildcard
        """
        granular_data = None

        if 'timestamp_interval' in kwargs and kwargs['timestamp_interval']:
            interval = kwargs['timestamp_interval']
            granular_data = f'{self.namespace}:UnixTimestampInterval({interval})'
        elif 'start_time' in kwargs:
            start_time = kwargs.get('start_time')
            end_time = kwargs.get('end_time')
            granular_data = self.get_interval(start_time, end_time, wildcard)
        elif 'timestamp' in kwargs:  # legacy single point
            ts = kwargs['timestamp']
            granular_data = f'{self.namespace}:UnixTimestampInterval({ts}-{ts})'

        if granular_data is None:
            granular_data = self.get_interval(use_wildcard=True)

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
        """Returns what's still needed after subtracting what we have.

        Interprets resources as UnixTimestampInterval(start-end) where end or start may be '*'.
        Coverage rules:
        - If have is wildcard (*) -> satisfies any need.
        - If need is wildcard but have isn't -> not satisfied unless have also wildcard.
        - Closed interval coverage: have_start <= need_start AND have_end >= need_end.
        - Open-ended have (start-*) covers any need whose start >= have_start.
        - Point intervals represented as start-start.
        - Mismatched types -> not satisfied.
        """
        if not needs:
            return set()
        if not have:
            return needs

        def extract(parsed_list):
            if not parsed_list:
                return None, None
            resource_dict = parsed_list[0]
            key, value = next(iter(resource_dict.items()))
            if not key.startswith('Calendar:'):
                return None, None
            rtype = key[9:]  # strip 'Calendar:'
            return rtype, value

        needs_type, needs_interval = extract(needs)
        have_type, have_interval = extract(have)

        if not needs_type or not have_type:
            return needs
        if needs_type != have_type:
            return needs

        # Expect type to be 'UnixTimestampInterval'
        if needs_interval == '*':
            # Only satisfied if have is wildcard too
            return set() if have_interval == '*' else needs
        if have_interval == '*':
            return set()

        def parse_interval(interval_str):
            # interval_str like 'start-end'
            if '-' not in interval_str:
                return None, None
            s, e = interval_str.split('-', 1)
            start = int(s) if s != '*' and s else None
            end = int(e) if e != '*' and e else None
            return start, end

        n_start, n_end = parse_interval(needs_interval)
        h_start, h_end = parse_interval(have_interval)

        # If parsing failed, be conservative
        if n_start is None and n_end is None:
            return needs

        # Start coverage: have start must be <= need start (or have start unspecified)
        start_ok = (h_start is None) or (n_start is not None and h_start <= n_start)
        # End coverage: if need has an end, have must have end >= need end or open-ended
        if n_end is None:
            # Need is open-ended; require have open-ended and start_ok
            end_ok = (h_end is None)
        else:
            # Need has end; open-ended have (h_end None) ok, or have end >= need end
            end_ok = (h_end is None) or (h_end >= n_end)

        return set() if (start_ok and end_ok) else needs

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
    schedule_at_timestamp = _api_method("schedule_at_timestamp: Schedule an event during a specific Unix timestamp interval.")
    query_timestamp = _api_method("query_timestamp: Query events overlapping a specific Unix timestamp interval.")
    check_timestamp_availability = _api_method("check_timestamp_availability: Check availability for a Unix timestamp interval.")
    update_timestamp_event = _api_method("update_timestamp_event: Update an event defined by a Unix timestamp interval or single timestamp.")
    delete_timestamp_event = _api_method("delete_timestamp_event: Delete an event defined by a Unix timestamp interval or single timestamp.")


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

    async def schedule_at_timestamp(self, start_time: Annotated[datetime, "The start time of the event as offset-naive datetime"], end_time: Annotated[datetime | None, "The optional end time of the event as offset-naive datetime"] = None, description: Annotated[str, "The description of the event, can also be empty"] = "") -> str:
        """Schedule an event in a Unix timestamp interval (start_time to end_time). If end_time omitted, open-ended."""
        return await self._call_api('schedule_at_timestamp', start_time=start_time, end_time=end_time, description=description)
        
    async def query_timestamp(self, start_time: Annotated[datetime, "The start of the interval to query events for as offset-naive datetime"], end_time: Annotated[datetime | None, "The optional end of the interval to query events for as offset-naive datetime"] = None) -> str:
        """Query events overlapping the specified Unix timestamp interval."""
        return await self._call_api('query_timestamp', start_time=start_time, end_time=end_time)
        
    async def check_timestamp_availability(self, start_time: Annotated[datetime, "The start of the interval to check availability for as offset-naive datetime"], end_time: Annotated[datetime | None, "The optional end of the interval to check availability for as offset-naive datetime"] = None) -> str:
        """Check availability for a Unix timestamp interval."""
        return await self._call_api('check_timestamp_availability', start_time=start_time, end_time=end_time)
        
    async def update_timestamp_event(self, timestamp: Annotated[int | None, "Legacy: The Unix timestamp of the event to update (single point)"] = None, start_time: Annotated[datetime | None, "The start of the interval of the event to update"] = None, end_time: Annotated[datetime | None, "The optional end of the interval of the event to update"] = None, description: Annotated[str, "The new description for the event"] = "") -> str:
        """Update an event identified by a Unix timestamp interval (preferred) or a single timestamp (legacy)."""
        return await self._call_api('update_timestamp_event', timestamp=timestamp, start_time=start_time, end_time=end_time, description=description)
        
    async def delete_timestamp_event(self, timestamp: Annotated[int | None, "Legacy: The Unix timestamp of the event to delete"] = None, start_time: Annotated[datetime | None, "The start of the interval of the event to delete"] = None, end_time: Annotated[datetime | None, "The optional end of the interval of the event to delete"] = None) -> str:
        """Delete an event identified by a Unix timestamp interval (preferred) or a single timestamp (legacy)."""
        return await self._call_api('delete_timestamp_event', timestamp=timestamp, start_time=start_time, end_time=end_time)

