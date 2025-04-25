import queue
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create queues for communication between the agent and the web app
input_request_queue = queue.Queue()  # Queue for sending input requests to the web UI
input_response_queue = queue.Queue()  # Queue for receiving responses from the web UI
agent_message_queue = queue.Queue()  # Queue for sending agent messages to the web UI

# Global variable to store the current user input
current_user_input = ""

# Global variables for agent session management
agent_session_active = False
agent_waiting_for_input_flag = False
agent_group_chat = None
agent_thread = None
agent_loop = None
agent_initialized = False  # New flag to track if agent has been initialized
last_input_request = None  # Track the last input request to avoid duplicate

def get_next_input_request():
    """Get the next input request from the queue"""
    try:
        global input_request_queue
        return input_request_queue.get_nowait()
    except queue.Empty:
        return None

def submit_user_input(user_input: str):
    """Submit user input to the agent"""
    global current_user_input, agent_session_active, last_input_request, input_response_queue
    
    logger.info(f"Submitting user input: {user_input}")
    current_user_input = user_input
    
    # Reset the last input request to avoid duplicate requests
    last_input_request = None
    
    # Put the user input in the response queue
    input_response_queue.put(user_input)

def get_next_agent_message():
    """Get the next agent message from the queue"""
    global agent_message_queue
    try:
        global agent_message_queue
        return agent_message_queue.get_nowait()
    except queue.Empty:
        return None

def is_agent_waiting_for_input():
    """Check if the agent is waiting for input"""
    global agent_waiting_for_input_flag
    # logger.info(f"Agent waiting for input: {agent_waiting_for_input_flag}")
    return agent_waiting_for_input_flag

def set_agent_waiting_for_input(waiting: bool):
    """Set the agent waiting for input flag"""
    global agent_waiting_for_input_flag
    agent_waiting_for_input_flag = waiting
    logger.info(f"Agent waiting for input set to: {agent_waiting_for_input_flag}")

def is_agent_session_active():
    """Check if the agent session is active"""
    # logger.info(f"Agent session active: {agent_session_active}")
    return agent_session_active

def set_agent_session_active(active: bool):
    """Set the agent session active flag"""
    global agent_session_active
    agent_session_active = active
    logger.info(f"Agent session active set to: {agent_session_active}")