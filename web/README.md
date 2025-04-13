# AutoGen Agent Web Interface

This is a web interface for the AutoGen agent system that provides a chat-based interface for interacting with various agents (Calendar, Wallet, Contact Manager, etc.).

## Approach

This web interface uses a wrapper approach to integrate with your existing AutoGen agent system without modifying it. The wrapper captures the output from the agent and provides it to the web interface.

## Mock Modules

Since the agent.py file imports from modules like `app.calendar`, `app.expedia`, etc., we've created mock implementations of these modules in `mock_app.py`. These mocks provide the necessary classes and methods that the agent expects, without requiring the actual implementations.

The mock modules include:
- `app.calendar` with `CalendarAPI` class
- `app.expedia` with `ExpediaAPI` class
- `app.wallet` with `WalletAPI` class
- `app.contact_manager` with `ContactManagerAPI` class

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

If you encounter any issues with Flask or Werkzeug, you can install them directly:
```bash
pip install flask==2.0.1 werkzeug==2.0.3 flask-cors==3.0.10 python-dotenv==0.19.0
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Testing the Wrapper

Before running the full web application, you can test the agent wrapper to make sure it works correctly:

```bash
python test_wrapper.py
```

This will run a simple test that sends a message to the agent and displays the response.

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## Features

- Real-time chat interface with the AutoGen agent system
- Support for multiple agent types (Calendar, Wallet, Contact Manager, etc.)
- Persistent chat history
- Modern and responsive UI
- Error handling and system messages

## Architecture

The web application consists of:

- Flask backend (`app.py`)
- Agent wrapper (`agent_wrapper.py`) - Captures output from the agent
- Mock modules (`mock_app.py`) - Provides mock implementations of the app modules
- HTML template (`templates/index.html`)
- CSS styles (`static/style.css`)
- Integration with the existing AutoGen agent system

## How It Works

1. The web interface sends user messages to the Flask backend
2. The backend uses the agent wrapper to run the agent with the user's input
3. The wrapper captures the output from the agent and returns it to the backend
4. The backend sends the response back to the web interface

## Notes

- This approach doesn't require modifying your existing agent.py
- The wrapper captures stdout and stderr to get the agent's output
- The chat interface supports both clicking the send button and pressing Enter to send messages 