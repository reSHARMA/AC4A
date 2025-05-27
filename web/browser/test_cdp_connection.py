#!/usr/bin/env python3
"""
Test script to verify Chrome DevTools Protocol connection
"""

import requests
import json
import time

def test_cdp_connection():
    """Test Chrome DevTools Protocol connection"""
    cdp_url = "http://localhost:9222"
    
    print("Testing Chrome DevTools Protocol Connection...")
    print("=" * 60)
    
    # Wait a bit for browser to start
    print("Waiting for browser to start...")
    time.sleep(5)
    
    # Test CDP endpoint
    print("1. Testing CDP endpoint...")
    try:
        response = requests.get(f"{cdp_url}/json/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"   ✅ CDP endpoint is accessible")
            print(f"   Browser: {version_info.get('Browser', 'Unknown')}")
            print(f"   Protocol Version: {version_info.get('Protocol-Version', 'Unknown')}")
            print(f"   User Agent: {version_info.get('User-Agent', 'Unknown')}")
        else:
            print(f"   ❌ CDP endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Failed to connect to CDP endpoint: {e}")
        return False
    
    # Test tabs endpoint
    print("\n2. Testing tabs endpoint...")
    try:
        response = requests.get(f"{cdp_url}/json", timeout=5)
        if response.status_code == 200:
            tabs = response.json()
            print(f"   ✅ Found {len(tabs)} tabs")
            for i, tab in enumerate(tabs):
                print(f"     Tab {i+1}: {tab.get('title', 'No title')} - {tab.get('url', 'No URL')}")
                if 'webSocketDebuggerUrl' in tab:
                    print(f"       WebSocket URL: {tab['webSocketDebuggerUrl']}")
        else:
            print(f"   ❌ Tabs endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Failed to get tabs: {e}")
        return False
    
    print("\n✅ Chrome DevTools Protocol is working correctly!")
    print("You can now use the HTML source API endpoints.")
    return True

if __name__ == "__main__":
    success = test_cdp_connection()
    if not success:
        print("\n❌ CDP connection failed. Check that:")
        print("   - Chromium is running")
        print("   - DevTools Protocol is enabled on port 9222")
        print("   - No firewall is blocking port 9222")
        exit(1)
    else:
        print("\n🎉 Ready to test HTML source API!")
        print("Run: python3 test_html_api.py") 