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
        system_message = """You are a user agent responsible for interfacing with the user on behalf of a AI assistant.

        You can send a message to the user using the `get_user_message` tool.
        for example, to ask the user for which card must be used for payment, you can use the following message:
        `get_user_message` with the message "Which card must be used for payment?"

        Do not hesitate to ask the user for any information, the user will decide what to provide. You must never worry about the user's privacy, the user will decide what to provide.

        If there is nothing to ask or you are not sure, just say, "Hi! What can I do for you today?" using the `get_user_message` tool.
        """
        
        tools = [web_input_func]
        
        super().__init__("User", system_message, tools, model_client)
        
    def get_user_message(self, prompt: str) -> str:
        """
        Get a message from the user
        
        Args:
            prompt: The prompt to send to the user
            
        Returns:
            The user's response
        """
        return web_input_func(prompt) 