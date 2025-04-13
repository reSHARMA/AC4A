import sys
import os
import asyncio
import threading
import queue
import io
import contextlib
import importlib.util

# Create a queue for communication between the agent and the web app
agent_response_queue = queue.Queue()

# Global variable to store the current user input
current_user_input = ""

def capture_output(func):
    """Decorator to capture stdout and stderr"""
    def wrapper(*args, **kwargs):
        # Create a string buffer to capture output
        output_buffer = io.StringIO()
        
        # Redirect stdout and stderr to the buffer
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
            result = func(*args, **kwargs)
        
        # Get the captured output
        output = output_buffer.getvalue()
        
        # Put the output in the queue
        if output.strip():
            agent_response_queue.put(output)
        
        return result
    return wrapper

# Patch the print function to capture output
original_print = print
def custom_print(*args, **kwargs):
    output = io.StringIO()
    original_print(*args, file=output, **kwargs)
    output_str = output.getvalue()
    if output_str.strip():
        agent_response_queue.put(output_str)
    return original_print(*args, **kwargs)

# Apply the patch
import builtins
builtins.print = custom_print

def run_agent_with_input(user_input):
    """Run the agent with the given user input"""
    global current_user_input
    
    # Set the current user input
    current_user_input = user_input
    
    # Clear the queue
    while not agent_response_queue.empty():
        agent_response_queue.get()
    
    # Create a new event loop for the async operation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Add the parent directory to the Python path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Import the mock_app module to set up the mock app modules
    mock_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_app.py')
    spec = importlib.util.spec_from_file_location("mock_app_module", mock_app_path)
    mock_app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mock_app_module)
    
    # Import the agent module dynamically to avoid circular imports
    agent_path = os.path.join(parent_dir, 'agent.py')
    spec = importlib.util.spec_from_file_location("agent_module", agent_path)
    agent_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_module)
    
    # Run the agent main function
    loop.run_until_complete(agent_module.main())
    
    # Put a sentinel value to indicate completion
    agent_response_queue.put("__COMPLETE__")
    
    # Collect all responses
    responses = []
    while True:
        try:
            response = agent_response_queue.get_nowait()
            if response == "__COMPLETE__":
                break
            responses.append(response)
        except queue.Empty:
            break
    
    # Combine all responses
    return "\n".join(responses)

# Example usage
if __name__ == "__main__":
    # Test the wrapper
    response = run_agent_with_input("Hello, agent!")
    print("Agent response:", response) 