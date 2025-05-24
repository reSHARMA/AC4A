import logging

# Set up logging
logger = logging.getLogger(__name__)

# Store browser chat history
browser_chat_history = []

def handle_termination() -> dict:
    """
    Handle termination of the browser chat session
    
    Returns:
        dict: Response containing role and content
    """
    clear_browser_chat_history()
    return {
        "role": "system",
        "content": "Chat session ended. Say Hi! to start a new session."
    }

def process_browser_message(user_message: str) -> dict:
    """
    Process a browser chat message and return a response
    
    Args:
        user_message (str): The user's message
        
    Returns:
        dict: Response containing role and content
    """
    try:
        # Check for termination
        if user_message.lower() == 'terminate':
            return handle_termination()
            
        # Add user message to history
        browser_chat_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Simple response - length of message
        response = {
            "role": "assistant",
            "content": f"Message length: {len(user_message)}"
        }
        
        # Add response to history
        browser_chat_history.append(response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing browser message: {str(e)}", exc_info=True)
        return {"error": str(e)}

def get_browser_chat_history() -> list:
    """
    Get the browser chat history
    
    Returns:
        list: List of chat messages
    """
    return browser_chat_history

def clear_browser_chat_history() -> None:
    """
    Clear the browser chat history
    """
    browser_chat_history.clear() 