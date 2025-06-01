import logging
from enum import Enum
from typing import Dict, Any, Tuple, List
import requests
import base64
import re
import json
import time
from src.utils.dummy_data import call_openai_api
from .agent_manager import agent_manager
from src.policy_system.policy_system import PolicySystem
from PIL import Image
import io
from src.prompts import BROWSER_INFER_DATA, BROWSER_CLASSIFY_DATA

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
    
    # If an element has an ID, remove its CLASS attribute
    # Handles cases where 'id' attribute might appear before or after 'class' attribute
    # Case 1: id attribute before class attribute
    html = re.sub(r'(<(\w+)[^>]*?\bid\s*=\s*(["\'])[^\3]*?\3[^>]*?)(\s*class\s*=\s*(["\'])[^\5]*?\5)([^>]*?>)', r'\1\6', html, flags=re.IGNORECASE)
    # Case 2: class attribute before id attribute
    html = re.sub(r'(<(\w+)[^>]*?)(\s*class\s*=\s*(["\'])[^\4]*?\4)([^>]*?\bid\s*=\s*(["\'])[^\6]*?\6[^>]*?>)', r'\1\5', html, flags=re.IGNORECASE)
    
    # Remove redundant nested divs that don't add semantic value
    # This is aggressive - removes div tags that only contain other divs or single elements
    html = re.sub(r'<div[^>]*>\s*(<(?:div|span|a|button|input|img)[^>]*>.*?</(?:div|span|a|button)>)\s*</div>', r'\1', html, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove span tags that have no attributes left after cleaning, preserving their content.
    # This ensures spans with meaningful attributes (like id) are kept.
    html = re.sub(r'<span\\s*>\\s*(.*?)\\s*</span>', r'\\1', html, flags=re.IGNORECASE | re.DOTALL)
    
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

def compress_screenshot(screenshot_data: bytes, max_size: tuple = (800, 600), quality: int = 55) -> bytes:
    """
    Compress and resize screenshot data to reduce size
    
    Args:
        screenshot_data (bytes): Raw PNG image data
        max_size (tuple): Maximum width and height
        quality (int): JPEG quality (1-100)
        
    Returns:
        bytes: Compressed image data
    """
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(screenshot_data))
        
        # Convert to RGB if needed (for PNG with transparency)
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # Calculate new dimensions while maintaining aspect ratio
        ratio = min(max_size[0] / img.width, max_size[1] / img.height)
        if ratio < 1:  # Only resize if image is larger than max_size
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save as JPEG with specified quality
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error compressing screenshot: {str(e)}")
        return screenshot_data  # Return original if compression fails

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
            # Compress the screenshot before returning
            return compress_screenshot(response.content)
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

        infer_permissions_from_html(screenshot_data)

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
                content=response,
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

def infer_data_from_html_structure(screenshot_data: bytes, minimal_html: Dict[str, str], html_content: str) -> Dict[str, Any]:
    """
    Infer data from the HTML structure using screenshot and HTML source
    
    Args:
        screenshot_data (bytes): Raw PNG image data of the current page
        minimal_html (Dict[str, str]): Pre-filtered HTML elements and their selectors
    
    Returns:
        dict with key as pair of data type and data value mapped to the CSS selector of the element
    """
    try:
        # Convert screenshot to base64 for API call
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Get all data and schema
        all_data = ""
        # Get and print attribute trees
        attribute_trees = agent_manager.get_attribute_trees()
        for i, tree in enumerate(attribute_trees):
            all_data += f"{tree.get_tree_string()}\n"

        # Get the DOM tree
        dom_tree = get_dom_tree_with_selectors(html_content)

        analysis_text = f"""Please analyze this webpage and classify the elements into data types and data values.
        <ALL DATA>
        {all_data}
        </ALL DATA>

        <ALL DATA SCHEMA>
        {str(agent_manager.get_attribute_schema())}
        </ALL DATA SCHEMA>

        <HTML ELEMENTS>
        {str(minimal_html)}
        </HTML ELEMENTS>
        
        <DOM TREE>
        {str(dom_tree)}
        </DOM TREE>
        """
        logger.info(f"[browser_agent_core.py] Analysis text: {analysis_text}")
        # Create input content with HTML and screenshot
        input_content = {
            "text": analysis_text,
            "image": f"data:image/png;base64,{screenshot_base64}"
        }

        logger.info(f"[browser_agent_core.py] Input content: {input_content}")
        # Call OpenAI API for analysis
        response = call_openai_api(BROWSER_INFER_DATA, input_content, "computer-use")

        if not response:
            logger.error("No response from OpenAI API for HTML analysis")
            return {
                'data': {},
                'error': 'No response from analysis model'
            }

        # Try to parse the JSON response
        try:
            # Clean the response - remove any markdown formatting
            response = response.strip()
            logger.debug(f"Raw response before cleaning: {response}")
            
            # Remove markdown code blocks
            if response.startswith('```json'):
                response = response[7:]
            elif response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            logger.debug(f"Response after removing markdown: {response}")

            # Remove comments starting with //
            response = re.sub(r'//.*$', '', response, flags=re.MULTILINE)
            logger.debug(f"Response after removing comments: {response}")

            # Remove trailing commas in arrays
            response = re.sub(r',(\s*])', r'\1', response)
            # Remove trailing commas in objects
            response = re.sub(r',(\s*})', r'\1', response)

            # Extract JSON from response if it's wrapped in other text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string: {json_str}")
                
                # Fix common JSON formatting issues
                # 1. Remove trailing commas before closing braces and brackets
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                
                # 2. Fix property names - handle both quoted and unquoted cases
                # First, find all property names (both quoted and unquoted)
                property_names = re.findall(r'([{,])\s*(?:"([^"]+)"|([^"{\s][^:]*?)):\s*', json_str)
                
                # Replace each property name with its properly quoted version
                for match in property_names:
                    prefix, quoted_name, unquoted_name = match
                    name = quoted_name if quoted_name else unquoted_name
                    if name:
                        # Escape any double quotes in the name
                        escaped_name = name.replace('"', '\\"')
                        # Replace the original property name with the properly quoted version
                        json_str = json_str.replace(f'{prefix} {name}:', f'{prefix} "{escaped_name}":')
                        json_str = json_str.replace(f'{prefix}"{name}":', f'{prefix} "{escaped_name}":')
                
                # 3. Fix single quotes to double quotes
                json_str = json_str.replace("'", '"')
                
                # 4. Fix missing quotes around values
                json_str = re.sub(r':\s*([a-zA-Z0-9_]+)([,}])', r':"\1"\2', json_str)
                
                logger.debug(f"Cleaned JSON string: {json_str}")
                try:
                    analysis_result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"First attempt failed: {str(e)}")
                    # Try one more time with more aggressive cleaning
                    json_str = re.sub(r'([{,])\s*([^"{\s][^:]*?):\s*', r'\1"\2":', json_str)
                    analysis_result = json.loads(json_str)
            else:
                # Try parsing the whole response as JSON
                # Apply the same fixes to the whole response
                response = re.sub(r',(\s*[}\]])', r'\1', response)  # Remove trailing commas
                
                # Fix property names in the whole response
                property_names = re.findall(r'([{,])\s*(?:"([^"]+)"|([^"{\s][^:]*?)):\s*', response)
                for match in property_names:
                    prefix, quoted_name, unquoted_name = match
                    name = quoted_name if quoted_name else unquoted_name
                    if name:
                        escaped_name = name.replace('"', '\\"')
                        response = response.replace(f'{prefix} {name}:', f'{prefix} "{escaped_name}":')
                        response = response.replace(f'{prefix}"{name}":', f'{prefix} "{escaped_name}":')
                
                response = response.replace("'", '"')
                response = re.sub(r':\s*([a-zA-Z0-9_]+)([,}])', r':"\1"\2', response)
                
                logger.debug(f"Cleaned full response: {response}")
                try:
                    analysis_result = json.loads(response)
                except json.JSONDecodeError as e:
                    logger.error(f"First attempt failed: {str(e)}")
                    # Try one more time with more aggressive cleaning
                    response = re.sub(r'([{,])\s*([^"{\s][^:]*?):\s*', r'\1"\2":', response)
                    analysis_result = json.loads(response)

            # Validate the structure
            if not isinstance(analysis_result, dict):
                raise ValueError("Response is not a dictionary")

            # Ensure the data field exists and is a dictionary
            if 'data' not in analysis_result:
                analysis_result = {'data': analysis_result}
            elif not isinstance(analysis_result['data'], dict):
                analysis_result['data'] = {}

            # Clean up the keys in the data dictionary
            cleaned_data = {}
            for key, value in analysis_result['data'].items():
                # Remove specific words from keys
                cleaned_key = key
                # Remove words in parentheses
                cleaned_key = re.sub(r'\([^)]*\)', '', cleaned_key)
                # Remove specific words
                cleaned_key = re.sub(r'\b(composite|direct|indirect)\b', '', cleaned_key, flags=re.IGNORECASE)
                # Remove extra spaces and clean up
                cleaned_key = re.sub(r'\s+', ' ', cleaned_key)
                cleaned_key = cleaned_key.strip()
                cleaned_data[cleaned_key] = value

            analysis_result['data'] = cleaned_data

            return {
                'data': analysis_result['data'],
                'success': True
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from analysis: {str(e)}")
            logger.error(f"Raw response: {response}")
            # Try one last time with a more aggressive cleaning
            try:
                # Remove any non-JSON text before and after the JSON object
                json_str = re.search(r'\{.*\}', response, re.DOTALL).group()
                # Remove comments starting with //
                json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
                # Remove trailing commas in arrays
                json_str = re.sub(r',(\s*])', r'\1', json_str)
                # Remove trailing commas in objects
                json_str = re.sub(r',(\s*})', r'\1', json_str)
                # Convert all single quotes to double quotes
                json_str = json_str.replace("'", '"')
                # Add quotes around all unquoted property names (including those with colons)
                json_str = re.sub(r'([{,])\s*"([^"]+)"\s*:', r'\1"\2":', json_str)
                # Add quotes around all unquoted values
                json_str = re.sub(r':\s*([a-zA-Z0-9_]+)([,}])', r':"\1"\2', json_str)
                
                logger.debug(f"Last attempt cleaned JSON: {json_str}")
                analysis_result = json.loads(json_str)
                
                if 'data' not in analysis_result:
                    analysis_result = {'data': analysis_result}
                elif not isinstance(analysis_result['data'], dict):
                    analysis_result['data'] = {}

                # Clean up the keys in the data dictionary
                cleaned_data = {}
                for key, value in analysis_result['data'].items():
                    # Remove specific words from keys
                    cleaned_key = key
                    # Remove words in parentheses
                    cleaned_key = re.sub(r'\([^)]*\)', '', cleaned_key)
                    # Remove specific words
                    cleaned_key = re.sub(r'\b(composite|direct|indirect)\b', '', cleaned_key, flags=re.IGNORECASE)
                    # Remove extra spaces and clean up
                    cleaned_key = re.sub(r'\s+', ' ', cleaned_key)
                    cleaned_key = cleaned_key.strip()
                    cleaned_data[cleaned_key] = value

                analysis_result['data'] = cleaned_data
                    
                return {
                    'data': analysis_result['data'],
                    'success': True
                }
            except Exception as e2:
                logger.error(f"Last attempt failed: {str(e2)}")
                return {
                    'data': {},
                    'error': f'Failed to parse analysis response: {str(e)}'
                }
    except Exception as e:
        logger.error(f"Error in infer_data_from_html_structure: {str(e)}", exc_info=True)
        return {
            'data': {},
            'error': f'Error in infer_data_from_html_structure: {str(e)}'
        }

def analyze_html_structure(screenshot_data: bytes, minimal_html: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze the HTML structure using screenshot and HTML source
    
    Args:
        screenshot_data (bytes): Raw PNG image data of the current page
        minimal_html (Dict[str, str]): Pre-filtered HTML elements and their selectors
    Returns:
        dict: Contains 'read' and 'write' lists with valid CSS selectors/paths
    """
    try:
        # Convert screenshot to base64 for API call
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Create system prompt for HTML analysis
        # Create input text for analysis
        analysis_text = f"""Please analyze this webpage and classify the elements into read and write elements.
List of HTML elements and their CSS selectors:
{str(minimal_html)}"""

        # Create input content with HTML and screenshot
        input_content = {
            "text": analysis_text,
            "image": f"data:image/png;base64,{screenshot_base64}"
        }
        
        # Call OpenAI API for analysis
        response = call_openai_api(BROWSER_CLASSIFY_DATA, input_content, "computer-use")
        
        logger.info(f"[browser_agent_core.py] Classification response: {response}")
        
        # response can have comments starting with // remove them till the end of the line
        response = re.sub(r'//.*', '', response)
        if not response:
            logger.error("No response from OpenAI API for HTML analysis")
            return {
                'read': [],
                'write': [],
                'error': 'No response from analysis model'
            }
        
        # Try to parse the JSON response
        try:
            # Clean the response - remove any markdown formatting
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            elif response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # Extract JSON from response if it's wrapped in other text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis_result = json.loads(json_str)
            else:
                # Try parsing the whole response as JSON
                analysis_result = json.loads(response)
            
            # Validate the structure
            if not isinstance(analysis_result, dict):
                raise ValueError("Response is not a dictionary")

            read_selectors = analysis_result.get('read', [])
            write_selectors = analysis_result.get('write', [])
            
            # Ensure they are lists
            if not isinstance(read_selectors, list):
                read_selectors = []
            if not isinstance(write_selectors, list):
                write_selectors = []
            
            # Filter out any non-string values and validate CSS selectors
            valid_read_selectors = []
            valid_write_selectors = []
            
            for selector in read_selectors:
                if isinstance(selector, str) and selector.strip():
                    valid_read_selectors.append(selector.strip())
            
            for selector in write_selectors:
                if isinstance(selector, str) and selector.strip():
                    valid_write_selectors.append(selector.strip())
            
            logger.info(f"HTML analysis found {len(valid_read_selectors)} read elements and {len(valid_write_selectors)} write elements")
            logger.info(f"Valid read selectors: {valid_read_selectors}")
            logger.info(f"Valid write selectors: {valid_write_selectors}")
            
            return {
                'read': valid_read_selectors,
                'write': valid_write_selectors,
                'success': True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from analysis: {str(e)}")
            logger.debug(f"Raw response: {response}")
            return {
                'read': [],
                'write': [],
                'error': f'Failed to parse analysis response: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error processing analysis response: {str(e)}")
            return {
                'read': [],
                'write': [],
                'error': f'Error processing response: {str(e)}'
            }
            
    except Exception as e:
        logger.error(f"Error in HTML structure analysis: {str(e)}", exc_info=True)
        return {
            'read': [],
            'write': [],
            'error': f'Analysis failed: {str(e)}'
        }

def highlight_analyzed_elements(html_structure: Dict[str, Any] | list, highlight_type: str = "both") -> Dict[str, Any]:
    """
    Highlight the analyzed HTML elements by injecting CSS borders
    
    Args:
        html_structure (dict | list): Either:
            - Dictionary containing data types as keys and arrays of CSS selectors as values
            - List of CSS selectors to highlight
        highlight_type (str): What to highlight - "read", "write", or "both"
        
    Returns:
        dict: Result of the CSS injection operation
    """
    try:
        logger.info(f"Starting to highlight {highlight_type} elements")
        
        # Define colors for read and write elements
        read_colors = [
            ('#4CAF50', '#4CAF50'),  # Green
            ('#2196F3', '#2196F3'),  # Blue
            ('#00BCD4', '#00BCD4'),  # Cyan
            ('#607D8B', '#607D8B'),  # Blue Grey
        ]
        
        write_colors = [
            ('#F44336', '#F44336'),  # Red
            ('#FF9800', '#FF9800'),  # Orange
            ('#9C27B0', '#9C27B0'),  # Purple
            ('#E91E63', '#E91E63'),  # Pink
        ]
        
        # Choose color palette based on highlight type
        colors = write_colors if highlight_type == "write" else read_colors
        logger.info(f"Using {'write' if highlight_type == 'write' else 'read'} color palette")
        
        css_rules = ""
        color_index = 0
        total_selectors = 0

        # Handle list input
        if isinstance(html_structure, list):
            logger.info(f"Processing list of {len(html_structure)} selectors")
            for selector in html_structure:
                if not isinstance(selector, str) or not selector.strip():
                    logger.warning(f"Invalid selector found, skipping")
                    continue
                
                total_selectors += 1
                # Add prefix to label based on highlight type
                label_prefix = "Write: " if highlight_type == "write" else "Read: "
                border_color, bg_color = colors[color_index % len(colors)]
                color_index += 1
                
                css_rules += f"""
                {selector} {{
                    border: 2px solid {border_color} !important;
                    box-shadow: 0 0 5px {border_color} !important;
                    position: relative !important;
                }}
                {selector}::after {{
                    content: '{label_prefix}Element';
                    position: absolute;
                    top: -18px;
                    right: 0;
                    background: {bg_color};
                    color: white;
                    padding: 1px 4px;
                    font-size: 9px;
                    font-family: monospace;
                    border-radius: 2px;
                    z-index: 9999;
                    pointer-events: none;
                    font-weight: bold;
                }}
                """
        # Handle dictionary input (existing functionality)
        elif isinstance(html_structure, dict):
            # Get the data dictionary from the structure
            data_dict = html_structure.get('data', {})
            if not data_dict:
                logger.error("No data found in HTML structure")
                return {
                    'success': False,
                    'error': 'No data found in HTML structure'
                }
            
            logger.info(f"Found {len(data_dict)} data types to highlight")
            
            # Process each data type and its selectors
            for data_type, selectors in data_dict.items():
                if not isinstance(selectors, list):
                    logger.warning(f"Selectors for {data_type} is not a list, skipping")
                    continue
                    
                # Get color for this data type
                border_color, bg_color = colors[color_index % len(colors)]
                color_index += 1
                
                logger.info(f"Processing {len(selectors)} selectors for data type: {data_type}")
                
                # Add CSS rules for each selector in this data type
                for selector in selectors:
                    if not isinstance(selector, str) or not selector.strip():
                        logger.warning(f"Invalid selector found for {data_type}, skipping")
                        continue
                    
                    total_selectors += 1
                    # Add prefix to label based on highlight type
                    label_prefix = "Write: " if highlight_type == "write" else "Read: "
                    
                    css_rules += f"""
                    {selector} {{
                        border: 2px solid {border_color} !important;
                        box-shadow: 0 0 5px {border_color} !important;
                        position: relative !important;
                    }}
                    {selector}::after {{
                        content: '{label_prefix}{data_type}';
                        position: absolute;
                        top: -18px;
                        right: 0;
                        background: {bg_color};
                        color: white;
                        padding: 1px 4px;
                        font-size: 9px;
                        font-family: monospace;
                        border-radius: 2px;
                        z-index: 9999;
                        pointer-events: none;
                        font-weight: bold;
                    }}
                    """
        else:
            logger.error("Invalid input type for html_structure")
            return {
                'success': False,
                'error': 'html_structure must be either a dictionary or a list'
            }
        
        if not css_rules:
            logger.error("No valid selectors found to highlight")
            return {
                'success': False,
                'error': 'No valid selectors found to highlight'
            }
        
        logger.info(f"Generated CSS rules for {total_selectors} selectors")
        
        # Send CSS to the injection endpoint
        payload = {
            'css': css_rules
        }
        
        logger.info("Sending CSS rules to injection endpoint")
        response = requests.post('http://localhost:8080/inject-css', 
                               json=payload, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Successfully highlighted {highlight_type} elements")
            return {
                'success': True,
                'message': f'Highlighted {highlight_type} elements',
                'css_applied': result.get('css_applied', '')
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            logger.error(f"Failed to inject CSS: {response.status_code} - {error_data}")
            return {
                'success': False,
                'error': f'CSS injection failed: {error_data.get("error", "Unknown error")}'
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to CSS injection server: {str(e)}")
        return {
            'success': False,
            'error': f'Connection error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Error highlighting elements: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Highlighting failed: {str(e)}'
        }

def clear_custom_css() -> Dict[str, Any]:
    """
    Clear all CSS highlighting from the page
    
    Returns:
        dict: Result of the CSS clearing operation
    """
    try:
        response = requests.post('http://localhost:8080/clear-css', timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("Successfully cleared element highlighting")
            return {
                'success': True,
                'message': result.get('message', 'Highlighting cleared')
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            logger.error(f"Failed to clear CSS: {response.status_code} - {error_data}")
            return {
                'success': False,
                'error': f'CSS clearing failed: {error_data.get("error", "Unknown error")}'
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to CSS clearing server: {str(e)}")
        return {
            'success': False,
            'error': f'Connection error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Error clearing highlighting: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Clearing failed: {str(e)}'
        }

def get_minimum_element_path(element) -> str:
    """
    Generate a unique CSS selector for an HTML element using the minimum necessary path.
    Prioritizes IDs, then classes, and falls back to tag names with nth-child if needed.
    
    Args:
        element: BeautifulSoup element to generate selector for
        
    Returns:
        str: Unique CSS selector for the element
    """
    if not element:
        return ""
        
    # If element has an ID, use that as it's unique
    if element.get('id'):
        return f"#{element['id']}"
        
    # Build selector using classes if available
    classes = element.get('class', [])
    if classes:
        class_selector = '.'.join(classes)
        # Check if this class combination is unique
        siblings = element.find_previous_siblings() + element.find_next_siblings()
        if not any(s.get('class') == classes for s in siblings):
            return f".{class_selector}"
            
    # If no unique identifier found, use tag name with nth-child
    tag = element.name
    if not tag:
        return ""
        
    # Count position among siblings
    position = 1
    for sibling in element.find_previous_siblings():
        if sibling.name == tag:
            position += 1
            
    return f"{tag}:nth-of-type({position})"

def get_element_paths(html_content: str) -> Dict[str, str]:
    """
    Analyze HTML content and create a mapping of content to unique selectors.
    
    Args:
        html_content (str): HTML content to analyze
        
    Returns:
        dict: Mapping of content descriptions to unique selectors
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        content_map = {}
        
        # Handle text elements
        for text_node in soup.find_all(text=True):
            if text_node.strip() and text_node.parent.name not in ['script', 'style']:
                cleaned_text = f"Text: {text_node.strip()}"
                selector = get_minimum_element_path(text_node.parent)
                if selector:
                    content_map[cleaned_text] = selector
        
        # Handle images/icons
        for element in soup.find_all(['img', 'i', 'svg']):
            identifier = element.get('alt') or element.get('title') or ' '.join(element.get('class', []))
            element_type = "Image" if element.name == 'img' else "Icon"
            key = f"{element_type}: {identifier}"
            selector = get_minimum_element_path(element)
            if selector:
                content_map[key] = selector
                
        return content_map
    
    except Exception as e:
        logger.error(f"Error getting element paths: {str(e)}", exc_info=True)
        return {}

def get_dom_tree_with_selectors(html_content: str) -> Dict[str, Any]:
    """
    Create a DOM tree where each node is a CSS selector.
    Uses the same selector generation logic as get_element_paths.
    
    Args:
        html_content (str): HTML content to analyze
        
    Returns:
        dict: Tree structure where each node is a CSS selector and has children if any
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        def build_tree(element) -> Dict[str, Any]:
            """Recursively build the tree structure for an element"""
            if element is None:
                return None
                
            # Skip script and style tags
            if element.name in ['script', 'style']:
                return None
                
            # Get the selector for this element
            selector = get_minimum_element_path(element)
            if not selector:
                return None
                
            # Process children
            children = {}
            for child in element.children:
                if child.name is not None:  # Skip text nodes
                    child_tree = build_tree(child)
                    if child_tree is not None:
                        children.update(child_tree)
            
            # If no children, just return the selector
            if not children:
                return {selector: {}}
            
            # Return selector with its children
            return {selector: children}
        
        # Start with the root element
        root = soup.find('html')
        if root is None:
            root = soup.find('body')
        if root is None:
            root = soup
            
        tree = build_tree(root)
        
        return {
            'success': True,
            'tree': tree
        }
        
    except Exception as e:
        logger.error(f"Error getting DOM tree with selectors: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'tree': None
        }

def get_allowed_and_not_allowed_elements(data_required: Dict[str, Any], html_structure: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Get allowed and not allowed elements based on data requirements
    
    Args:
        data_required (Dict[str, Any]): Data requirements with data type as key and list of CSS selectors as value
        html_structure (Dict[str, Any]): HTML structure with read and write elements
    Returns:
        Tuple[Dict[str, List[str]], Dict[str, List[str]]]: Allowed and not allowed elements
    """
    
    allowed_elements = {'read': [], 'write': []}
    not_allowed_elements = {'read': [], 'write': []}

    for data_type, selectors in data_required['data'].items():
        permission_result = {'read': None, 'write': None}
        
        for selector in selectors:
            selector_type = 'read' if selector in html_structure['read'] else 'write' if selector in html_structure['write'] else None
            if not selector_type:
                logger.warning(f"Selector {selector} not found in HTML structure")
                continue

            if permission_result[selector_type] is None:
                temp_policy_system = PolicySystem()
                permission_text = f"Grant {data_type} access for {data_type}"
                temp_policy_system.add_policies_from_text(permission_text, agent_manager)
                permission_allowed = True
                for policy in temp_policy_system.get_all_policy_rules():
                    permission_allowed = agent_manager.policy_system.is_action_allowed(policy)
                    if not permission_allowed:
                        break
                permission_result[selector_type] = permission_allowed
            
            if permission_result[selector_type] is True:
                allowed_elements[selector_type].append(selector)
            else:
                not_allowed_elements[selector_type].append(selector)
                
    return allowed_elements, not_allowed_elements
            
def infer_permissions_from_html(screenshot_data: bytes) -> Dict[str, Any]:
    clear_custom_css()

    # Get the HTML source and create minimal version
    html_result = get_html_source()
    if not html_result.get('success', False) or not html_result.get('html'):
        return create_message(
            content="Failed to get HTML source",
            role="system",
            msg_type=MessageType.ERROR
        )

    # Create minimal HTML with element paths
    minimal_html = get_element_paths(html_result['html'])

    # First analyze HTML structure to get read/write elements
    html_structure = analyze_html_structure(screenshot_data, minimal_html)
    if not html_structure.get('success', False):
        return create_message(
            content=html_structure.get('error', 'Failed to analyze HTML structure'),
            role="system",
            msg_type=MessageType.ERROR
        )

    # Filter the minimal HTML to only include elements that are in the read and write lists to create a single dict from conetnt to css selector
    filtered_minimal_html = {}
    for element, selector in minimal_html.items():
        if selector in html_structure.get('read', []):
            filtered_minimal_html[element] = selector
        if selector in html_structure.get('write', []):
            filtered_minimal_html[element] = selector

    # Now infer data from the filtered HTML structure for all elements
    data_required = infer_data_from_html_structure(screenshot_data, filtered_minimal_html, html_result['html'])
    if not data_required.get('success', False):
        return create_message(
            content=data_required.get('error', 'Failed to infer data from HTML structure'),
            role="system",
            msg_type=MessageType.ERROR
        )

    logger.info(f"[browser_agent_core.py] Data required: {data_required}")

    allowed_elements, not_allowed_elements = get_allowed_and_not_allowed_elements(data_required, html_structure)

    logger.info(f"[browser_agent_core.py] Allowed elements: {allowed_elements}")
    logger.info(f"[browser_agent_core.py] Not allowed elements: {not_allowed_elements}")

    handle_not_allowed_elements(not_allowed_elements)

def handle_not_allowed_elements(not_allowed_elements: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Handle elements that are not allowed to be read or written to by adding CSS rules.
    For read elements: Black out with a message
    For write elements: Disable interaction and show a message
    
    Args:
        not_allowed_elements (Dict[str, List[str]]): Dictionary with 'read' and 'write' lists of CSS selectors
        
    Returns:
        dict: Result of the CSS injection operation
    """
    try:
        css_rules = ""
        
        # Handle read elements - black out with message
        for selector in not_allowed_elements.get('read', []):
            if not isinstance(selector, str) or not selector.strip():
                continue
                
            css_rules += f"""
            {selector} {{
                position: relative !important;
                background: #000 !important;
                color: transparent !important;
                text-shadow: 0 0 8px rgba(0,0,0,0.5) !important;
                pointer-events: none !important;
                user-select: none !important;
            }}
            {selector}::before {{
                content: 'Data not permissioned for viewing' !important;
                position: absolute !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                background: rgba(0, 0, 0, 0.9) !important;
                color: white !important;
                padding: 12px 16px !important;
                border-radius: 6px !important;
                font-size: 16px !important;
                font-weight: bold !important;
                z-index: 99999 !important;
                white-space: nowrap !important;
                pointer-events: none !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
                border: 2px solid rgba(255,255,255,0.2) !important;
            }}
            """
            
        # Handle write elements - disable interaction
        for selector in not_allowed_elements.get('write', []):
            if not isinstance(selector, str) or not selector.strip():
                continue
                
            css_rules += f"""
            {selector} {{
                position: relative !important;
                opacity: 0.5 !important;
                pointer-events: none !important;
                cursor: not-allowed !important;
            }}
            {selector}::before {{
                content: 'No permission to interact' !important;
                position: absolute !important;
                top: -24px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                background: rgba(255, 0, 0, 0.9) !important;
                color: white !important;
                padding: 6px 12px !important;
                border-radius: 4px !important;
                font-size: 14px !important;
                font-weight: bold !important;
                z-index: 99999 !important;
                white-space: nowrap !important;
                pointer-events: none !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
                border: 2px solid rgba(255,255,255,0.2) !important;
            }}
            {selector}::after {{
                content: '' !important;
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                background: rgba(255, 0, 0, 0.1) !important;
                z-index: 99998 !important;
                pointer-events: auto !important;
                cursor: not-allowed !important;
            }}
            """
            
        if not css_rules:
            logger.warning("No valid selectors found to handle")
            return {
                'success': False,
                'error': 'No valid selectors found to handle'
            }
            
        # Send CSS to the injection endpoint
        payload = {
            'css': css_rules
        }
        
        logger.info("Sending CSS rules to handle non-allowed elements")
        response = requests.post('http://localhost:8080/inject-css', 
                               json=payload, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("Successfully handled non-allowed elements")
            return {
                'success': True,
                'message': 'Non-allowed elements handled',
                'css_applied': result.get('css_applied', '')
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            logger.error(f"Failed to inject CSS: {response.status_code} - {error_data}")
            return {
                'success': False,
                'error': f'CSS injection failed: {error_data.get("error", "Unknown error")}'
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to CSS injection server: {str(e)}")
        return {
            'success': False,
            'error': f'Connection error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Error handling non-allowed elements: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Handling failed: {str(e)}'
        }