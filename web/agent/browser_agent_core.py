import logging
from enum import Enum
from typing import Dict, Any, Tuple, List
import os
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
from src.prompts import BROWSER_INFER_DATA, BROWSER_CLASSIFY_DATA, BROWSER_AGENT
from .text_transforms import process_text_value
from datetime import datetime, timedelta

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

# Add selector cache implementation
class SelectorCache:
    def __init__(self, cache_duration_minutes: int = 30):
        self.cache = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        logger.info(f"Initialized SelectorCache with {cache_duration_minutes} minute duration")
    
    def _get_cache_key(self, url: str, selector_type: str) -> str:
        """Generate a cache key from URL and selector type"""
        return f"{url}:{selector_type}"
    
    def get(self, url: str, selector_type: str) -> Tuple[Dict[str, Any], bool]:
        """Get cached selectors for a URL and type"""
        cache_key = self._get_cache_key(url, selector_type)
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry['timestamp'] < self.cache_duration:
                logger.info(f"Cache HIT for {cache_key} (age: {datetime.now() - entry['timestamp']})")
                return entry['data'], True
            else:
                # Remove expired entry
                logger.info(f"Cache EXPIRED for {cache_key} (age: {datetime.now() - entry['timestamp']})")
                del self.cache[cache_key]
        logger.info(f"Cache MISS for {cache_key}")
        return {}, False
    
    def set(self, url: str, selector_type: str, data: Dict[str, Any]) -> None:
        """Cache selectors for a URL and type"""
        cache_key = self._get_cache_key(url, selector_type)
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        logger.info(f"Cache SET for {cache_key} (total entries: {len(self.cache)})")
    
    def clear(self) -> None:
        """Clear all cached entries"""
        logger.info(f"Cache CLEARED (removed {len(self.cache)} entries)")
        self.cache.clear()

# Initialize global selector cache
selector_cache = SelectorCache()

class EvaluationCache:
    def __init__(self, cache_duration_minutes: int = 30):
        self.cache = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        logger.info(f"Initialized EvaluationCache with {cache_duration_minutes} minute duration")
    
    def _get_cache_key(self, expression: str, tab_id: str) -> str:
        """Generate a cache key from expression and tab ID"""
        return f"{tab_id}:{expression}"
    
    def get(self, expression: str, tab_id: str) -> Tuple[Dict[str, Any], bool]:
        """Get cached evaluation result"""
        cache_key = self._get_cache_key(expression, tab_id)
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry['timestamp'] < self.cache_duration:
                logger.info(f"Cache HIT for evaluation: {cache_key[:50]}...")
                return entry['result'], True
            else:
                logger.info(f"Cache EXPIRED for evaluation: {cache_key[:50]}...")
                del self.cache[cache_key]
        logger.info(f"Cache MISS for evaluation: {cache_key[:50]}...")
        return None, False
    
    def set(self, expression: str, tab_id: str, result: Dict[str, Any]) -> None:
        """Cache evaluation result"""
        cache_key = self._get_cache_key(expression, tab_id)
        self.cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        logger.info(f"Cache SET for evaluation: {cache_key[:50]}...")
    
    def clear(self) -> None:
        """Clear all cached entries"""
        logger.info(f"Cache CLEARED (removed {len(self.cache)} entries)")
        self.cache.clear()

# Initialize caches
selector_cache = SelectorCache()
evaluation_cache = EvaluationCache()

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

def get_active_tab_url() -> Dict[str, Any]:
    """
    Get the URL of the currently active tab
    
    Returns:
        dict: URL data or error information
    """
    try:
        # Get the active tab URL from the Flask API
        response = requests.get('http://localhost:8080/active-tab-url', timeout=10)
        
        if response.status_code == 200:
            url_data = response.json()
            return url_data
        elif response.status_code == 404:
            logger.warning("No active browser tab found")
            return {
                'success': False,
                'error': 'No active browser tab found',
                'url': None,
                'title': None
            }
        else:
            logger.error(f"Failed to get active tab URL: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'url': None,
                'title': None
            }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to screenshot server: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Connection error: {str(e)}',
            'url': None,
            'title': None
        }
    except Exception as e:
        logger.error(f"Error getting active tab URL: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'url': None,
            'title': None
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

# Add a global click counter for browser chat
browser_click_counter = 0

def process_with_computer_use(user_input: str) -> Dict[str, Any]:
    global browser_click_counter
    browser_click_counter += 1
    # Odd click: only infer permissions
    if browser_click_counter % 2 == 1:
        screenshot_data = get_latest_screenshot()
        if not screenshot_data:
            return create_message(
                content="Failed to get screenshot",
                role="system",
                msg_type=MessageType.DEBUG
            )
        infer_permissions_from_html(screenshot_data)
        return create_message(
            content="Screenshot ready for processing.",
            role="system",
            msg_type=MessageType.SYSTEM,
            visibility=MessageVisibility.INTERNAL
        )
    # Even click: original logic
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

        time.sleep(1)
        screenshot_data = get_latest_screenshot()
        # Convert screenshot to base64
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Create the system prompt for computer use
        system_prompt = BROWSER_AGENT
        
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

            # Remove trailing commas in arrays and objects
            response = re.sub(r',(\s*[}\]])', r'\1', response)
            
            # Extract JSON from response if it's wrapped in other text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string: {json_str}")
                try:
                    analysis_result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"First attempt failed: {str(e)}")
                    # Try one more time with more aggressive cleaning
                    json_str = re.sub(r'([{,])\s*([^"{\s][^:]*?):\s*', r'\1"\2":', json_str)
                    analysis_result = json.loads(json_str)
            else:
                # Try parsing the whole response as JSON
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
                # Remove trailing commas in arrays and objects
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                # Convert all single quotes to double quotes
                json_str = json_str.replace("'", '"')
                # Add quotes around all unquoted property names
                json_str = re.sub(r'([{,])\s*([^"{\s][^:]*?):\s*', r'\1"\2":', json_str)
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
        dict: Contains 'read', 'write', and 'create' lists with valid CSS selectors/paths
    """
    try:
        # Convert screenshot to base64 for API call
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Create system prompt for HTML analysis
        # Create input text for analysis
        analysis_text = f"""Please analyze this webpage and classify the elements into read, write, and create elements.
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
                'create': [],
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
            create_selectors = analysis_result.get('create', [])
            
            # Ensure they are lists
            if not isinstance(read_selectors, list):
                read_selectors = []
            if not isinstance(write_selectors, list):
                write_selectors = []
            if not isinstance(create_selectors, list):
                create_selectors = []
            
            # Filter out any non-string values and validate CSS selectors
            valid_read_selectors = []
            valid_write_selectors = []
            valid_create_selectors = []
            
            for selector in read_selectors:
                if isinstance(selector, str) and selector.strip():
                    valid_read_selectors.append(selector.strip())
            
            for selector in write_selectors:
                if isinstance(selector, str) and selector.strip():
                    valid_write_selectors.append(selector.strip())
            
            for selector in create_selectors:
                if isinstance(selector, str) and selector.strip():
                    valid_create_selectors.append(selector.strip())
            
            logger.info(f"HTML analysis found {len(valid_read_selectors)} read elements, {len(valid_write_selectors)} write elements, and {len(valid_create_selectors)} create elements")
            logger.info(f"Valid read selectors: {valid_read_selectors}")
            logger.info(f"Valid write selectors: {valid_write_selectors}")
            logger.info(f"Valid create selectors: {valid_create_selectors}")
            
            return {
                'read': valid_read_selectors,
                'write': valid_write_selectors,
                'create': valid_create_selectors,
                'success': True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from analysis: {str(e)}")
            logger.debug(f"Raw response: {response}")
            return {
                'read': [],
                'write': [],
                'create': [],
                'error': f'Failed to parse analysis response: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error processing analysis response: {str(e)}")
            return {
                'read': [],
                'write': [],
                'create': [],
                'error': f'Error processing response: {str(e)}'
            }
            
    except Exception as e:
        logger.error(f"Error in HTML structure analysis: {str(e)}", exc_info=True)
        return {
            'read': [],
            'write': [],
            'create': [],
            'error': f'Analysis failed: {str(e)}'
        }

def highlight_analyzed_elements(html_structure: Dict[str, Any] | list, highlight_type: str = "both") -> Dict[str, Any]:
    """
    Highlight elements in the browser based on their read/write status.
    Uses caching to improve performance for repeated highlighting of the same URL.
    """
    try:
        # Get current URL
        url_result = get_active_tab_url()
        if not url_result.get('success'):
            logger.error("Failed to get active tab URL")
            return {'success': False, 'error': 'Failed to get active tab URL'}
        
        current_url = url_result.get('url')
        
        # Try to get from cache first
        cache_key = f"highlight_{highlight_type}"
        cached_result, found = selector_cache.get(current_url, cache_key)
        if found:
            logger.info(f"Using cached highlight rules for {current_url}")
            return cached_result
        
        # If not in cache, proceed with highlighting
        logger.info(f"Generating highlight rules for type: {highlight_type}")
        
        css_rules = ""
        total_selectors = 0
        colors = [
            ('#ff6b6b', '#ff4d4f'),  # Red
            ('#4dabf7', '#339af0'),  # Blue
            ('#51cf66', '#37b24d'),  # Green
            ('#ffd43b', '#fcc419'),  # Yellow
            ('#cc5de8', '#be4bdb'),  # Purple
            ('#20c997', '#12b886'),  # Teal
        ]
        color_index = 0
        
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
        # Handle dictionary input
        elif isinstance(html_structure, dict):
            for data_type, selectors in html_structure.items():
                if not isinstance(selectors, list):
                    continue
                    
                # Skip if not the requested highlight type
                if highlight_type != "both":
                    if highlight_type == "read" and data_type not in html_structure.get('read', []):
                        continue
                    if highlight_type == "write" and data_type not in html_structure.get('write', []):
                        continue
                    if highlight_type == "create" and data_type not in html_structure.get('create', []):
                        continue
                
                # Get colors for this data type
                border_color, bg_color = colors[color_index % len(colors)]
                color_index += 1
                
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
        
        if response.status_code != 200:
            logger.error(f"Failed to inject CSS: {response.text}")
            return {
                'success': False,
                'error': f'Failed to inject CSS: {response.text}'
            }
        
        result = {
            'success': True,
            'message': f'Highlighted {total_selectors} elements',
            'css': css_rules
        }
        
        # Cache the result
        selector_cache.set(current_url, cache_key, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in highlight_analyzed_elements: {str(e)}")
        return {
            'success': False,
            'error': str(e)
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
    Uses a combination of structural selectors, text content, and semantic attributes to create
    deterministic selectors that don't rely heavily on IDs or classes.
    
    Args:
        element: BeautifulSoup element to generate selector for
        
    Returns:
        str: Unique CSS selector for the element
    """
    if not element:
        return ""
        
    # Strategy 1: Use semantic attributes (most reliable)
    semantic_attrs = {
        'role': element.get('role'),
        'aria-label': element.get('aria-label'),
        'aria-labelledby': element.get('aria-labelledby'),
        'name': element.get('name'),
        'type': element.get('type'),
        'alt': element.get('alt'),
        'title': element.get('title')
    }
    
    # Try each semantic attribute
    for attr, value in semantic_attrs.items():
        if value:
            # For aria-labelledby, we need to handle it differently
            if attr == 'aria-labelledby':
                return f"[aria-labelledby='{value}']"
            # For other attributes, use a simple attribute selector
            return f"[{attr}='{value}']"
    
    # Strategy 2: Use text content with tag name
    text = element.get_text(strip=True)
    if text and len(text) < 50:  # Only use text if it's not too long
        tag = element.name
        # Escape single quotes in text
        text = text.replace("'", "\\'")
        return f"{tag}:contains('{text}')"
    
    # Strategy 3: Use structural selectors
    tag = element.name
    if not tag:
        return ""
        
    # Build a path using parent-child relationships
    path = []
    current = element
    
    while current and current.name not in ['html', 'body']:
        # Get position among siblings
        position = 1
        for sibling in current.find_previous_siblings():
            if sibling.name == current.name:
                position += 1
        
        # Add to path
        path.append(f"{current.name}:nth-of-type({position})")
        current = current.parent
    
    # Reverse the path to get top-down order
    path.reverse()
    
    # Join with > to create a direct child selector
    return ' > '.join(path)

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

def get_base_url(url: str) -> str:
    """
    Get the base URL from a full URL
    
    Args:
        url (str): Full URL
        
    Returns:
        str: Base URL (protocol + domain)
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        return base_url
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {str(e)}")
        return url

def get_allowed_and_not_allowed_elements_from_text(data_required: Dict[str, Any], html_structure: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Get allowed and not allowed elements based on data requirements
    
    Args:
        data_required (Dict[str, Any]): Data requirements with data type as key and list of CSS selectors as value
        html_structure (Dict[str, Any]): HTML structure with read and write elements
    Returns:
        Tuple[Dict[str, List[str]], Dict[str, List[str]]]: Allowed and not allowed elements
    """
    
    allowed_elements = {'read': [], 'write': [], 'create': []}
    not_allowed_elements = {'read': [], 'write': [], 'create': []}
    granular_data = {}

    for data_type, selectors in data_required['data'].items():
        permission_result = {'read': None, 'write': None, 'create': None}
        
        for selector in selectors:
            selector_type = 'read' if selector in html_structure['read'] else 'write' if selector in html_structure['write'] else 'create' if selector in html_structure['create'] else None
            if not selector_type:
                logger.warning(f"Selector {selector} not found in HTML structure")
                continue

            if permission_result[selector_type] is None:
                temp_policy_system = PolicySystem()
                permission_text = f"Grant {selector_type} access for {data_type}"
                if data_type not in granular_data:
                    temp_policy_system.add_policies_from_text(permission_text, agent_manager)
                    granular_data[data_type] = [
                        policy.get('granular_data')
                        for policy in temp_policy_system.get_all_policy_rules()
                    ]
                else: 
                    for granular_data_type in granular_data[data_type]:
                                        temp_policy_system.add_policy({
                    "granular_data": f"{granular_data_type}",
                    "data_access": "Read" if selector_type == 'read' else "Write" if selector_type == 'write' else "Create" if selector_type == 'create' else "Create"
                })

                permission_allowed = True
                for policy in temp_policy_system.get_all_policy_rules():
                    permission_allowed = agent_manager.policy_system.is_action_allowed([policy])
                    if not permission_allowed:
                        break
                permission_result[selector_type] = permission_allowed
            
            if permission_result[selector_type] is True:
                allowed_elements[selector_type].append(selector)
            else:
                not_allowed_elements[selector_type].append(selector)

    update_config(granular_data)
    return allowed_elements, not_allowed_elements
            
def get_allowed_and_not_allowed_elements_from_config(data_required: Dict[str, Any], html_structure: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Get allowed and not allowed elements based on data requirements
    
    Args:
        data_required (Dict[str, Any]): Data requirements with data type as key and list of CSS selectors as value
        html_structure (Dict[str, Any]): HTML structure with read, write, and create elements
    Returns:
        Tuple[Dict[str, List[str]], Dict[str, List[str]]]: Allowed and not allowed elements
    """
    
    allowed_elements = {'read': [], 'write': [], 'create': []}
    not_allowed_elements = {'read': [], 'write': [], 'create': []}

    logger.info(f"[DEBUG] Processing data required: {data_required}")
    logger.info(f"[DEBUG] HTML structure: {html_structure}")

    for data_type, selectors in data_required['data'].items():
        logger.info(f"[DEBUG] Processing data type: {data_type}")
        logger.info(f"[DEBUG] Selectors for this type: {selectors}")
        permission_result = {'read': None, 'write': None, 'create': None}
        
        for selector in selectors:
            logger.info(f"[DEBUG] Processing selector: {selector}")
            selector_type = 'read' if selector in html_structure['read'] else 'write' if selector in html_structure['write'] else 'create' if selector in html_structure['create'] else None
            if not selector_type:
                logger.warning(f"Selector {selector} not found in HTML structure")
                continue

            if permission_result[selector_type] is None:
                temp_policy_system = PolicySystem()
                permission_text = f"Grant {selector_type} access for {data_type}"
                logger.info(f"[DEBUG] Checking permission: {permission_text}")
                temp_policy_system.add_policy({
                    "granular_data": f"{data_type}",
                    "data_access": "Read" if selector_type == 'read' else "Write" if selector_type == 'write' else "Create"
                })
                permission_allowed = True
                for policy in temp_policy_system.get_all_policy_rules():
                    logger.info(f"[DEBUG] Checking policy: {policy}")
                    permission_allowed = agent_manager.policy_system.is_action_allowed([policy])
                    logger.info(f"[DEBUG] Policy allowed: {permission_allowed}")
                    if not permission_allowed:
                        break
                permission_result[selector_type] = permission_allowed
            
            if permission_result[selector_type] is True:
                logger.info(f"[DEBUG] Adding to allowed elements: {selector}")
                allowed_elements[selector_type].append(selector)
            else:
                logger.info(f"[DEBUG] Adding to not allowed elements: {selector}")
                not_allowed_elements[selector_type].append(selector)
                
    logger.info(f"[DEBUG] Final allowed elements: {allowed_elements}")
    logger.info(f"[DEBUG] Final not allowed elements: {not_allowed_elements}")
    return allowed_elements, not_allowed_elements

def infer_permissions_from_html(screenshot_data: bytes) -> Dict[str, Any]:
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
    logger.info(f"[browser_agent_core.py] Minimal HTML: {minimal_html}")

    success = handle_from_config(minimal_html)
    if success:
        logger.info(f"[browser_agent_core.py] Success in handle_from_config, returning")
        return
    logger.info(f"[browser_agent_core.py] Failed to handle from config, inferring permissions from HTML")

  

    # First analyze HTML structure to get read/write elements
    html_structure = analyze_html_structure(screenshot_data, minimal_html)
    if not html_structure.get('success', False):
        return create_message(
            content=html_structure.get('error', 'Failed to analyze HTML structure'),
            role="system",
            msg_type=MessageType.ERROR
        )

    # Filter the minimal HTML to only include elements that are in the read, write, and create lists to create a single dict from content to css selector
    filtered_minimal_html = {}
    for element, selector in minimal_html.items():
        if selector in html_structure.get('read', []):
            filtered_minimal_html[element] = selector
        if selector in html_structure.get('write', []):
            filtered_minimal_html[element] = selector
        if selector in html_structure.get('create', []):
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

    add_to_config(html_structure, data_required)

    allowed_elements, not_allowed_elements = get_allowed_and_not_allowed_elements_from_text(data_required, html_structure)

    logger.info(f"[browser_agent_core.py] Allowed elements: {allowed_elements}")
    logger.info(f"[browser_agent_core.py] Not allowed elements: {not_allowed_elements}")

    handle_not_allowed_elements(not_allowed_elements)

def handle_not_allowed_elements(not_allowed_elements: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Handle elements that are not allowed to be read or written to by adding CSS rules.
    For read elements: Show emoji icon and tooltip for all, hide all child content, make non-interactive and disable form elements
    For write elements: Disable interaction and show a message
    
    Args:
        not_allowed_elements (Dict[str, List[str]]): Dictionary with 'read', 'write', and 'create' lists of CSS selectors
        
    Returns:
        dict: Result of the CSS injection operation
    """
    try:
        logger.info(f"[DEBUG] Starting handle_not_allowed_elements with elements: {not_allowed_elements}")
        css_rules = ""
        
        def convert_text_selector(selector: str) -> str:
            """Convert text-based selector to valid CSS selector"""
            logger.info(f"[DEBUG] Converting selector: {selector}")
            # Handle :contains() selector
            match = re.match(r'(.*?):contains\([\'"](.*?)[\'"]\)', selector)
            if match:
                tag = match.group(1) or '*'
                text = match.group(2)
                # Escape special characters in text
                text = text.replace("'", "\\'").replace('"', '\\"')
                # Create a data attribute selector that will be set via JavaScript
                converted = f"{tag}[data-axiom-text='{text}']"
                logger.info(f"[DEBUG] Converted selector: {selector} -> {converted}")
                return converted
            logger.info(f"[DEBUG] No conversion needed for selector: {selector}")
            return selector

        # Convert all selectors to valid CSS
        converted_read = [convert_text_selector(sel) for sel in not_allowed_elements.get('read', [])]
        converted_write = [convert_text_selector(sel) for sel in not_allowed_elements.get('write', [])]
        converted_create = [convert_text_selector(sel) for sel in not_allowed_elements.get('create', [])]
        
        logger.info(f"[DEBUG] Converted read selectors: {converted_read}")
        logger.info(f"[DEBUG] Converted write selectors: {converted_write}")
        logger.info(f"[DEBUG] Converted create selectors: {converted_create}")
        
        # Add JavaScript to set data attributes for text matching
        js_code = """
        (function() {
            function setTextAttributes() {
                console.log('Setting text attributes...');
                // Handle read elements
                %s
                
                // Handle write elements
                %s
                
                // Handle create elements
                %s
            }
            setTextAttributes();
            // Re-run after any DOM changes
            const observer = new MutationObserver(() => {
                console.log('DOM changed, updating text attributes...');
                setTextAttributes();
            });
            observer.observe(document.body, { childList: true, subtree: true });
            console.log('Text attribute observer set up');
        })();
        """ % (
            '\n'.join(f"""
                document.querySelectorAll('{sel.split('[')[0]}').forEach(el => {{
                    if (el.textContent.trim() === '{text}') {{
                        console.log('Setting attribute for exact match element:', el);
                        el.setAttribute('data-axiom-text', '{text}');
                    }}
                }});
            """ for sel, text in [(sel, re.search(r'data-axiom-text=\'([^\']+)\'', sel).group(1)) for sel in converted_read if 'data-axiom-text' in sel]),
            '\n'.join(f"""
                document.querySelectorAll('{sel.split('[')[0]}').forEach(el => {{
                    if (el.textContent.trim() === '{text}') {{
                        console.log('Setting attribute for exact match element:', el);
                        el.setAttribute('data-axiom-text', '{text}');
                    }}
                }});
            """ for sel, text in [(sel, re.search(r'data-axiom-text=\'([^\']+)\'', sel).group(1)) for sel in converted_write if 'data-axiom-text' in sel]),
            '\n'.join(f"""
                document.querySelectorAll('{sel.split('[')[0]}').forEach(el => {{
                    if (el.textContent.trim() === '{text}') {{
                        console.log('Setting attribute for exact match element:', el);
                        el.setAttribute('data-axiom-text', '{text}');
                    }}
                }});
            """ for sel, text in [(sel, re.search(r'data-axiom-text=\'([^\']+)\'', sel).group(1)) for sel in converted_create if 'data-axiom-text' in sel])
        )

        logger.info(f"[DEBUG] Generated JavaScript code: {js_code}")

        # Inject JavaScript first
        logger.info("[DEBUG] Injecting JavaScript for text matching...")
        js_response = requests.post('http://localhost:8080/evaluate', 
                                  json={'expression': js_code},
                                  timeout=10)
        
        if js_response.status_code != 200:
            logger.error(f"[DEBUG] Failed to inject JavaScript: {js_response.status_code}")
            logger.error(f"[DEBUG] JavaScript response: {js_response.text}")
            return {
                'success': False,
                'error': 'Failed to inject JavaScript for text matching'
            }
        
        logger.info("[DEBUG] JavaScript injected successfully")

        # Now add CSS rules using converted selectors
        logger.info("[DEBUG] Generating CSS rules...")
        for selector in converted_read:
            if not isinstance(selector, str) or not selector.strip():
                continue
            sel = selector.strip()
            logger.info(f"[DEBUG] Adding CSS rules for read selector: {sel}")
            css_rules += f"""
{sel} {{
    background: rgba(40,40,40,0.85) !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    color: transparent !important; /* Hide direct text */
    text-shadow: none !important;   /* Remove any text shadow */
    position: relative !important;
}}
{sel}::before {{
    content: '🚫';
    font-size: 22px !important;
    color: #fff !important;
    position: absolute !important;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    opacity: 0.8;
}}
{sel}:hover::after {{
    opacity: 1 !important;
}}
{sel}::after {{
    content: 'Access restricted';
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translateX(-50%);
    background: #222;
    color: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
    margin-top: 4px;
    z-index: 10000000;
}}
{sel} * {{
    visibility: hidden !important;
    color: transparent !important;
    pointer-events: none !important;
}}
"""
        # Handle write elements - disable interaction and hide data
        for selector in converted_write:
            if not isinstance(selector, str) or not selector.strip():
                continue
            logger.info(f"[DEBUG] Adding CSS rules for write selector: {selector}")
            css_rules += f"""
{selector} {{
    background: #ff4d4f !important;
    border-radius: 8px !important;
    border: 2px solid #ff7875 !important;
    color: transparent !important; /* Hide direct text */
    text-shadow: none !important;   /* Remove any text shadow */
    position: relative !important;
    pointer-events: none !important;
    cursor: not-allowed !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    min-width: 16px !important;
    min-height: 16px !important;
    overflow: hidden !important;
}}
{selector}::before {{
    content: '🚫';
    font-size: 22px !important;
    color: #fff !important;
    position: absolute !important;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    opacity: 0.8;
}}
{selector}:hover::after {{
    opacity: 1 !important;
}}
{selector}::after {{
    content: 'No permission to interact';
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translateX(-50%);
    background: #ff4d4f;
    color: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
    margin-top: 4px;
    z-index: 10000000;
}}
{selector} * {{
    visibility: hidden !important;
    color: transparent !important;
    pointer-events: none !important;
}}
"""
        # Handle create elements - disable interaction and hide data
        for selector in converted_create:
            if not isinstance(selector, str) or not selector.strip():
                continue
            logger.info(f"[DEBUG] Adding CSS rules for create selector: {selector}")
            css_rules += f"""
{selector} {{
    background: #ffd700 !important;
    border-radius: 8px !important;
    border: 2px solid #ffcc00 !important;
    color: transparent !important; /* Hide direct text */
    text-shadow: none !important;   /* Remove any text shadow */
    position: relative !important;
    pointer-events: none !important;
    cursor: not-allowed !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    min-width: 16px !important;
    min-height: 16px !important;
    overflow: hidden !important;
}}
{selector}::before {{
    content: '🚫';
    font-size: 22px !important;
    color: #fff !important;
    position: absolute !important;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    opacity: 0.8;
}}
{selector}:hover::after {{
    opacity: 1 !important;
}}
{selector}::after {{
    content: 'No permission to interact';
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translateX(-50%);
    background: #ffd700;
    color: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
    margin-top: 4px;
    z-index: 10000000;
}}
{selector} * {{
    visibility: hidden !important;
    color: transparent !important;
    pointer-events: none !important;
}}
"""
        if not css_rules:
            logger.warning("[DEBUG] No valid selectors found to handle")
            # Clear any existing CSS since we have no new rules to inject
            clear_result = clear_custom_css()
            if not clear_result.get('success'):
                logger.error(f"[DEBUG] Failed to clear CSS: {clear_result.get('error')}")
            return {
                'success': False,
                'error': 'No valid selectors found to handle'
            }
            
        logger.info(f"[DEBUG] Generated CSS rules (first 500 chars): {css_rules[:500]}")
        
        # Send CSS to the injection endpoint
        payload = {
            'css': css_rules
        }
        logger.info("[DEBUG] Sending CSS rules to injection endpoint...")
        response = requests.post('http://localhost:8080/inject-css', 
                               json=payload, 
                               timeout=10)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[DEBUG] CSS injection successful. Result: {result}")
            return {
                'success': True,
                'message': 'Non-allowed elements handled',
                'css_applied': result.get('css_applied', '')
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            logger.error(f"[DEBUG] Failed to inject CSS: {response.status_code} - {error_data}")
            return {
                'success': False,
                'error': f'CSS injection failed: {error_data.get("error", "Unknown error")}'
            }
    except requests.exceptions.RequestException as e:
        logger.error(f"[DEBUG] Error connecting to CSS injection server: {str(e)}")
        return {
            'success': False,
            'error': f'Connection error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"[DEBUG] Error handling non-allowed elements: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Handling failed: {str(e)}'
        }

def update_config(granular_data: Dict[str, Any]) -> None:
    """
    Update the config with the granular data
    """
    config_file = os.path.join(os.path.dirname(__file__), 'agents', 'browser.agents.json')
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Get the active tab URL
    active_tab = get_active_tab_url()
    if not active_tab.get('success', False):
        logger.error("Failed to get active tab URL")
        return

    active_url = active_tab.get('url', 'unknown')

    for data_type, granular_data_type in granular_data.items():
        data_value = config[active_url]['data'].get(data_type, [])
        for gd in granular_data_type:
            if not gd in config[active_url]['data']:
                config[active_url]['data'][gd] = data_value
            else:
                config[active_url]['data'][gd].extend(data_value)
        # remove the data_type from the config
        del config[active_url]['data'][data_type]

    # Save the updated config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Updated config for URL: {active_url}")

def add_to_config(html_structure: Dict[str, Any], data_required: Dict[str, Any]) -> None:
    """
    Add the HTML structure and data required to the config
    
    Args:
        html_structure (Dict[str, Any]): HTML structure with read and write elements
        data_required (Dict[str, Any]): Data requirements with data type as key and list of CSS selectors as value
    """
    # check if the config file exists, browser.agents.json
    config_file = os.path.join(os.path.dirname(__file__), 'agents', 'browser.agents.json')
    if not os.path.exists(config_file):
        # create the file
        with open(config_file, 'w') as f:
            json.dump({}, f)

    # load the config
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Get the active tab URL
    active_tab = get_active_tab_url()
    if not active_tab.get('success', False):
        logger.error("Failed to get active tab URL")
        return

    active_url = active_tab.get('url', 'unknown')
    
    # Create or update the entry for this URL
    if active_url not in config:
        config[active_url] = {
            'verified': False,
            'read': [],
            'write': [],
            'create': [],
            'data': {}
        }
    
    # Update read, write, and create selectors
    config[active_url]['read'] = html_structure.get('read', [])
    config[active_url]['write'] = html_structure.get('write', [])
    config[active_url]['create'] = html_structure.get('create', [])
    
    # Update data requirements
    if 'data' in data_required:
        config[active_url]['data'] = data_required['data']
    
    # Save the updated config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Updated config for URL: {active_url}")

def convert_text_to_selector(text: str, minimal_html: Dict[str, str]) -> str:
    """
    Convert a text-based selector (text(some text)) to a CSS selector using minimal_html mapping
    
    Args:
        text (str): Text-based selector in format text(some text)
        minimal_html (Dict[str, str]): Mapping of text content to CSS selectors
        
    Returns:
        str: CSS selector for the element containing the text, or original text if not found
    """
    try:
        logger.info(f"Converting text selector: {text}")
        
        # Extract text from text(some text) format
        match = re.match(r'text\((.*?)\)', text)
        if not match:
            logger.info(f"No text() format found, returning original: {text}")
            return text  # Return original if not in text() format
            
        search_text = match.group(1)
        logger.info(f"Searching for text: {search_text}")
        
        # Look for exact match in minimal_html keys
        for content, selector in minimal_html.items():
            if content.strip() == search_text:
                logger.info(f"Found exact match, returning selector: {selector}")
                return selector
                
        # If no exact match, try partial match
        for content, selector in minimal_html.items():
            if search_text in content.strip():
                logger.info(f"Found partial match, returning selector: {selector}")
                return selector
                
        logger.info(f"No match found, returning original: {text}")
        return text  # Return original if no match found
        
    except Exception as e:
        logger.error(f"Error converting text to selector: {str(e)}")
        return text  # Return original on error

def evaluate_javascript(expression: str) -> Dict[str, Any]:
    """
    Evaluate JavaScript in the currently active page using the evaluate endpoint.
    Uses caching to improve performance for repeated evaluations.
    
    Args:
        expression (str): JavaScript code to evaluate
        
    Returns:
        dict: Result of the evaluation or error information
    """
    try:
        # Get the active tab
        active_tab = get_active_tab_url()
        if not active_tab.get('success'):
            return {
                'success': False,
                'error': 'Failed to get active tab URL'
            }
        
        tab_id = active_tab.get('url')
        
        # Check cache first
        cached_result, found = evaluation_cache.get(expression, tab_id)
        if found:
            return cached_result
        
        # If not in cache, make the API call
        response = requests.post('http://localhost:8080/evaluate', 
                               json={'expression': expression},
                               timeout=10)
        
        if response.status_code != 200:
            error_msg = f"Failed to evaluate JavaScript: {response.text}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        result = response.json()
        
        # Cache successful results
        if result.get('success') and result.get('result') is not None:
            data = result['result']
            if data.get('value') is not None:
                evaluation_cache.set(expression, tab_id, result)
        
        return result
        
    except Exception as e:
        error_msg = f"Error evaluating JavaScript: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }

def get_completion(prompt: str, model: str = "gpt-4-turbo-preview") -> str:
    """
    Get a completion from the OpenAI API.
    
    Args:
        prompt (str): The prompt to send to the model
        model (str): The model to use for completion (ignored, using default model)
        
    Returns:
        str: The model's response
    """
    try:
        # Split the prompt into system and user parts if it contains HTML ELEMENTS
        if "<HTML ELEMENTS>" in prompt:
            system_part = prompt.split("<HTML ELEMENTS>")[0]
            user_part = "<HTML ELEMENTS>" + prompt.split("<HTML ELEMENTS>")[1]
        else:
            system_part = ""
            user_part = prompt
            
        # Use "computer-use" mode since this is for browser automation
        response = call_openai_api(system_part, user_part, "computer-use")
        return response
    except Exception as e:
        logger.error(f"Error getting completion: {str(e)}")
        raise

def process_dynamic_data_key(key: str, html_content: str) -> str:
    """
    Process a key containing dynamic data extraction syntax.
    
    Args:
        key (str): Key in format "Type:Field($data{selector}{transform}[idx](transform)@attr)"
        html_content (str): HTML content to extract data from
        
    Returns:
        str: Processed key with extracted data, or None if extraction fails
    """
    try:
        logger.info(f"[DEBUG] Processing dynamic data key: {key}")
        
        # Find all dynamic data parts in the key and collect their replacements
        replacements = []
        # Enforce order: {} transforms, then [] index, then () element transforms
        dynamic_parts = re.finditer(r'\$data\{([^}]+)\}(?:\{([^}]+)\})?(?:\[([:\d]+)\])?(?:\(([^)]+)\))?(?:@([a-zA-Z-]+))?', key)
        
        for match in dynamic_parts:
            full_match = match.group(0)  # The complete match including $data{...}
            selector = match.group(1)  # The selector inside {}
            list_transforms = match.group(2)  # List-level transforms in {}
            idx_str = match.group(3)  # Index after list transforms
            element_transforms = match.group(4)  # Element-level transforms in ()
            attr_type = match.group(5) or 'text'  # Default to text if no attr specified
            
            logger.info(f"[DEBUG] Extracted components:")
            logger.info(f"[DEBUG] - Full match: {full_match}")
            logger.info(f"[DEBUG] - Selector: {selector}")
            logger.info(f"[DEBUG] - List transforms: {list_transforms}")
            logger.info(f"[DEBUG] - Index: {idx_str}")
            logger.info(f"[DEBUG] - Element transforms: {element_transforms}")
            logger.info(f"[DEBUG] - Attribute type: {attr_type}")
            
            # Extract data
            data_values = extract_dynamic_data(selector, html_content, attr_type)
            logger.info(f"[DEBUG] Extracted data values: {data_values}")
            
            if not data_values:
                logger.warning(f"[DEBUG] No data values found for selector: {selector}")
                return None
                
            # Get the value
            value = data_values[0]  # Always get first element since we're using unique selectors
            logger.info(f"[DEBUG] Selected value: {value}")
            
            # Apply list-level transforms
            if list_transforms:
                transforms = [t.strip() for t in list_transforms.split(',')]
                for transform in transforms:
                    logger.info(f"[DEBUG] Applying list transform '{transform}' to value: {value}")
                    value = process_text_value(value, transform)
                    logger.info(f"[DEBUG] After list transform: {value}")
            else:
                # Default list transform is split by space
                value = value.split()
                logger.info(f"[DEBUG] Applied default split_space transform: {value}")
            
            # Handle index
            if idx_str == ':':
                # Use complete string without splitting
                logger.info(f"[DEBUG] Using complete string ([:]): {value}")
                pass
            elif idx_str is not None:
                # Get the element at the specified index
                idx = int(idx_str)
                if isinstance(value, list):
                    if idx < len(value):
                        value = value[idx]
                        logger.info(f"[DEBUG] Selected element at index {idx}: {value}")
                    else:
                        logger.warning(f"[DEBUG] Index {idx} out of range for list: {value}")
                        return None
                else:
                    logger.warning(f"[DEBUG] Value is not a list, cannot index: {value}")
                    return None
            
            # Apply element-level transforms
            if element_transforms:
                transforms = [t.strip() for t in element_transforms.split(',')]
                for transform in transforms:
                    logger.info(f"[DEBUG] Applying element transform '{transform}' to value: {value}")
                    value = process_text_value(value, transform)
                    logger.info(f"[DEBUG] After element transform: {value}")
            
            # Store the replacement
            replacements.append((full_match, str(value)))
            logger.info(f"[DEBUG] Added replacement: {full_match} -> {value}")
        
        # Apply replacements in reverse order to avoid interference
        result = key
        for original, replacement in reversed(replacements):
            result = result.replace(original, replacement)
            logger.info(f"[DEBUG] Applied replacement: {original} -> {replacement}")
            logger.info(f"[DEBUG] Intermediate result: {result}")
            
        logger.info(f"[DEBUG] Final result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[DEBUG] Error processing dynamic data key: {str(e)}", exc_info=True)
        return None

def extract_dynamic_data(selector: str, html_content: str, attr_type: str = 'text') -> List[str]:
    try:
        js_code = f"""
        (function() {{
            try {{
                // Try the original selector
                const element = document.querySelector(`{selector}`);
                if (element) {{
                    if (element.tagName.toLowerCase() === 'input') {{
                        const value = element.value;
                        return {{ value: value }};
                    }}
                    // For text content, get it from the element itself or its first child
                    if ('{attr_type}' === 'text') {{
                        const text = element.textContent || (element.firstElementChild ? element.firstElementChild.textContent : '');
                        return {{ value: text }};
                    }}
                    return {{ value: element.{attr_type if attr_type == 'text' else f'getAttribute("{attr_type}")'} }};
                }}
                
                // If not found, try finding by aria-label
                const ariaLabel = '{selector.split("'")[1] if "'" in selector else ""}';
                const elements = document.querySelectorAll('input[aria-label]');
                const foundElement = Array.from(elements).find(el => 
                    el.getAttribute('aria-label') === ariaLabel
                );
                
                if (foundElement) {{
                    if (foundElement.tagName.toLowerCase() === 'input') {{
                        const value = foundElement.value;
                        return {{ value: value }};
                    }}
                    // For text content, get it from the element itself or its first child
                    if ('{attr_type}' === 'text') {{
                        const text = foundElement.textContent || (foundElement.firstElementChild ? foundElement.firstElementChild.textContent : '');
                        return {{ value: text }};
                    }}
                    return {{ value: foundElement.{attr_type if attr_type == 'text' else f'getAttribute("{attr_type}")'} }};
                }}
                
                return {{ value: null }};
            }} catch (e) {{
                return {{ error: e.toString(), value: null }};
            }}
        }})()
        """
        
        result = evaluate_javascript(js_code)
        
        if result.get('success') and result.get('result') is not None:
            data = result['result']
            if data.get('value') is not None:
                logger.info(f"[DEBUG] CDP extracted value: {data['value']}")
                return [data['value']] if data['value'] else []
            
            if 'error' in data:
                logger.error(f"[DEBUG] JavaScript error: {data['error']}")
        
        logger.error(f"[DEBUG] CDP query failed: {result.get('error', 'Unknown error')}")
        logger.info(f"[DEBUG] CDP evaluation failed, falling back to BeautifulSoup")
        
    except Exception as e:
        logger.error(f"[DEBUG] CDP evaluation error: {str(e)}")
        logger.info(f"[DEBUG] Falling back to BeautifulSoup")
    
    return []

def strip_query_params(url: str) -> str:
    """
    Strip query parameters from a URL
    
    Args:
        url (str): Full URL with query parameters
        
    Returns:
        str: URL without query parameters
    """
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        # Reconstruct URL without query parameters
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, '', parsed.fragment))
    except Exception as e:
        logger.error(f"Error stripping query parameters from URL {url}: {str(e)}")
        return url

def handle_from_config(minimal_html: Dict[str, str]) -> bool:
    """
    Handle permissions based on the config file
    
    Args:
        minimal_html (Dict[str, str]): Mapping of text content to CSS selectors
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the active tab URL
        active_tab = get_active_tab_url()
        if not active_tab.get('success', False):
            logger.error("Failed to get active tab URL")
            return False

        active_url = active_tab.get('url', 'unknown')
        logger.info(f"[DEBUG] Active URL: {active_url}")
        
        # Strip query parameters from active URL for matching
        active_url_no_query = strip_query_params(active_url)
        logger.info(f"[DEBUG] Active URL without query params: {active_url_no_query}")
        
        config_file = os.path.join(os.path.dirname(__file__), 'agents', 'browser.agents.json')
        if not os.path.exists(config_file):
            logger.info("Config file not found")
            return False
            
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        # Since config URLs never have query params, we can directly check if the stripped active URL exists
        if active_url_no_query not in config:
            # Try wildcard matching for config keys
            for config_key in config:
                if '*' in config_key:
                    # Convert wildcard to regex
                    import re
                    pattern = re.escape(config_key).replace('\\*', '[^/]+')
                    if re.fullmatch(pattern, active_url_no_query):
                        logger.info(f"Wildcard config entry matched: {config_key} for URL: {active_url_no_query}")
                        url_config = config[config_key]
                        break
            else:
                logger.info(f"No config entry found for URL: {active_url_no_query}")
                return False
        else:
            url_config = config[active_url_no_query]

        # If not verified, we need to do a fresh analysis
        if not url_config.get('verified', False):
            logger.info(f"URL {active_url_no_query} not verified, will do fresh analysis")
            return False

        # Get HTML content for dynamic data extraction
        html_result = get_html_source()
        if not html_result.get('success', False) or not html_result.get('html'):
            logger.error("Failed to get HTML source")
            return False
            
        logger.info(f"[DEBUG] Got HTML source, length: {len(html_result['html'])}")
        logger.info(f"[DEBUG] HTML source sample (first 500 chars): {html_result['html'][:500]}")
            
        # Convert text-based selectors to CSS selectors while preserving direct CSS selectors
        converted_read = [convert_text_to_selector(sel, minimal_html) for sel in url_config.get('read', [])]
        converted_write = [convert_text_to_selector(sel, minimal_html) for sel in url_config.get('write', [])]
        converted_create = [convert_text_to_selector(sel, minimal_html) for sel in url_config.get('create', [])]
        
        # Create HTML structure from config with converted selectors
        html_structure = {
            'read': converted_read,
            'write': converted_write,
            'create': converted_create,
            'success': True
        }
        
        # Convert text-based selectors in data requirements while preserving direct CSS selectors
        # and process any dynamic data keys
        converted_data = {}
        for data_type, selectors in url_config.get('data', {}).items():
            logger.info(f"[DEBUG] Processing data type: {data_type}")
            # Process the data type key for dynamic data
            processed_data_type = process_dynamic_data_key(data_type, html_result['html'])
            if processed_data_type is None:
                logger.warning(f"[DEBUG] Failed to process dynamic data key: {data_type}")
                continue
            logger.info(f"[DEBUG] Processed data type: {processed_data_type}")
            
            # Preserve :contains() selectors when converting
            converted_selectors = []
            for sel in selectors:
                    converted_sel = convert_text_to_selector(sel, minimal_html)
                    logger.info(f"[DEBUG] Converted selector: {sel} -> {converted_sel}")
                    converted_selectors.append(converted_sel)
            
            if processed_data_type in converted_data:
                converted_data[processed_data_type].extend(converted_selectors)
            else:
                converted_data[processed_data_type] = converted_selectors
            logger.info(f"[DEBUG] Added converted data entry: {processed_data_type} -> {converted_selectors}")
            
        # Create data required from config with converted selectors
        data_required = {
            'data': converted_data,
            'success': True
        }
        
        logger.info(f"[DEBUG] Found config for URL: {active_url}")
        logger.info(f"[DEBUG] Data required: {data_required}")
        # Handle not allowed elements
        allowed_elements, not_allowed_elements = get_allowed_and_not_allowed_elements_from_config(data_required, html_structure)
        handle_not_allowed_elements(not_allowed_elements)

        # clear selector and evaluation cache
        selector_cache.clear()
        evaluation_cache.clear()

        return True
    except Exception as e:
        logger.error(f"Error handling from config: {str(e)}", exc_info=True)
        return False