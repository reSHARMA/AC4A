import asyncio
import logging
from agent_wrapper import run_agent_with_input, selector_exp

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_agent():
    """Debug the agent with a simple input"""
    logger.info("Starting agent debug")
    user_input = "Book a flight from sea to slc"
    logger.info(f"User input: {user_input}")
    
    # Set a breakpoint in the selector_exp function
    # This will pause execution when selector_exp is called
    
    try:
        response = await run_agent_with_input(user_input)
        logger.info(f"Agent response: {response}")
    except Exception as e:
        logger.error(f"Error testing agent: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(debug_agent()) 