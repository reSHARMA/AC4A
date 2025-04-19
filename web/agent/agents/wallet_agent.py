import logging
from .base_agent import BaseAgent
from ..web_input import web_input_func
from mock_app import WalletAPI

# Set up logging
logger = logging.getLogger(__name__)

class WalletAgent(BaseAgent):
    """Wallet agent for managing wallet operations"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the wallet agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a wallet agent.

        wallet_get_credit_card_info tool takes card_name as input and returns all the credit card information, always including the card type, card number, and card pin or CVV and the billing and anything else necessary for making a payment for the given card name.

        If the card information is requested but card name is not provided, ask the user for the card name using `get_user_input` tool.

        Return "done" when you have completed your work.
        """
        
        self.wallet_api = WalletAPI(policy_system)
        
        tools = [
            self.wallet_get_credit_card_info,
            self.wallet_add_credit_card,
            self.wallet_remove_credit_card,
            self.wallet_update_credit_card,
            web_input_func
        ]
        
        super().__init__("Wallet", system_message, tools, model_client)
        
    async def wallet_add_credit_card(self, card_name: str, card_type: str, card_number: str, card_pin: str) -> str:
        """
        Add a credit card to the wallet
        
        Args:
            card_name: The name of the card
            card_type: The type of the card
            card_number: The card number
            card_pin: The card PIN
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WalletAPI add_credit_card with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}")
        result = self.wallet_api.add_credit_card(card_name=card_name, card_type=card_type, card_number=card_number, card_pin=card_pin)
        return result
        
    async def wallet_remove_credit_card(self, card_name: str) -> str:
        """
        Remove a credit card from the wallet
        
        Args:
            card_name: The name of the card
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WalletAPI remove_credit_card with card_name={card_name}")
        result = self.wallet_api.remove_credit_card(card_name=card_name)
        return result
        
    async def wallet_update_credit_card(self, card_name: str, card_type: str = None, card_number: str = None, card_pin: str = None) -> str:
        """
        Update a credit card in the wallet
        
        Args:
            card_name: The name of the card
            card_type: The type of the card
            card_number: The card number
            card_pin: The card PIN
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WalletAPI update_credit_card with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}")
        result = self.wallet_api.update_credit_card(card_name=card_name, card_type=card_type, card_number=card_number, card_pin=card_pin)
        return result
        
    async def wallet_get_credit_card_info(self, card_name: str) -> str:
        """
        Get credit card information
        
        Args:
            card_name: The name of the card
            
        Returns:
            The credit card information
        """
        logger.info(f"Calling WalletAPI get_credit_card_info with card_name={card_name}")
        result = self.wallet_api.get_credit_card_info(card_name=card_name)
        return result 