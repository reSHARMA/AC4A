import logging
from datetime import datetime
from .base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data
from config import WILDCARD
from typing import Annotated

# Set up logging
logger = logging.getLogger(__name__)

class WalletAPIAnnotation(APIAnnotationBase):
    attributes_schema = {
        'Wallet:CreditCard': {
            'description': 'The name of the credit card',
            'examples': ['Venture X', 'Amex Gold', 'Chase Sapphire']
        }, 
        'Wallet:CreditCardType': {
            'description': 'The type of the credit card, payment network',
            'examples': ['Visa', 'Mastercard', 'Amex']
        },
        'Wallet:CreditCardNumber': {
            'description': 'The number of the credit card, must be 16 digits',
            'examples': ['1234567890123456', '1234567890123456']
        },
        'Wallet:CreditCardPin': {
            'description': 'The pin of the credit card, must be 3 for visa and mastercard or 4 for amex',
            'examples': ['123', '456', '1234']
        },
    }
    def __init__(self):
        super().__init__("Wallet", {
            'granular_data': [
                AttributeTree(f'Wallet:CreditCard', [
                    AttributeTree(f'Wallet:CreditCardType'),
                    AttributeTree(f'Wallet:CreditCardNumber'),
                    AttributeTree(f'Wallet:CreditCardPin')
                ])
            ],
            'data_access': [
                AttributeTree('Read'),
                AttributeTree('Write')
            ],
            'position': [
                AttributeTree('Previous', [AttributeTree('Current')]),
                AttributeTree('Next', [AttributeTree('Current')])
            ]
        }, self.attributes_schema)

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'add_credit_card': ('CreditCard', kwargs.get('card_name', '*')),
            'remove_credit_card': ('CreditCard', kwargs.get('card_name', '*')),
            'update_credit_card': ('CreditCard', kwargs.get('card_name', '*')),
            'get_credit_card_info': ('CreditCard', kwargs.get('card_name', '*')),
            'get_all_credit_card_names': ('CreditCard', '*')
        }
        label, detail = api_to_granular_data.get(endpoint_name, ('CreditCard', '*'))
        if use_wildcard:
            return f"{self.namespace}:{label}(*)"
        else:
            return f"{self.namespace}:{label}({detail})"

    def get_access_level(self, endpoint_name):
        return 'Write' if 'add' in endpoint_name or 'remove' in endpoint_name or 'update' in endpoint_name else 'Read'

    def get_time_period(self, start_time, end_time, use_wildcard):
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        start_time = datetime.now()
        end_time = start_time  # For wallet operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, wildcard)
        
        return {
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
        }

class WalletAPI:
    def __init__(self, policy_system):
        self.annotation = WalletAPIAnnotation()
        self.policy_system = policy_system

    @WalletAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @WalletAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @WalletAPIAnnotation.annotate
    def add_credit_card(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="add_credit_card: add a new credit card with the given card name, card type, card number, card expiry date, card pin and the billing zip code",
            **kwargs
        )

    @WalletAPIAnnotation.annotate
    def remove_credit_card(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="remove_credit_card: remove the credit card with the given card name",
            **kwargs
        )

    @WalletAPIAnnotation.annotate
    def update_credit_card(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="update_credit_card: update the credit card information, including the card type, card number, card expiry date, card pin and the billing zip code",
            **kwargs
        )

    @WalletAPIAnnotation.annotate
    def get_credit_card_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_credit_card_info: get all the credit card information, including the card type, card number, card expiry date, card pin and the billing zip code",
            **kwargs
        )

    @WalletAPIAnnotation.annotate
    def get_all_credit_card_names(self):
        return generate_dummy_data(
            api_endpoint="get_all_credit_card_names: get all the credit card names"
        )

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
        You are a wallet agent. Use the tools provided to you to complete the task given to you. Start with reasoning about the task and then use the tools to complete the task. If you have a specific card name, use the tool `wallet_get_credit_card_info` directly to get the credit card information. Only use `wallet_get_all_credit_card_names` if you need to list all available cards or if you don't have a specific card name.
        
        Important: When using card names, always use the exact card name without adding the word "card" at the end. For example, use "Amex Gold" instead of "Amex Gold card", "Venture X" instead of "Venture X card", etc.
        
        """
        
        policy_system.register_api(WalletAPI)
        self.wallet_api = WalletAPI(policy_system)
        
        tools = [
            self.wallet_get_all_credit_card_names,
            self.wallet_get_credit_card_info,
            self.wallet_add_credit_card,
            self.wallet_remove_credit_card,
            self.wallet_update_credit_card,
            get_user_input
        ]
        
        super().__init__("Wallet", system_message, tools, model_client)
        
    async def wallet_add_credit_card(self, card_name: Annotated[str, "The name of the card, example 'Venture X'"], card_type: Annotated[str, "The type of the card, example 'Visa'"], card_number: Annotated[str, "The card number, example '1234567890123456'"], card_pin: Annotated[str, "The card PIN, example '123'"], billing_zip_code: Annotated[str, "The billing zip code, example '12345'"] = None) -> str:
        """Add a credit card to the wallet with all the required information"""
        logger.info(f"Calling WalletAPI add_credit_card with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}")
        result = self.wallet_api.add_credit_card(card_name=card_name, card_type=card_type, card_number=card_number, card_pin=card_pin)
        return result
        
    async def wallet_remove_credit_card(self, card_name: Annotated[str, "The name of the card, example 'Venture X'"] = None) -> str:
        """Remove a credit card from the wallet with the given card name"""
        logger.info(f"Calling WalletAPI remove_credit_card with card_name={card_name}")
        result = self.wallet_api.remove_credit_card(card_name=card_name)
        return result
        
    async def wallet_update_credit_card(self, card_name: Annotated[str, "The name of the card, example 'Venture X'"], card_type: Annotated[str, "The type of the card, example 'Visa'"] = None, card_number: Annotated[str, "The card number, example '1234567890123456'"] = None, card_pin: Annotated[str, "The card PIN, example '123'"] = None, billing_zip_code: Annotated[str, "The billing zip code, example '12345'"] = None) -> str:
        """Update a credit card in the wallet with the given card name and the values for the fields which need to be updated everthing else can be left empty."""
        logger.info(f"Calling WalletAPI update_credit_card with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}")
        result = self.wallet_api.update_credit_card(card_name=card_name, card_type=card_type, card_number=card_number, card_pin=card_pin)
        return result
        
    async def wallet_get_credit_card_info(self, card_name: Annotated[str, "The name of the card, example 'Venture X'"] = None) -> str:
        """Get credit card information with the given card name"""
        logger.info(f"Calling WalletAPI get_credit_card_info with card_name={card_name}")
        result = self.wallet_api.get_credit_card_info(card_name=card_name)
        return result 

    async def wallet_get_all_credit_card_names(self) -> str:
        """Get all the credit card names, must only be used if you don't have a specific card name"""
        logger.info("Calling WalletAPI get_all_credit_card_names")
        result = self.wallet_api.get_all_credit_card_names()
        return result