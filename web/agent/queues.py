import queue
import logging
import threading

# Set up logging
logger = logging.getLogger(__name__)

# Create queues for communication between the agent and the web app
input_request_queue = queue.Queue()  # Queue for sending input requests to the web UI
input_response_queue = queue.Queue()  # Queue for receiving responses from the web UI
agent_message_queue = queue.Queue()  # Queue for sending agent messages to the web UI

# Create separate queues for video mode
video_input_request_queue = queue.Queue()  # Queue for video mode input requests
video_input_response_queue = queue.Queue()  # Queue for video mode responses
video_agent_message_queue = queue.Queue()  # Queue for video mode agent messages

# Global variable to store the current user input
current_user_input = ""
current_video_input = ""  # Store video mode input separately

# Global variables for agent session management
agent_session_active = False
video_session_active = False  # Track video mode session separately
agent_waiting_for_input_flag = False
video_waiting_for_input_flag = False  # Track video mode input waiting separately
agent_group_chat = None
agent_thread = None
agent_loop = None
agent_initialized = False  # New flag to track if agent has been initialized
last_input_request = None  # Track the last input request to avoid duplicate
last_video_input_request = None  # Track the last video mode input request

# Browser mode specific queues and flags
browser_message_queue = queue.Queue()
browser_input_request_queue = queue.Queue()
browser_input_response_queue = queue.Queue()
current_browser_input = None
browser_session_active = False
browser_waiting_for_input = False
last_browser_input_request = None

def get_next_input_request(is_video_mode=False):
    """Get the next input request from the queue"""
    try:
        queue_to_use = video_input_request_queue if is_video_mode else input_request_queue
        return queue_to_use.get_nowait()
    except queue.Empty:
        return None

def submit_user_input(user_input: str, is_video_mode=False):
    """Submit user input to the agent"""
    global current_user_input, current_video_input, agent_session_active, video_session_active
    global last_input_request, last_video_input_request, input_response_queue, video_input_response_queue
    
    logger.info(f"Submitting {'video' if is_video_mode else 'chat'} input: {user_input}")
    
    if is_video_mode:
        current_video_input = user_input
        last_video_input_request = None
        video_input_response_queue.put(user_input)
    else:
        current_user_input = user_input
        last_input_request = None
        input_response_queue.put(user_input)

def get_next_agent_message(is_video_mode=False):
    """Get the next agent message from the queue"""
    try:
        queue_to_use = video_agent_message_queue if is_video_mode else agent_message_queue
        return queue_to_use.get_nowait()
    except queue.Empty:
        return None

def is_agent_waiting_for_input(is_video_mode=False):
    """Check if the agent is waiting for input"""
    flag = video_waiting_for_input_flag if is_video_mode else agent_waiting_for_input_flag
    logger.info(f"{'Video' if is_video_mode else 'Agent'} waiting for input: {flag}")
    return flag

def set_agent_waiting_for_input(waiting: bool, is_video_mode=False):
    """Set the agent waiting for input flag"""
    global agent_waiting_for_input_flag, video_waiting_for_input_flag
    if is_video_mode:
        video_waiting_for_input_flag = waiting
        logger.info(f"Video waiting for input set to: {video_waiting_for_input_flag}")
    else:
        agent_waiting_for_input_flag = waiting
        logger.info(f"Agent waiting for input set to: {agent_waiting_for_input_flag}")

def is_agent_session_active(is_video_mode=False):
    """Check if the agent session is active"""
    active = video_session_active if is_video_mode else agent_session_active
    logger.info(f"{'Video' if is_video_mode else 'Agent'} session active: {active}")
    return active

def set_agent_session_active(active: bool, is_video_mode=False):
    """Set the agent session active flag"""
    global agent_session_active, video_session_active
    if is_video_mode:
        video_session_active = active
        logger.info(f"Video session active set to: {video_session_active}")
    else:
        agent_session_active = active
        logger.info(f"Agent session active set to: {agent_session_active}")

def get_next_browser_input_request():
    """Get the next input request from the browser agent"""
    global last_browser_input_request
    try:
        request = browser_input_request_queue.get_nowait()
        last_browser_input_request = request
        logger.info(f"Got browser input request: {request}")
        return request
    except queue.Empty:
        return None

def submit_browser_user_input(input_text: str):
    """Submit user input to the browser agent"""
    global current_browser_input
    current_browser_input = input_text
    browser_input_response_queue.put(input_text)
    logger.info(f"Submitted browser user input: {input_text}")

def get_next_browser_agent_message():
    """Get the next message from the browser agent"""
    try:
        message = browser_message_queue.get_nowait()
        logger.info(f"Got browser agent message: {message}")
        return message
    except queue.Empty:
        return None

def is_browser_agent_waiting_for_input():
    """Check if the browser agent is waiting for input"""
    return browser_waiting_for_input

def set_browser_agent_waiting_for_input(waiting: bool):
    """Set whether the browser agent is waiting for input"""
    global browser_waiting_for_input
    browser_waiting_for_input = waiting
    logger.info(f"Set browser agent waiting for input: {waiting}")

def is_browser_agent_session_active():
    """Check if the browser agent session is active"""
    return browser_session_active

def set_browser_agent_session_active(active: bool):
    """Set whether the browser agent session is active"""
    global browser_session_active
    browser_session_active = active
    logger.info(f"Set browser agent session active: {active}")

def reset_browser_queues():
    """Reset all browser queues"""
    global current_browser_input, browser_waiting_for_input, last_browser_input_request
    
    # Clear all queues
    while not browser_message_queue.empty():
        try:
            browser_message_queue.get_nowait()
        except queue.Empty:
            break
    
    while not browser_input_request_queue.empty():
        try:
            browser_input_request_queue.get_nowait()
        except queue.Empty:
            break
    
    while not browser_input_response_queue.empty():
        try:
            browser_input_response_queue.get_nowait()
        except queue.Empty:
            break
    
    # Reset state
    current_browser_input = None
    browser_waiting_for_input = False
    last_browser_input_request = None
    
    logger.info("Reset all browser queues")