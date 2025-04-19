import logging
from typing import Sequence
from autogen_agentchat.messages import AgentEvent, ChatMessage

# Set up logging
logger = logging.getLogger(__name__)

# Default agent list
default_agent = ["Planner"]

def selector_exp(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
    """
    Select the next agent to respond in the conversation.
    
    Args:
        messages: Sequence of agent events or chat messages
        
    Returns:
        The name of the next agent to respond, or None
    """
    global default_agent
    agent = ""
    
    # Log the last message content if there are messages
    if len(messages) > 0:
        logger.debug(f"Last message content: {messages[-1].content}")
    
    # Determine the next agent based on the conversation state
    if len(messages) == 0:
        logger.debug("No messages, waiting for user input")
        agent = "User"
    
    elif messages[-1].source == "User":
        logger.debug(f"Last message from User, returning {default_agent[-1]}")
        agent = default_agent[-1]
    
    elif len(messages) > 0 and messages[-1].source == "Planner":
        logger.info(f"Planner: {messages[-1].content}")
        next_agent = messages[-1].content.split(":")[0]
        
        logger.debug(f"Last message from 'Planner', next agent determined as: {next_agent}")
        agent = next_agent
        
        if agent == "terminate":
            logger.debug("Terminate detected, setting agent to Planner")
            agent = "Planner"
    
    elif len(messages) > 0:
        if messages[-1].content.lower() == "done":
            logger.debug("Message content is 'done', setting agent to Planner")
            agent = "Planner"
        elif messages[-1].content.lower().startswith("user"):
            logger.info(f"User: {messages[-1].content}")
            agent = "User"
        elif messages[-1].content.lower().startswith("data"):
            logger.info(f"Need data: {messages[-1].content}")
            agent = "Planner"
        elif messages[-1].content.lower().startswith("done"):
            logger.debug("Message content starts with 'done', setting agent to Planner")
            agent = "Planner"
        else:
            logger.debug(f"Using message source as agent: {messages[-1].source}")
            agent = messages[-1].source
    
    logger.debug(f"Returning agent: {agent}")
    
    # Add the agent to the default_agent list if it's not "User"
    if agent != "User":
        default_agent.append(agent)
        logger.debug(f"Added {agent} to default_agent list. Current list: {default_agent}")
    
    return agent 