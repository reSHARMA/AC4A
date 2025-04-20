import logging
from .base_agent import BaseAgent
from ..web_input import web_input_func
from web.mock_app import ContactManagerAPI

# Set up logging
logger = logging.getLogger(__name__)

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

        Use the tool `contact_get_names_by_relation` to get the names of all the contacts with the given relation and you may later use the `contact_get_contact_info` tool to get the information for the contact.

        `contact_get_contact_info` tool takes name as input and returns all the contact information, including phone, address, email, relation, birthday, and notes for the given name.

        use `get_user_input` tool to ask the user for user input.

        Return "done" when your work is completed.
        """
        
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