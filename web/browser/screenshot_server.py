#!/usr/bin/env python3

import os
import sys
import time
import logging
import json
import requests
import websocket
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
# Chrome DevTools Protocol endpoint
CDP_PORT = 9222
CDP_BASE_URL = f"http://localhost:{CDP_PORT}"

def set_screenshot_path(path):
    """Set the path where screenshots are stored"""
    global SCREENSHOT_PATH
    SCREENSHOT_PATH = path
    logger.info(f"Screenshot path set to: {SCREENSHOT_PATH}")

def get_active_tab():
    """Get the active Chrome tab using DevTools Protocol"""
    try:
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=5)
        tabs = response.json()
        
        # Find the first tab that's not a DevTools tab
        for tab in tabs:
            if tab.get('type') == 'page' and not tab.get('url', '').startswith('devtools://'):
                return tab
        
        # If no regular tab found, return the first available tab
        if tabs:
            return tabs[0]
        
        return None
    except Exception as e:
        logger.error(f"Error getting active tab: {str(e)}")
        return None

def get_page_html_via_cdp(tab_id):
    """Get HTML content of a page using Chrome DevTools Protocol"""
    try:
        # Get the WebSocket URL for the tab
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=5)
        tabs = response.json()
        
        target_tab = None
        for tab in tabs:
            if tab.get('id') == tab_id:
                target_tab = tab
                break
        
        if not target_tab:
            logger.error(f"Tab with ID {tab_id} not found")
            return None
            
        if 'webSocketDebuggerUrl' not in target_tab:
            logger.error(f"No WebSocket URL found for tab {tab_id}")
            return None
        
        ws_url = target_tab['webSocketDebuggerUrl']
        logger.info(f"Connecting to WebSocket: {ws_url}")
        
        # Connect to WebSocket and get HTML
        ws = websocket.create_connection(ws_url, timeout=10)
        
        # Enable Runtime domain
        enable_cmd = {
            "id": 1,
            "method": "Runtime.enable"
        }
        logger.debug(f"Sending Runtime.enable command: {enable_cmd}")
        ws.send(json.dumps(enable_cmd))
        
        # Wait for Runtime.enable response (ignore events)
        while True:
            enable_response = json.loads(ws.recv())
            logger.debug(f"Received message: {enable_response}")
            if 'id' in enable_response and enable_response['id'] == 1:
                logger.debug(f"Runtime.enable response: {enable_response}")
                break
            elif 'method' in enable_response:
                logger.debug(f"Ignoring event: {enable_response['method']}")
                continue
        
        # Get the HTML content
        eval_cmd = {
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True
            }
        }
        logger.debug(f"Sending Runtime.evaluate command: {eval_cmd}")
        ws.send(json.dumps(eval_cmd))
        
        # Wait for Runtime.evaluate response (ignore events)
        while True:
            eval_response = json.loads(ws.recv())
            logger.debug(f"Received message: {eval_response}")
            if 'id' in eval_response and eval_response['id'] == 2:
                logger.debug(f"Runtime.evaluate response keys: {eval_response.keys()}")
                break
            elif 'method' in eval_response:
                logger.debug(f"Ignoring event: {eval_response['method']}")
                continue
        
        ws.close()
        
        if 'result' in eval_response and 'result' in eval_response['result']:
            html_content = eval_response['result']['result']['value']
            logger.info(f"Successfully extracted HTML content ({len(html_content)} characters)")
            return html_content
        else:
            logger.error(f"Unexpected response structure: {eval_response}")
            return None
        
    except websocket.WebSocketException as e:
        logger.error(f"WebSocket error getting HTML via CDP: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting HTML via CDP: {str(e)}")
        return None

@app.route('/html-source', methods=['GET'])
def get_html_source():
    """
    Get the HTML source of the currently active page in Chromium
    
    Returns:
        JSON: HTML source content or error message
    """
    try:
        # Get the active tab
        active_tab = get_active_tab()
        if not active_tab:
            return jsonify({
                'error': 'No active browser tab found',
                'message': 'Chrome DevTools Protocol connection failed or no tabs available'
            }), 404
        
        # Get HTML content
        html_content = get_page_html_via_cdp(active_tab.get('id'))
        if html_content is None:
            return jsonify({
                'error': 'Failed to retrieve HTML content',
                'message': 'Could not extract HTML from the active tab'
            }), 500
        
        return jsonify({
            'success': True,
            'url': active_tab.get('url', 'unknown'),
            'title': active_tab.get('title', 'unknown'),
            'html': html_content,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting HTML source: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/tabs', methods=['GET'])
def get_tabs():
    """
    Get list of all open tabs in Chrome
    
    Returns:
        JSON: List of tabs with their info
    """
    try:
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=5)
        tabs = response.json()
        
        # Filter and format tab information
        formatted_tabs = []
        for tab in tabs:
            if tab.get('type') == 'page':
                formatted_tabs.append({
                    'id': tab.get('id'),
                    'title': tab.get('title', 'Unknown'),
                    'url': tab.get('url', 'Unknown'),
                    'active': not tab.get('url', '').startswith('devtools://')
                })
        
        return jsonify({
            'success': True,
            'tabs': formatted_tabs,
            'count': len(formatted_tabs)
        })
        
    except Exception as e:
        logger.error(f"Error getting tabs: {str(e)}")
        return jsonify({
            'error': 'Failed to get tabs',
            'message': str(e)
        }), 500

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
    # Check CDP connectivity
    cdp_available = False
    try:
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=2)
        cdp_available = response.status_code == 200
    except:
        pass
    
    return jsonify({
        'status': 'healthy',
        'screenshot_available': SCREENSHOT_PATH is not None and os.path.exists(SCREENSHOT_PATH) if SCREENSHOT_PATH else False,
        'screenshot_path': SCREENSHOT_PATH,
        'html_source_available': cdp_available,
        'cdp_endpoint': CDP_BASE_URL
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