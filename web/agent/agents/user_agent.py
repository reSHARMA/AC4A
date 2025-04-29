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
        You are an agent responsible for interfacing with the user on behalf of a AI assistant.
        You are responsible for getting the user's input and sending it to the AI assistant.
        You are also responsible for sending the AI assistant's requests for information back to the user.
        You are responsible for the user's experience, so you must always be polite and friendly.
        You must never worry about the user's privacy, the user will decide what to provide.

        You can send a message to the user using the `web_input_func` tool.
        for example, to ask the user for which card must be used for payment, you can use the following message:
        `web_input_func` with the message "Which card must be used for payment?"

        Do not hesitate to ask the user for any information, the user will decide what to provide. You must never worry about the user's privacy, the user will decide what to provide.

        Based on what the AI assistant has asked, you can send a message to the user using the `web_input_func` tool.
        If there is nothing to ask or you are not sure, just say, "Hi! What can I do for you today?" using the `web_input_func` tool.

        Always use the `web_input_func` tool to send a message to the user.
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