import logging
from autogen_agentchat.agents import AssistantAgent
from .permission_management_agent import PermissionManagementAgent

# Set up logging
logger = logging.getLogger(__name__)

class BaseAgent():
    """Base class for all agents"""
    
    def __init__(self, name, system_message, tools, model_client, skip_permission_management=False):
        """
        Initialize the base agent
        
        Args:
            name: The name of the agent
            system_message: The system message for the agent
            tools: The tools available to the agent
            model_client: The model client to use
        """
        self.name = name
        self.system_message = system_message
        self.tools = tools
        self.model_client = model_client
        self.agent = None
        if not skip_permission_management:
            self.permission_management_agent = PermissionManagementAgent(mode="ask")
            self.system_message += f"\n\n{self.permission_management_agent.get_prompt()}"
        
    def create_agent(self):
        """
        Create the agent
        
        Returns:
            The created agent
        """
        logger.info(f"Creating agent: {self.name}")
        self.agent = AssistantAgent(
            name=self.name,
            system_message=self.system_message,
            tools=self.tools,
            model_client=self.model_client
        )
        return self.agent
    
    def get_agent(self):
        """
        Get the agent
        
        Returns:
            The agent
        """
        if self.agent is None:
            self.create_agent()
        return self.agent 