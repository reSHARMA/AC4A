#!/usr/bin/env python3
"""
Test script to verify WebSocket CORS fix for Chrome DevTools Protocol
"""

import requests
import json
import websocket
import time

def test_websocket_connection():
    """Test WebSocket connection to Chrome DevTools Protocol"""
    cdp_url = "http://localhost:9222"
    
    print("Testing WebSocket Connection to Chrome DevTools Protocol...")
    print("=" * 65)
    
    # First, get available tabs
    print("1. Getting available tabs...")
    try:
        response = requests.get(f"{cdp_url}/json", timeout=5)
        if response.status_code != 200:
            print(f"   ❌ Failed to get tabs: HTTP {response.status_code}")
            return False
            
        tabs = response.json()
        if not tabs:
            print("   ❌ No tabs found")
            return False
            
        # Find a suitable tab
        target_tab = None
        for tab in tabs:
            if tab.get('type') == 'page' and 'webSocketDebuggerUrl' in tab:
                target_tab = tab
                break
                
        if not target_tab:
            print("   ❌ No suitable tab found with WebSocket URL")
            return False
            
        print(f"   ✅ Found tab: {target_tab.get('title', 'Unknown')} - {target_tab.get('url', 'Unknown')}")
        ws_url = target_tab['webSocketDebuggerUrl']
        print(f"   WebSocket URL: {ws_url}")
        
    except Exception as e:
        print(f"   ❌ Error getting tabs: {e}")
        return False
    
    # Test WebSocket connection
    print("\n2. Testing WebSocket connection...")
    try:
        print(f"   Connecting to: {ws_url}")
        ws = websocket.create_connection(ws_url, timeout=10)
        print("   ✅ WebSocket connection established successfully!")
        
        # Test Runtime.enable
        print("\n3. Testing Runtime.enable command...")
        enable_cmd = {
            "id": 1,
            "method": "Runtime.enable"
        }
        ws.send(json.dumps(enable_cmd))
        
        # Wait for Runtime.enable response (ignore events)
        while True:
            response = json.loads(ws.recv())
            if 'id' in response and response['id'] == 1:
                print(f"   ✅ Runtime.enable response: {response}")
                break
            elif 'method' in response:
                print(f"   📡 Ignoring event: {response['method']}")
                continue
        
        # Test getting HTML
        print("\n4. Testing HTML extraction...")
        eval_cmd = {
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True
            }
        }
        ws.send(json.dumps(eval_cmd))
        
        # Wait for Runtime.evaluate response (ignore events)
        while True:
            eval_response = json.loads(ws.recv())
            if 'id' in eval_response and eval_response['id'] == 2:
                break
            elif 'method' in eval_response:
                print(f"   📡 Ignoring event: {eval_response['method']}")
                continue
        
        if 'result' in eval_response and 'result' in eval_response['result']:
            html_content = eval_response['result']['result']['value']
            print(f"   ✅ HTML extracted successfully! Length: {len(html_content)} characters")
            print(f"   📄 HTML preview: {html_content[:100]}...")
        else:
            print(f"   ⚠️  Unexpected response: {eval_response}")
        
        ws.close()
        print("\n✅ All WebSocket tests passed!")
        return True
        
    except websocket.WebSocketException as e:
        print(f"   ❌ WebSocket error: {e}")
        if "403" in str(e) or "Forbidden" in str(e):
            print("   💡 This looks like a CORS issue. Make sure the browser was launched with --remote-allow-origins=*")
        return False
    except Exception as e:
        print(f"   ❌ Error testing WebSocket: {e}")
        return False

if __name__ == "__main__":
    success = test_websocket_connection()
    if success:
        print("\n🎉 WebSocket connection is working correctly!")
        print("The HTML source API should now work properly.")
    else:
        print("\n❌ WebSocket connection failed.")
        print("Make sure:")
        print("   - Chromium is running with the updated browser_launcher.js")
        print("   - The browser was launched with --remote-allow-origins=* flag")
        print("   - Port 9222 is accessible")
        exit(1) 