import logging
from datetime import datetime
from .base_agent import BaseAgent
from ..web_input import get_user_input

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
        system_message = f"""You have access to multiple different applications which you must invoke to complete the user request. Output the name of the application from the applications given to you which must be invoked next. You will see the history of applications invoked and their results. Along with the name of the application, send a description of the task that application needs to perform with all the necessary data you have without explicitly sending the exact user request. Only send all the necessary information.

        List of the available application with description:
        Calendar: A calendar app with API to reserve, check availability and read the calendar data.
        Expedia: A travel booking application with APIs for searching, booking and paying for flights, hotels, rental cars, experiences like cruises.
        Wallet: A wallet application with saved cards and with APIs for adding, removing, updating and getting credit card information.
        ContactManager: A contact manager application with APIs to add, remove, update and get contact information.
        Trello: A Trello application with APIs to create, read, update and delete workspaces, boards, lists and cards.
        Game: A Tic Tac Toe game application with APIs to create, read, update and delete games.
        User: User proxy agent acting as a messenger to ask the user for input, comfirmation if there are choices to be made, etc.

        Think deeply and break the task into sub tasks for the applications. Explicity provide credentials, or any other information that is needed to complete the task after fetching them from the relevant application to the application that is invoking the task along the task description.
        
        First output the name of the application and then the description in the format, application: description. The description must contains all the required information for the application, do not make up data, if you need data ask the user to get the required data first before calling the application.
        
        Prefer invoking applications than asking the user to get the required data to reduce the overhead of the user.
        Only output one application and the description of the task for that application.

        When all tasks are completed from your end, output terminate along with the reason of termination.
        """
        
        tools = []
        
        super().__init__("Planner", system_message, tools, model_client, skip_permission_suffix=True, skip_input_tool_description=True) 