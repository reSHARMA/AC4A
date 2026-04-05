#!/usr/bin/env python3

import os
import sys
import time
import logging
import json
import requests
import websocket
from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
import threading
import base64

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

def check_cdp_reachable():
    """
    Check if Chrome DevTools Protocol is reachable.
    Returns (True, tabs_list) on success, or (False, error_message) on failure.
    """
    try:
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=2)
        if response.status_code != 200:
            return False, f"CDP returned HTTP {response.status_code}"
        return True, response.json()
    except requests.exceptions.ConnectionError as e:
        return False, (
            "Chrome DevTools Protocol (port 9222) is not reachable. "
            "Start the browser with remote debugging, e.g. run web/browser/start_full_browser.sh"
        )
    except Exception as e:
        return False, str(e)


def get_active_tab():
    """Get the active (most-recently-focused) Chrome tab via CDP.

    Chrome's ``/json`` endpoint returns tabs ordered by activation time
    (most recent first).  We pick the first ``page``-type entry that
    isn't a DevTools page — this naturally follows tab switches and
    new-tab creation.
    """
    try:
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=5)
        tabs = response.json()

        for tab in tabs:
            if tab.get('type') == 'page' and not tab.get('url', '').startswith('devtools://'):
                return tab

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

def inject_css_via_cdp(tab_id, css_rules):
    """Inject CSS into a page using Chrome DevTools Protocol"""
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
            return False
            
        if 'webSocketDebuggerUrl' not in target_tab:
            logger.error(f"No WebSocket URL found for tab {tab_id}")
            return False
        
        ws_url = target_tab['webSocketDebuggerUrl']
        logger.info(f"Connecting to WebSocket for CSS injection: {ws_url}")
        
        # Connect to WebSocket and inject CSS
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
        
        # Create a unique style element ID to avoid conflicts
        style_id = f"axiom-injected-css-{int(time.time())}"
        
        # Create JavaScript to inject CSS
        css_injection_script = f"""
        (function() {{
            // Remove any existing axiom injected styles
            var existingStyles = document.querySelectorAll('[id^="axiom-injected-css-"]');
            existingStyles.forEach(function(style) {{
                style.remove();
            }});
            
            // Create new style element
            var style = document.createElement('style');
            style.id = '{style_id}';
            style.type = 'text/css';
            style.innerHTML = `{css_rules}`;
            
            // Append to head
            document.head.appendChild(style);
            
            return 'CSS injected successfully with ID: {style_id}';
        }})();
        """
        
        # Inject the CSS
        eval_cmd = {
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": css_injection_script,
                "returnByValue": True
            }
        }
        logger.debug(f"Sending CSS injection command")
        ws.send(json.dumps(eval_cmd))
        
        # Wait for Runtime.evaluate response (ignore events)
        while True:
            eval_response = json.loads(ws.recv())
            logger.debug(f"Received message: {eval_response}")
            if 'id' in eval_response and eval_response['id'] == 2:
                logger.debug(f"CSS injection response: {eval_response}")
                break
            elif 'method' in eval_response:
                logger.debug(f"Ignoring event: {eval_response['method']}")
                continue
        
        ws.close()
        
        if 'result' in eval_response and 'result' in eval_response['result']:
            result = eval_response['result']['result']['value']
            logger.info(f"CSS injection result: {result}")
            return True
        else:
            logger.error(f"Unexpected CSS injection response: {eval_response}")
            return False
        
    except websocket.WebSocketException as e:
        logger.error(f"WebSocket error injecting CSS via CDP: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error injecting CSS via CDP: {str(e)}")
        return False

@app.route('/html-source', methods=['GET'])
def get_html_source():
    """
    Get the HTML source of the currently active page in Chromium
    
    Returns:
        JSON: HTML source content or error message
    """
    try:
        cdp_ok, cdp_result = check_cdp_reachable()
        if not cdp_ok:
            msg = cdp_result if isinstance(cdp_result, str) else 'Chrome DevTools Protocol unavailable'
            return jsonify({
                'error': 'Browser CDP unavailable',
                'message': msg
            }), 503
        # Get the active tab
        active_tab = get_active_tab()
        if not active_tab:
            return jsonify({
                'error': 'No active browser tab found',
                'message': 'No tabs available. Open a page in the browser.'
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
        cdp_ok, cdp_result = check_cdp_reachable()
        if not cdp_ok:
            msg = cdp_result if isinstance(cdp_result, str) else 'Chrome DevTools Protocol unavailable'
            return jsonify({
                'error': 'Browser CDP unavailable',
                'message': msg
            }), 503
        tabs = cdp_result
        
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

@app.route('/inject-css', methods=['POST'])
def inject_css():
    """
    Inject CSS into the currently active page
    
    Expects JSON payload:
    {
        "css": "selector { property: value; }",
        "selectors": ["selector1", "selector2"] // optional, will auto-generate border CSS
    }
    
    Returns:
        JSON: Success or error message
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'message': 'Request must contain JSON data'
            }), 400
        
        # Get the active tab
        active_tab = get_active_tab()
        if not active_tab:
            return jsonify({
                'error': 'No active browser tab found',
                'message': 'Chrome DevTools Protocol connection failed or no tabs available'
            }), 404
        
        css_rules = ""
        
        # If selectors are provided, generate border CSS for them
        if 'selectors' in data and data['selectors']:
            selectors = data['selectors']
            if not isinstance(selectors, list):
                return jsonify({
                    'error': 'Invalid selectors format',
                    'message': 'Selectors must be an array of strings'
                }), 400
            
            # Generate CSS to add borders to the selectors
            for selector in selectors:
                if isinstance(selector, str) and selector.strip():
                    css_rules += f"""
                    {selector} {{
                        border: 2px solid #ff6b6b !important;
                        box-shadow: 0 0 5px rgba(255, 107, 107, 0.5) !important;
                        position: relative !important;
                    }}
                    {selector}::before {{
                        content: attr(class) attr(id);
                        position: absolute;
                        top: -20px;
                        left: 0;
                        background: #ff6b6b;
                        color: white;
                        padding: 2px 5px;
                        font-size: 10px;
                        font-family: monospace;
                        border-radius: 2px;
                        z-index: 9999;
                        pointer-events: none;
                    }}
                    """
        
        # If raw CSS is provided, use it (will override/add to selector-generated CSS)
        if 'css' in data and data['css']:
            css_rules += "\n" + data['css']
        
        if not css_rules.strip():
            return jsonify({
                'error': 'No CSS provided',
                'message': 'Either "css" or "selectors" must be provided'
            }), 400
        
        # Inject the CSS
        success = inject_css_via_cdp(active_tab.get('id'), css_rules)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'CSS injected successfully',
                'tab_url': active_tab.get('url', 'unknown'),
                'css_applied': css_rules.strip()
            })
        else:
            return jsonify({
                'error': 'Failed to inject CSS',
                'message': 'CSS injection via Chrome DevTools Protocol failed'
            }), 500
        
    except Exception as e:
        logger.error(f"Error injecting CSS: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/clear-css', methods=['POST'])
def clear_injected_css():
    """
    Clear all previously injected CSS from the page
    
    Returns:
        JSON: Success or error message
    """
    try:
        # Get the active tab
        active_tab = get_active_tab()
        if not active_tab:
            return jsonify({
                'error': 'No active browser tab found',
                'message': 'Chrome DevTools Protocol connection failed or no tabs available'
            }), 404
        
        # Execute JavaScript to remove all injected CSS
        clear_css_script = """
        (function() {
            var existingStyles = document.querySelectorAll('[id^="axiom-injected-css-"]');
            var count = existingStyles.length;
            existingStyles.forEach(function(style) {
                style.remove();
            });
            return 'Removed ' + count + ' injected style elements';
        })();
        """
        
        # Execute the clearing script via CDP
        try:
            response = requests.get(f"{CDP_BASE_URL}/json", timeout=5)
            tabs = response.json()
            
            target_tab = None
            for tab in tabs:
                if tab.get('id') == active_tab.get('id'):
                    target_tab = tab
                    break
            
            if not target_tab or 'webSocketDebuggerUrl' not in target_tab:
                return jsonify({
                    'error': 'Cannot connect to tab',
                    'message': 'WebSocket URL not found for active tab'
                }), 500
            
            ws_url = target_tab['webSocketDebuggerUrl']
            ws = websocket.create_connection(ws_url, timeout=10)
            
            # Enable Runtime domain
            enable_cmd = {"id": 1, "method": "Runtime.enable"}
            ws.send(json.dumps(enable_cmd))
            
            # Wait for response
            while True:
                response = json.loads(ws.recv())
                if 'id' in response and response['id'] == 1:
                    break
                elif 'method' in response:
                    continue
            
            # Execute clearing script
            eval_cmd = {
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": clear_css_script,
                    "returnByValue": True
                }
            }
            ws.send(json.dumps(eval_cmd))
            
            # Wait for response
            while True:
                response = json.loads(ws.recv())
                if 'id' in response and response['id'] == 2:
                    break
                elif 'method' in response:
                    continue
            
            ws.close()
            
            if 'result' in response and 'result' in response['result']:
                result = response['result']['result']['value']
                return jsonify({
                    'success': True,
                    'message': result,
                    'tab_url': active_tab.get('url', 'unknown')
                })
            else:
                return jsonify({
                    'error': 'Failed to clear CSS',
                    'message': 'Unexpected response from browser'
                }), 500
                
        except Exception as e:
            logger.error(f"Error executing clear script: {str(e)}")
            return jsonify({
                'error': 'Failed to clear CSS',
                'message': f'Script execution failed: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error clearing CSS: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Minimum size for a valid 1024x768 PNG (avoid serving empty or half-written files)
MIN_SCREENSHOT_BYTES = 5000

# 1x1 transparent PNG so the frontend <img> loads without onError when screenshot isn't ready
_PLACEHOLDER_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)

@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    """
    Get the latest screenshot. When not ready (missing or too small), serves a
    tiny placeholder PNG so the frontend img doesn't fire onError.
    """
    try:
        if not SCREENSHOT_PATH or not os.path.exists(SCREENSHOT_PATH):
            return Response(_PLACEHOLDER_PNG, mimetype='image/png')

        size = os.path.getsize(SCREENSHOT_PATH)
        if size < MIN_SCREENSHOT_BYTES:
            return Response(_PLACEHOLDER_PNG, mimetype='image/png')

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
    cdp_available, cdp_result = check_cdp_reachable()
    hint = None
    if not cdp_available and isinstance(cdp_result, str):
        hint = cdp_result
    
    return jsonify({
        'status': 'healthy',
        'screenshot_available': SCREENSHOT_PATH is not None and os.path.exists(SCREENSHOT_PATH) if SCREENSHOT_PATH else False,
        'screenshot_path': SCREENSHOT_PATH,
        'html_source_available': cdp_available,
        'css_injection_available': cdp_available,
        'cdp_endpoint': CDP_BASE_URL,
        'cdp_hint': hint,
        'endpoints': {
            'screenshot': '/screenshot',
            'html_source': '/html-source',
            'inject_css': '/inject-css',
            'clear_css': '/clear-css',
            'tabs': '/tabs',
            'health': '/health',
            'status': '/status'
        }
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

@app.route('/active-tab-url', methods=['GET'])
def get_active_tab_url():
    """
    Get the URL of the currently active tab
    
    Returns:
        JSON: URL of the active tab or error message
    """
    try:
        # Get the active tab
        active_tab = get_active_tab()
        if not active_tab:
            return jsonify({
                'error': 'No active browser tab found',
                'message': 'Chrome DevTools Protocol connection failed or no tabs available'
            }), 404
        
        return jsonify({
            'success': True,
            'url': active_tab.get('url', 'unknown'),
            'title': active_tab.get('title', 'unknown'),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting active tab URL: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/evaluate', methods=['POST'])
def evaluate_javascript():
    """
    Evaluate JavaScript in the currently active page using Chrome DevTools Protocol
    
    Expects JSON payload:
    {
        "expression": "JavaScript code to evaluate"
    }
    
    Returns:
        JSON: Result of the evaluation or error message
    """
    try:
        data = request.get_json()
        if not data or 'expression' not in data:
            return jsonify({
                'error': 'No expression provided',
                'message': 'Request must contain JSON data with "expression" field'
            }), 400
        
        # Get the active tab
        active_tab = get_active_tab()
        if not active_tab:
            return jsonify({
                'error': 'No active browser tab found',
                'message': 'Chrome DevTools Protocol connection failed or no tabs available'
            }), 404
        
        # Get the WebSocket URL for the tab
        response = requests.get(f"{CDP_BASE_URL}/json", timeout=5)
        tabs = response.json()
        
        target_tab = None
        for tab in tabs:
            if tab.get('id') == active_tab.get('id'):
                target_tab = tab
                break
        
        if not target_tab or 'webSocketDebuggerUrl' not in target_tab:
            return jsonify({
                'error': 'Cannot connect to tab',
                'message': 'WebSocket URL not found for active tab'
            }), 500
        
        ws_url = target_tab['webSocketDebuggerUrl']
        ws = websocket.create_connection(ws_url, timeout=10)
        
        try:
            # Enable Runtime domain
            enable_cmd = {"id": 1, "method": "Runtime.enable"}
            ws.send(json.dumps(enable_cmd))
            
            # Wait for Runtime.enable response
            while True:
                response = json.loads(ws.recv())
                if 'id' in response and response['id'] == 1:
                    break
                elif 'method' in response:
                    continue
            
            # Evaluate the JavaScript expression
            eval_cmd = {
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": data['expression'],
                    "returnByValue": True
                }
            }
            ws.send(json.dumps(eval_cmd))
            
            # Wait for evaluation response
            while True:
                response = json.loads(ws.recv())
                if 'id' in response and response['id'] == 2:
                    break
                elif 'method' in response:
                    continue
            
            if 'result' in response and 'result' in response['result']:
                result = response['result']['result']
                return jsonify({
                    'success': True,
                    'result': result.get('value'),
                    'type': result.get('type')
                })
            else:
                return jsonify({
                    'error': 'Evaluation failed',
                    'message': 'Unexpected response from browser'
                }), 500
                
        finally:
            ws.close()
            
    except Exception as e:
        logger.error(f"Error evaluating JavaScript: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

def _capture_via_cdp(output_path):
    """Take a screenshot of the active tab via CDP and write it atomically."""
    try:
        tab = get_active_tab()
        if not tab or 'webSocketDebuggerUrl' not in tab:
            return False

        ws = websocket.create_connection(tab['webSocketDebuggerUrl'], timeout=10)

        ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot",
                            "params": {"format": "png"}}))
        while True:
            resp = json.loads(ws.recv())
            if 'id' in resp and resp['id'] == 1:
                break
            if 'method' in resp:
                continue
        ws.close()

        data = resp.get('result', {}).get('data')
        if not data:
            return False

        buf = base64.b64decode(data)
        if len(buf) < MIN_SCREENSHOT_BYTES:
            return False

        tmp = output_path + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(buf)
        os.replace(tmp, output_path)
        return True
    except Exception as e:
        logger.debug(f"CDP screenshot failed: {e}")
        return False


def _screenshot_loop(output_path, interval=1.0):
    """Background thread that updates the screenshot file every `interval` seconds."""
    logger.info(f"Screenshot capture loop started (interval={interval}s, path={output_path})")
    while True:
        _capture_via_cdp(output_path)
        time.sleep(interval)


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
        t = threading.Thread(target=_screenshot_loop, args=(screenshot_path,), daemon=True)
        t.start()
    
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