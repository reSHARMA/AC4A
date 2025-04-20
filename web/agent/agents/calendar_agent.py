import logging
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from ..web_input import web_input_func
from web.mock_app import CalendarAPI

# Set up logging
logger = logging.getLogger(__name__)

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