import logging
from typing import Dict, List, Any, Optional
from src.policy_system.policy_system import PolicySystem
from src.utils.attribute_tree import AttributeTree

# Import all agent classes from the agents directory
from .agents.calendar_agent import CalendarAgent
from .agents.wallet_agent import WalletAgent
from .agents.expedia_agent import ExpediaAgent
from .agents.contact_manager_agent import ContactManagerAgent
from .agents.planner_agent import PlannerAgent
from .agents.user_agent import UserAgent
from .model_client import setup_model_client

# Set up logging
logger = logging.getLogger(__name__)

class AgentManager:
    """
    Centralized manager for creating and accessing agents and their attribute trees.
    This ensures we have a single source of truth for agent instances.
    """
    
    def __init__(self):
        # Initialize PolicySystem
        self.policy_system = PolicySystem()
        logger.info("PolicySystem instance created in AgentManager")
        self.policy_system.disable()  # Disabled by default
        
        # Dictionary to store created agents
        self.agents = {}
        
        # Model client for agents
        self.model_client = None
        
        # Flag to track if agents have been initialized
        self.initialized = False
        
        # Store attribute trees
        self.attribute_trees = []

    def initialize_agents(self) -> Dict[str, Any]:
        """Initialize all agents with the model client"""
            
        logger.info("Initializing agents")
        
        # Set up model client if not already done
        if not self.model_client:
            self.model_client = setup_model_client()
        
        # Create agent instances
        self.agents['user'] = UserAgent(self.model_client).create_agent()
        self.agents['planner'] = PlannerAgent(self.model_client).create_agent()
        self.agents['calendar'] = CalendarAgent(self.model_client, self.policy_system).create_agent()
        self.agents['wallet'] = WalletAgent(self.model_client, self.policy_system).create_agent()
        self.agents['expedia'] = ExpediaAgent(self.model_client, self.policy_system).create_agent()
        self.agents['contact_manager'] = ContactManagerAgent(self.model_client, self.policy_system).create_agent()
        
        # Update attribute trees
        self._update_attribute_trees()
        
        # Mark as initialized
        self.initialized = True
        
        logger.info(f"Initialized {len(self.agents)} agents")
        return self.agents
    
    def get_agents_list(self) -> List[Any]:
        """Get a list of all agent instances for group chat"""
        self.initialize_agents()
        return list(self.agents.values())
    
    def get_agent(self, agent_name: str) -> Optional[Any]:
        """Get a specific agent by name"""
        if not self.initialized:
            self.initialize_agents()
            
        return self.agents.get(agent_name)
    
    def get_attribute_trees(self) -> List[AttributeTree]:
        """Get all attribute trees for display"""
        logger.info("Getting attribute trees")
        if not self.initialized:
            logger.info("Agents not initialized, initializing now")
            self.initialize_agents()
            
        logger.info(f"Current attribute trees count: {len(self.attribute_trees)}")
        for i, tree in enumerate(self.attribute_trees):
            logger.info(f"Tree {i}: {tree.get_tree_string()}")
            
        return self.attribute_trees
    
    def _update_attribute_trees(self):
        """Update the attribute trees from the policy system"""
        logger.info("Updating attribute trees from policy system")
        logger.info(f"Policy system status: {'enabled' if self.policy_system.status else 'disabled'}")
        
        attribute_definitions = self.policy_system.export_attributes()
        logger.info(f"Exported attributes: {attribute_definitions.keys()}")
        
        if 'granular_data' in attribute_definitions:
            # Get the trees from the policy system
            trees = attribute_definitions['granular_data']
            logger.info(f"Found granular_data with {len(trees)} trees")
            
            # Deduplicate trees based on their root key
            unique_trees = []
            seen_keys = set()
            
            for tree in trees:
                if isinstance(tree, AttributeTree):
                    key, _ = list(tree.value.items())[0]
                    if key not in seen_keys:
                        seen_keys.add(key)
                        unique_trees.append(tree)
                        logger.info(f"Added unique tree: {key}")
                    else:
                        logger.info(f"Skipping duplicate tree: {key}")
            
            self.attribute_trees = unique_trees
            logger.info(f"Deduplicated trees: {len(self.attribute_trees)} unique trees")
        else:
            logger.warning("No granular_data found in attribute definitions")
            self.attribute_trees = []
        
        logger.info(f"Updated attribute trees: found {len(self.attribute_trees)} trees")
        for i, tree in enumerate(self.attribute_trees):
            logger.info(f"Tree {i}: {tree.get_tree_string()}")
    
    def enable_policy_system(self):
        """Enable the policy system"""
        logger.info("Enabling policy system")
        self.policy_system.enable()
        logger.info("PolicySystem enabled")
        # Update trees after enabling
        self._update_attribute_trees()
    
    def disable_policy_system(self):
        """Disable the policy system"""
        logger.info("Disabling policy system")
        self.policy_system.disable()
        logger.info("PolicySystem disabled")

# Create a singleton instance
agent_manager = AgentManager() 