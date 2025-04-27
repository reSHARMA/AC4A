#!/usr/bin/env python
"""
Wrapper script to run the Flask application.
This script should be run from the root directory of the project.
"""

import os
import sys
import logging
import subprocess
import time
import signal
import atexit
import psutil
import threading
import queue
import json
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from agent.agent_manager import AgentManager
from agent.agent_core import AgentCore
from agent.web_input import WebInput
from agent.agents.permission_management_agent import PermissionManagementAgent
from agent.agents.user_agent import UserAgent
from agent.agents.planner_agent import PlannerAgent
from agent.agents.calendar_agent import CalendarAgent
from agent.agents.wallet_agent import WalletAgent
from agent.agents.contact_manager_agent import ContactManagerAgent
from agent.agents.expedia_agent import ExpediaAgent
from agent.selector import Selector
from agent.queues import MessageQueue
from agent.session import Session
from agent.model_client import ModelClient

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

# Ensure logs don't propagate up to avoid duplicates
policy_logger.propagate = False

# Import and run the Flask application
from web.app import app, socketio

# Force a test log message to verify logging works
policy_logger.critical("POLICY SYSTEM LOGGER TEST - THIS SHOULD APPEAR IN CONSOLE")

if __name__ == '__main__':
    print("Policy system logger configured at DEBUG level - logs will appear in console and policy_debug.log")
    socketio.run(app, debug=True, port=5000, use_reloader=False) 