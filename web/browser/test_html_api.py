#!/usr/bin/env python3
"""
Test script for the HTML source API endpoint
"""

import requests
import json
import time

def test_html_source_api():
    """Test the HTML source API endpoint"""
    base_url = "http://localhost:8080"
    
    print("Testing HTML Source API...")
    print("=" * 50)
    
    # Test health check
    print("1. Checking server health...")
    try:
        response = requests.get(f"{base_url}/health")
        health_data = response.json()
        print(f"   Server status: {health_data.get('status')}")
        print(f"   HTML source available: {health_data.get('html_source_available')}")
        print(f"   CDP endpoint: {health_data.get('cdp_endpoint')}")
        
        if not health_data.get('html_source_available'):
            print("   ⚠️  HTML source not available - Chrome DevTools Protocol may not be enabled")
            return
            
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test tabs endpoint
    print("\n2. Getting browser tabs...")
    try:
        response = requests.get(f"{base_url}/tabs")
        tabs_data = response.json()
        print(f"   Found {tabs_data.get('count', 0)} tabs:")
        for i, tab in enumerate(tabs_data.get('tabs', [])):
            print(f"     {i+1}. {tab.get('title')} - {tab.get('url')}")
            
    except Exception as e:
        print(f"   ❌ Failed to get tabs: {e}")
    
    # Test HTML source endpoint
    print("\n3. Getting HTML source...")
    try:
        response = requests.get(f"{base_url}/html-source")
        
        if response.status_code == 200:
            html_data = response.json()
            print(f"   ✅ Success!")
            print(f"   URL: {html_data.get('url')}")
            print(f"   Title: {html_data.get('title')}")
            print(f"   HTML length: {len(html_data.get('html', ''))} characters")
            print(f"   Timestamp: {html_data.get('timestamp')}")
            
            # Save HTML to file for inspection
            with open('/tmp/page_source.html', 'w', encoding='utf-8') as f:
                f.write(html_data.get('html', ''))
            print(f"   💾 HTML saved to /tmp/page_source.html")
            
            # Show first 200 characters of HTML
            html_preview = html_data.get('html', '')[:200]
            print(f"   📄 HTML preview: {html_preview}...")
            
        else:
            error_data = response.json()
            print(f"   ❌ Failed: {error_data.get('error')}")
            print(f"   Message: {error_data.get('message')}")
            
    except Exception as e:
        print(f"   ❌ Failed to get HTML source: {e}")

if __name__ == "__main__":
    test_html_source_api() 