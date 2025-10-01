import logging
from datetime import datetime, timedelta
from typing import Annotated

from ..base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data

logger = logging.getLogger(__name__)


class CalendarEventsYMDApiAnnotation(APIAnnotationBase):
    """Calendar API annotation using Events with Year/Month/Day hierarchy as the resource model."""
    
    def __init__(self):
        # Define resources: Year -> Month -> Day -> Event
        calendar_year = AttributeTree.create_resource(
            'Calendar:Year', 
            description='The year of the calendar', 
            examples=['2025', '2026', '2027']
        )
        calendar_month = AttributeTree.create_resource(
            'Calendar:Month', 
            description='The month of the calendar', 
            examples=['January', 'February', 'December']
        )
        calendar_day = AttributeTree.create_resource(
            'Calendar:Day', 
            description='The day of the calendar must be a number between 1 and 31', 
            examples=['1', '2', '31']
        )
        calendar_event = AttributeTree.create_resource(
            'Calendar:Event', 
            description='A specific calendar event', 
            examples=['Team_Meeting', 'Doctor_Appointment', 'Birthday_Party']
        )
        calendar_meeting = AttributeTree.create_resource(
            'Calendar:Meeting', 
            description='A meeting event', 
            examples=['Team_Standup', 'Client_Call', 'Board_Meeting']
        )
        calendar_reminder = AttributeTree.create_resource(
            'Calendar:Reminder', 
            description='A reminder event', 
            examples=['Birthday_Reminder', 'Deadline_Alert', 'Medication_Reminder']
        )
        calendar_all_day = AttributeTree.create_resource(
            'Calendar:AllDay', 
            description='An all-day event', 
            examples=['Holiday', 'Vacation', 'Conference']
        )
        
        AttributeTree.add_edge(calendar_year, calendar_month)
        AttributeTree.add_edge(calendar_month, calendar_day)
        AttributeTree.add_edge(calendar_event, calendar_meeting)
        AttributeTree.add_edge(calendar_event, calendar_reminder)
        AttributeTree.add_edge(calendar_event, calendar_all_day)
        
        super().__init__(
            "CalendarEventsYMD",
            [calendar_year, calendar_event],
            [AttributeTree('Read'), AttributeTree('Write'), AttributeTree('Create')]
        )

    def get_hierarchy(self, start_time, duration, description, use_wildcard):
        """Build Year->Month->Day->Event hierarchy."""
        end_time = start_time + duration
        
        # Define month names
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        
        # Create event identifier
        event_id = f"{start_time.strftime('%H%M')}_{description.replace(' ', '_')}"
        
        if use_wildcard:
            return f'{self.namespace}:Year(*)::{self.namespace}:Month(*)::{self.namespace}:Day(*)::{self.namespace}:Event(*)'
        else:
            if start_time.year == end_time.year and start_time.month == end_time.month and start_time.day == end_time.day:
                # Same day
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Month({month_names[start_time.month - 1]})::{self.namespace}:Day({start_time.day})::{self.namespace}:Event({event_id})'
            elif start_time.year == end_time.year and start_time.month == end_time.month:
                # Same month, different days
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Month({month_names[start_time.month - 1]})::{self.namespace}:Day(*)::{self.namespace}:Event(*)'
            elif start_time.year == end_time.year:
                # Same year, different months
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Month(*)::{self.namespace}:Day(*)::{self.namespace}:Event(*)'
            else:
                # Different years
                return f'{self.namespace}:Year(*)::{self.namespace}:Month(*)::{self.namespace}:Day(*)::{self.namespace}:Event(*)'

    def get_access_level(self, endpoint_name):
        """Get access level for endpoint using dictionary mapping."""
        access_map = {
            'schedule_event_on_date': 'Create',
            'get_daily_events': 'Read',
            'get_monthly_events': 'Read',
            'get_yearly_events': 'Read',
            'check_date_availability': 'Read',
            'move_event_to_date': 'Write',
            'add_meeting': 'Create',
            'add_reminder': 'Create',
            'add_all_day_event': 'Create',
            'set_reminder_on_date': 'Create',
            'set_reminder_tomorrow': 'Create',
            'update_event': 'Write',
            'delete_event': 'Write'
        }
        return access_map.get(endpoint_name, 'Read')

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        # Handle different parameter patterns for YMD operations and allow returning
        # multiple attributes when both temporal and event subtrees are involved.
        access = self.get_access_level(endpoint_name)

        # Helper: month names
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']

        # Determine categories by endpoint name
        temporal_only_endpoints = {'get_daily_events', 'get_monthly_events', 'get_yearly_events', 'check_date_availability'}
        event_only_endpoints = {'add_meeting', 'add_reminder', 'add_all_day_event', 'update_event', 'delete_event'}
        combined_endpoints = {'schedule_event_on_date', 'move_event_to_date', 'set_reminder_on_date', 'set_reminder_tomorrow'}

        results = []

        # Build temporal resource if applicable
        def build_temporal(start_time, duration, use_wild):
            end_time = start_time + duration
            if use_wild:
                return f'{self.namespace}:Year(*)::{self.namespace}:Month(*)::{self.namespace}:Day(*)'
            if start_time.year == end_time.year and start_time.month == end_time.month and start_time.day == end_time.day:
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Month({month_names[start_time.month - 1]})::{self.namespace}:Day({start_time.day})'
            if start_time.year == end_time.year and start_time.month == end_time.month:
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Month({month_names[start_time.month - 1]})::{self.namespace}:Day(*)'
            if start_time.year == end_time.year:
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Month(*)::{self.namespace}:Day(*)'
            return f'{self.namespace}:Year(*)::{self.namespace}:Month(*)::{self.namespace}:Day(*)'

        # Build event resource if applicable
        def build_event(resource_type, identifier, use_wild):
            ident = '*' if use_wild else (identifier or '*')
            return f'{self.namespace}:{resource_type}({ident})'

        # Parameters
        start_time = kwargs.get('start_time') or kwargs.get('date')
        duration = kwargs.get('duration') or timedelta(hours=1)
        message = kwargs.get('message', '')
        title = kwargs.get('title', '')
        description = kwargs.get('description', '')
        event_id = kwargs.get('event_id')

        # EVENT-ONLY
        if endpoint_name in event_only_endpoints:
            if endpoint_name == 'add_meeting':
                results.append({'granular_data': build_event('Event', title.replace(' ', '_'), wildcard), 'data_access': access})
                results.append({'granular_data': build_event('Meeting', title.replace(' ', '_'), wildcard), 'data_access': access})
            elif endpoint_name == 'add_reminder':
                results.append({'granular_data': build_event('Event', message.replace(' ', '_'), wildcard), 'data_access': access})
                results.append({'granular_data': build_event('Reminder', message.replace(' ', '_'), wildcard), 'data_access': access})
            elif endpoint_name == 'add_all_day_event':
                results.append({'granular_data': build_event('Event', title.replace(' ', '_'), wildcard), 'data_access': access})
                results.append({'granular_data': build_event('AllDay', title.replace(' ', '_'), wildcard), 'data_access': access})
            elif endpoint_name in {'update_event', 'delete_event'} and event_id:
                results.append({'granular_data': build_event('Event', event_id, wildcard), 'data_access': access})
            else:
                results.append({'granular_data': build_event('Event', '*', True), 'data_access': access})
            return results

        # TEMPORAL-ONLY
        if endpoint_name in temporal_only_endpoints:
            if 'year' in kwargs and 'month' in kwargs:
                year = kwargs['year']
                month = kwargs['month']
                month_name = month_names[month - 1]
                results.append({'granular_data': f'{self.namespace}:Year({year})::{self.namespace}:Month({month_name})::{self.namespace}:Day(*)', 'data_access': access})
                return results
            if 'year' in kwargs:
                year = kwargs['year']
                results.append({'granular_data': f'{self.namespace}:Year({year})::{self.namespace}:Month(*)::{self.namespace}:Day(*)', 'data_access': access})
                return results
            if start_time is not None:
                results.append({'granular_data': build_temporal(start_time, duration, wildcard), 'data_access': access})
                return results

        # COMBINED (temporal + event) – return both resources
        if endpoint_name in combined_endpoints:
            # Temporal part
            if start_time is None:
                # Fallback to wildcard temporal if no date provided (e.g., tomorrow computed upstream)
                temporal_path = f'{self.namespace}:Year(*)::{self.namespace}:Month(*)::{self.namespace}:Day(*)'
            else:
                temporal_path = build_temporal(start_time, duration, wildcard)
            results.append({'granular_data': temporal_path, 'data_access': access})

            # Event part
            ident = (title or description or message or (event_id or '')).replace(' ', '_')
            if endpoint_name in {'set_reminder_on_date', 'set_reminder_tomorrow'}:
                results.append({'granular_data': build_event('Reminder', ident, wildcard), 'data_access': access})
            else:
                results.append({'granular_data': build_event('Event', ident, wildcard), 'data_access': access})
            return results

        # Default fallback: return both trees with all
        results.append({'granular_data': f'{self.namespace}:Year(*)::{self.namespace}:Month(*)::{self.namespace}:Day(*)', 'data_access': access})
        results.append({'granular_data': f'{self.namespace}:Event(*)', 'data_access': access})
        return results


class CalendarEventsYMDApi:
    """Calendar API using Events with Year/Month/Day hierarchy for resource modeling."""
    
    def __init__(self, policy_system):
        self.annotation = CalendarEventsYMDApiAnnotation()
        self.policy_system = policy_system

    def resource_difference(self, needs, have):
        """Returns what's still needed after subtracting what we have."""
        if not needs:
            return set()
        if not have:
            return needs
        
        # Extract resource info from the complex hierarchy
        def extract_info(parsed_list):
            if not parsed_list:
                return None, None, None, None, None
            resource_dict = parsed_list[0]
            year = resource_dict.get('Calendar:Year', None)
            month = resource_dict.get('Calendar:Month', None)
            day = resource_dict.get('Calendar:Day', None)
            event = resource_dict.get('Calendar:Event', None)
            event_type = resource_dict.get('Calendar:Meeting', None) or resource_dict.get('Calendar:Reminder', None) or resource_dict.get('Calendar:AllDay', None)
            return year, month, day, event, event_type
        
        needs_year, needs_month, needs_day, needs_event, needs_type = extract_info(needs)
        have_year, have_month, have_day, have_event, have_type = extract_info(have)
        
        if not needs_year and not needs_event:
            return needs
        
        # Check temporal hierarchy coverage (Year -> Month -> Day)
        year_covered = (needs_year == have_year or have_year == '*' or not needs_year)
        month_covered = (needs_month == have_month or have_month == '*' or not needs_month)
        day_covered = (needs_day == have_day or have_day == '*' or not needs_day)
        
        # Check event hierarchy coverage (Event -> {Meeting, Reminder, AllDay})
        event_covered = (needs_event == have_event or have_event == '*' or not needs_event)
        type_covered = (needs_type == have_type or have_type == '*' or not needs_type)
        
        # Both hierarchies must be satisfied
        temporal_ok = year_covered and month_covered and day_covered
        event_ok = event_covered and type_covered
        
        return set() if (temporal_ok and event_ok) else needs

    @CalendarEventsYMDApiAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarEventsYMDApiAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    def _api_method(self, description):
        """Factory method for creating API methods."""
        @CalendarEventsYMDApiAnnotation.annotate
        def method(*args, **kwargs):
            return generate_dummy_data(description, **kwargs)
        return method

    # API methods using factory pattern
    schedule_event_on_date = _api_method("schedule_event_on_date: Schedule an event on a specific date.")
    get_daily_events = _api_method("get_daily_events: Get all events for a specific day.")
    get_monthly_events = _api_method("get_monthly_events: Get all events for a specific month.")
    get_yearly_events = _api_method("get_yearly_events: Get all events for a specific year.")
    check_date_availability = _api_method("check_date_availability: Check availability for a specific date.")
    move_event_to_date = _api_method("move_event_to_date: Move an event to a different date.")
    add_meeting = _api_method("add_meeting: Add a meeting event.")
    add_reminder = _api_method("add_reminder: Add a reminder event.")
    add_all_day_event = _api_method("add_all_day_event: Add an all-day event.")
    set_reminder_on_date = _api_method("set_reminder_on_date: Set a reminder on a specific date.")
    set_reminder_tomorrow = _api_method("set_reminder_tomorrow: Set a reminder for tomorrow.")
    update_event = _api_method("update_event: Update an existing event.")
    delete_event = _api_method("delete_event: Delete an event.")


class CalendarEventsYMDAgent(BaseAgent):
    """Calendar agent using Events with Year/Month/Day hierarchy for resource modeling."""
    
    def __init__(self, model_client, policy_system):
        system_message = """
        You are a calendar agent that works with Events organized by Year/Month/Day hierarchy.
        Assume offset-naive datetime for simplicity.

        Output "done" when the task given to you is completed. Do not suggest any other actions to the user.
        If you are given a task which is not related to calendar, also return "done"
        """
        policy_system.register_api(CalendarEventsYMDApi)
        self.calendar_api = CalendarEventsYMDApi(policy_system)
        
        tools = [
            self.schedule_event_on_date,
            self.get_daily_events,
            self.get_monthly_events,
            self.get_yearly_events,
            self.check_date_availability,
            self.move_event_to_date,
            self.add_meeting,
            self.add_reminder,
            self.add_all_day_event,
            self.set_reminder_on_date,
            self.set_reminder_tomorrow,
            self.update_event,
            self.delete_event,
            get_user_input
        ]
        
        super().__init__("CalendarEventsYMD", system_message, tools, model_client)
        
    async def _call_api(self, method_name: str, **kwargs) -> str:
        """Generic method to call API methods with logging."""
        logger.info(f"Calling CalendarEventsYMDApi {method_name} with {kwargs}")
        method = getattr(self.calendar_api, method_name)
        return method(**kwargs)

    async def schedule_event_on_date(self, start_time: Annotated[datetime, "The start time of the event as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the event as timedelta"], title: Annotated[str, "The title of the event"], location: Annotated[str, "The location of the event"]) -> str:
        """Schedule an event on a specific date."""
        return await self._call_api('schedule_event_on_date', start_time=start_time, duration=duration, title=title, location=location)
        
    async def get_daily_events(self, date: Annotated[datetime, "The date to get events for as offset-naive datetime"]) -> str:
        """Get all events for a specific day."""
        return await self._call_api('get_daily_events', date=date)
        
    async def get_monthly_events(self, year: Annotated[int, "The year"], month: Annotated[int, "The month (1-12)"]) -> str:
        """Get all events for a specific month."""
        return await self._call_api('get_monthly_events', year=year, month=month)
        
    async def get_yearly_events(self, year: Annotated[int, "The year"]) -> str:
        """Get all events for a specific year."""
        return await self._call_api('get_yearly_events', year=year)
        
    async def check_date_availability(self, date: Annotated[datetime, "The date to check availability for as offset-naive datetime"], duration: Annotated[timedelta, "The duration to check availability for as timedelta"]) -> str:
        """Check availability for a specific date."""
        return await self._call_api('check_date_availability', date=date, duration=duration)
        
    async def move_event_to_date(self, event_id: Annotated[str, "The ID of the event to move"], new_date: Annotated[datetime, "The new date for the event as offset-naive datetime"]) -> str:
        """Move an event to a different date."""
        return await self._call_api('move_event_to_date', event_id=event_id, new_date=new_date)
        
    async def add_meeting(self, start_time: Annotated[datetime, "The start time of the meeting as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the meeting as timedelta"], title: Annotated[str, "The title of the meeting"], attendees: Annotated[str, "The attendees of the meeting"]) -> str:
        """Add a meeting event."""
        return await self._call_api('add_meeting', start_time=start_time, duration=duration, title=title, attendees=attendees)
        
    async def add_reminder(self, start_time: Annotated[datetime, "The start time of the reminder as offset-naive datetime"], message: Annotated[str, "The reminder message"], priority: Annotated[str, "The priority of the reminder (High/Medium/Low)"]) -> str:
        """Add a reminder event."""
        return await self._call_api('add_reminder', start_time=start_time, message=message, priority=priority)
        
    async def add_all_day_event(self, date: Annotated[datetime, "The date of the all-day event as offset-naive datetime"], title: Annotated[str, "The title of the all-day event"], category: Annotated[str, "The category of the all-day event"]) -> str:
        """Add an all-day event."""
        return await self._call_api('add_all_day_event', date=date, title=title, category=category)
        
    async def set_reminder_on_date(self, date: Annotated[datetime, "The date to set the reminder for as offset-naive datetime"], message: Annotated[str, "The reminder message"], priority: Annotated[str, "The priority of the reminder (High/Medium/Low)"]) -> str:
        """Set a reminder on a specific date."""
        # Use date as start_time with 1-hour duration by convention
        start_time = date
        duration = timedelta(hours=1)
        return await self._call_api('set_reminder_on_date', date=date, start_time=start_time, duration=duration, message=message, priority=priority)

    async def set_reminder_tomorrow(self, message: Annotated[str, "The reminder message"], priority: Annotated[str, "The priority of the reminder (High/Medium/Low)"]) -> str:
        """Set a reminder for tomorrow (local naive date)."""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        date = datetime(tomorrow.year, tomorrow.month, tomorrow.day)
        start_time = date
        duration = timedelta(hours=1)
        return await self._call_api('set_reminder_tomorrow', date=date, start_time=start_time, duration=duration, message=message, priority=priority)

    async def update_event(self, event_id: Annotated[str, "The ID of the event to update"], title: Annotated[str, "The new title for the event"], description: Annotated[str, "The new description for the event"]) -> str:
        """Update an existing event."""
        return await self._call_api('update_event', event_id=event_id, title=title, description=description)
        
    async def delete_event(self, event_id: Annotated[str, "The ID of the event to delete"]) -> str:
        """Delete an event."""
        return await self._call_api('delete_event', event_id=event_id)
