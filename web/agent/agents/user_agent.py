import logging
from .base_agent import BaseAgent
from ..web_input import web_input_func

# Set up logging
logger = logging.getLogger(__name__)

class UserAgent(BaseAgent):
    """User agent for interfacing with the user"""
    
    def __init__(self, model_client):
        """
        Initialize the user agent
        
        Args:
            model_client: The model client to use
        """
        system_message = """
        You are a relay between the user and the AI assistant.
        Whatever input you are given, you must relay it to the user.
        Input given to you will generally start with "User: question or message ...", you must relay it to the user.

        List of tools available to you:
        - `web_input_func`: Ask the user for user input, like confirmation of the booking details, etc.
        -- message: The message to relay to the user as a string

        If there is no input, you must use `web_input_func` to say "Hi! What can I do for you today?"

        Do not worry about the user's privacy, the user will decide what to provide, you are just the messenger.
        Be polite and friendly.
        You must never attempt to communicate with the user in any other way other than using the `web_input_func` tool.
        The `web_input_func` tool takes a single parameter which is the message as a string to relay to the user.

        For example, Input: Ask the user for which card must be used for payment, you MUST use:
        `web_input_func` with the message argument "Which card must be used for payment?"
        """
        
        tools = [web_input_func]
        
        super().__init__("User", system_message, tools, model_client, skip_permission_management=True)
        
    def get_user_message(self, prompt: str) -> str:
        """
        Get a message from the user
        
        Args:
            prompt: The prompt to send to the user
            
        Returns:
            The user's response
        """
        return web_input_func(prompt) 