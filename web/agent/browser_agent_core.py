import logging
from enum import Enum
from typing import Dict, Any
import requests
import base64
from src.utils.dummy_data import call_openai_api

# Set up logging
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages that can be sent to the frontend"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    INTERNAL = "internal"  # For messages that should not be sent to frontend
    DEBUG = "debug"  # For debugging messages
    ERROR = "error"

class MessageVisibility(Enum):
    """Visibility levels for messages"""
    PUBLIC = "public"  # Visible to all
    INTERNAL = "internal"  # Only visible in logs
    DEBUG = "debug"  # Only visible in debug mode

# Store browser chat history
browser_chat_history = []

def create_message(content: str, role: str, msg_type: MessageType = MessageType.ASSISTANT, 
                  visibility: MessageVisibility = MessageVisibility.PUBLIC) -> Dict[str, Any]:
    """
    Create a message with metadata
    
    Args:
        content (str): The message content
        role (str): The role of the sender
        msg_type (MessageType): The type of message
        visibility (MessageVisibility): The visibility level of the message
        
    Returns:
        dict: Message with metadata
    """
    return {
        "role": role,
        "content": content,
        "type": msg_type.value,
        "visibility": visibility.value
    }

def handle_termination() -> dict:
    """
    Handle termination of the browser chat session
    
    Returns:
        dict: Response containing role and content
    """
    clear_browser_chat_history()
    return create_message(
        content="Chat session ended. Say Hi! to start a new session.",
        role="system",
        msg_type=MessageType.SYSTEM
    )

def process_browser_message(user_message: str) -> dict:
    """
    Process a browser chat message and return a response
    
    Args:
        user_message (str): The user's message
        
    Returns:
        dict: Response containing role and content
    """
    try:
        # Check for termination
        if user_message.lower() == 'terminate':
            return handle_termination()
            
        # Add user message to history
        user_msg = create_message(
            content=user_message,
            role="user",
            msg_type=MessageType.USER
        )
        browser_chat_history.append(user_msg)
        
        # Process with computer-use model
        response = process_with_computer_use(user_message)
        
        # Add response to history
        browser_chat_history.append(response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing browser message: {str(e)}", exc_info=True)
        return create_message(
            content=str(e),
            role="system",
            msg_type=MessageType.ERROR
        )

def get_browser_chat_history() -> list:
    """
    Get the browser chat history
    
    Returns:
        list: List of chat messages
    """
    return browser_chat_history

def clear_browser_chat_history() -> None:
    """
    Clear the browser chat history
    """
    browser_chat_history.clear()

def get_latest_screenshot() -> bytes:
    """
    Get the latest screenshot from the browser preview server
    
    Returns:
        bytes: Raw PNG image data
    """
    try:
        # Get the latest screenshot from the preview server
        response = requests.get('http://localhost:8080/latest-preview.png')
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Failed to get screenshot: {response.status_code}")
            return b''
    except Exception as e:
        logger.error(f"Error getting screenshot: {str(e)}", exc_info=True)
        return b''

def process_with_computer_use(user_input: str) -> Dict[str, Any]:
    """
    Process user input with computer-use model using the latest screenshot
    
    Args:
        user_input (str): The user's input/instruction
        
    Returns:
        dict: Response from the model
    """
    try:
        # Get the latest screenshot
        screenshot_data = get_latest_screenshot()
        if not screenshot_data:
            return create_message(
                content="Failed to get screenshot",
                role="system",
                msg_type=MessageType.ERROR
            )
            
        # Convert screenshot to base64
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Create the system prompt for computer use
        system_prompt = """You are an AI agent with the ability to control a browser. You can ask the user to do one action at a time with the keyboard or the mouse. You are given a task and you have to successfully complete it by asking the user to perform actions one by one.

        You will also be given a screenshot of the browser after each action and also the list of past actions. You should check the screenshot to see if your action was successful and decide what to do next. 

        Only output the next action to take or ask the user for confirmation or resolve choices or give missing information.
        Do not output any other text.
        Once you have completed the requested task you should output done."""
        
        global browser_chat_history
        _input = f"""
Task: {browser_chat_history[0]['content']}

The following is the history of interactions with the user:
"""
        for chat_item in browser_chat_history[1:]:
            _input += f"""
{chat_item['role']}: {chat_item['content']}
"""
        if user_input == "done" or user_input == "":
                _input += f"""
The user says they have completed the task. Check the screenshot to validate and move on to the next action to complete the task.
"""
        else:
                _input += f"""
User: {user_input}
"""
        # Create the input as a dictionary with text and image
        input_content = {
            "text": _input,
            "image": f"data:image/png;base64,{screenshot_base64}"
        }
        
        # Call the OpenAI API using the existing function
        response = call_openai_api(system_prompt, input_content, "computer-use")
        
        if response:
            return create_message(
                content=response,
                role="assistant",
                msg_type=MessageType.ASSISTANT
            )
        else:
            return create_message(
                content="No response generated from model",
                role="system",
                msg_type=MessageType.ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in computer use processing: {str(e)}", exc_info=True)
        return create_message(
            content=f"Error processing with computer-use model: {str(e)}",
            role="system",
            msg_type=MessageType.ERROR
        ) 