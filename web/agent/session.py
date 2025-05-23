import asyncio
import threading
import gc
import logging
import uuid
import queue
import os
from .queues import (
    agent_initialized, 
    agent_message_queue, 
    input_request_queue, 
    input_response_queue, 
    last_input_request,
    current_user_input
)
from .agent_core import run_agent, agent_group_chat
from .model_client import setup_model_client
from .agent_manager import agent_manager
from .queues import set_agent_session_active, is_agent_session_active, set_agent_waiting_for_input

# Set up logging
logger = logging.getLogger(__name__)

# Global variables for agent session management
agent_thread = None
agent_loop = None

# Browser mode specific variables
browser_thread = None
browser_loop = None
browser_initialized = False
browser_message_queue = queue.Queue()
browser_input_request_queue = queue.Queue()
browser_input_response_queue = queue.Queue()
current_browser_input = None
browser_session_active = False
browser_waiting_for_input = False
last_browser_input_request = None

def reset_agent_session(emit_termination: bool = True):
    """Reset the agent session"""
    global agent_thread, agent_loop, agent_initialized, current_user_input
    
    logger.info("Resetting agent session")
    
    # Only reset if the session is active
    if not is_agent_session_active():
        logger.info("Session already inactive, skipping reset")
        return
    
    # Wait for agent thread to finish if it exists
    if agent_thread and agent_thread.is_alive():
        logger.info("Waiting for agent thread to finish")
        agent_thread.join(timeout=5)  # Wait up to 5 seconds
    
    # Reset user input
    current_user_input = None
    
    # Clear all queues
    while not input_request_queue.empty():
        try:
            input_request_queue.get_nowait()
        except queue.Empty:
            break
    
    while not input_response_queue.empty():
        try:
            input_response_queue.get_nowait()
        except queue.Empty:
            break
    
    # Reset flags
    set_agent_waiting_for_input(False)
    last_input_request = None
    
    # Force garbage collection to clean up any lingering objects
    gc.collect()
    
    # Add a termination message to the queue only if requested
    if emit_termination:
        agent_message_queue.put("TERMINATION: Session reset by user")
    
    # Set session as inactive after cleanup
    set_agent_session_active(False)
    
    logger.info("Agent session reset complete")

def initialize_agent_session():
    """Initialize the agent session"""
    global agent_thread, agent_loop, agent_initialized
    
    # If the agent session is already active, do nothing
    if is_agent_session_active():
        logger.info("Agent session already active")
        return

    # If the agent has already been initialized, reset it first
    if agent_initialized:
        logger.info("Agent already initialized, resetting first")
        reset_agent_session(emit_termination=False)  # Don't emit termination message during initialization

    # Clear the debug.log file
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug.log')
    try:
        with open(log_path, 'w') as f:
            f.write('')
        logger.info("Cleared debug.log file")
    except Exception as e:
        logger.error(f"Error clearing debug.log: {str(e)}")
    # Emit session reset event to all connected clients
    try:
        logger.info("Emitting session_reset event")
        from web.utils.events import socketio
        socketio.emit('session_reset', {'reset': True}, namespace='/')
        logger.info("Session reset event emitted")
    except Exception as e:
        logger.error(f"Error emitting session_reset event: {str(e)}") 
 
    logger.info("Initializing agent session")
    
    # Create a new event loop for the agent
    agent_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(agent_loop)
    
    # Start the agent in a separate thread
    agent_thread = threading.Thread(target=run_agent_thread)
    agent_thread.daemon = True
    agent_thread.start()
    
    # Mark the agent as initialized and active
    agent_initialized = True
    set_agent_session_active(True)
    
    logger.info("Agent session initialized")

def run_agent_thread():
    """Run the agent in a separate thread"""
    global agent_thread, agent_loop, agent_initialized
    
    try:
        # Set the agent session as active before running
        set_agent_session_active(True)
        logger.info("Agent session set to active")
        
        # Initialize the agent
        agent_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(agent_loop)
        
        # Run the agent using the imported run_agent function
        agent_loop.run_until_complete(run_agent())
        
    except Exception as e:
        logger.error(f"Error in agent thread: {str(e)}")
        # Only set inactive if there was an error
        set_agent_session_active(False)
        logger.info("Agent session set to inactive due to error")
        
    finally:
        logger.info("Agent thread finally block")
        # Clean up
        if agent_loop:
            agent_loop.run_until_complete(agent_loop.shutdown_asyncgens())
            tasks = asyncio.all_tasks(loop=agent_loop)
            for task in tasks:
                task.cancel()
            agent_loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            agent_loop.close()
        
        agent_loop = None
        agent_thread = None
        agent_initialized = False
        reset_agent_session(emit_termination=False)

def run_agent_sync() -> str:
    """Synchronous wrapper for running the agent"""

    logger.info(f"Running agent synchronously")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_agent())
        logger.info(f"Agent run completed with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}", exc_info=True)
        # Return a fallback response
        return f"Assistant: I apologize, but I encountered an error while processing your request: {str(e)}. This might be due to API connectivity issues. Please try again later or contact support if the problem persists."
    finally:
        loop.close()

def reset_browser_session(emit_termination: bool = True):
    """Reset the browser agent session"""
    global browser_thread, browser_loop, browser_initialized, current_browser_input, browser_session_active, browser_waiting_for_input
    
    logger.info("Resetting browser agent session")
    
    # Only reset if the session is active
    if not browser_session_active:
        logger.info("Browser session already inactive, skipping reset")
        return
    
    # Wait for browser thread to finish if it exists
    if browser_thread and browser_thread.is_alive():
        logger.info("Waiting for browser thread to finish")
        browser_thread.join(timeout=5)  # Wait up to 5 seconds
    
    # Reset browser input
    current_browser_input = None
    
    # Clear all browser queues
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
    
    # Reset flags
    browser_waiting_for_input = False
    last_browser_input_request = None
    
    # Force garbage collection to clean up any lingering objects
    gc.collect()
    
    # Add a termination message to the queue only if requested
    if emit_termination:
        browser_message_queue.put("TERMINATION: Browser session reset by user")
    
    # Set session as inactive after cleanup
    browser_session_active = False
    
    logger.info("Browser agent session reset complete")

def initialize_browser_session():
    """Initialize the browser agent session"""
    global browser_thread, browser_loop, browser_initialized, browser_session_active
    
    # If the browser session is already active, do nothing
    if browser_session_active:
        logger.info("Browser agent session already active")
        return

    # If the browser agent has already been initialized, reset it first
    if browser_initialized:
        logger.info("Browser agent already initialized, resetting first")
        reset_browser_session(emit_termination=False)  # Don't emit termination message during initialization

    # Clear the debug.log file
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug.log')
    try:
        with open(log_path, 'w') as f:
            f.write('')
        logger.info("Cleared debug.log file")
    except Exception as e:
        logger.error(f"Error clearing debug.log: {str(e)}")
    # Emit session reset event to all connected clients
    try:
        logger.info("Emitting session_reset event")
        from web.utils.events import socketio
        socketio.emit('session_reset', {'reset': True}, namespace='/')
        logger.info("Session reset event emitted")
    except Exception as e:
        logger.error(f"Error emitting session_reset event: {str(e)}") 
 
    logger.info("Initializing browser agent session")
    
    # Create a new event loop for the browser agent
    browser_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(browser_loop)
    
    # Start the browser agent in a separate thread
    browser_thread = threading.Thread(target=run_browser_agent_thread)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Mark the browser agent as initialized and active
    browser_initialized = True
    browser_session_active = True
    
    logger.info("Browser agent session initialized")

def run_browser_agent_thread():
    """Run the browser agent in a separate thread"""
    global browser_thread, browser_loop, browser_initialized, browser_session_active
    
    try:
        # Set the browser session as active before running
        browser_session_active = True
        logger.info("Browser agent session set to active")
        
        # Initialize the browser agent
        browser_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(browser_loop)
        
        # Run the agent using the imported run_agent function
        browser_loop.run_until_complete(run_agent())
        
    except Exception as e:
        logger.error(f"Error in browser agent thread: {str(e)}")
        # Only set inactive if there was an error
        browser_session_active = False
        logger.info("Browser agent session set to inactive due to error")
        
    finally:
        logger.info("Browser agent thread finally block")
        # Clean up
        if browser_loop:
            browser_loop.run_until_complete(browser_loop.shutdown_asyncgens())
            tasks = asyncio.all_tasks(loop=browser_loop)
            for task in tasks:
                task.cancel()
            browser_loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            browser_loop.close()
        
        browser_loop = None
        browser_thread = None
        browser_initialized = False
        reset_browser_session(emit_termination=False)

def run_browser_agent_sync() -> str:
    """Synchronous wrapper for running the browser agent"""

    logger.info("Running browser agent synchronously")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_agent())
        logger.info(f"Browser agent run completed with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error running browser agent: {str(e)}", exc_info=True)
        # Return a fallback response
        return f"Assistant: I apologize, but I encountered an error while processing your request: {str(e)}. This might be due to API connectivity issues. Please try again later or contact support if the problem persists."
    finally:
        loop.close()