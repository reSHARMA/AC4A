import eventlet
eventlet.monkey_patch()

import sys
import os
import json
from datetime import datetime

# Add the root directory to the Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import queue
import logging
from datetime import datetime, timedelta
import time

# Import autogen logging
from autogen_agentchat import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME

# Import from our new modular components
from web.agent.session import initialize_agent_session, reset_agent_session
from web.agent.queues import (
    get_next_input_request,
    submit_user_input,
    get_next_agent_message,
    is_agent_waiting_for_input,
    set_agent_waiting_for_input,
    is_agent_session_active,
    input_request_queue,
    input_response_queue,
    agent_message_queue
)

# Import the agent manager
from web.agent.agent_manager import agent_manager
from src.utils.resource_type_tree import ResourceTypeTree
from src.prompts import POLICY_GENERATOR_WILDCARD_V2
from src.utils.dummy_data import call_openai_api

from web.utils.events import socketio, emit_policy_update
from web.utils.socket_io import init_socketio

# Import the browser_agent_core module
from web.agent.browser_agent_core import process_browser_message, get_browser_chat_history, clear_browser_chat_history, create_message, MessageType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug.log')
    ]
)

# Configure autogen agentchat logging
# For trace logging
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

# For structured message logging
event_logger = logging.getLogger(EVENT_LOGGER_NAME)
event_logger.addHandler(logging.StreamHandler())
event_logger.setLevel(logging.DEBUG)

# Set log levels for specific modules
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('autogen').setLevel(logging.DEBUG)
logging.getLogger('autogen_core').setLevel(logging.DEBUG)
logging.getLogger('autogen_agentchat').setLevel(logging.DEBUG)
logging.getLogger('autogen_runtime').setLevel(logging.DEBUG)
logging.getLogger('OpenAI').setLevel(logging.DEBUG)

# Get logger for this module
logger = logging.getLogger(__name__)
policy_logger = logging.getLogger('web.policy_system')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Required for session management
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin", "Access-Control-Allow-Headers"],
        "supports_credentials": True,
        "max_age": 3600
    }
})
socketio = init_socketio(app)

# Store conversation history
conversation_history = []

# Store browser chat history
browser_chat_history = []

# Flag to track if a new session is needed
new_session_needed = False

# Add cache dictionary at the top level of the file
text_cache = {}


def _format_permission_log(event_type, target_key):
    """Format Permission Added/Removed: extract namespace, return (category, short_message) without namespace in spec.
    Strip namespace from each ::-separated segment so we get year(2026)::month(june)-read not year(2026)::calendar:month(june)-read.
    """
    if not target_key or '-' not in target_key:
        return event_type, target_key or ''
    spec_part, _, action_part = target_key.rpartition('-')
    if not spec_part or ':' not in spec_part:
        return event_type, target_key
    namespace = spec_part.split(':')[0]
    shortened = '::'.join(part.split(':', 1)[-1] if ':' in part else part for part in spec_part.split('::'))
    return f"{event_type} for {namespace.title()}", f"{shortened}-{action_part}"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_attribute_trees', methods=['GET'])
def get_attribute_trees():
    """Get attribute trees for UI display"""
    try:
        logger.info("Received request for attribute trees")
        
        # Ensure agent manager is initialized
        if not agent_manager.initialized:
            logger.info("Agent manager not initialized, initializing now")
            agent_manager.initialize_agents()
            logger.info("Agent manager initialized")
            
            logger.info("Enabling policy system")
            agent_manager.enable_policy_system()
            logger.info("Policy system enabled")
        
        # Get attribute trees from the agent manager
        attribute_trees = agent_manager.get_attribute_trees()
        logger.info(f"Retrieved {len(attribute_trees)} attribute trees")
        
        # Process trees into a format suitable for UI display
        def process_tree(tree):
            if not isinstance(tree, ResourceTypeTree):
                logger.warning(f"Found non-AttributeTree object: {type(tree)}")
                return {"label": str(tree), "value": str(tree), "children": [], "access": ""}
            
            key, value = list(tree.value.items())[0]
            node = {
                "label": key, 
                "value": value, 
                "children": [],
                "access": getattr(tree, 'access', '')
            }
            
            for child in tree.children:
                node["children"].append(process_tree(child))
            
            return node
        
        # Process each tree in resource_value_specification
        processed_trees = []
        seen_keys = set()
        
        for tree in attribute_trees:
            if isinstance(tree, ResourceTypeTree):
                key, _ = list(tree.value.items())[0]
                if key not in seen_keys:
                    seen_keys.add(key)
                    processed_tree = process_tree(tree)
                    processed_trees.append(processed_tree)
                    logger.info(f"Added unique processed tree: {key}")
                else:
                    logger.info(f"Skipping duplicate processed tree: {key}")
            else:
                processed_tree = process_tree(tree)
                processed_trees.append(processed_tree)
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
        return jsonify({"attribute_trees": processed_trees})
    except Exception as e:
        logger.error(f"Error in get_attribute_trees: {str(e)}", exc_info=True)
        error_response = jsonify({"error": str(e)})
        error_response.headers['Content-Type'] = 'application/json'
        return error_response, 500

@app.route('/add_policy', methods=['POST'])
def add_policy():
    """Add a new policy to the policy system"""
    try:
        logger.info("Received request to add policy")
        
        # Ensure agent manager is initialized
        if not agent_manager.initialized:
            logger.info("Agent manager not initialized, initializing now")
            agent_manager.initialize_agents()
            logger.info("Agent manager initialized")
            
            logger.info("Enabling policy system")
            agent_manager.enable_policy_system()
            logger.info("Policy system enabled")
        
        # Get policy data from request
        policy_data = request.json
        logger.info(f"Policy data: {policy_data}")
        
        # Add policy to the policy system
        agent_manager.policy_system.add_policy(policy_data)
        logger.info(f"Added policy: {policy_data}")
        
        # Construct policy key for highlighting
        policy_key = f"{policy_data['resource_value_specification']}-{policy_data['action']}"
        logger.info(f"Emitting highlight for policy: {policy_key}")
        socketio.emit('highlight_policy', policy_key)
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
        # Emit a log entry for the new policy (category and message without namespace in spec)
        level, msg = _format_permission_log("Permission Added", policy_key)
        emit_new_log({
            'source': 'CustomLog',
            'level': f'CUSTOM_{level}',
            'message': msg
        })
        
        return jsonify({"status": "success", "message": "Policy added successfully"})
    except Exception as e:
        logger.error(f"Error in add_policy: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/get_policies', methods=['GET'])
def get_policies():
    """Get all policies from the policy system"""
    try:
        logger.info("Received request to get policies")
        
        # Ensure agent manager is initialized
        if not agent_manager.initialized:
            logger.info("Agent manager not initialized, initializing now")
            agent_manager.initialize_agents()
            logger.info("Agent manager initialized")
            
            logger.info("Enabling policy system")
            agent_manager.enable_policy_system()
            logger.info("Policy system enabled")
        
        # Get policies from the policy system
        policies = agent_manager.policy_system.policy_rules
        logger.info(f"Retrieved {len(policies)} policies")
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
        return jsonify({"policies": policies})
    except Exception as e:
        logger.error(f"Error in get_policies: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/delete_policy', methods=['POST'])
def delete_policy():
    """Delete a policy from the policy system"""
    try:
        logger.info("Received request to delete policy")
        
        # Ensure agent manager is initialized
        if not agent_manager.initialized:
            logger.info("Agent manager not initialized, initializing now")
            agent_manager.initialize_agents()
            logger.info("Agent manager initialized")
            
            logger.info("Enabling policy system")
            agent_manager.enable_policy_system()
            logger.info("Policy system enabled")
        
        # Get policy data from request
        policy_data = request.json
        logger.info(f"Policy data to delete: {policy_data}")
        
        # Remove policy from the policy system
        success = agent_manager.policy_system.remove_policy(policy_data)
        if not success:
            logger.warning(f"Failed to remove policy: {policy_data}")
            return jsonify({"error": "Policy not found"}), 200
        
        logger.info(f"Successfully removed policy: {policy_data}")
        
        # Construct policy key for highlighting
        policy_key = f"{policy_data['resource_value_specification']}-{policy_data['action']}"
        logger.info(f"Emitting highlight for policy: {policy_key}")
        socketio.emit('highlight_policy', policy_key)
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
        # Emit a log entry for the removed policy (category and message without namespace in spec)
        level, msg = _format_permission_log("Permission Removed", policy_key)
        emit_new_log({
            'source': 'CustomLog',
            'level': f'CUSTOM_{level}',
            'message': msg
        })
        
        return jsonify({"status": "success", "message": "Policy deleted successfully"})
    except Exception as e:
        logger.error(f"Error in delete_policy: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/reset_session', methods=['POST'])
def reset_session():
    """Reset the agent session and conversation history"""
    global conversation_history, new_session_needed
    
    logger.info("Resetting session")
    
    # Reset the agent session
    reset_agent_session()
    
    # Clear the conversation history
    conversation_history = []
    
    # Clear the debug.log file
    log_path = os.path.join(os.path.dirname(__file__), 'debug.log')
    try:
        with open(log_path, 'w') as f:
            f.write('')
        logger.info("Cleared debug.log file")
    except Exception as e:
        logger.error(f"Error clearing debug.log: {str(e)}")
    
    # Reset the waiting flag
    set_agent_waiting_for_input(False)
    
    # Set the new session flag
    new_session_needed = True
    
    # Initialize a new session immediately
    logger.info("Initializing new session after reset")
    initialize_agent_session()
    new_session_needed = False
    logger.info("New session initialized after reset")
    
    # Emit session reset event to all connected clients
    try:
        logger.info("Emitting session_reset event")
        socketio.emit('session_reset', {'reset': True}, namespace='/')
        logger.info("Session reset event emitted")
    except Exception as e:
        logger.error(f"Error emitting session_reset event: {str(e)}")
    
    return jsonify({"status": "success", "message": "Session reset"})

@socketio.on('connect')
def handle_connect():
    global new_session_needed, conversation_history
    logger.info('Client connected')
    
    # Reset the conversation history and session on new connection
    conversation_history = []

    # Emit system_ready event to the client
    emit('system_ready')

    if not is_agent_session_active():
        logger.info("Agent session not active, resetting")
        reset_agent_session()
        initialize_agent_session()
        emit_policy_update()
    else:
        logger.info("Agent session is active, not resetting")

def emit_new_log(log_entry):
    """Emit a new log entry to all connected clients"""
    logger.info(f"Emitting new log: {log_entry}")
    socketio.emit('new_log', log_entry, namespace='/')
    logger.info("New log event emitted")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('request_policy_update')
def handle_policy_update_request():
    """Handle request for policy update"""
    logger.info("Received request for policy update")
    emit_policy_update()

@socketio.on('user_message')
def handle_message(data):
    global conversation_history, new_session_needed
    logger.info(f"Received message: {data}")
    user_message = data.get('content', '')
    is_video_mode = data.get('isVideoMode', False)
    logger.info(f"User message in {'video' if is_video_mode else 'chat'} mode: {user_message}")
    
    # Check if we need to initialize a new session
    if new_session_needed or not is_agent_session_active(is_video_mode):
        logger.info(f"Initializing new {'video' if is_video_mode else 'agent'} session")
        # Make sure the agent session is fully reset before initializing a new one
        if is_agent_session_active(is_video_mode):
            logger.info(f"{'Video' if is_video_mode else 'Agent'} session is active, but a reset was requested")
            reset_agent_session()
        initialize_agent_session()
    
    # Check if the agent is waiting for input
    if is_agent_waiting_for_input(is_video_mode):
        logger.info(f"{'Video' if is_video_mode else 'Agent'} is waiting for input, submitting user message")
        submit_user_input(user_message, is_video_mode)
        set_agent_waiting_for_input(False, is_video_mode)
    
    # Add user message to conversation history but don't emit it
    # The frontend already displays user messages on the right side
    conversation_history.append({"role": "user", "content": user_message})

def check_for_input_requests():
    """Check for input requests from the agent"""
    global new_session_needed, conversation_history
    
    while True:
        try:
            # Check both chat and video mode sessions
            for is_video_mode in [False, True]:
                if is_agent_session_active(is_video_mode):
                    logger.info(f"{'Video' if is_video_mode else 'Agent'} session is active, checking for input requests and messages")
                    # Check if agent is waiting for input
                    if is_agent_waiting_for_input(is_video_mode):
                        input_request = get_next_input_request(is_video_mode)
                        if input_request:
                            logger.info(f"Received input request from {'video' if is_video_mode else 'agent'}: {input_request}")
                            set_agent_waiting_for_input(True, is_video_mode)
                            # Emit the input request to the web UI
                            logger.info(f"Emitting input request to web UI: {input_request}")
                            socketio.emit('input_request', {"prompt": input_request, "isVideoMode": is_video_mode})
                    
                    # Check for agent messages
                    agent_message = get_next_agent_message(is_video_mode)
                    if agent_message:
                        logger.info(f"Received {'video' if is_video_mode else 'agent'} message: {agent_message}")
                        
                        # Check for termination messages
                        if "termination" in agent_message.lower():
                            logger.info(f"{'Video' if is_video_mode else 'Agent'} terminated: {agent_message}")
                            # Set the new session flag
                            new_session_needed = True
                            # Emit the termination message
                            socketio.emit('message', {"role": "System", "content": agent_message, "isVideoMode": is_video_mode})
                            # Add a small delay to prevent rapid cycling
                            eventlet.sleep(1)
                            continue
                        
                        # Extract the agent name and content from the message
                        agent_name = "Assistant"  # Default role
                        content = agent_message
                        
                        # Check if the message starts with an agent name followed by a colon
                        if ": " in agent_message:
                            parts = agent_message.split(": ", 1)
                            agent_name = parts[0]
                            content = parts[1]
                        
                        # Skip user messages to prevent duplication
                        if agent_name == "User":
                            logger.info(f"[app.py] Skipping user message to prevent duplication: {content}")
                            continue
                        
                        # Skip system messages about awaiting user input
                        if agent_name == "System" and "Awaiting user input" in content:
                            logger.info("Skipping system message about awaiting user input")
                            continue
                        
                        # Add message to conversation history
                        conversation_history.append({"role": agent_name, "content": content})
                        
                        # Emit the message to the web UI
                        socketio.emit('message', {"role": agent_name, "content": content, "isVideoMode": is_video_mode})
                else:
                    logger.info(f"{'Video' if is_video_mode else 'Agent'} session not active, skipping check for input requests and flushing message queue")
                    while remaining_message := get_next_agent_message(is_video_mode):
                        logger.info(f"Flushing remaining message from {'video' if is_video_mode else 'agent'} message queue: {remaining_message}")
                        socketio.emit('message', {"role": "System", "content": remaining_message, "isVideoMode": is_video_mode})

            # Add a small delay to prevent CPU hogging
            eventlet.sleep(1.0)
        except Exception as e:
            logger.error(f"Error in check_for_input_requests: {str(e)}", exc_info=True)
            # Add a small delay to prevent rapid cycling in case of errors
            eventlet.sleep(1)

# Start the input request checker thread
input_checker_thread = eventlet.spawn(check_for_input_requests)

@app.route('/get_history', methods=['GET'])
def get_history():
    return jsonify({"history": conversation_history})

@app.route('/convert_to_text', methods=['POST', 'OPTIONS'])
def convert_to_text():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
        
    try:
        data = request.get_json()
        # Create a unique key for the policy
        cache_key = f"{data['resource_value_specification']}-{data['action']}"
        
        # Check if we have a cached result
        if cache_key in text_cache:
            logger.info(f"Using cached text for policy: {cache_key}")
            return jsonify({'text': text_cache[cache_key]})
            
        policy = {
            'resource_value_specification': data['resource_value_specification'],
            'action': data['action']
        }
        text = agent_manager.policy_system.text(policy=policy, mode="decl")
        
        # Cache the result
        text_cache[cache_key] = text
        logger.info(f"Cached text for policy: {cache_key}")
        
        return jsonify({'text': text})
    except Exception as e:
        logger.error(f"Error converting policy to text: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

@app.route('/add_policy_from_text', methods=['POST', 'OPTIONS'])
def add_policy_from_text():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
        
    try:
        data = request.get_json()
        policy_text = data.get('policy_text', '')
        
        if not policy_text:
            return jsonify({'error': 'No policy text provided'}), 400
            
        # Generate and add policies
        success = agent_manager.policy_system.add_policies_from_text(policy_text)
        
        if success:
            logger.info("Successfully added all policies")
            return jsonify({"status": "success", "message": "Policies added successfully"})
        else:
            logger.error("Failed to add some policies")
            return jsonify({"status": "error", "message": "Failed to add some policies"}), 500
            
    except Exception as e:
        logger.error(f"Error processing policy text: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

@app.route('/set_permission_mode', methods=['POST'])
def set_permission_mode():
    data = request.get_json()
    mode = data.get('mode', 'ask').lower()
    logger.info(f"Setting permission mode to: {mode}")
    os.environ['PERMISSION_MANAGEMENT_MODE'] = mode
    return jsonify({'status': 'ok', 'mode': mode})

@app.route('/send_log', methods=['POST'])
def send_log():
    """Send a new log message with category"""
    try:
        data = request.get_json()
        category = str(data.get('category'))  # Convert category to string
        message = data.get('message')
        
        if not category or not message:
            return jsonify({"error": "Category and message are required"}), 400
            
        # Format the log entry without timestamp
        log_entry = f"{category} - {message}\n"
        
        # Append to debug.log
        log_path = os.path.join(os.path.dirname(__file__), 'debug.log')
        with open(log_path, 'a') as f:
            f.write(log_entry)
            
        # Emit the new log to all connected clients
        emit_new_log({
            'source': 'CustomLog',
            'level': category,  # Don't strip the CUSTOM_ prefix
            'message': message
        })
            
        return jsonify({"status": "success", "message": "Log sent successfully"})
    except Exception as e:
        logger.error(f"Error in send_log: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/get_logs', methods=['GET'])
def get_logs():
    """Get logs from the debug.log file"""
    try:
        logger.info("Received request to get logs")
        
        # Use the correct path to debug.log
        log_path = os.path.join(os.path.dirname(__file__), 'debug.log')
        logger.info(f"Looking for log file at: {log_path}")
        
        # Check if the file exists
        if not os.path.exists(log_path):
            logger.warning(f"debug.log file not found at {log_path}")
            return jsonify({"logs": [], "message": "No logs available yet"})
            
        # Read the debug.log file
        logs = []
        try:
            with open(log_path, 'r') as f:
                for line in f:
                    # Skip lines that don't match our custom log format (category - message)
                    if ' - ' not in line:
                        continue
                    
                    # Parse the log line
                    # Format: category - message
                    parts = line.strip().split(' - ', 1)
                    if len(parts) == 2:
                        category, message = parts
                        # Only include logs with CUSTOM_ prefix
                        if category.startswith('CUSTOM_'):
                            # Remove the CUSTOM_ prefix when displaying
                            logs.append({
                                'level': category[7:],  # Remove 'CUSTOM_' prefix
                                'message': message
                            })
        except PermissionError:
            logger.error("Permission denied when reading debug.log")
            return jsonify({"error": "Permission denied when reading logs"}), 403
        except Exception as e:
            logger.error(f"Error reading debug.log: {str(e)}")
            return jsonify({"error": f"Error reading logs: {str(e)}"}), 500
        
        # Return the last 1000 logs (most recent)
        logs = logs[-1000:]
        return jsonify({"logs": logs})
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def emit_message(message: dict, room: str = None) -> None:
    """
    Emit a message to the frontend, filtering based on message type and visibility
    
    Args:
        message (dict): The message to emit
        room (str, optional): The room to emit to. Defaults to None.
    """
    # Skip internal messages
    if message.get("visibility") == "internal":
        return
        
    # Only emit debug messages in debug mode
    if message.get("visibility") == "debug" and not app.debug:
        return
        
    # Emit the message
    if room:
        socketio.emit("agent_message", message, room=room)
    else:
        socketio.emit("agent_message", message)

@app.route("/browser_chat", methods=["POST"])
def browser_chat():
    """Handle browser chat messages"""
    try:
        data = request.get_json()
        user_message = data.get("content", "")  # Changed from "message" to "content"
        
        # Process the message
        response = process_browser_message(user_message)
        
        # Emit the response
        emit_message(response)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in browser_chat: {str(e)}", exc_info=True)
        error_msg = create_message(
            content=str(e),
            role="system",
            msg_type=MessageType.ERROR
        )
        emit_message(error_msg)
        return jsonify(error_msg), 500

@app.route("/browser_chat_history", methods=["GET"])
def get_browser_chat_history():
    """Get browser chat history"""
    try:
        history = get_browser_chat_history()
        # Filter out internal messages before sending to frontend
        filtered_history = [
            msg for msg in history 
            if msg.get("visibility") != "internal"
        ]
        return jsonify(filtered_history)
    except Exception as e:
        logger.error(f"Error getting browser chat history: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/eval', methods=['POST'])
def eval_permission():
    """Dynamic permission probe for any registered agent API"""
    from importlib import import_module
    try:
        data = request.get_json(force=True, silent=True) or {}
        agent_name = (data.get('agent') or '').lower()
        endpoint = data.get('endpoint')
        args = data.get('args', {}) or {}

        if not agent_name or not endpoint:
            return jsonify({"error": "agent and endpoint are required"}), 400

        # Ensure model client & policy system initialized once
        if not agent_manager.initialized:
            agent_manager.initialize_agents()
            agent_manager.enable_policy_system()

        # Derive module path & class name dynamically from agent name pattern
        # e.g. wallet -> web.agent.agents.wallet_agent.WalletAgent
        #       contact_manager -> web.agent.agents.contact_manager_agent.ContactManagerAgent
        import re
        if not re.fullmatch(r"[a-z_]+", agent_name):
            return jsonify({"allowed": False, "reason": "invalid agent name"}), 400

        module_path = f"web.agent.agents.{agent_name}_agent"
        class_name = ''.join(part.capitalize() for part in agent_name.split('_')) + 'Agent'
        try:
            mod = import_module(module_path)
            wrapper_cls = getattr(mod, class_name)
        except Exception as e:
            logger.warning(f"Agent wrapper not found for {agent_name}: {e}")
            return jsonify({"allowed": False, "reason": "unknown agent"}), 200

        # Create ephemeral wrapper (registers API again; acceptable for probe)
        try:
            wrapper = wrapper_cls(agent_manager.model_client, agent_manager.policy_system)
        except Exception as e:
            logger.error(f"Wrapper init failed for {agent_name}: {e}", exc_info=True)
            return jsonify({"allowed": False, "reason": "wrapper init failed"}), 500

        # Locate API object containing the endpoint (attribute ending in _api with callable endpoint)
        api_func = None
        for attr, val in wrapper.__dict__.items():
            if attr.endswith('_api') and hasattr(val, endpoint):
                candidate = getattr(val, endpoint)
                if callable(candidate):
                    api_func = candidate
                    break

        if api_func is None:
            return jsonify({"allowed": False, "reason": "unknown endpoint"}), 200

        # Invoke to trigger policy check
        try:
            api_func(**args)
            return jsonify({"allowed": True})
        except PermissionError:
            return jsonify({"allowed": False})
        except TypeError as te:
            return jsonify({"allowed": False, "reason": "bad arguments", "details": str(te)})
        except Exception as e:
            logger.error("Unexpected error during eval call", exc_info=True)
            return jsonify({"allowed": False, "reason": "internal error", "details": str(e)})
    except Exception as outer:
        logger.error("/eval top-level failure", exc_info=True)
        return jsonify({"allowed": False, "reason": "internal error", "details": str(outer)}), 500

# ---------------------------------------------------------------------------
# Testing mode routes
# ---------------------------------------------------------------------------

# Singleton runner kept across requests so status polling works
_test_runner_instance = None
_test_runner_thread = None

@app.route('/testing/config', methods=['GET'])
def testing_config():
    """Return the test configuration."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'test_config.json')
    try:
        with open(config_path) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "test_config.json not found"}), 404

@app.route('/testing/generate', methods=['POST'])
def testing_generate():
    """Generate tests for an application."""
    from importlib import import_module
    from src.testing.test_generator import generate_api_tests, generate_web_tests
    from src.testing.test_store import save_test_suite, compute_api_hash, compute_web_hash

    data = request.get_json(force=True, silent=True) or {}
    app_name = data.get('app', '')
    num_tests = int(data.get('num_tests', 20))

    if not app_name:
        return jsonify({"error": "app is required"}), 400

    config_path = os.path.join(os.path.dirname(__file__), '..', 'test_config.json')
    with open(config_path) as f:
        config = json.load(f)

    app_cfg = config.get('applications', {}).get(app_name)
    if not app_cfg:
        return jsonify({"error": f"Unknown application: {app_name}"}), 400

    num_tests = min(num_tests, app_cfg.get('max_tests', 20))

    try:
        if app_cfg.get('type') == 'api':
            mod = import_module(app_cfg['agent_module'])
            annotation_cls = getattr(mod, app_cfg['annotation_class'])
            annotation = annotation_cls()
            resource_trees = annotation.attributes.get('resource_value_specification', [])
            action_names = [list(a.value.keys())[0] for a in annotation.attributes.get('action', [])]
            tree_hash = compute_api_hash(resource_trees, annotation_cls, action_names)
            tests = generate_api_tests(app_name, resource_trees, annotation_cls, action_names, num_tests)
        else:
            # Web type — load from browser.agents.json
            agents_json_path = os.path.join(os.path.dirname(__file__), 'agent', 'agents', 'browser.agents.json')
            with open(agents_json_path) as f:
                agents_config = json.load(f)
            url_pattern = app_cfg.get('url_pattern', '')
            matching = {k: v for k, v in agents_config.items() if _url_matches(k, url_pattern)}
            if not matching:
                return jsonify({"error": f"No URLs match pattern: {url_pattern}"}), 400
            url = next(iter(matching))
            mapping = matching[url]
            tree_hash = compute_web_hash(mapping)
            tests = generate_web_tests(url, mapping, num_tests)

        path = save_test_suite(app_name, tree_hash, tests)
        return jsonify({
            "app": app_name,
            "tree_hash": tree_hash,
            "test_count": len(tests),
            "tests": tests,
            "saved_to": path,
        })
    except Exception as e:
        logger.error("Test generation failed for %s: %s", app_name, e, exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/testing/list', methods=['GET'])
def testing_list():
    """List available test suites."""
    from src.testing.test_store import list_test_suites
    return jsonify(list_test_suites())

@app.route('/testing/suites', methods=['GET'])
def testing_suites_all():
    """Return full suite data (with tests) for all apps or a specific one."""
    from src.testing.test_store import load_all_suites, load_all_suites_for_app
    app_name = request.args.get('app', '')
    if app_name:
        return jsonify(load_all_suites_for_app(app_name))
    return jsonify(load_all_suites())

@app.route('/testing/delete_test', methods=['POST'])
def testing_delete_test():
    """Delete a single test from a suite."""
    from src.testing.test_store import delete_test_from_suite
    data = request.get_json(force=True, silent=True) or {}
    app_name = data.get('app', '')
    tree_hash = data.get('tree_hash', '')
    test_id = data.get('test_id', '')
    if not all([app_name, tree_hash, test_id]):
        return jsonify({"error": "app, tree_hash, and test_id are required"}), 400
    ok = delete_test_from_suite(app_name, tree_hash, test_id)
    if ok:
        return jsonify({"status": "deleted", "test_id": test_id})
    return jsonify({"error": "Test not found"}), 404

@app.route('/testing/select', methods=['POST'])
def testing_select():
    """Strategically select N tests from a suite."""
    from src.testing.test_store import load_test_suite
    from src.testing.test_selector import select_tests

    data = request.get_json(force=True, silent=True) or {}
    app_name = data.get('app', '')
    tree_hash = data.get('tree_hash', '')
    num = int(data.get('num_tests', 5))

    suite = load_test_suite(app_name, tree_hash)
    if not suite:
        return jsonify({"error": "Test suite not found or hash mismatch"}), 404

    result = select_tests(suite['tests'], num)
    return jsonify(result)

@app.route('/testing/run', methods=['POST'])
def testing_run():
    """Run selected tests (blocking — returns when done)."""
    global _test_runner_instance
    from src.testing.test_runner import TestRunner

    data = request.get_json(force=True, silent=True) or {}
    tests = data.get('tests', [])
    app_name = data.get('app', '')
    tree_hash = data.get('tree_hash', '')

    if not tests:
        return jsonify({"error": "No tests provided"}), 400

    if not agent_manager.initialized:
        agent_manager.initialize_agents()
        agent_manager.enable_policy_system()

    config_path = os.path.join(os.path.dirname(__file__), '..', 'test_config.json')
    with open(config_path) as f:
        config = json.load(f)
    max_retries = config.get('execution', {}).get('max_retries', 3)

    runner = TestRunner(
        agent_manager.policy_system,
        agent_manager,
        max_retries,
        socketio=socketio,
        browser_message_handler=process_browser_message,
    )
    _test_runner_instance = runner

    report = runner.run_all(tests, app_name, tree_hash)
    return jsonify(report)


@socketio.on('testing_run_single')
def handle_testing_run_single(data):
    """Run a single test in a background greenlet with real-time traces."""
    global _test_runner_instance
    from src.testing.test_runner import TestRunner

    test = data.get('test')
    if not test:
        emit('testing_trace', {'test_id': '?', 'role': 'error', 'content': 'No test provided'})
        return

    if not agent_manager.initialized:
        agent_manager.initialize_agents()
        agent_manager.enable_policy_system()

    config_path = os.path.join(os.path.dirname(__file__), '..', 'test_config.json')
    with open(config_path) as f:
        config = json.load(f)
    max_retries = config.get('execution', {}).get('max_retries', 3)

    runner = TestRunner(
        agent_manager.policy_system,
        agent_manager,
        max_retries,
        socketio=socketio,
        browser_message_handler=process_browser_message,
    )
    _test_runner_instance = runner

    def _run():
        try:
            runner.run_single(test)
        except Exception as e:
            logger.error("Single test run failed: %s", e, exc_info=True)
            socketio.emit('testing_trace', {
                'test_id': test.get('test_id', '?'),
                'role': 'error',
                'content': f'Runner crashed: {e}',
            })

    eventlet.spawn(_run)


@socketio.on('testing_run_batch')
def handle_testing_run_batch(data):
    """Run multiple tests in a background greenlet with real-time traces."""
    global _test_runner_instance
    from src.testing.test_runner import TestRunner

    tests = data.get('tests', [])
    app_name = data.get('app', '')
    tree_hash = data.get('tree_hash', '')

    if not tests:
        emit('testing_trace', {'test_id': '?', 'role': 'error', 'content': 'No tests provided'})
        return

    if not agent_manager.initialized:
        agent_manager.initialize_agents()
        agent_manager.enable_policy_system()

    config_path = os.path.join(os.path.dirname(__file__), '..', 'test_config.json')
    with open(config_path) as f:
        config = json.load(f)
    max_retries = config.get('execution', {}).get('max_retries', 3)

    runner = TestRunner(
        agent_manager.policy_system,
        agent_manager,
        max_retries,
        socketio=socketio,
        browser_message_handler=process_browser_message,
    )
    _test_runner_instance = runner

    def _run():
        try:
            runner.run_all(tests, app_name, tree_hash)
        except Exception as e:
            logger.error("Batch test run failed: %s", e, exc_info=True)
            socketio.emit('testing_trace', {
                'test_id': '?',
                'role': 'error',
                'content': f'Runner crashed: {e}',
            })

    eventlet.spawn(_run)

@app.route('/testing/status', methods=['GET'])
def testing_status():
    """Poll the current test run status."""
    global _test_runner_instance
    if _test_runner_instance is None:
        return jsonify({"running": False, "completed": 0, "results_so_far": []})
    return jsonify(_test_runner_instance.get_status())

@app.route('/testing/results', methods=['GET'])
def testing_results():
    """Get stored test results."""
    from src.testing.test_store import list_test_results, load_latest_results

    app_name = request.args.get('app', '')
    if app_name:
        data = load_latest_results(app_name)
        if data:
            return jsonify(data)
        return jsonify({"error": "No results found"}), 404
    return jsonify(list_test_results())

@app.route('/testing/coverage', methods=['GET'])
def testing_coverage():
    """Get cumulative coverage report from the latest run."""
    global _test_runner_instance
    if _test_runner_instance is None:
        from src.testing.coverage_tracker import ALL_BRANCH_IDS
        return jsonify({
            "branches_hit": [],
            "branches_missing": ALL_BRANCH_IDS,
            "branch_coverage_pct": 0.0,
            "total_branches": len(ALL_BRANCH_IDS),
        })
    return jsonify(_test_runner_instance.coverage.get_cumulative_report())


def _url_matches(url: str, pattern: str) -> bool:
    """Simple wildcard URL matching (only trailing * is supported)."""
    if pattern.endswith('*'):
        return url.startswith(pattern[:-1])
    return url == pattern


if __name__ == '__main__':
    # Don't initialize the agent session when the application starts
    # socketio.run(app, debug=True, port=5000, use_reloader=False)
    port = int(os.environ.get('PORT', 5002))
    socketio.run(app, debug=True, port=port, use_reloader=False)