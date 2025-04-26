import queue
import logging
import time
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

def web_input_func(prompt: str) -> str:
    """Function to handle web input"""
    global last_input_request, input_request_queue, input_response_queue, agent_initialized
    
    if prompt == "":
        prompt = "Hi, how can I help you today?"
    
    # If this is the same prompt as the last one, don't ask again
    if prompt == last_input_request and last_input_request is not None:
        logger.info(f"Duplicate input request detected: {prompt}")
        return "No response received. Please try again."
    
    logger.info(f"Web input function called with prompt: {prompt}")
    
    # Set the waiting flag
    set_agent_waiting_for_input(True)
    
    # Store the last input request
    last_input_request = prompt
    
    # Put the prompt in the input request queue
    input_request_queue.put(prompt)
    logger.info(f"Added prompt to input request queue: {prompt}")
    
    # Wait indefinitely for a response from the web UI
    try:
        while True:
            try:
                response = input_response_queue.get()  # Block until response is received
                if response:
                    logger.info(f"Received response from web UI: {response}")
                    set_agent_waiting_for_input(False)
                    last_input_request = None  # Reset the last input request
                    return response
            except queue.Empty:
                continue  # Keep waiting if no response yet
    except Exception as e:
        logger.error(f"Error in web_input_func: {str(e)}", exc_info=True)
        set_agent_waiting_for_input(False)
        last_input_request = None  # Reset the last input request
        return "An error occurred. Please try again."