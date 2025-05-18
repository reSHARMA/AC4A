import logging
import re
import uuid
import queue
from datetime import datetime, timedelta
from contextlib import aclosing
import asyncio
import os

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import AgentEvent, ChatMessage

from .model_client import setup_model_client
from .web_input import web_input_func
from .selector import selector_exp
from .queues import agent_message_queue, set_agent_session_active
from .agent_manager import agent_manager
from src.prompts import PERMISSION_REQUIRED
from src.utils.dummy_data import call_openai_api
from web.utils.events import emit_policy_update
from src.policy_system.policy_system import PolicySystem

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
            if "terminate:" in termination_message.lower():
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

        # logger.info("Setting up termination condition")
        # termination = TextMentionTermination("terminate") | TextMentionTermination("perm_err") | TextMentionTermination("error")
        termination = TextMentionTermination("terminate")
        
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

        chat_result = "Chat completed"

        stream = None
        try: 
            async with aclosing(group_chat.run_stream()) as stream:
                async for message in stream:
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
                        
                        if type(content) == str and ("terminate" in content.lower()):
                            logger.info(f"Termination detected: {content}")
                            chat_result = f"Termination reason: {content}"
                            agent_message_queue.put(f"Chat Session Ended:\n{content}\n\nSay Hi! to start a new session")
                            await stream.aclose()
                            break
                        
                        # Skip user messages to prevent duplication
                        if source == "User":
                            logger.info(f"[agent_core.py] Skipping user message to prevent duplication: {content}")
                            continue
                        
                        if message.type == "ToolCallExecutionEvent" or message.type == "ToolCallRequestEvent":
                            logger.info(f"[agent_core.py] Skipping tool call message to prevent duplication: {content}")
                            continue

                        # Format the message for display
                        formatted_message = ""
                        
                        if source == "Planner":
                            # Get the current mode
                            mode = os.environ.get('PERMISSION_MANAGEMENT_MODE', 'ask').lower()

                            if mode in ['infer', 'yolo']:
                                all_data = "<ALL DATA>\n"
                                # Get and print attribute trees
                                attribute_trees = agent_manager.get_attribute_trees()
                                for i, tree in enumerate(attribute_trees):
                                    all_data += f"{tree.get_tree_string()}\n"
                                all_data += "</ALL DATA>"
                                logger.info(f"[agent_core.py] All data: {all_data}")

                                all_data_schema = "<ALL DATA SCHEMA>\n"
                                all_data_schema += str(agent_manager.get_attribute_schema())
                                all_data_schema += "</ALL DATA SCHEMA>"
                                logger.info(f"[agent_core.py] All data schema: {all_data_schema}")

                                permission_required = call_openai_api(PERMISSION_REQUIRED + all_data + all_data_schema, "<TASK>\n" + content + "\n</TASK>")
                                logger.error(f"[agent_core.py] Permission required: {permission_required}")
                                    
                                def is_empty_permission_required(permission_required: str) -> bool:
                                    return permission_required == "" or permission_required == "``````" or permission_required == "```\n```"
                                
                                if not is_empty_permission_required(permission_required):
                                    infer_response = 'n'
                                    if mode == 'infer':
                                        temp_policy_system = PolicySystem()
                                        for permission in permission_required.split("\n"):
                                            temp_policy_system.add_policies_from_text(permission, agent_manager)
                                        prompts = temp_policy_system.get_all_policy_prompts()
                                        logger.info(f"[agent_core.py] Prompts: {prompts}")
                                        agent_message_queue.put("\n".join(prompts))
                                        infer_response = web_input_func("Do you approve? [y/n]")

                                    if mode == 'yolo' or (mode == 'infer' and infer_response == 'y'):
                                        for permission in permission_required.split("\n"):
                                            success = agent_manager.policy_system.add_policies_from_text(permission, agent_manager)
                                            if not success:
                                                logger.info(f"[agent_core.py] Failed to add permission: {permission}")
                                    emit_policy_update()

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
                            
                            # Emit policy update after processing planner message
                            emit_policy_update()
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
                                if len(agent_called) <= 1:
                                    return False
                                first_word = agent_called[1].strip().split()[0].lower()
                                return first_word in ["user", "data"]
                            
                            if not check_user_or_data(formatted_message):
                                # Put the formatted message in the agent message queue
                                logger.info(f"Putting formatted message in the agent message queue: {formatted_message}")
                                agent_message_queue.put(formatted_message)
                        else:
                            logger.info(f"Could not format content: {content}, so skipping")

                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}", exc_info=True)
                        responses.append(f"Error: {str(e)}")
        finally:
            if stream:
                await stream.aclose()
        
        await agent_group_chat.reset()
        logger.info(f"Chat completed with {len(responses)} responses")
        
        return chat_result

    except Exception as e:
        logger.error(f"Error in run_agent: {str(e)}", exc_info=True)
        # Return a fallback response
        error_message = f"Assistant: I apologize, but I encountered an error while processing your request: {str(e)}. This might be due to API connectivity issues. Please try again later or contact support if the problem persists."
        # Add the error message to the queue
        agent_message_queue.put(error_message)
        return error_message