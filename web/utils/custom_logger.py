import requests
import os
import logging
logger = logging.getLogger(__name__)

def send_custom_log(category: int, message: str) -> bool:
    """
    Send a custom log message to the backend.
    
    Args:
        category (int): The category number for the log
        message (str): The log message
        
    Returns:
        bool: True if the log was sent successfully, False otherwise
    """
    try:
        # Get the port from environment or use default
        port = int(os.environ.get('PORT', 5000))
        
        logger.info(f"Sent custom log: {message}")
        # Send the log to the backend
        response = requests.post(
            f'http://localhost:{port}/send_log',
            json={
                'category': category,
                'message': message
            }
        )
        logger.info(f"Response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending custom log: {str(e)}")
        return False 