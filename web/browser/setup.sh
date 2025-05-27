#!/bin/bash

# Exit on error
set -e

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
    
    # Copy package.json template and screenshot.js from script directory
    cp "${SCRIPT_DIR}/package.json.template" "$INSTALL_DIR/playwright-project/package.json"
    cp "${SCRIPT_DIR}/screenshot.js" "$INSTALL_DIR/playwright-project/screenshot.js"
    
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

# Copy screenshot server
echo "Copying screenshot server..."
cp "${SCRIPT_DIR}/screenshot_server.py" "$INSTALL_DIR/screenshot_server.py"

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
echo "Launching browser..."
cd "$INSTALL_DIR/playwright-project"
export PLAYWRIGHT_BROWSERS_PATH="$INSTALL_DIR/playwright-browsers"
npx playwright open --viewport-size=1024,768 https://example.com &
BROWSER_PID=$!

# Wait for browser to start
sleep 2
if ! kill -0 $BROWSER_PID 2>/dev/null; then
    echo "Error: Browser failed to start"
    exit 1
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

echo "✅ Setup complete! You can now access the browser at:"
echo "http://localhost:6080/vnc.html"

# Keep script running
echo "Press Ctrl+C to stop all services..."
wait

