import logging
import re
import uuid
import queue
from datetime import datetime, timedelta
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import AgentEvent, ChatMessage

from .model_client import setup_model_client
from .web_input import web_input_func
from .selector import selector_exp
from .queues import agent_message_queue, set_agent_session_active
from .agent_manager import agent_manager

# Set up logging
logger = logging.getLogger(__name__)

# Store the group chat instance
agent_group_chat = None

async def run_agent() -> str:
    """Run the agent"""
    global agent_group_chat, agent_message_queue
    
    # Generate a unique session ID to ensure no memory is shared between sessions
    session_id = str(uuid.uuid4())
    logger.info(f"Running agent with session ID: {session_id}")
    
    try:
        # Check if there's a termination message in the queue
        try:
            termination_message = agent_message_queue.get_nowait()
            if "Termination reason:" in termination_message:
                logger.info(f"Termination message found in queue: {termination_message}")
                return termination_message
        except queue.Empty:
            pass
        
        # Set up model client
        logger.info("Setting up model client")
        model_client = setup_model_client()
        
        # Initialize agents via the agent manager
        logger.info("Initializing agents via AgentManager")
        agents = agent_manager.get_agents_list()
        
        # Get attribute trees from the agent manager
        attribute_trees = agent_manager.get_attribute_trees()
        logger.info(f"Retrieved {len(attribute_trees)} attribute trees from AgentManager")

        logger.info("Setting up termination condition")
        termination = TextMentionTermination("terminate") | TextMentionTermination("perm_err") | TextMentionTermination("error")
        
        # Create group chat
        logger.info("Creating group chat")
        group_chat = SelectorGroupChat(
            agents,
            max_turns=55,
            termination_condition=termination,
            model_client=model_client,
            selector_func=selector_exp
        )
        
        # Store the group chat for later use
        agent_group_chat = group_chat
        
        # Set the agent session as active
        set_agent_session_active(True)
        
        # Run the chat
        logger.info("Running chat")
        responses = []

        async for message in group_chat.run_stream():
            try:
                # Handle different message types
                if hasattr(message, 'source') and hasattr(message, 'content'):
                    source = message.source
                    content = message.content
                elif isinstance(message, dict):
                    source = message.get('source', 'Unknown')
                    content = message.get('content', '')
                else:
                    # For TaskResult objects or other types
                    source = getattr(message, 'source', 'Unknown')
                    content = getattr(message, 'content', str(message))
                
                logger.info(f"Received message: {source}: {content}")
                
                # Skip TaskResult messages that contain all previous messages
                if source == "Unknown" and "TaskResult" in str(message) and "messages=" in str(message):
                    logger.info("Skipping concatenated TaskResult message")
                    continue
                
                if type(content) == str and ("terminate" in content.lower() or "perm_err" in content.lower() or "error" in content.lower()):
                    logger.info(f"Termination detected: {content}")
                    return "TERMINATION: " + content
                
                # Skip user messages to prevent duplication
                if source == "User":
                    logger.info(f"[agent_core.py] Skipping user message to prevent duplication: {content}")
                    continue
                
                # Format the message for display
                formatted_message = ""
                
                if source == "Planner":
                    # Clean up markdown formatting
                    content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                    
                    # Extract the task description
                    task_match = re.search(r'Task:\s*([^\n]+)', content)
                    if task_match:
                        task = task_match.group(1).strip()
                        formatted_message = f"{source}: {task}"
                    else:
                        # Look for Description: pattern
                        desc_match = re.search(r'Description:\s*([^\n]+)', content)
                        if desc_match:
                            desc = desc_match.group(1).strip()
                            formatted_message = f"{source}: {desc}"
                        else:
                            formatted_message = f"{source}: {content}"
                elif source == "User":
                    # Skip user messages to prevent duplication
                    continue
                elif source == "Agent":
                    # Handle messages from the Agent source
                    # Clean up markdown formatting
                    content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                    
                    # Extract the task description if available
                    task_match = re.search(r'Task:\s*([^\n]+)', content)
                    if task_match:
                        task = task_match.group(1).strip()
                        formatted_message = f"Agent: {task}"
                    else:
                        # Look for Description: pattern
                        desc_match = re.search(r'Description:\s*([^\n]+)', content)
                        if desc_match:
                            desc = desc_match.group(1).strip()
                            formatted_message = f"Agent: {desc}"
                        else:
                            formatted_message = f"Agent: {content}"
                else:
                    # Handle messages from other sources
                    # Clean up markdown formatting
                    if isinstance(content, str):
                        content = re.sub(r'\*\*|\*|__|\[|\]|\(|\)|`|#', '', content)
                        formatted_message = f"{source}: {content}"
                    else:
                        # If content is not a string, convert it to string representation
                        formatted_message = f"{source}: {str(content)}"
                
                # Add the formatted message to the responses
                if formatted_message:
                    responses.append(formatted_message)
                    
                    def check_user_or_data(formatted_message: str) -> bool:
                        agent_called = formatted_message.split(":")
                        logger.info(f"Agent called: {agent_called}")
                        return len(agent_called) > 1 and agent_called[1].strip().lower() in ["user", "data"]
                    
                    if not check_user_or_data(formatted_message):
                        # Put the formatted message in the agent message queue
                        agent_message_queue.put(formatted_message)

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                responses.append(f"Error: {str(e)}")
        
        logger.info(f"Chat completed with {len(responses)} responses")
        
        return "Conversation completed"

    except Exception as e:
        logger.error(f"Error in run_agent: {str(e)}", exc_info=True)
        # Return a fallback response
        error_message = f"Assistant: I apologize, but I encountered an error while processing your request: {str(e)}. This might be due to API connectivity issues. Please try again later or contact support if the problem persists."
        # Add the error message to the queue
        agent_message_queue.put(error_message)
        return error_message