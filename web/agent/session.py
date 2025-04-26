import asyncio
import threading
import gc
import logging
import uuid
import queue
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
    
    while not agent_message_queue.empty():
        try:
            agent_message_queue.get_nowait()
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
        reset_agent_session(emit_termination=True)

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