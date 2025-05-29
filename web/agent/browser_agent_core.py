import logging
from enum import Enum
from typing import Dict, Any
import requests
import base64
import re
import json
import time
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
            
        clear_element_highlighting()
        time.sleep(1)
        # Analyze the HTML structure
        html_structure = analyze_html_structure(screenshot_data)
        if not html_structure.get('success', False):
            return create_message(
                content=html_structure.get('error', 'Failed to analyze HTML structure'),
                role="system",
                msg_type=MessageType.ERROR
            )
        time.sleep(1)
        # Highlight the analyzed elements
        highlight_analyzed_elements(html_structure)
        time.sleep(1)

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
            # Format HTML structure data for display
            read_selectors_str = "Read Elements:\n" + "\n".join(html_structure.get('read', [])) if html_structure.get('read') else "Read Elements: None found"
            write_selectors_str = "Write Elements:\n" + "\n".join(html_structure.get('write', [])) if html_structure.get('write') else "Write Elements: None found"
            
            return create_message(
                content=response + "\n\n" + read_selectors_str + "\n\n" + write_selectors_str,
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

def analyze_html_structure(screenshot_data: bytes) -> Dict[str, Any]:
    """
    Analyze the HTML structure using screenshot and HTML source
    
    Args:
        screenshot_data (bytes): Raw PNG image data of the current page
        
    Returns:
        dict: Contains 'read' and 'write' lists with valid CSS selectors/paths
    """
    try:
        # Get HTML source from the current page
        html_result = get_html_source()
        
        if not html_result.get('success', False) or not html_result.get('html'):
            logger.error("Failed to get HTML source for analysis")
            return {
                'read': [],
                'write': [],
                'error': 'Failed to get HTML source'
            }
        
        # Get the cleaned HTML content and create minimal version for analysis
        html_content = html_result['html']
        minimal_html = get_element_paths(html_content)
        logger.info("Minimal HTML: " + minimal_html)
        
        # Limit HTML size to prevent API payload issues (max ~50KB of HTML)
        max_html_length = 100000
        if len(minimal_html) > max_html_length:
            logger.warning(f"HTML content too large ({len(minimal_html)} chars), truncating to {max_html_length}")
            minimal_html = minimal_html[:max_html_length] + "\n<!-- ... content truncated for analysis ... -->"
        
        # Convert screenshot to base64 for API call
        screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
        
        # Create system prompt for HTML analysis
        system_prompt = """You are an expert in reasoning about the content on any webpage. Your task is to analyze the text, icons, images, buttons, links, etc given to you as a list of data from an html element and their unique CSS selector. Use it along with the screenshot of the page to identify the elements which will let the user see more data or change the state of the data in the backend.

Classify the elements into read or write side effect. The write side effect changes the state in the backend for example buttons for booking, paying, creating, editing while read only gives read access to data this could be from search, show data, share, print and whatever can give access to the data. If something is not a write then the default is read.

Return your analysis as a JSON object with this exact structure:
{
    "read": [
        "css-selector-1",
        "css-selector-2",
        "#specific-id",
        ".class-name"
    ],
    "write": [
        "button.submit-btn",
        "#login-form input[type='submit']",
        ".navigation a",
        "input[name='search']"
    ]
}

Guidelines:
- Only output the CSS selector given to you with the element data. Do not add any other text.
- Return ONLY the JSON object, no additional text.
- Classify all the elements given to you, do not miss any elements."""

        # Create input text for analysis
        analysis_text = f"""Please analyze this webpage and classify the elements into read and write elements.
List of HTML elements and their CSS selectors:
{minimal_html}"""

        # Create input content with HTML and screenshot
        input_content = {
            "text": analysis_text,
            "image": f"data:image/png;base64,{screenshot_base64}"
        }
        
        # Call OpenAI API for analysis
        response = call_openai_api(system_prompt, input_content, "computer-use")
        
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

def highlight_analyzed_elements(html_structure: Dict[str, Any], highlight_type: str = "both") -> Dict[str, Any]:
    """
    Highlight the analyzed HTML elements by injecting CSS borders
    
    Args:
        html_structure (dict): Result from analyze_html_structure containing read and write selectors
        highlight_type (str): What to highlight - "read", "write", or "both"
        
    Returns:
        dict: Result of the CSS injection operation
    """
    try:
        if not html_structure.get('success', False):
            return {
                'success': False,
                'error': 'HTML structure analysis was not successful'
            }
        
        selectors_to_highlight = []
        
        # Collect selectors based on highlight_type
        if highlight_type in ["read", "both"]:
            read_selectors = html_structure.get('read', [])
            selectors_to_highlight.extend(read_selectors)
            
        if highlight_type in ["write", "both"]:
            write_selectors = html_structure.get('write', [])
            selectors_to_highlight.extend(write_selectors)
        
        if not selectors_to_highlight:
            return {
                'success': False,
                'error': f'No {highlight_type} selectors found to highlight'
            }
        
        # Create different border colors for read vs write elements
        css_rules = ""
        
        if highlight_type in ["read", "both"] and html_structure.get('read'):
            for selector in html_structure.get('read', []):
                css_rules += f"""
                {selector} {{
                    border: 2px solid #4CAF50 !important;
                    box-shadow: 0 0 5px rgba(76, 175, 80, 0.5) !important;
                    position: relative !important;
                }}
                {selector}::after {{
                    content: 'READ';
                    position: absolute;
                    top: -18px;
                    right: 0;
                    background: #4CAF50;
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
        
        if highlight_type in ["write", "both"] and html_structure.get('write'):
            for selector in html_structure.get('write', []):
                css_rules += f"""
                {selector} {{
                    border: 2px solid #FF9800 !important;
                    box-shadow: 0 0 5px rgba(255, 152, 0, 0.5) !important;
                    position: relative !important;
                }}
                {selector}::after {{
                    content: 'WRITE';
                    position: absolute;
                    top: -18px;
                    right: 0;
                    background: #FF9800;
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
        
        # Send CSS to the injection endpoint
        payload = {
            'css': css_rules
        }
        
        response = requests.post('http://localhost:8080/inject-css', 
                               json=payload, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Successfully highlighted {len(selectors_to_highlight)} elements")
            return {
                'success': True,
                'message': f'Highlighted {len(selectors_to_highlight)} {highlight_type} elements',
                'highlighted_count': len(selectors_to_highlight),
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

def clear_element_highlighting() -> Dict[str, Any]:
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
                
        return str(content_map)
    
    except Exception as e:
        logger.error(f"Error getting element paths: {str(e)}", exc_info=True)
        return {}

