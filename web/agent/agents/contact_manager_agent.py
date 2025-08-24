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

class ContactManagerAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        attributes_schema = {
            'ContactManager:Contact': {
                'description': 'The name of the contact, must be the name of the person',
                'examples': ['Ron Swanson', 'Leslie Knope', 'Tom Haverford']
            },
            'ContactManager:ContactPhone': {
                'description': 'The phone number of the contact, must be a 10 digit number',
                'examples': ['2061234567', '7321234567']
            },
            'ContactManager:ContactAddress': {
                'description': 'The address of the contact, must be a valid address',
                'examples': ['123 Main St, Anytown, USA', '123 Main St, Anytown, USA']
            },
            'ContactManager:ContactEmail': {
                'description': 'The email of the contact, must be a valid email address',
                'examples': ['ron@swanson.com', 'leslie@knope.com', 'tom@haverford.com']
            },
            'ContactManager:ContactRelation': {
                'description': 'The relation of the contact, must be a valid relation with the user',
                'examples': ['spouse', 'child', 'parent', 'friend', 'business partner', 'other']
            },
            'ContactManager:ContactBirthday': {
                'description': 'The birthday of the contact, must be in the format YYYY-MM-DD',
                'examples': ['1980-01-01', '1980-01-01']
            },
            'ContactManager:ContactNotes': {
                'description': 'The notes of the contact, must be a valid note',
                'examples': ['Ron is a great boss', 'Leslie is a great friend', 'Tom is a great business partner']
            }
        }
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
                AttributeTree('Write'),
                AttributeTree('Create')
            ],
            'position': [
                AttributeTree('Previous', [AttributeTree('Current')]),
                AttributeTree('Next', [AttributeTree('Current')])
            ]
        }, attributes_schema)

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
        if 'add' in endpoint_name:
            return 'Create'
        elif 'remove' in endpoint_name or 'update' in endpoint_name:
            return 'Write'
        else:
            return 'Read'

    def get_time_period(self, start_time, end_time, use_wildcard):
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        start_time = datetime.now()
        end_time = start_time  # For contact operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, wildcard)
        
        return [{
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
        }]

class ContactManagerAPI:
    def __init__(self, policy_system):
        self.annotation = ContactManagerAPIAnnotation()
        self.policy_system = policy_system

    @ContactManagerAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @ContactManagerAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

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
        system_message = """You are a contact manager agent. The name of the user who is interacting with you is Ron Swanson and its Ron's contacts you are managing. Return "done" when your work is completed."""
        
        policy_system.register_api(ContactManagerAPI)
        self.contact_manager_api = ContactManagerAPI(policy_system)
        
        tools = [
            self.contact_add_contact,
            self.contact_remove_contact,
            self.contact_update_contact,
            self.contact_get_contact_info,
            self.contact_get_names_by_relation,
            get_user_input
        ]
        
        super().__init__("ContactManager", system_message, tools, model_client)
        
    async def contact_add_contact(self, name: Annotated[str, "The name of the contact, must be the name of the person"], phone: Annotated[str, "The phone number of the contact, must be a 10 digit number"], address: Annotated[str, "The address of the contact, can be empty"], email: Annotated[str, "The email of the contact, can be empty"], relation: Annotated[str, "The relation of the contact with the user, can be 'spouse', 'child', 'parent', 'friend', 'business partner', 'other' etc. or empty"], birthday: Annotated[str, "The birthday of the contact (YYYY-MM-DD) or empty"], notes: Annotated[str, "The notes about the contact, can be empty"]) -> str:
        """Add a new contact with the given details. The name and phone are required, rest all are optional."""
        logger.info(f"Calling ContactManagerAPI add_contact with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}")
        result = self.contact_manager_api.add_contact(name=name, phone=phone, address=address, email=email, relation=relation, birthday=birthday, notes=notes)
        return result
        
    async def contact_remove_contact(self, name: Annotated[str, "The name of the contact, must be the name of the person"]) -> str:
        """Remove the contact with the given name."""
        logger.info(f"Calling ContactManagerAPI remove_contact with name={name}")
        result = self.contact_manager_api.remove_contact(name=name)
        return result
        
    async def contact_update_contact(self, name: Annotated[str, "The name of the contact, must be the name of the person"], phone: Annotated[str, "The phone number of the contact, can also be empty"], address: Annotated[str, "The address of the contact, can also be empty"], email: Annotated[str, "The email of the contact, can also be empty"], relation: Annotated[str, "The relation of the contact, can also be empty"], birthday: Annotated[str, "The birthday of the contact, can also be empty"], notes: Annotated[str, "The notes of the contact, can also be empty"]) -> str:
        """Update the contact information with the given details. The name is required and rest all are optional. The data which needs to be updated must have a non-empty value. If you just want to update one field, use empty string for the rest."""
        logger.info(f"Calling ContactManagerAPI update_contact with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}")
        result = self.contact_manager_api.update_contact(name=name, phone=phone, address=address, email=email, relation=relation, birthday=birthday, notes=notes)
        return result
        
    async def contact_get_contact_info(self, name: Annotated[str, "The name of the contact, must be the name of the person"]) -> str:
        """Get the contact information for the given name including phone, address, email, relation, birthday, and notes."""
        logger.info(f"Calling ContactManagerAPI get_contact_info with name={name}")
        result = self.contact_manager_api.get_contact_info(name=name)
        return result
        
    async def contact_get_names_by_relation(self, relation: Annotated[str, "The relation of the contact, can be 'spouse', 'child', 'parent', 'friend', 'business partner', 'other' etc."]) -> str:
        """Get the names of the contacts with the given relation. For example, if the relation is 'co-worker', you should return the names of all the contacts with the relation 'co-worker'."""
        logger.info(f"Calling ContactManagerAPI get_names_by_relation with relation={relation}")
        result = self.contact_manager_api.get_names_by_relation(relation=relation)
        return result 