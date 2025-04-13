from flask import Flask, render_template, request, jsonify, session
import sys
import os
import threading
import queue
from datetime import datetime, timedelta

# Import the agent_wrapper module dynamically to avoid circular imports
agent_wrapper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_wrapper.py')
import importlib.util
spec = importlib.util.spec_from_file_location("agent_wrapper_module", agent_wrapper_path)
agent_wrapper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_wrapper_module)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# Store conversation history
conversation_history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    user_message = data.get('message', '')
    
    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    try:
        # Run the agent in a separate thread to avoid blocking the web server
        def run_agent_thread():
            # Run the agent with the user input
            agent_response = agent_wrapper_module.run_agent_with_input(user_message)
            
            # Add agent response to conversation history
            conversation_history.append({"role": "assistant", "content": agent_response})
        
        # Start the agent thread
        agent_thread = threading.Thread(target=run_agent_thread)
        agent_thread.daemon = True
        agent_thread.start()
        
        # Wait for the agent to complete (with timeout)
        agent_thread.join(timeout=30)  # 30 second timeout
        
        if agent_thread.is_alive():
            # Thread is still running (timeout occurred)
            return jsonify({
                "status": "error",
                "message": "Agent response timed out"
            }), 408
        
        # Get the last assistant message from the conversation history
        agent_response = conversation_history[-1]["content"]
        
        return jsonify({
            "status": "success",
            "response": agent_response,
            "history": conversation_history
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/get_history', methods=['GET'])
def get_history():
    return jsonify({"history": conversation_history})

if __name__ == '__main__':
    app.run(debug=True, port=5000) 