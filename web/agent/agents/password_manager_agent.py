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

class PasswordManagerAPIAnnotation(APIAnnotationBase):
    attributes_schema = {
        'PasswordManager:ServiceName': {
            'description': 'The identifier for the given website or service',
            'examples': ['gmail', 'facebook', 'twitter']
        },
        'PasswordManager:UserName': {
            'description': 'The identifier for the given user name',
            'examples': ['xyz@gmail.com', 'user123', '@Ron']
        } 
    }
    def __init__(self):
        super().__init__("PasswordManager", {
            'granular_data': [
                AttributeTree('PasswordManager:ServiceName', [AttributeTree('PasswordManager:UserName')])
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
            'add_password': f'{self.namespace}:ServiceName({kwargs.get("service_name", "*")})::{self.namespace}:UserName({kwargs.get("user_name", "*")})',
            'remove_password': f'{self.namespace}:ServiceName({kwargs.get("service_name", "*")})::{self.namespace}:UserName({kwargs.get("user_name", "*")})',
            'update_password': f'{self.namespace}:ServiceName({kwargs.get("service_name", "*")})::{self.namespace}:UserName({kwargs.get("user_name", "*")})',
            'get_password': f'{self.namespace}:ServiceName({kwargs.get("service_name", "*")})::{self.namespace}:UserName({kwargs.get("user_name", "*")})',
            'list_all_saved_password_services': f'{self.namespace}:ServiceName(*)',
            'list_all_saved_password_users': f'{self.namespace}:ServiceName({kwargs.get("service_name", "*")})::{self.namespace}:UserName(*)'
        }
        data = api_to_granular_data.get(endpoint_name, (f'{self.namespace}:ServiceName(*)'))
        return data

    def get_access_level(self, endpoint_name):
        return 'Write' if 'add' in endpoint_name or 'remove' in endpoint_name or 'update' in endpoint_name else 'Read'

    def get_time_period(self, start_time, end_time, use_wildcard):
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        start_time = datetime.now()
        end_time = start_time  # For password manager operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, wildcard)
        
        return {
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
        }

class PasswordManagerAPI:
    def __init__(self, policy_system):
        self.annotation = PasswordManagerAPIAnnotation()
        self.policy_system = policy_system

    @PasswordManagerAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @PasswordManagerAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @PasswordManagerAPIAnnotation.annotate
    def add_password(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="add_password: add a new password with the given service name and user name",
            **kwargs
        )

    @PasswordManagerAPIAnnotation.annotate
    def remove_password(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="remove_password: remove the password with the given service name and user name",
            **kwargs
        )

    @PasswordManagerAPIAnnotation.annotate
    def update_password(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="update_password: update the password with the given service name and user name",
            **kwargs
        )

    @PasswordManagerAPIAnnotation.annotate
    def get_password(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_password: get the password for the given service name and user name",
            **kwargs
        )

    @PasswordManagerAPIAnnotation.annotate
    def list_all_saved_password_services(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="list_all_saved_password_services: get all the saved password services",
            **kwargs
        )

    @PasswordManagerAPIAnnotation.annotate
    def list_all_saved_password_users(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="list_all_saved_password_users: get all the saved password users for the given service name",
            **kwargs
        )

class PasswordManagerAgent(BaseAgent):
    """Password manager agent for managing password operations"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the password manager agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a password manager agent, you manage the passwords stored by the user. The user can ask you for the password for a specific website or service (e.g. gmail, facebook, twitter, etc. as service name) and each website or service can have multiple user names (e.g. xyz@gmail.com, user123, @Ron, etc. as user name). Use the tools provided to you to complete the task given to you. Start with reasoning about the task and then use the tools to complete the task.

        List of tools available to you
        [
            list_all_saved_password_services,
            list_all_saved_password_users,
            get_password,
            add_password,
            remove_password,
            update_password
        ]
        
        ## Description of the tools available to you

        Use the tool `list_all_saved_password_services` to get all the saved password services. This tool returns a list of all the saved password services and does not take any parameters. Example output: ["gmail", "facebook", "twitter"].
        Should be used ONLY when you need to see all available services that have saved passwords.

        Use the tool `list_all_saved_password_users` to get all the saved password users for the given service name. The tool takes the following parameters:
        - service_name: The name of the service to get the password for, example "gmail".
        and returns a list of all the saved password users for the given service name. Example output: ["xyz@gmail.com", "user123", "@Ron"].
        Should be used when you need to see all users that have saved passwords for a specific service. If you have a specific service name, always use this tool directly instead of listing all services.

        Use the tool `get_password` to get the password for the given service name and user name. The tool takes the following parameters:
        - service_name: The name of the service to get the password for, example "gmail".
        - user_name: The name of the user to get the password for, example "xyz@gmail.com".
        and returns the password for the given service name and user name. 
        Should be used when you need to get the password for a specific service and user.

        Use the tool `add_password` to add a password to the password manager. The tool takes the following parameters:
        - service_name: The name of the service to add the password for, example "gmail".
        - user_name: The name of the user to add the password for, example "xyz@gmail.com".
        - password: The password to add, example "1234567890".
        Should be used when you need to add a password for a specific service and user.

        Use the tool `remove_password` to remove a password from the password manager. The tool takes the following parameters:
        - service_name: The name of the service to remove the password for, example "gmail".
        - user_name: The name of the user to remove the password for, example "xyz@gmail.com".
        Should be used when you need to remove a password for a specific service and user.

        Use the tool `update_password` to update a password in the password manager. The tool takes the following parameters:
        - service_name: The name of the service to update the password for, example "gmail".
        - user_name: The name of the user to update the password for, example "xyz@gmail.com".
        - password: The password to update, example "1234567890".
        Should be used when you need to update a password for a specific service and user.

        Carefully pick the tool to use based on the user request and you can use multiple tools if needed. If you have a specific service name, use the appropriate tool directly instead of listing all services first.

        Return "done" when you have completed your work.
        """
        
        policy_system.register_api(PasswordManagerAPI)
        self.password_manager_api = PasswordManagerAPI(policy_system)
        
        tools = [
            self.password_manager_list_all_saved_password_services,
            self.password_manager_list_all_saved_password_users,
            self.password_manager_get_password,
            self.password_manager_add_password,
            self.password_manager_remove_password,
            self.password_manager_update_password,
            web_input_func
        ]
        
        super().__init__("PasswordManager", system_message, tools, model_client)
        
    async def password_manager_list_all_saved_password_services(self) -> str:
        """
        Get all the saved password services

        Args:
            None
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling PasswordManagerAPI list_all_saved_password_services")
        result = self.password_manager_api.list_all_saved_password_services()
        return result
        
    async def password_manager_list_all_saved_password_users(self, service_name: str) -> str:
        """
        Get all the saved password users for the given service name
        
        Args:
            service_name: The name of the service to get the password for, example "gmail".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling PasswordManagerAPI list_all_saved_password_users with service_name={service_name}")
        result = self.password_manager_api.list_all_saved_password_users(service_name=service_name)
        return result
        
    async def password_manager_add_password(self, service_name: str, user_name: str, password: str) -> str:
        """
        Add a password to the password manager
        
        Args:
            service_name: The name of the service to add the password for, example "gmail".
            user_name: The name of the user to add the password for, example "xyz@gmail.com".
            password: The password to add, example "1234567890".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling PasswordManagerAPI add_password with service_name={service_name}, user_name={user_name}, password={password}")
        result = self.password_manager_api.add_password(service_name=service_name, user_name=user_name, password=password)
        return result
        
    async def password_manager_remove_password(self, service_name: str, user_name: str) -> str:
        """
        Remove a password from the password manager
        
        Args:
            service_name: The name of the service to remove the password for, example "gmail".
            user_name: The name of the user to remove the password for, example "xyz@gmail.com".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling PasswordManagerAPI remove_password with service_name={service_name}, user_name={user_name}")
        result = self.password_manager_api.remove_password(service_name=service_name, user_name=user_name)
        return result 

    async def password_manager_update_password(self, service_name: str, user_name: str, password: str) -> str:
        """
        Update a password in the password manager
        
        Args:
            service_name: The name of the service to update the password for, example "gmail".
            user_name: The name of the user to update the password for, example "xyz@gmail.com".
            password: The password to update, example "1234567890".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling PasswordManagerAPI update_password with service_name={service_name}, user_name={user_name}, password={password}")
        result = self.password_manager_api.update_password(service_name=service_name, user_name=user_name, password=password)
        return result   
    
    async def password_manager_get_password(self, service_name: str, user_name: str) -> str:
        """
        Get the password for the given service name and user name
        
        Args:
            service_name: The name of the service to get the password for, example "gmail".
            user_name: The name of the user to get the password for, example "xyz@gmail.com".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling PasswordManagerAPI get_password with service_name={service_name}, user_name={user_name}")
        result = self.password_manager_api.get_password(service_name=service_name, user_name=user_name)
        return result