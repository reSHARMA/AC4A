# AC4A: Access Control for Agents

**AC4A (Access Control for Agents)** is a comprehensive framework that provides fine-grained access control for Large Language Model (LLM) agents. It enables users to define and enforce precise permissions over what data and capabilities agents can access, addressing the critical security challenge of agent autonomy.

📄 [AC4A Technical Paper](https://arxiv.org/abs/2603.20933v1)

## 🎯 Problem Statement

Current LLM agent systems operate on an all-or-nothing basis: agents either have full access to an API's capabilities or no access at all. This coarse-grained approach forces users to trust agents with more capabilities than they actually need. For example, when asking an agent to book a flight to a specific destination, users must grant access to the entire flight booking API, potentially allowing the agent to book flights anywhere, modify existing bookings, or access personal payment information.

## 🚀 Solution: AC4A Framework

AC4A introduces a flexible, hierarchical access control system that works across both API-based and browser-based agents. The framework:

- **Defines granular permissions** over data hierarchies using read/write access patterns
- **Enforces permissions at runtime** by intercepting agent actions
- **Provides a visual management dashboard** for creating and monitoring permissions
- **Supports both manual and LLM-generated permission policies**
- **Works seamlessly with existing agent frameworks**

## 🏗️ Architecture

```
AC4A Framework
├── Policy System (Core)
│   ├── Hierarchical Data Representation
│   ├── Permission Enforcement Engine
│   ├── Policy Validation & Translation
│   └── Runtime Action Interception
├── Web Interface
│   ├── Visual Policy Editor
│   ├── Real-time Permission Monitoring
│   ├── Agent Session Management
│   └── Interactive Demo Applications
└── Demo Applications
    ├── Calendar Management
    ├── Digital Wallet
    ├── Travel Booking (Expedia)
    └── Contact Manager
```

## ✨ Key Features

### 🔐 Fine-Grained Access Control
- **Hierarchical Data Permissions**: Define permissions over nested data structures
- **Read/Write Separation**: Distinguish between data access and modification capabilities
- **Wildcard Support**: Use `?` for flexible permission patterns
- **Context-Aware Enforcement**: Permissions adapt based on agent context and task

### 🎛️ Visual Policy Management
- **Interactive Policy Editor**: Create and modify permissions through an intuitive web interface
- **Real-time Monitoring**: Watch permissions being enforced in real-time
- **LLM-Assisted Generation**: Automatically generate appropriate permissions using AI

### 🔄 Runtime Enforcement
- **Action Interception**: Automatically intercept and validate agent actions
- **Permission Validation**: Check each action against defined policies
- **Graceful Degradation**: Handle permission violations with clear error messages
- **Audit Logging**: Comprehensive logging of all permission checks and violations

### 🌐 Multi-Platform Support
- **API-Based Agents**: Works with REST APIs, GraphQL, and custom endpoints
- **Browser-Based Agents**: Supports web automation and browser interactions
- **Framework Agnostic**: Compatible with AutoGen, LangChain, and other agent frameworks
- **Extensible Architecture**: Easy to add new data sources and applications

## 🎮 Demo Applications

AC4A includes four comprehensive demo applications to showcase the framework's capabilities:

### 📅 Calendar Management
- Schedule meetings and events
- Check availability across time periods
- Manage recurring appointments
- **Permission Examples**: Read-only access to specific date ranges, write access for personal events only

### 💳 Digital Wallet
- Manage credit cards and payment methods
- Store card details securely
- Handle payment processing
- **Permission Examples**: Read card numbers for specific cards only, write access for adding new cards

### ✈️ Travel Booking (Expedia)
- Search and book flights, hotels, and activities
- Manage travel itineraries
- Handle payment processing
- **Permission Examples**: Search flights to specific destinations only, book hotels within budget limits

### 👥 Contact Manager
- Store and manage contact information
- Organize contacts by groups and relationships
- Handle contact updates and deletions
- **Permission Examples**: Read contacts by relationship type, write access for personal contacts only

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.8+**
- **Node.js 16+**
- **Redis Server**
- **Git**

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/reSHARMA/AC4A.git
   cd AC4A
   ```

2. **Run the unified setup script**
   ```bash
   ./start_services.sh
   ```

This comprehensive script will automatically:
- ✅ Install all required dependencies (Python, Node.js, Redis)
- ✅ Set up Python virtual environment
- ✅ Install Python dependencies from `web/requirements.txt`
- ✅ Install frontend dependencies from `web/frontend/package.json`
- ✅ Start Redis server
- ✅ Launch backend server on port 5002
- ✅ Start frontend development server on port 5173
- ✅ Initialize browser services for web automation
- ✅ Monitor all services and provide status updates

### Service Endpoints
After running the setup script, access the following services:
- **Frontend Dashboard**: `http://localhost:5173`
- **Backend API**: `http://localhost:5002`
- **Browser VNC**: `http://localhost:6080/vnc.html`
- **Redis**: `localhost:6379`

## 📖 Usage Examples

### Creating a Permission Policy

```python
# Allow agent to read calendar events for specific month only
policy_system.add_policy({
    'resource_value_specification': 'Calendar:Year(2025)::Calendar:Month(6)',
    'action': 'read',
    'position': 'current'
})

# Allow agent to add new credit cards but not view existing ones
policy_system.add_policy({
    'resource_value_specification': 'Wallet:CreditCard(?)',
    'action': 'write',
    'position': 'current'
})
```

### Using the Web Interface

1. **Access the Dashboard**: Navigate to `http://localhost:5173`
2. **View Data Hierarchy**: Explore the available data structures and their relationships
3. **Create Policies**: Use the visual editor to define new permissions
4. **Monitor Enforcement**: Watch real-time permission checks as agents interact with applications
5. **Test Scenarios**: Try the built-in demo tasks to see AC4A in action

### Demo Tasks

The framework includes extensive test scenarios in `tasks.md`:

- **Single Application Tasks**: Test permissions within individual apps
- **Multi-Application Tasks**: Test cross-application permission enforcement
- **Complex Workflows**: Test sophisticated multi-step processes

## 🎥 Demo Videos

### Demo 1: Browser-Based Agents & Hierarchical Data Abstraction
[![AC4A Demo 1](https://img.shields.io/badge/YouTube-Watch%20Demo%201-red?style=for-the-badge&logo=youtube)](https://youtu.be/-lzbZ0gbHAM)

This demo showcases how our hierarchical data abstraction—combined with read and write attributes—can represent rich, practical permissions for **browser-based agents**. The same concepts and infrastructure work seamlessly across both API-based and browser-based agents, demonstrating AC4A's versatility in controlling web automation.

**Browser-Based Agent Capabilities Demonstrated:**
1. **Viewing Tic-Tac-Toe Game History** - Browser agent with read-only access to web game data
2. **Deleting a Game from History** - Browser agent with write access and permission validation for web interactions
3. **Booking Flight Tickets** - Cross-application workflow combining browser automation with API constraints
4. **Adding Calendar Events** - Browser agent with permission-controlled event creation on web interfaces

### Demo 2: Complex Multi-Application Workflow
[![AC4A Demo 2](https://img.shields.io/badge/YouTube-Watch%20Demo%202-red?style=for-the-badge&logo=youtube)](https://youtu.be/h-qCFNgurGU)

**Task**: *"Can you book a cruise to Alaska for July based on the constraints on my calendar? Go for the cheapest option. Book and pay using my Venture X card and add it to my calendar."*

This demo demonstrates AC4A's ability to handle complex, multi-step workflows involving:
- **Calendar Integration**: Checking availability constraints
- **Travel Booking**: Finding and booking the cheapest cruise option
- **Payment Processing**: Using specific credit card for payment
- **Cross-Application Coordination**: Seamlessly moving between applications
- **Permission Enforcement**: Ensuring each step respects defined access controls

## 🔧 Development

### Project Structure
```
AC4A/
├── src/                    # Core policy system
│   ├── policy_system/      # Policy engine and enforcement
│   ├── utils/             # Utility functions and helpers
│   └── prompts.py         # LLM prompts for policy generation
├── web/                   # Web application
│   ├── frontend/          # React-based dashboard
│   ├── agent/             # Agent management and session handling
│   ├── templates/         # HTML templates
│   └── app.py             # Flask backend server
├── app/                   # Demo applications
│   ├── calendar.py        # Calendar API implementation
│   ├── wallet.py          # Wallet API implementation
│   ├── expedia.py         # Travel booking API
│   └── contact_manager.py # Contact management API
└── agent.py               # Standalone agent (deprecated)
```

### Demo Scenarios
The `tasks.md` file contains 100+ test scenarios covering:
- Single application permissions
- Cross-application workflows
- Complex multi-step processes
- Permission violation handling

---

**AC4A** - Empowering secure and controlled agent autonomy through fine-grained access control.