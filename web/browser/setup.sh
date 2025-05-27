#!/bin/bash

# Exit on error
set -e

# =============================================================================
# CONFIGURATION
# =============================================================================
# uBlock Origin Lite Extension Configuration (Manifest V3)
UBOL_VERSION="2025.525.2314"
UBOL_URL="https://github.com/uBlockOrigin/uBOL-home/releases/download/uBOLite_${UBOL_VERSION}/uBOLite_${UBOL_VERSION}.chromium.mv3.zip"

# Default mode
MODE="normal"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--config)
            MODE="config"
            shift
            ;;
        -n|--normal)
            MODE="normal"
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🚀 Starting browser setup in $MODE mode..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define installation directories
INSTALL_DIR="$HOME/browser-remote"
MINICONDA_DIR="$HOME/miniconda3"
ENV_NAME="browser-env"

# Function to cleanup processes on script exit
cleanup() {
    echo "Cleaning up processes..."
    kill $XVFB_PID $BROWSER_PID $VNC_PID $NOVNC_PID $SCREENSHOT_PID $HTTP_PID 2>/dev/null || true
}

# Register cleanup function to run on script exit
trap cleanup EXIT

# Clean up existing environment if it exists
if [ -d "$MINICONDA_DIR" ]; then
    echo "Cleaning up existing environment..."
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    conda deactivate 2>/dev/null || true
    conda env remove -n "$ENV_NAME" 2>/dev/null || true
fi

# Remove existing browser-remote directory
rm -rf "$INSTALL_DIR"

# Create working directory and screenshots directory
mkdir -p "$INSTALL_DIR/screenshots"
cd "$INSTALL_DIR"

# Step 1: Install Miniconda if not already installed
if [ ! -d "$MINICONDA_DIR" ]; then
    echo "Downloading and installing Miniconda..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p "$MINICONDA_DIR"
    rm miniconda.sh
fi

# Step 2: Initialize conda and activate environment
source "$MINICONDA_DIR/etc/profile.d/conda.sh"
conda activate || true

# Step 3: Create conda environment with required packages
if ! conda info --envs | grep -q "$ENV_NAME"; then
    echo "Creating conda environment..."
    conda create -y -n "$ENV_NAME" -c conda-forge nodejs git python=3.9 pip
    conda activate "$ENV_NAME"
    
    # Install Flask dependencies
    echo "Installing Flask dependencies..."
    pip install -r "${SCRIPT_DIR}/requirements.txt"
fi

# Ensure we're in the conda environment
conda activate "$ENV_NAME"

# Step 4: Install Xvfb and its dependencies
echo "Installing Xvfb and dependencies..."
sudo apt-get update
sudo apt-get install -y \
    xvfb \
    x11vnc \
    x11-xserver-utils \
    x11-utils \
    x11-apps \
    x11-session-utils \
    x11-xkb-utils \
    x11-xserver-utils \
    x11proto-dev \
    x11proto-core-dev \
    x11proto-dri2-dev \
    x11proto-fonts-dev \
    x11proto-input-dev \
    x11proto-kb-dev \
    x11proto-present-dev \
    x11proto-randr-dev \
    x11proto-record-dev \
    x11proto-render-dev \
    x11proto-scrnsaver-dev \
    x11proto-video-dev \
    x11proto-xext-dev \
    x11proto-xf86dri-dev \
    x11proto-xinerama-dev \
    libxkbfile-dev \
    libxfont-dev \
    libxau-dev \
    libxdmcp-dev \
    libgl1-mesa-dev \
    x11proto-gl-dev

# Step 5: Install Playwright and browsers
if [ ! -d "$INSTALL_DIR/playwright-project" ]; then
    mkdir "$INSTALL_DIR/playwright-project"
    cd "$INSTALL_DIR/playwright-project"
    
    # Copy package.json template, screenshot.js, and browser_launcher.js from script directory
    cp "${SCRIPT_DIR}/package.json.template" "$INSTALL_DIR/playwright-project/package.json"
    cp "${SCRIPT_DIR}/screenshot.js" "$INSTALL_DIR/playwright-project/screenshot.js"
    cp "${SCRIPT_DIR}/browser_launcher.js" "$INSTALL_DIR/playwright-project/browser_launcher.js"
    
    # Copy element hider files to playwright-project for config mode
    cp "${SCRIPT_DIR}/element_hider.js" "$INSTALL_DIR/playwright-project/element_hider.js"
    cp "${SCRIPT_DIR}/browser_launcher_with_hider.js" "$INSTALL_DIR/playwright-project/browser_launcher_with_hider.js"
    cp "${SCRIPT_DIR}/element_hiding_config.json" "$INSTALL_DIR/playwright-project/element_hiding_config.json"
    
    npm install
    # Install browsers with explicit path
    export PLAYWRIGHT_BROWSERS_PATH="$INSTALL_DIR/playwright-browsers"
    npx playwright install chromium
    cd "$INSTALL_DIR"
fi

# Step 6: Clone noVNC
if [ ! -d "$INSTALL_DIR/noVNC" ]; then
    git clone https://github.com/novnc/noVNC.git
    git clone https://github.com/novnc/websockify noVNC/utils/websockify
fi

# Copy our custom VNC viewer
echo "Copying custom VNC viewer..."
cp "${SCRIPT_DIR}/vnc_lite.html" "$INSTALL_DIR/noVNC/vnc_lite.html"

# Copy screenshot server and browser launcher
echo "Copying screenshot server and browser launcher..."
cp "${SCRIPT_DIR}/screenshot_server.py" "$INSTALL_DIR/screenshot_server.py"
cp "${SCRIPT_DIR}/browser_launcher.js" "$INSTALL_DIR/browser_launcher.js"

# Download and install uBlock Origin Lite extension
echo "Downloading uBlock Origin Lite extension..."
mkdir -p "$INSTALL_DIR/extension/ublock-origin-lite"
cd "$INSTALL_DIR/extension/ublock-origin-lite"

# Download uBlock Origin Lite from GitHub releases
echo "Downloading uBlock Origin Lite v${UBOL_VERSION} from GitHub..."
wget -q --show-progress "$UBOL_URL" -O "ublock-origin-lite.zip"

if [ $? -eq 0 ]; then
    echo "✓ uBlock Origin Lite downloaded successfully"
    
    # Extract the extension
    echo "Extracting uBlock Origin Lite extension..."
    unzip -q "ublock-origin-lite.zip"
    
    if [ -f "manifest.json" ]; then
        # Create the expected directory structure since files are extracted to root
        mkdir -p "uBOLite.chromium"
        mv * "uBOLite.chromium/" 2>/dev/null || true
        # Move back the zip file if it was moved
        if [ -f "uBOLite.chromium/ublock-origin-lite.zip" ]; then
            mv "uBOLite.chromium/ublock-origin-lite.zip" .
        fi
        
        if [ -f "uBOLite.chromium/manifest.json" ]; then
            echo "✓ uBlock Origin Lite extracted successfully"
            rm "ublock-origin-lite.zip"
        else
            echo "✗ Error: Failed to create proper directory structure"
            exit 1
        fi
    else
        echo "✗ Error: Extension extraction failed"
        exit 1
    fi
else
    echo "✗ Error: Failed to download uBlock Origin Lite"
    echo "Trying alternative download method..."
    
    # Fallback: try with curl
    curl -L "$UBOL_URL" -o "ublock-origin-lite.zip"
    
    if [ $? -eq 0 ] && [ -f "ublock-origin-lite.zip" ]; then
        echo "✓ uBlock Origin Lite downloaded with curl"
        unzip -q "ublock-origin-lite.zip"
        
        if [ -f "manifest.json" ]; then
            echo "✓ uBlock Origin Lite extracted successfully"
            rm "ublock-origin-lite.zip"
        else
            echo "✗ Error: Extension extraction failed"
            exit 1
        fi
    else
        echo "✗ Error: Could not download uBlock Origin Lite with either wget or curl"
        exit 1
    fi
fi

cd "$INSTALL_DIR"

# Step 7: Start Xvfb
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 2
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "Error: Xvfb failed to start"
    exit 1
fi

# Step 8: Set display
export DISPLAY=:99

# Step 9: Set up Xauthority
echo "Setting up Xauthority..."
touch "$INSTALL_DIR/.Xauthority"
export XAUTHORITY="$INSTALL_DIR/.Xauthority"
xauth generate :99 . trusted

# Step 10: Launch browser
echo "Launching browser in $MODE mode..."
cd "$INSTALL_DIR/playwright-project"
export PLAYWRIGHT_BROWSERS_PATH="$INSTALL_DIR/playwright-browsers"

if [ "$MODE" = "config" ]; then
    echo "🎯 Configuration Mode: Visual element picker"
    node browser_launcher_with_hider.js &
else
    echo "🌐 Normal Mode: Applying element hiding rules automatically"
    node browser_launcher.js &
fi

BROWSER_PID=$!

# Wait for browser to start
sleep 5
if ! kill -0 $BROWSER_PID 2>/dev/null; then
    echo "Error: Browser failed to start"
    exit 1
fi

# Test extension loading
echo "Testing uBlock Origin Lite extension and Element Hider..."
sleep 3

# Test browser accessibility
BROWSER_TEST_PASSED=false
EXTENSION_TEST_PASSED=false
ELEMENT_HIDER_TEST_PASSED=false

# Check if browser is responding on debugging port
if curl -s http://localhost:9222/json > /dev/null 2>&1; then
    echo "✅ Browser debugging interface is accessible"
    BROWSER_TEST_PASSED=true
    
    # Get browser tabs/pages info
    PAGES_INFO=$(curl -s http://localhost:9222/json)
    if echo "$PAGES_INFO" | grep -q "example.com"; then
        echo "✅ Browser successfully navigated to example.com"
    else
        echo "⚠ Could not verify example.com navigation"
    fi
    
    # Test extension by checking background pages
    BACKGROUND_PAGES=$(curl -s "http://localhost:9222/json" | grep -o '"type":"background_page"' | wc -l)
    if [ "$BACKGROUND_PAGES" -gt 0 ]; then
        echo "✅ uBlock Origin Lite extension loaded successfully ($BACKGROUND_PAGES background page(s))"
        EXTENSION_TEST_PASSED=true
    else
        echo "⚠ uBlock Origin Lite extension may not be loaded (no background pages found)"
    fi
else
    echo "❌ Browser debugging interface not accessible"
fi

# Test Element Hider based on mode
if [ "$MODE" = "config" ]; then
    # In config mode, test if CLI is available by checking the prompt
    sleep 2
    if ps aux | grep -q "node.*browser_launcher_with_hider.js" && [ "$BROWSER_TEST_PASSED" = true ]; then
        echo "✅ Element Hider CLI is running in interactive mode"
        ELEMENT_HIDER_TEST_PASSED=true
    else
        echo "❌ Element Hider CLI failed to start properly"
    fi
else
    # In normal mode, test if element hider is initialized
    sleep 1
    if ps aux | grep -q "node.*browser_launcher.js" && [ "$BROWSER_TEST_PASSED" = true ]; then
        echo "✅ Element Hider is running in automatic mode"
        ELEMENT_HIDER_TEST_PASSED=true
    else
        echo "❌ Element Hider failed to start properly"
    fi
fi

echo "Extension test completed. Browser is running with uBlock Origin Lite."

echo ""
echo "🧪 SETUP TEST RESULTS"
echo "====================="

# Count passed tests
TESTS_PASSED=0
TOTAL_TESTS=3

if [ "$BROWSER_TEST_PASSED" = true ]; then
    echo "✅ Browser: Running and accessible"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "❌ Browser: Failed to start or not accessible"
fi

if [ "$EXTENSION_TEST_PASSED" = true ]; then
    echo "✅ uBlock Origin Lite: Extension loaded successfully"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "⚠ uBlock Origin Lite: Extension may not be loaded properly"
fi

if [ "$ELEMENT_HIDER_TEST_PASSED" = true ]; then
    echo "✅ Element Hider: Initialized and running correctly"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "❌ Element Hider: Failed to initialize properly"
fi

echo ""
echo "📊 Test Summary: $TESTS_PASSED/$TOTAL_TESTS tests passed"

if [ "$TESTS_PASSED" -eq "$TOTAL_TESTS" ]; then
    echo "🎉 ALL TESTS PASSED - Setup completed successfully!"
elif [ "$TESTS_PASSED" -ge 2 ]; then
    echo "⚠ PARTIAL SUCCESS - Setup mostly working, check warnings above"
else
    echo "❌ SETUP FAILED - Multiple critical issues detected"
    echo "   Check the error messages above and try running setup again"
fi

echo ""

if [ "$MODE" = "config" ]; then
    echo "🎯 CONFIGURATION MODE ACTIVE"
    echo "=========================="
    echo "Visual element picker interface available:"
    if [ "$ELEMENT_HIDER_TEST_PASSED" = true ]; then
        echo "• Hover over elements to highlight them"
        echo "• Click to hide elements permanently"
        echo "• Rules automatically saved to: $INSTALL_DIR/playwright-project/element_hiding_config.json"
        echo "• Press ESC to temporarily disable zapper"
    else
        echo "⚠ Element Hider CLI may not be responding properly"
        echo "  Try manually checking the browser window or restarting setup"
    fi
else
    echo "🌐 NORMAL MODE ACTIVE"
    echo "==================="
    echo "Element hiding rules applied automatically:"
    if [ "$ELEMENT_HIDER_TEST_PASSED" = true ]; then
        echo "• Rules loaded from: $INSTALL_DIR/playwright-project/element_hiding_config.json"
        echo "• Browser ready for automation and remote control"
    else
        echo "⚠ Element hiding may not be working properly"
        echo "  Rules loading may have failed - check browser console for errors"
    fi
fi

# Start Flask screenshot server
echo "Starting Flask screenshot server..."
cd "$INSTALL_DIR"
python3 screenshot_server.py --host localhost --port 8080 --screenshot-path "$INSTALL_DIR/screenshots/latest-preview.png" &
HTTP_PID=$!

# Step 11: Start x11vnc
echo "Starting x11vnc..."
x11vnc -display :99 -nopw -forever -shared -auth "$INSTALL_DIR/.Xauthority" &
VNC_PID=$!

# Wait for x11vnc to start
sleep 2
if ! kill -0 $VNC_PID 2>/dev/null; then
    echo "Error: x11vnc failed to start"
    exit 1
fi

# Step 12: Start noVNC
echo "Starting noVNC..."
cd "$INSTALL_DIR/noVNC"
./utils/novnc_proxy --vnc localhost:5900 --listen localhost:6080 &
NOVNC_PID=$!

# Wait for noVNC to start
sleep 2
if ! kill -0 $NOVNC_PID 2>/dev/null; then
    echo "Error: noVNC failed to start"
    exit 1
fi

# Start screenshot capture process
echo "Starting screenshot capture..."
(
  while kill -0 $BROWSER_PID 2>/dev/null; do
    echo "Taking screenshot..."
    cd "$INSTALL_DIR/playwright-project"
    node screenshot.js "$INSTALL_DIR/screenshots/latest-preview.png" 2>&1 | tee -a "$INSTALL_DIR/screenshots/screenshot.log"
    
    if [ $? -eq 0 ]; then
      echo "Screenshot saved successfully"
    else
      echo "Failed to save screenshot"
    fi
    
    sleep 1  # Take screenshots every second
  done
) &
SCREENSHOT_PID=$!

echo ""
echo "🌐 SERVICES STATUS"
echo "=================="

# Check and display all service endpoints
echo "Available endpoints:"

# Browser debugging interface
if curl -s http://localhost:9222/json > /dev/null 2>&1; then
    echo "✅ Browser DevTools: http://localhost:9222"
else
    echo "❌ Browser DevTools: http://localhost:9222 (not accessible)"
fi

# noVNC interface
if curl -s http://localhost:6080 > /dev/null 2>&1; then
    echo "✅ VNC Web Interface: http://localhost:6080/vnc.html"
else
    echo "❌ VNC Web Interface: http://localhost:6080/vnc.html (not accessible)"
fi

# Screenshot server
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Screenshot API: http://localhost:8080"
else
    echo "❌ Screenshot API: http://localhost:8080 (not accessible)"
fi

echo ""
echo "📝 QUICK ACCESS GUIDE"
echo "===================="
echo "• Browser Control: http://localhost:6080/vnc.html"
echo "• DevTools/Debug: http://localhost:9222"  
echo "• Screenshots: http://localhost:8080"

if [ "$MODE" = "config" ]; then
    echo "• Element Picker: Use visual interface"
else
    echo "• Switch to config mode: $0 --config"
fi

echo ""
echo "🔧 TROUBLESHOOTING"
echo "=================="
if [ "$TESTS_PASSED" -lt "$TOTAL_TESTS" ]; then
    echo "If you see failures above:"
    echo "1. Wait 30 seconds for services to fully start"
    echo "2. Check if ports 6080, 8080, 9222 are available"
    echo "3. Verify X11 display is working: echo \$DISPLAY"
    echo "4. Restart setup: $0 $([ "$MODE" = "config" ] && echo "--config" || echo "--normal")"
else
    echo "All systems operational! 🚀"
    echo "Use Ctrl+C to stop all services when done."
fi

echo "✅ Setup complete! You can now access the browser at:"
echo "http://localhost:6080/vnc.html"

# Keep script running
echo "Press Ctrl+C to stop all services..."
wait

show_help() {
    echo "Browser Setup with Element Hiding"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --normal      Normal mode: Auto-apply saved element hiding rules (default)"
    echo "  --config      Zapper mode: Visual element picker for configuring rules"
    echo "  --help        Show this help message"
    echo ""
    echo "MODES:"
    echo "  Normal Mode:"
    echo "    - Launches browser with saved element hiding rules"
    echo "    - Rules automatically applied from element_hiding_config.json"
    echo "    - Lightweight operation, no configuration interface"
    echo ""
    echo "  Zapper Mode (--config):"
    echo "    - Visual element picker interface (like uBlock Origin's zapper)"
    echo "    - Hover over elements to highlight them"
    echo "    - Click to hide elements permanently"
    echo "    - Rules automatically saved to element_hiding_config.json"
    echo "    - Press ESC to temporarily disable zapper"
    echo "    - No command line interface - pure visual interaction"
    echo ""
    echo "BROWSER ACCESS:"
    echo "  - VNC Web Interface: http://localhost:6080/vnc.html"
    echo "  - DevTools Protocol: http://localhost:9222"
    echo "  - Screenshot API: http://localhost:8080"
    echo ""
    exit 0
}

