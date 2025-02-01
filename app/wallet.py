from datetime import datetime
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data

class WalletAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("Wallet", {
            'granular_data': [
                AttributeTree(f'Wallet:CreditCard', [
                    AttributeTree(f'Wallet:CreditCardName'),
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
                AttributeTree('Previous'),
                AttributeTree('Current'),
                AttributeTree('Next')
            ]
        })

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'add_credit_card': ('CreditCard', kwargs.get('card_name', '*')),
            'remove_credit_card': ('CreditCard', kwargs.get('card_name', '*')),
            'update_credit_card': ('CreditCard', kwargs.get('card_name', '*')),
            'get_credit_card_info': ('CreditCard', kwargs.get('card_name', '*'))
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

    def generate_attributes(self, kwargs, endpoint_name, use_wildcard):
        start_time = datetime.now()
        end_time = start_time  # For wallet operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, use_wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, use_wildcard)
        
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

    @WalletAPIAnnotation.annotate
    def add_credit_card(self, card_name, card_type, card_number, card_pin):
        # Args: card_name (str), card_type (str), card_number (str), card_pin (str)
        return generate_dummy_data(
            api_endpoint="add_credit_card",
            card_name=card_name,
            card_type=card_type,
            card_number=card_number,
            card_pin=card_pin
        )

    @WalletAPIAnnotation.annotate
    def remove_credit_card(self, card_name):
        # Args: card_name (str)
        return generate_dummy_data(
            api_endpoint="remove_credit_card",
            card_name=card_name
        )

    @WalletAPIAnnotation.annotate
    def update_credit_card(self, card_name, card_type=None, card_number=None, card_pin=None):
        # Args: card_name (str), card_type (str, optional), card_number (str, optional), card_pin (str, optional)
        return generate_dummy_data(
            api_endpoint="update_credit_card",
            card_name=card_name,
            card_type=card_type,
            card_number=card_number,
            card_pin=card_pin
        )

    @WalletAPIAnnotation.annotate
    def get_credit_card_info(self, card_name):
        # Args: card_name (str)
        return generate_dummy_data(
            api_endpoint="get_credit_card_info",
            card_name=card_name
        )
