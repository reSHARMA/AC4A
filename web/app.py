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
app.secret_key = os.urandom(24)  # Required for session management
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173"], async_mode='threading')

# Store conversation history
conversation_history = []

# Flag to track if a new session is needed
new_session_needed = False

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
        logger.info("Fetching attribute trees from agent manager")
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
        logger.info("Processing attribute trees for UI display")
        result = []
        for i, tree in enumerate(attribute_trees):
            logger.info(f"Processing tree {i}")
            processed_tree = process_tree(tree)
            result.append(processed_tree)
            logger.info(f"Processed tree {i}: {processed_tree}")
        
        logger.info("Successfully processed all trees")
        
        # Set response headers explicitly
        response = jsonify({"attribute_trees": result})
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        logger.error(f"Error in get_attribute_trees: {str(e)}", exc_info=True)
        error_response = jsonify({"error": str(e)})
        error_response.headers['Content-Type'] = 'application/json'
        return error_response, 500

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

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

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
                        socketio.sleep(1)
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
            socketio.sleep(1.0)
        except Exception as e:
            logger.error(f"Error in check_for_input_requests: {str(e)}", exc_info=True)
            # Add a small delay to prevent rapid cycling in case of errors
            socketio.sleep(1)

# Start the input request checker thread
input_checker_thread = threading.Thread(target=check_for_input_requests)
input_checker_thread.daemon = True
input_checker_thread.start()

@app.route('/get_history', methods=['GET'])
def get_history():
    return jsonify({"history": conversation_history})

if __name__ == '__main__':
    # Don't initialize the agent session when the application starts
    # socketio.run(app, debug=True, port=5000, use_reloader=False)
    socketio.run(app, debug=True, port=5000, use_reloader=False)