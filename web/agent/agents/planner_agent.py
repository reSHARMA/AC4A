import logging
from datetime import datetime
from .base_agent import BaseAgent

# Set up logging
logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    """Planner agent for coordinating other agents"""
    
    def __init__(self, model_client):
        """
        Initialize the planner agent
        
        Args:
            model_client: The model client to use
        """
        system_message = f"""You have access to multiple different applications which you must invoke to complete the user request. Output the name of the application from the applications given to you which must be invoked next. You will see the history of applications invoked and their results. Along with the name of the application, send a description of the task that application needs to perform with all the necessary data you have without explicitly sending the exact user request. Only send the necessary information.

        List of the available application with description:
        Calendar: A calendar app with API to reserve, check availability and read the calendar data.
        Expedia: A travel booking application with APIs for searching, booking and paying for flights, hotels, rental cars, experiences like cruises.
        Wallet: A wallet application with saved cards and with APIs for adding, removing, updating and getting credit card information.
        ContactManager: A contact manager application with APIs to add, remove, update and get contact information.
        PasswordManager: A password manager application with APIs to add, remove, update and get password information for various services and users.
        User: The user application only for asking the user for input and data.

        Think deeply and break the task into sub tasks for the application.
        First output the name of the application and then the description in the format, application: description. The description must contains all the required information for the application, do not make up data, if you need data invoke the User application to get the required data first before calling the application.
        Prefer invoking applications other than User application to reduce the human in the loop.
        Only output one application and the description of the task for that application.

        When all tasks are completed from your end, output terminate along with the reason of termination.

        Today's date is {datetime.now().strftime("%Y-%m-%d")}
        """
        
        tools = []
        
        super().__init__("Planner", system_message, tools, model_client) 