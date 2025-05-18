import logging
from .base_agent import BaseAgent
from ..web_input import get_user_input

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
        system_message = """You are a relay between the user and the AI assistant. Relay all input to the user using the `get_user_input` tool. For uninterpretable input, use `get_user_input` with an empty message.
Only communicate through the `get_user_input` tool. Be polite and friendly.
Example, "Input - User: Ask the user for which card must be used for payment, you MUST use:
`get_user_input` with the message argument "Which card must be used for payment?"
"""
        
        tools = [get_user_input]
        
        super().__init__("User", system_message, tools, model_client, skip_permission_management=True)
        
    def get_user_message(self, prompt: str) -> str:
        """
        Get a message from the user
        
        Args:
            prompt: The prompt to send to the user
            
        Returns:
            The user's response
        """
        return get_user_input(prompt) 