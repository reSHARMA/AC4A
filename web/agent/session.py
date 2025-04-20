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
from .agents.user_agent import UserAgent
from .agents.planner_agent import PlannerAgent
from .agents.calendar_agent import CalendarAgent
from .agents.wallet_agent import WalletAgent
from .agents.expedia_agent import ExpediaAgent
from .agents.contact_manager_agent import ContactManagerAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from src.policy_system.policy_system import PolicySystem
from .selector import selector_exp
from .queues import set_agent_session_active, is_agent_session_active, set_agent_waiting_for_input
# Set up logging
logger = logging.getLogger(__name__)

# Create an instance of the PolicySystem
policy_system = PolicySystem()

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
    
    # Set session as inactive first to prevent new messages
    set_agent_session_active(False)
    
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
    global agent_loop, agent_initialized, agent_message_queue, input_request_queue, input_response_queue
    
    try:
        # Check if there's a termination message in the queue
        try:
            termination_message = agent_message_queue.get_nowait()
            if "TERMINATION:" in termination_message:
                logger.info(f"Termination message found in queue: {termination_message}")
                agent_message_queue.put(termination_message)
                agent_initialized = False
                return
        except queue.Empty:
            pass
        
        # Set the agent session as active before running
        set_agent_session_active(True)
        logger.info("Starting agent session")
        
        # Run the agent in the event loop
        result = agent_loop.run_until_complete(run_agent())
        
        # Check if the result is a termination message
        if "TERMINATION:" in result:
            logger.info(f"Agent returned termination message: {result}")
            agent_message_queue.put(result)
    except Exception as e:
        logger.error(f"Error in agent thread: {str(e)}", exc_info=True)
        error_message = f"TERMINATION: Error in agent thread: {str(e)}"
        # Add the error message to the queue
        agent_message_queue.put(error_message)
        set_agent_session_active(False)
        agent_initialized = False
    finally:
        # Set the agent session as inactive
        set_agent_session_active(False)
        agent_initialized = False
        logger.info("Agent session ended")
        
        # Close the event loop to ensure clean shutdown
        try:
            agent_loop.close()
        except Exception as e:
            logger.error(f"Error closing event loop: {str(e)}", exc_info=True)
        
        # Clear any remaining messages in the queues
        try:
            while not input_request_queue.empty():
                input_request_queue.get_nowait()
            while not input_response_queue.empty():
                input_response_queue.get_nowait()
        except Exception as e:
            logger.error(f"Error clearing message queues: {str(e)}", exc_info=True)

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