import logging
from datetime import datetime
from .base_agent import BaseAgent
from ..web_input import web_input_func
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data
from config import WILDCARD

# Set up logging
logger = logging.getLogger(__name__)

class ContactManagerAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("ContactManager", {
            'granular_data': [
                AttributeTree('ContactManager:Contact', [
                    AttributeTree('ContactManager:ContactPhone'),
                    AttributeTree('ContactManager:ContactAddress'),
                    AttributeTree('ContactManager:ContactEmail'),
                    AttributeTree('ContactManager:ContactRelation'),
                    AttributeTree('ContactManager:ContactBirthday'),
                    AttributeTree('ContactManager:ContactNotes')
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
        })

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'add_contact': ('Contact', kwargs.get('name', '*')),
            'remove_contact': ('Contact', kwargs.get('name', '*')),
            'update_contact': ('Contact', kwargs.get('name', '*')),
            'get_contact_info': ('Contact', kwargs.get('name', '*')),
            'get_names_by_relation': ('Contact', '*')
        }
        label, detail = api_to_granular_data.get(endpoint_name, ('Contact', '*'))
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
        end_time = start_time  # For contact operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, wildcard)
        
        return {
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
        }

class ContactManagerAPI:
    def __init__(self, policy_system):
        self.annotation = ContactManagerAPIAnnotation()
        self.policy_system = policy_system

    @ContactManagerAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @ContactManagerAPIAnnotation.annotate
    def add_contact(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="add_contact: add a new contact with the given details like name, phone, address, email, relation, birthday, and notes",
            **kwargs
        )

    @ContactManagerAPIAnnotation.annotate
    def remove_contact(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="remove_contact: remove the contact with the given name",
            **kwargs
        )

    @ContactManagerAPIAnnotation.annotate
    def update_contact(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="update_contact: update the contact information with the given details",
            **kwargs
        )

    @ContactManagerAPIAnnotation.annotate
    def get_contact_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_contact_info: get all the contact information for the given name like phone, address, email, relation, birthday, and notes",
            **kwargs
        )

    @ContactManagerAPIAnnotation.annotate
    def get_names_by_relation(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_names_by_relation: get names of persons with the given relation, for example, 'spouse', 'child', 'parent', etc.",
            **kwargs
        )

class ContactManagerAgent(BaseAgent):
    """Contact Manager agent for managing contacts"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the contact manager agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a contact manager agent.

        The name of the user is Ron Swanson whose information is already stored in the contact manager.

        The tool `contact_get_contact_info` takes name as an argument and returns all the contact information, including phone, address, email, relation, birthday, and notes for the given name.

        The tool `contact_get_names_by_relation` takes relation as an argument and returns the names of all the contacts with the given relation.

        The tool `contact_add_contact` takes name, phone, address, email, relation, birthday, and notes as arguments and adds a new contact with the given details. If some non-essential information is not available, you can use empty string as the value for that argument.

        The tool `contact_remove_contact` takes name as an argument and removes the contact with the given name.

        The tool `contact_update_contact` takes name, phone, address, email, relation, birthday, and notes as arguments and updates the contact information with the given details. If some non-essential information is not available, you can use empty string as the value for that argument.

        use `web_input_func` tool to ask the user for input and clarify the information if needed.

        Return "done" when your work is completed.
        """
        
        policy_system.register_api(ContactManagerAPI)
        self.contact_manager_api = ContactManagerAPI(policy_system)
        
        tools = [
            self.contact_add_contact,
            self.contact_remove_contact,
            self.contact_update_contact,
            self.contact_get_contact_info,
            self.contact_get_names_by_relation,
            web_input_func
        ]
        
        super().__init__("ContactManager", system_message, tools, model_client)
        
    async def contact_add_contact(self, name: str, phone: str, address: str, email: str, relation: str, birthday: str = None, notes: str = None) -> str:
        """
        Add a contact
        
        Args:
            name: The name of the contact
            phone: The phone number of the contact
            address: The address of the contact
            email: The email of the contact
            relation: The relation of the contact
            birthday: The birthday of the contact
            notes: Notes about the contact
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling ContactManagerAPI add_contact with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}")
        result = self.contact_manager_api.add_contact(name=name, phone=phone, address=address, email=email, relation=relation, birthday=birthday, notes=notes)
        return result
        
    async def contact_remove_contact(self, name: str) -> str:
        """
        Remove a contact
        
        Args:
            name: The name of the contact
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling ContactManagerAPI remove_contact with name={name}")
        result = self.contact_manager_api.remove_contact(name=name)
        return result
        
    async def contact_update_contact(self, name: str, phone: str = None, address: str = None, email: str = None, relation: str = None, birthday: str = None, notes: str = None) -> str:
        """
        Update a contact
        
        Args:
            name: The name of the contact
            phone: The phone number of the contact
            address: The address of the contact
            email: The email of the contact
            relation: The relation of the contact
            birthday: The birthday of the contact
            notes: Notes about the contact
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling ContactManagerAPI update_contact with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}")
        result = self.contact_manager_api.update_contact(name=name, phone=phone, address=address, email=email, relation=relation, birthday=birthday, notes=notes)
        return result
        
    async def contact_get_contact_info(self, name: str) -> str:
        """
        Get contact information
        
        Args:
            name: The name of the contact
            
        Returns:
            The contact information
        """
        logger.info(f"Calling ContactManagerAPI get_contact_info with name={name}")
        result = self.contact_manager_api.get_contact_info(name=name)
        return result
        
    async def contact_get_names_by_relation(self, relation: str) -> str:
        """
        Get names of contacts by relation
        
        Args:
            relation: The relation to filter by
            
        Returns:
            The names of contacts with the given relation
        """
        logger.info(f"Calling ContactManagerAPI get_names_by_relation with relation={relation}")
        result = self.contact_manager_api.get_names_by_relation(relation=relation)
        return result 