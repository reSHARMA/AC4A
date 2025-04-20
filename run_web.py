#!/usr/bin/env python
"""
Wrapper script to run the Flask application.
This script should be run from the root directory of the project.
"""

import os
import sys
import logging

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure policy_system logger before importing any modules that use it
policy_logger = logging.getLogger('policy_system')
policy_logger.setLevel(logging.DEBUG)

# Reset any existing handlers to prevent duplicates
if policy_logger.handlers:
    for handler in policy_logger.handlers:
        policy_logger.removeHandler(handler)

# Create console handler with a more visible format
console = logging.StreamHandler(stream=sys.stderr)  # Use stderr for better visibility
console.setLevel(logging.DEBUG)  # Ensure DEBUG level for the handler
formatter = logging.Formatter('\033[1;36m%(asctime)s - %(name)s - %(levelname)s - %(message)s\033[0m')  # Cyan color for visibility
console.setFormatter(formatter)
policy_logger.addHandler(console)

# Create a file handler for debug log
file_handler = logging.FileHandler("policy_debug.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
policy_logger.addHandler(file_handler)

# Ensure logs don't propagate up to avoid duplicates
policy_logger.propagate = False

# Import and run the Flask application
from web.app import app, socketio

# Force a test log message to verify logging works
policy_logger.critical("POLICY SYSTEM LOGGER TEST - THIS SHOULD APPEAR IN CONSOLE")

if __name__ == '__main__':
    print("Policy system logger configured at DEBUG level - logs will appear in console and policy_debug.log")
    socketio.run(app, debug=True, port=5000, use_reloader=False) 