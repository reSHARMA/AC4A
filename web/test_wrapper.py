#!/usr/bin/env python3
"""
Test script for the agent wrapper.
This script tests the agent wrapper without the Flask app to verify that it works correctly.
"""

import os
import sys
import asyncio
import importlib.util
import traceback

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the mock_app module to set up the mock app modules
mock_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_app.py')
spec = importlib.util.spec_from_file_location("mock_app_module", mock_app_path)
mock_app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock_app_module)

# Import the agent_wrapper module dynamically
agent_wrapper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_wrapper.py')
spec = importlib.util.spec_from_file_location("agent_wrapper_module", agent_wrapper_path)
agent_wrapper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_wrapper_module)

def test_agent():
    """Test the agent wrapper with a simple input."""
    print("Testing agent wrapper...")
    user_input = "Hello, agent! Can you help me with my calendar?"
    print(f"User input: {user_input}")
    
    try:
        # Run the agent with the user input
        response = agent_wrapper_module.run_agent_with_input(user_input)
        
        print("\nAgent response:")
        print(response)
        
        return response
    except Exception as e:
        print("\nError running agent:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    test_agent() 