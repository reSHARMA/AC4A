from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import sys
import os
import threading
import queue
import logging
from datetime import datetime, timedelta
import time

# Import the agent_wrapper module
from agent_wrapper import (
    initialize_agent_session, 
    get_next_input_request, 
    submit_user_input, 
    get_next_agent_message,
    is_agent_waiting_for_input,
    is_agent_session_active
)

# Set up logging - change level to INFO to reduce logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable Flask-SocketIO debug logs
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store conversation history
conversation_history = []

# Flag to indicate if the agent is waiting for input
agent_waiting_for_input = False

# Remove the automatic initialization of the agent session
# @app.before_first_request
# def initialize_agent():
#     logger.info("Initializing agent session")
#     initialize_agent_session()
#     logger.info("Agent session initialized")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    if not is_agent_session_active():
        logger.info("Agent session not active, initializing")
        initialize_agent_session()
        logger.info("Agent session initialized")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    logger.info(f"Received message: {data}")
    user_message = data.get('message', '')
    logger.info(f"User message: {user_message}")
    
    # Check if the agent is waiting for input
    global agent_waiting_for_input
    if agent_waiting_for_input:
        logger.info("Agent is waiting for input, submitting user message")
        submit_user_input(user_message)
        agent_waiting_for_input = False
    
    # Add user message to conversation history but don't emit it
    # The frontend already displays user messages on the right side
    conversation_history.append({"role": "user", "content": user_message})
    
# Function to check for input requests from the agent
def check_for_input_requests():
    global agent_waiting_for_input
    while True:
        # Only check for input requests if the agent session is active
        if is_agent_session_active():
            # Check if agent is waiting for input
            if is_agent_waiting_for_input():
                input_request = get_next_input_request()
                if input_request:
                    logger.info(f"Received input request from agent: {input_request}")
                    agent_waiting_for_input = True
                    # Emit the input request to the web UI
                    socketio.emit('input_request', {"prompt": input_request})
            
            # Check for agent messages
            agent_message = get_next_agent_message()
            if agent_message:
                logger.info(f"Received agent message: {agent_message}")
                
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
                
                # Emit the message to all clients
                socketio.emit('message', {"role": agent_name, "content": content})
                logger.info(f"Emitted agent message: {agent_message}")
        else:
            while x := get_next_agent_message():
                logger.info(f"Remaining messages: {x}")
                socketio.emit('message', {"role": "Assistant", "content": x})

        socketio.sleep(0.5)  # Sleep to prevent CPU hogging

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