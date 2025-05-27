import logging
from enum import Enum
from typing import Dict, Any
import requests
import base64
import re
from src.utils.dummy_data import call_openai_api

# Set up logging
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages that can be sent to the frontend"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    INTERNAL = "internal"  # For messages that should not be sent to frontend
    DEBUG = "debug"  # For debugging messages
    ERROR = "error"

class MessageVisibility(Enum):
    """Visibility levels for messages"""
    PUBLIC = "public"  # Visible to all
    INTERNAL = "internal"  # Only visible in logs
    DEBUG = "debug"  # Only visible in debug mode

# Store browser chat history
browser_chat_history = []

def create_message(content: str, role: str, msg_type: MessageType = MessageType.ASSISTANT, 
                  visibility: MessageVisibility = MessageVisibility.PUBLIC) -> Dict[str, Any]:
    """
    Create a message with metadata
    
    Args:
        content (str): The message content
        role (str): The role of the sender
        msg_type (MessageType): The type of message
        visibility (MessageVisibility): The visibility level of the message
        
    Returns:
        dict: Message with metadata
    """
    return {
        "role": role,
        "content": content,
        "type": msg_type.value,
        "visibility": visibility.value
    }

def handle_termination() -> dict:
    """
    Handle termination of the browser chat session
    
    Returns:
        dict: Response containing role and content
    """
    clear_browser_chat_history()
    return create_message(
        content="Chat session ended. Say Hi! to start a new session.",
        role="system",
        msg_type=MessageType.SYSTEM
    )

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
        user_msg = create_message(
            content=user_message,
            role="user",
            msg_type=MessageType.USER
        )
        browser_chat_history.append(user_msg)
        
        # Process with computer-use model
        response = process_with_computer_use(user_message)
        
        # Add response to history
        browser_chat_history.append(response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing browser message: {str(e)}", exc_info=True)
        return create_message(
            content=str(e),
            role="system",
            msg_type=MessageType.ERROR
        )

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

def clean_html_content(html: str) -> str:
    """
    Clean HTML content for both structure analysis AND CSS path mapping
    Preserves essential structure and attributes needed for CSS targeting
    while removing unnecessary content for analysis
    
    Args:
        html (str): Raw HTML content
        
    Returns:
        str: Cleaned HTML that maintains CSS-targetable structure
    """
    if not html:
        return html
    
    # Remove entire head section and its contents
    html = re.sub(r'<head\b[^>]*>.*?</head>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove non-visible elements that don't contribute to user interaction
    html = re.sub(r'<meta\b[^>]*/?>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*/?>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<title\b[^>]*>.*?</title>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<base\b[^>]*/?>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove script tags and their content (case-insensitive, multiline)
    html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove style tags and their content (case-insensitive, multiline)
    html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Replace SVG content but keep the SVG tag structure
    html = re.sub(r'(<svg\b[^>]*>).*?(<\/svg>)', r'\1retracted\2', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove JavaScript-related attributes (these don't affect CSS targeting)
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsaction\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jscontroller\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsname\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsdata\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsmodel\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsshadow\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsslot\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+jsowner\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove most data attributes but keep some that might be used for CSS targeting
    html = re.sub(r'\s+data-(?!testid|role|target|toggle|dismiss)[^=]*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove accessibility attributes (don't affect CSS targeting)
    html = re.sub(r'\s+aria-[^=]*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+role\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove inline styles (we want to apply our own styles)
    html = re.sub(r'\s+style\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Replace URL attributes with "retracted" but keep the attribute for structure
    html = re.sub(r'href\s*=\s*["\'][^"\']*["\']', 'href="retracted"', html, flags=re.IGNORECASE)
    html = re.sub(r'src\s*=\s*["\'][^"\']*["\']', 'src="retracted"', html, flags=re.IGNORECASE)
    html = re.sub(r'action\s*=\s*["\'][^"\']*["\']', 'action="retracted"', html, flags=re.IGNORECASE)
    html = re.sub(r'poster\s*=\s*["\'][^"\']*["\']', 'poster="retracted"', html, flags=re.IGNORECASE)
    html = re.sub(r'background\s*=\s*["\'][^"\']*["\']', 'background="retracted"', html, flags=re.IGNORECASE)
    
    # Replace data URIs and base64 content with "retracted"
    html = re.sub(r'data:[^;]+;base64,[A-Za-z0-9+/=]+', 'retracted', html)
    
    # Remove hidden elements (not visible to users)
    html = re.sub(r'<[^>]*\s+hidden\s*(?:=\s*["\'](?:true|hidden)["\'])?\s*[^>]*>.*?</[^>]+>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<[^>]*\s+style\s*=\s*["\'][^"\']*display\s*:\s*none[^"\']*["\'][^>]*>.*?</[^>]+>', '', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Extract only body content if body tag exists
    body_match = re.search(r'<body\b[^>]*>(.*?)</body>', html, flags=re.IGNORECASE | re.DOTALL)
    if body_match:
        html = body_match.group(1)
    
    # KEEP ALL CLASS NAMES - they're essential for CSS targeting
    # KEEP ALL ID ATTRIBUTES - they're essential for CSS targeting
    # KEEP structural attributes like name, type, value for form elements
    
    # Remove empty attributes
    html = re.sub(r'\s+\w+\s*=\s*["\']["\']', '', html)
    
    # Clean up extra whitespace but preserve structure
    html = re.sub(r'\n\s*\n', '\n', html)
    html = re.sub(r'  +', ' ', html)
    
    # Don't remove empty tags - they might be styled with CSS
    # Don't collapse nested divs - they might be part of CSS selectors
    
    return html.strip()

def create_minimal_html_for_analysis(html: str) -> str:
    """
    Create an ultra-minimal HTML version focused purely on structure analysis
    This removes almost everything except essential tags and visible text content
    
    Args:
        html (str): Raw HTML content
        
    Returns:
        str: Ultra-minimal HTML for pure structure analysis
    """
    if not html:
        return html
    
    # Start with the cleaned version
    html = clean_html_content(html)
    
    # Remove all attributes except essential ones for targeting
    # Keep only: id, class (simplified), name, type, value, alt, title
    html = re.sub(r'\s+(?!(?:id|class|name|type|value|alt|title|href|src|action)\b)\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove redundant nested divs that don't add semantic value
    # This is aggressive - removes div tags that only contain other divs or single elements
    html = re.sub(r'<div[^>]*>\s*(<(?:div|span|a|button|input|img)[^>]*>.*?</(?:div|span|a|button)>)\s*</div>', r'\1', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove span tags that don't have meaningful attributes
    html = re.sub(r'<span[^>]*>\s*(.*?)\s*</span>', r'\1', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Collapse multiple nested divs with no content between them
    html = re.sub(r'<div[^>]*>\s*<div', '<div', html, flags=re.IGNORECASE)
    html = re.sub(r'</div>\s*</div>', '</div>', html, flags=re.IGNORECASE)
    
    # Remove empty elements more aggressively
    html = re.sub(r'<(?!(?:img|input|br|hr|meta|link)\b)([^>]+)>\s*</\1>', '', html, flags=re.IGNORECASE)
    
    # Final cleanup
    html = re.sub(r'\n\s*\n', '\n', html)
    html = re.sub(r'>\s+<', '><', html)
    
    return html.strip()

def check_screenshot_server_health() -> Dict[str, Any]:
    """
    Check the health of the screenshot server and HTML source API
    
    Returns:
        dict: Health status information
    """
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            # Add additional context for easier interpretation
            health_data['services'] = {
                'screenshot': health_data.get('screenshot_available', False),
                'html_source': health_data.get('html_source_available', False),
                'cdp_endpoint': health_data.get('cdp_endpoint', 'Unknown')
            }
            return health_data
        else:
            return {
                'status': 'unhealthy',
                'error': f'HTTP {response.status_code}',
                'screenshot_available': False,
                'html_source_available': False,
                'services': {
                    'screenshot': False,
                    'html_source': False,
                    'cdp_endpoint': 'Unknown'
                }
            }
    except Exception as e:
        return {
            'status': 'unreachable',
            'error': str(e),
            'screenshot_available': False,
            'html_source_available': False,
            'services': {
                'screenshot': False,
                'html_source': False,
                'cdp_endpoint': 'Unknown'
            }
        }

def get_html_source() -> Dict[str, Any]:
    """
    Get the HTML source of the currently active page in the browser
    
    Returns:
        dict: HTML source data or error information
    """
    try:
        # Get the HTML source from the Flask API
        response = requests.get('http://localhost:8080/html-source', timeout=10)
        
        if response.status_code == 200:
            html_data = response.json()
            # Clean the HTML content before returning
            if html_data.get('html'):
                html_data['html'] = clean_html_content(html_data['html'])
            return html_data
        elif response.status_code == 404:
            logger.warning("No active browser tab found")
            return {
                'success': False,
                'error': 'No active browser tab found',
                'html': None
            }
        elif response.status_code == 500:
            error_data = response.json()
            logger.error(f"Failed to get HTML source: {error_data.get('error', 'Unknown error')}")
            return {
                'success': False,
                'error': error_data.get('error', 'Unknown error'),
                'message': error_data.get('message', ''),
                'html': None
            }
        else:
            logger.error(f"Failed to get HTML source: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'html': None
            }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to HTML source server: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Connection error: {str(e)}',
            'html': None
        }
    except Exception as e:
        logger.error(f"Error getting HTML source: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'html': None
        }

def get_latest_screenshot() -> bytes:
    """
    Get the latest screenshot from the Flask screenshot server
    
    Returns:
        bytes: Raw PNG image data
    """
    try:
        # Get the latest screenshot from the Flask API
        response = requests.get('http://localhost:8080/screenshot', timeout=10)
        
        if response.status_code == 200:
            return response.content
        elif response.status_code == 404:
            logger.warning("Screenshot not available yet")
            return b''
        else:
            logger.error(f"Failed to get screenshot: {response.status_code} - {response.text}")
            return b''
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to screenshot server: {str(e)}", exc_info=True)
        return b''
    except Exception as e:
        logger.error(f"Error getting screenshot: {str(e)}", exc_info=True)
        return b''

def process_with_computer_use(user_input: str) -> Dict[str, Any]:
    """
    Process user input with computer-use model using the latest screenshot
    
    Args:
        user_input (str): The user's input/instruction
        
    Returns:
        dict: Response from the model
    """
    try:
        # Get the latest screenshot
        screenshot_data = get_latest_screenshot()
        if not screenshot_data:
            return create_message(
                content="Failed to get screenshot",
                role="system",
                msg_type=MessageType.ERROR
            )
            
        # Convert screenshot to base64
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Create the system prompt for computer use
        system_prompt = """You are an AI agent with the ability to control a browser. You can ask the user to do one action at a time with the keyboard or the mouse. You are given a task and you have to successfully complete it by asking the user to perform actions one by one.

        You will also be given a screenshot of the browser after each action and also the list of past actions. You should check the screenshot to see if your action was successful and decide what to do next. 

        Only output the next action to take or ask the user for confirmation or resolve choices or give missing information.
        Do not output any other text.
        Once you have completed the requested task you should output done."""
        
        global browser_chat_history
        _input = f"""
Task: {browser_chat_history[0]['content']}

The following is the history of interactions with the user:
"""
        for chat_item in browser_chat_history[1:]:
            _input += f"""
{chat_item['role']}: {chat_item['content']}
"""
        if user_input == "done" or user_input == "":
                _input += f"""
The user says they have completed the task. Check the screenshot to validate and move on to the next action to complete the task.
"""
        else:
                _input += f"""
User: {user_input}
"""
        # Create the input as a dictionary with text and image
        input_content = {
            "text": _input,
            "image": f"data:image/png;base64,{screenshot_base64}"
        }
        
        # Call the OpenAI API using the existing function
        response = call_openai_api(system_prompt, input_content, "computer-use")
        
        if response:
            return create_message(
                content=response + "\n\n" + get_html_source()['html'],
                role="assistant",
                msg_type=MessageType.ASSISTANT
            )
        else:
            return create_message(
                content="No response generated from model",
                role="system",
                msg_type=MessageType.ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in computer use processing: {str(e)}", exc_info=True)
        return create_message(
            content=f"Error processing with computer-use model: {str(e)}",
            role="system",
            msg_type=MessageType.ERROR
        ) 