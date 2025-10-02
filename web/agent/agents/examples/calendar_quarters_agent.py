import logging
from datetime import datetime, timedelta
from typing import Annotated

from ..base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree
from src.utils.dummy_data import generate_dummy_data

logger = logging.getLogger(__name__)


class CalendarQuartersAPIAnnotation(APIAnnotationBase):
    """Calendar API annotation using Years and Quarters as the resource model."""

    def __init__(self):
        # Define resources: Year -> Quarter
        calendar_year = ResourceTypeTree.create_resource(
            'Calendar:Year',
            description='The year of the calendar',
            examples=['2025', '2026', '2027']
        )
        ResourceTypeTree.create_resource(
            'Calendar:Quarter', parent=calendar_year,
            description='The quarter of the year (Q1, Q2, Q3, Q4)',
            examples=['Q1', 'Q2', 'Q3', 'Q4']
        )

        super().__init__(
            "CalendarQuarters",
            [calendar_year],
            [ResourceTypeTree('Read'), ResourceTypeTree('Write'), ResourceTypeTree('Create')]
        )

    def get_quarter_from_month(self, month):
        """Convert month number to quarter."""
        if month <= 3:
            return 'Q1'
        elif month <= 6:
            return 'Q2'
        elif month <= 9:
            return 'Q3'
        else:
            return 'Q4'

    def get_hierarchy(self, start_time, duration, use_wildcard):
        """Build Year->Quarter hierarchy for the time period."""
        end_time = start_time + duration
        
        # Get quarters for start and end times
        start_quarter = self.get_quarter_from_month(start_time.month)
        end_quarter = self.get_quarter_from_month(end_time.month)
        
        if use_wildcard:
            return f'{self.namespace}:Year(*)::{self.namespace}:Quarter(*)'
        else:
            if start_time.year == end_time.year and start_quarter == end_quarter:
                # Same year and quarter
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Quarter({start_quarter})'
            elif start_time.year == end_time.year:
                # Same year, different quarters
                return f'{self.namespace}:Year({start_time.year})::{self.namespace}:Quarter(*)'
            else:
                # Different years
                return f'{self.namespace}:Year(*)::{self.namespace}:Quarter(*)'

    def get_access_level(self, endpoint_name):
        """Get access level for endpoint using dictionary mapping."""
        access_map = {
            'plan_quarterly_events': 'Create',
            'schedule_quarterly_recurring': 'Create',
            'get_quarterly_summary': 'Read',
            'check_quarter_availability': 'Read'
        }
        return access_map.get(endpoint_name, 'Read')

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        """Generate attributes for Year->Quarter operations."""
        # Handle different parameter patterns for quarterly operations
        if 'start_time' in kwargs and 'duration' in kwargs:
            start_time = kwargs['start_time']
            duration = kwargs['duration']
            granular_data = self.get_hierarchy(start_time, duration, wildcard)
        elif 'year' in kwargs and 'month' in kwargs:
            # For get_monthly_events operation - convert month to quarter
            year = kwargs['year']
            month = kwargs['month']
            quarter = self.get_quarter_from_month(month)
            granular_data = f'{self.namespace}:Year({year})::{self.namespace}:Quarter({quarter})'
        elif 'year' in kwargs:
            # For get_yearly_events operation
            year = kwargs['year']
            granular_data = f'{self.namespace}:Year({year})::{self.namespace}:Quarter(*)'
        else:
            # Default fallback
            granular_data = f'{self.namespace}:Year(*)::{self.namespace}:Quarter(*)'
            
        return [{
            'granular_data': granular_data,
            'data_access': self.get_access_level(endpoint_name)
        }]


class CalendarQuartersAPI:
    """Calendar API using Years and Quarters for resource modeling."""
    
    def __init__(self, policy_system):
        self.annotation = CalendarQuartersAPIAnnotation()
        self.policy_system = policy_system

    def resource_difference(self, needs, have):
        """Returns what's still needed after subtracting what we have."""
        if not needs:
            return set()
        if not have:
            return needs
        
        # Extract resource info: [{"Calendar:Year": "2025", "Calendar:Quarter": "Q1"}] -> ("Year", "2025", "Quarter", "Q1")
        def extract_info(parsed_list):
            if not parsed_list:
                return None, None
            resource_dict = parsed_list[0]
            year_key = 'Calendar:Year'
            quarter_key = 'Calendar:Quarter'
            year_value = resource_dict.get(year_key, None)
            quarter_value = resource_dict.get(quarter_key, None)
            return year_value, quarter_value
        
        needs_year, needs_quarter = extract_info(needs)
        have_year, have_quarter = extract_info(have)
        
        if not needs_year or not have_year:
            return needs
        
        # Check year coverage
        year_covered = (needs_year == have_year or have_year == '*')
        if not year_covered:
            return needs  # Different year, still need everything
        
        # Check quarter coverage
        quarter_covered = (needs_quarter == have_quarter or have_quarter == '*')
        if quarter_covered:
            return set()  # Fully satisfied
        
        # Need to calculate missing quarters
        if needs_quarter == '*':
            # Need all quarters, but have specific quarter
            # Return missing quarters
            all_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            missing_quarters = [q for q in all_quarters if q != have_quarter]
            return [{f'Calendar:Year': needs_year, f'Calendar:Quarter': q} for q in missing_quarters]
        else:
            # Need specific quarter, don't have it
            return needs

    @CalendarQuartersAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarQuartersAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    def _api_method(self, description):
        """Factory method for creating API methods."""
        @CalendarQuartersAPIAnnotation.annotate
        def method(*args, **kwargs):
            return generate_dummy_data(description, **kwargs)
        return method

    # API methods using factory pattern
    plan_quarterly_events = _api_method("plan_quarterly_events: Plan events for a specific quarter.")
    get_quarterly_summary = _api_method("get_quarterly_summary: Get summary of events for a quarter.")
    check_quarter_availability = _api_method("check_quarter_availability: Check availability for a quarter.")
    schedule_quarterly_recurring = _api_method("schedule_quarterly_recurring: Schedule recurring events for a quarter.")


class CalendarQuartersAgent(BaseAgent):
    """Calendar agent using Years and Quarters for resource modeling."""
    
    def __init__(self, model_client, policy_system):
        system_message = """
        You are a calendar agent that works with Years and Quarters.
        Assume offset-naive datetime for simplicity.

        Output "done" when the task given to you is completed. Do not suggest any other actions to the user.
        If you are given a task which is not related to calendar, also return "done"
        """
        policy_system.register_api(CalendarQuartersAPI)
        self.calendar_api = CalendarQuartersAPI(policy_system)
        
        tools = [
            self.plan_quarterly_events,
            self.get_quarterly_summary,
            self.check_quarter_availability,
            self.schedule_quarterly_recurring,
            get_user_input
        ]
        
        super().__init__("CalendarQuarters", system_message, tools, model_client)
        
    async def _call_api(self, method_name: str, **kwargs) -> str:
        """Generic method to call API methods with logging."""
        logger.info(f"Calling CalendarQuartersAPI {method_name} with {kwargs}")
        method = getattr(self.calendar_api, method_name)
        return method(**kwargs)

    async def plan_quarterly_events(self, start_time: Annotated[datetime, "The start time of the planning period as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the planning period as timedelta"], description: Annotated[str, "The description of the quarterly planning, can also be empty"]) -> str:
        """Plan events for a specific quarter."""
        return await self._call_api('plan_quarterly_events', start_time=start_time, duration=duration, description=description)
        
    async def get_quarterly_summary(self, start_time: Annotated[datetime, "The start time of the quarter as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the quarter as timedelta"]) -> str:
        """Get summary of events for a quarter."""
        return await self._call_api('get_quarterly_summary', start_time=start_time, duration=duration)
        
    async def check_quarter_availability(self, start_time: Annotated[datetime, "The start time of the quarter as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the quarter as timedelta"]) -> str:
        """Check availability for a quarter."""
        return await self._call_api('check_quarter_availability', start_time=start_time, duration=duration)
        
    async def schedule_quarterly_recurring(self, start_time: Annotated[datetime, "The start time of the quarter as offset-naive datetime"], duration: Annotated[timedelta, "The duration of the quarter as timedelta"], event_type: Annotated[str, "The type of recurring event"]) -> str:
        """Schedule recurring events for a quarter."""
        return await self._call_api('schedule_quarterly_recurring', start_time=start_time, duration=duration, event_type=event_type)

