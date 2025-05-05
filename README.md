# AC4A: Access Control for Agents

AC4A is a comprehensive framework for managing access control permissions for agents. This repository consists of a Python backend and a React-based frontend, providing a user-friendly interface for policy management and enforcement demo.

## Project Structure

```
.
├── src/                    # Core policy system implementation
│   ├── policy_system/      # Policy system components
│   ├── utils/             # Utility functions
│   ├── prompts.py         # System prompts and templates
│   └── app.py             # Core application logic
│
└── web/                   # Web application
    ├── frontend/          # React frontend
    ├── api/               # API endpoints
    ├── agent/             # Agent-related functionality
    ├── templates/         # HTML templates
    ├── static/            # Static assets
    ├── utils/             # Web utilities
    └── app.py             # Web server implementation
```

## Available Applications

The system includes several demo applications to showcase the access control framework:

- **Calendar**: Manage and schedule events
- **Wallet**: Handle financial transactions and balances
- **TravelBooking**: Book and manage travel arrangements
- **ContactManager**: Store and manage contact information

Example tasks for these applications can be found in `tasks.md`, which contains various scenarios to test the access control system.

## Prerequisites

### Backend Requirements
- Python 3.x
- Required Python packages (see `web/requirements.txt`)

### Frontend Requirements
- Node.js
- npm

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/reSHARMA/AC4A.git
   cd data-policy-lang
   ```

2. **Install Backend Dependencies**
   ```bash
   cd web
   pip install -r requirements.txt
   ```

3. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

## Running the Project

### Development Mode

1. **Start the Backend Server:**
   ```bash
   cd web
   python app.py
   ```

2. **Start the Frontend Development Server:**
   ```bash
   npm run dev
   ```

The application will be available at:
- Frontend: `http://localhost:5000`
- Backend API: `http://localhost:5173`

## Features

- Permission Management System
- Agent Access Control
- Interactive Permission Editor
- Real-time Permission Enforcement
- Comprehensive Logging System
- Multiple Demo Applications (Calendar, Wallet, TravelBooking, ContactManager)

## Development

### Testing
- Backend tests are located in `src/tests/`
- Frontend tests are located in `web/frontend/tests/`

### Debugging
- Use `web/debug_app.py` for debugging purposes
- Logs are stored in `web/debug.log` and `web/log`

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request