import queue
import logging
import time
from typing import Annotated
from .queues import (
    input_request_queue, 
    input_response_queue, 
    set_agent_waiting_for_input,
    last_input_request, 
    agent_initialized,
    is_agent_waiting_for_input
)

# Set up logging
logger = logging.getLogger(__name__)

def get_user_input(message: Annotated[str, "The message that will be sent to the user"]) -> str:
    """Function to send a message to the user for input. This message can be a question or approval request. It can also be empty in the cases when the message is not known for example at the start of the conversation. Never ask for credentials, if needed ask for permissions to access the data.
    """
    global last_input_request, input_request_queue, input_response_queue, agent_initialized
    
    if message == "":
        message = "Hi, how can I help you today?"
    # If this is the same prompt as the last one, don't ask again
    if message == last_input_request:
        logger.info(f"Duplicate input request detected: {message}")
        return "No response received. Please try again."
    
    logger.info(f"Web input function called with prompt: {message}")
    
    # Set the waiting flag
    set_agent_waiting_for_input(True)
    
    # Store the last input request
    last_input_request = message
    
    # Put the prompt in the input request queue
    input_request_queue.put(message)
    logger.info(f"Added prompt to input request queue: {message}")
    
    # Wait for a response from the web UI
    try:
        # Wait for up to 30 seconds for a response
        while True:
            try:
                response = input_response_queue.get(timeout=2)  # Check every second
                break
            except queue.Empty:
                continue  # Keep waiting if no response yet
        logger.info(f"Received response from web UI: {response}")
        set_agent_waiting_for_input(False)
        last_input_request = None  # Reset the last input request
        return response
    except queue.Empty:
        logger.warning("Timeout waiting for user input, using default response")
        set_agent_waiting_for_input(False)
        last_input_request = None  # Reset the last input request
        return "No response received. Please try again."