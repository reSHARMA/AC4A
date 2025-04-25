import eventlet
eventlet.monkey_patch()

import sys
import os

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

# Set up logging - change level to INFO to reduce logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable Flask-SocketIO and autogen debug logs
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('autogen').setLevel(logging.ERROR)
logging.getLogger('autogen_core').setLevel(logging.ERROR)
logging.getLogger('autogen_agentchat').setLevel(logging.ERROR)
logging.getLogger('autogen_runtime').setLevel(logging.ERROR)

# Enable full debug for policy_system
policy_logger = logging.getLogger('policy_system')
policy_logger.setLevel(logging.DEBUG)

# Make sure policy logger has handlers
if not policy_logger.handlers:
    # Create console handler with formatting
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    policy_logger.addHandler(console)
    policy_logger.propagate = False  # Avoid duplicate logs

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
socketio = SocketIO(app, 
    cors_allowed_origins="*", 
    allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin", "Access-Control-Allow-Headers"],
    transports=['websocket'],
    async_mode='eventlet',
    message_queue='redis://localhost:6379/0',
    channel='socketio'
)

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
                return {"label": str(tree), "value": str(tree), "children": [], "access": "", "position": ""}
            
            key, value = list(tree.value.items())[0]
            node = {
                "label": key, 
                "value": value, 
                "children": [],
                "access": getattr(tree, 'access', ''),
                "position": getattr(tree, 'position', '')
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
        
        # Emit policy update to all connected clients
        emit_policy_update()
        
        return jsonify({"status": "success", "message": "Policy added successfully"})
    except Exception as e:
        logger.error(f"Error in add_policy: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def emit_policy_update():
    """Emit policy update to all connected clients"""
    try:
        logger.info("Emitting policy update to all connected clients")
        
        # Get attribute trees
        attribute_trees = agent_manager.get_attribute_trees()
        
        # Process trees into a format suitable for UI display
        def process_tree(tree):
            if not isinstance(tree, AttributeTree):
                logger.warning(f"Found non-AttributeTree object: {type(tree)}")
                return {"label": str(tree), "value": str(tree), "children": [], "access": "", "position": ""}
            
            key, value = list(tree.value.items())[0]
            node = {
                "label": key, 
                "value": value, 
                "children": [],
                "access": getattr(tree, 'access', ''),
                "position": getattr(tree, 'position', '')
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
        
        # Get policies
        policies = agent_manager.policy_system.policy_rules
        
        # Emit the update
        socketio.emit('policy_update', {
            "attribute_trees": processed_trees,
            "policies": policies
        })
        
        logger.info("Policy update emitted successfully")
    except Exception as e:
        logger.error(f"Error emitting policy update: {str(e)}", exc_info=True)

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
    
    # Reset the waiting flag
    set_agent_waiting_for_input(False)
    
    # Set the new session flag
    new_session_needed = True
    
    # Initialize a new session immediately
    logger.info("Initializing new session after reset")
    initialize_agent_session()
    new_session_needed = False
    
    return jsonify({"status": "success", "message": "Session reset"})

@socketio.on('connect')
def handle_connect():
    global new_session_needed, conversation_history
    logger.info('Client connected')
    
    # Reset the conversation history and session on new connection
    conversation_history = []
    reset_agent_session()
    
    # Initialize a new session
    logger.info("Initializing new agent session")
    initialize_agent_session()
    new_session_needed = False
    logger.info("Agent session initialized")
    
    # Send a welcome message
    welcome_message = {"role": "System", "content": "Welcome to the Autogen Chat! Type a message to start."}
    socketio.emit('message', welcome_message)
    conversation_history.append(welcome_message)
    
    # Send initial policy update
    emit_policy_update()

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
        logger.info("Initializing new agent session")
        # Make sure the agent session is fully reset before initializing a new one
        if is_agent_session_active():
            logger.info("Agent session still active, resetting first")
            reset_agent_session(emit_termination=False)  # Don't emit termination during normal reset
        initialize_agent_session()
        new_session_needed = False
        logger.info("Agent session initialized")
    
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
                        socketio.emit('input_request', {"prompt": input_request})
                
                # Check for agent messages
                agent_message = get_next_agent_message()
                if agent_message:
                    logger.info(f"Received agent message: {agent_message}")
                    
                    # Check for termination messages
                    if "Termination reason:" in agent_message:
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
                        logger.info("Skipping user message to prevent duplication")
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
            
        # Call OpenAI to generate policy code
        generated_code = call_openai_api(POLICY_GENERATOR_WILDCARD_V2, policy_text)
        
        # Extract code blocks from the response
        import re
        def extract_code_blocks(code: str) -> list:
            pattern = r"```python(.*?)```"
            code_blocks = re.findall(pattern, code, re.DOTALL)
            return [block.strip() for block in code_blocks]
            
        snippets = extract_code_blocks(generated_code)
        
        # Execute each policy snippet
        success = True
        for snippet in snippets:
            try:
                # Create a dictionary with policy_system for exec
                exec_globals = {"policy_system": agent_manager.policy_system}
                exec(snippet, exec_globals)
            except Exception as e:
                logger.error(f"Error executing policy: {str(e)}", exc_info=True)
                success = False
                
        if success:
            # Emit policy update to all connected clients
            emit_policy_update()
            return jsonify({'status': 'success', 'message': 'Policies added successfully'})
        else:
            return jsonify({'error': 'Some policies failed to execute'}), 400
            
    except Exception as e:
        logger.error(f"Error processing policy text: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Don't initialize the agent session when the application starts
    # socketio.run(app, debug=True, port=5000, use_reloader=False)
    socketio.run(app, debug=True, port=5000, use_reloader=False)