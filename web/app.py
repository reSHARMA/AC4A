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
from src.utils.attribute_tree import AttributeTree
from src.prompts import POLICY_GENERATOR_WILDCARD_V2
from src.utils.dummy_data import call_openai_api

from web.utils.events import socketio, emit_policy_update
from web.utils.socket_io import init_socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug.log')
    ]
)

# Set log levels for specific modules
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('autogen').setLevel(logging.ERROR)
logging.getLogger('autogen_core').setLevel(logging.ERROR)
logging.getLogger('autogen_agentchat').setLevel(logging.INFO)
logging.getLogger('autogen_runtime').setLevel(logging.ERROR)

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

# Flag to track if a new session is needed
new_session_needed = False

# Add cache dictionary at the top level of the file
text_cache = {}

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
            if not isinstance(tree, AttributeTree):
                logger.warning(f"Found non-AttributeTree object: {type(tree)}")
                return {"label": str(tree), "value": str(tree), "children": [], "access": "", "position": "", "positionValue": 0}
            
            key, value = list(tree.value.items())[0]
            node = {
                "label": key, 
                "value": value, 
                "children": [],
                "access": getattr(tree, 'access', ''),
                "position": getattr(tree, 'position', ''),
                "positionValue": getattr(tree, 'positionValue', 0)
            }
            
            for child in tree.children:
                node["children"].append(process_tree(child))
            
            return node
        
        # Process each tree in granular_data
        processed_trees = []
        seen_keys = set()
        
        for tree in attribute_trees:
            if isinstance(tree, AttributeTree):
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
        policy_key = f"{policy_data['granular_data']}-{policy_data['data_access']}-{policy_data['position']}"
        logger.info(f"Emitting highlight for policy: {policy_key}")
        socketio.emit('highlight_policy', policy_key)
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
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
            return jsonify({"error": "Policy not found"}), 404
        
        logger.info(f"Successfully removed policy: {policy_data}")
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
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
    logger.info(f"User message: {user_message}")
    
    # Check if we need to initialize a new session
    if new_session_needed or not is_agent_session_active():
        logger.info("Initializing new agent session because we received a user message but the agent session is not active")
        # Make sure the agent session is fully reset before initializing a new one
        if is_agent_session_active():
            logger.info("Agent session is active, but a reset was requested")
            reset_agent_session()
        initialize_agent_session()
    
    # Check if the agent is waiting for input
    if is_agent_waiting_for_input():
        logger.info("Agent is waiting for input, submitting user message")
        submit_user_input(user_message)
        set_agent_waiting_for_input(False)
    
    # Add user message to conversation history but don't emit it
    # The frontend already displays user messages on the right side
    conversation_history.append({"role": "user", "content": user_message})
    
# Function to check for input requests from the agent
def check_for_input_requests():
    global new_session_needed
    while True:
        try:
            # Check if we need to initialize a new session
            if new_session_needed:
                logger.info("New session needed, initializing")
                # Make sure the agent session is fully reset before initializing a new one
                if is_agent_session_active():
                    logger.info("Agent session still active, resetting first")
                    reset_agent_session()
                initialize_agent_session()
                new_session_needed = False
                logger.info("New session initialized")
            
            # Only check for input requests if the agent session is active
            if is_agent_session_active():
                logger.info("Agent session is active, checking for input requests and messages")
                # Check if agent is waiting for input
                if is_agent_waiting_for_input():
                    input_request = get_next_input_request()
                    if input_request:
                        logger.info(f"Received input request from agent: {input_request}")
                        set_agent_waiting_for_input(True)
                        # Emit the input request to the web UI
                        logger.info(f"Emitting input request to web UI: {input_request}")
                        socketio.emit('input_request', {"prompt": input_request})
                
                # Check for agent messages
                agent_message = get_next_agent_message()
                if agent_message:
                    logger.info(f"Received agent message: {agent_message}")
                    
                    # Check for termination messages
                    if "termination" in agent_message.lower():
                        logger.info(f"Agent terminated: {agent_message}")
                        # Set the new session flag
                        new_session_needed = True
                        # Emit the termination message
                        socketio.emit('message', {"role": "System", "content": agent_message})
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
                    socketio.emit('message', {"role": agent_name, "content": content})
            else:
                logger.info("Agent session not active, skipping check for input requests and flushing agent message queue")
                while remaining_message := get_next_agent_message():
                    logger.info(f"Flushing remaining message from agent message queue: {remaining_message}")
                    socketio.emit('message', {"role": "System", "content": remaining_message})

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
        cache_key = f"{data['granular_data']}-{data['data_access']}-{data['position']}"
        
        # Check if we have a cached result
        if cache_key in text_cache:
            logger.info(f"Using cached text for policy: {cache_key}")
            return jsonify({'text': text_cache[cache_key]})
            
        policy = {
            'granular_data': data['granular_data'],
            'data_access': data['data_access'],
            'position': data['position']
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
            
        # Format the log entry without timestamp and CustomLog prefix
        log_entry = f"{category} - {message}\n"
        
        # Append to debug.log
        log_path = os.path.join(os.path.dirname(__file__), 'debug.log')
        with open(log_path, 'a') as f:
            f.write(log_entry)
            
        # Emit the new log to all connected clients
        emit_new_log({
            'source': 'CustomLog',
            'level': category,
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
        logger.info(f"Returning {len(logs)} logs")
        
        return jsonify({"logs": logs})
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Don't initialize the agent session when the application starts
    # socketio.run(app, debug=True, port=5000, use_reloader=False)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=True, port=port, use_reloader=False)