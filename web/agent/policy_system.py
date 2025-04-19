import logging

# Set up logging
logger = logging.getLogger(__name__)

class MockPolicySystem:
    def __init__(self):
        self.policies = []
        logger.info("Mock policy system initialized")
    
    def add_policy(self, policy):
        self.policies.append(policy)
        logger.info(f"Added policy: {policy}")
    
    def reset(self):
        self.policies = []
        logger.info("Policy system reset")
    
    def enable(self):
        logger.info("Policy system enabled")
    
    def disable(self):
        logger.info("Policy system disabled")
    
    def text(self):
        return "Mock policy system text"
    
    def ask(self):
        logger.info("Policy system ask called")
        return True

# Create a mock policy system instance
policy_system = MockPolicySystem() 