#!/usr/bin/env python
"""
Wrapper script to run the Flask application.
This script should be run from the root directory of the project.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import and run the Flask application
from web.app import app, socketio

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, use_reloader=False) 