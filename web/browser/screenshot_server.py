#!/usr/bin/env python3

import os
import sys
import time
import logging
from flask import Flask, jsonify, send_file
from flask_cors import CORS
import threading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variable to store the screenshot path
SCREENSHOT_PATH = None

def set_screenshot_path(path):
    """Set the path where screenshots are stored"""
    global SCREENSHOT_PATH
    SCREENSHOT_PATH = path
    logger.info(f"Screenshot path set to: {SCREENSHOT_PATH}")

@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    """
    Get the latest screenshot
    
    Returns:
        File: PNG image file or error message
    """
    try:
        if not SCREENSHOT_PATH or not os.path.exists(SCREENSHOT_PATH):
            return jsonify({
                'error': 'Screenshot not available',
                'message': 'Screenshot file not found'
            }), 404
            
        # Check if file was modified recently (within last 10 seconds)
        file_age = time.time() - os.path.getmtime(SCREENSHOT_PATH)
        if file_age > 10:
            logger.warning(f"Screenshot file is {file_age:.1f} seconds old")
            
        return send_file(
            SCREENSHOT_PATH,
            mimetype='image/png',
            as_attachment=False,
            download_name='screenshot.png'
        )
        
    except Exception as e:
        logger.error(f"Error serving screenshot: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Returns:
        JSON: Server status
    """
    return jsonify({
        'status': 'healthy',
        'screenshot_available': SCREENSHOT_PATH is not None and os.path.exists(SCREENSHOT_PATH) if SCREENSHOT_PATH else False,
        'screenshot_path': SCREENSHOT_PATH
    })

@app.route('/status', methods=['GET'])
def get_status():
    """
    Get server status and screenshot info
    
    Returns:
        JSON: Detailed status information
    """
    status = {
        'server': 'running',
        'screenshot_path': SCREENSHOT_PATH,
        'screenshot_exists': False,
        'screenshot_age': None,
        'screenshot_size': None
    }
    
    if SCREENSHOT_PATH and os.path.exists(SCREENSHOT_PATH):
        status['screenshot_exists'] = True
        status['screenshot_age'] = time.time() - os.path.getmtime(SCREENSHOT_PATH)
        status['screenshot_size'] = os.path.getsize(SCREENSHOT_PATH)
    
    return jsonify(status)

def run_server(host='localhost', port=8080, screenshot_path=None):
    """
    Run the Flask server
    
    Args:
        host (str): Host to bind to
        port (int): Port to bind to
        screenshot_path (str): Path to the screenshot file
    """
    if screenshot_path:
        set_screenshot_path(screenshot_path)
    
    logger.info(f"Starting screenshot server on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Screenshot server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--screenshot-path', required=True, help='Path to the screenshot file')
    
    args = parser.parse_args()
    
    run_server(args.host, args.port, args.screenshot_path) 