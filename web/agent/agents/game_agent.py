import logging
from datetime import datetime
from .base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from config import WILDCARD
from typing import Annotated
import requests

# Set up logging
logger = logging.getLogger(__name__)

class GameAPIAnnotation(APIAnnotationBase):
    attributes_schema = {
        'Game:GameId': {
            'description': 'The id of the game',
            'examples': ['1', '2', '3']
        },
    }
    def __init__(self):
        super().__init__("Game", {
            'granular_data': [
                AttributeTree(f'Game:GameId')
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
        }, self.attributes_schema)

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'get_games': ('Game', '*'),
            'get_game': ('Game', kwargs.get('game_id', '*')),
            'delete_game': ('Game', kwargs.get('game_id', '*')),
        }
        label, detail = api_to_granular_data.get(endpoint_name, ('Game', '*'))
        if use_wildcard:
            return f"{self.namespace}:{label}(*)"
        else:
            return f"{self.namespace}:{label}({detail})"

    def get_access_level(self, endpoint_name):
        if 'delete' in endpoint_name:
            return 'Write'
        elif 'create' in endpoint_name or 'add' in endpoint_name:
            return 'Create'
        else:
            return 'Read'

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        return [{
            'granular_data': granular_data,
            'data_access': data_access
        }]

class GameAPI:
    def __init__(self, policy_system):
        self.annotation = GameAPIAnnotation()
        self.policy_system = policy_system

    @GameAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @GameAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @GameAPIAnnotation.annotate
    def get_games(self, *args, **kwargs):
        response = requests.get('http://127.0.0.1:5000/games')
        return response.json()

    @GameAPIAnnotation.annotate
    def get_game(self, *args, **kwargs):
        game_id = kwargs.get('game_id')
        response = requests.get(f'http://127.0.0.1:5000/games/{game_id}')
        return response.json()

    @GameAPIAnnotation.annotate
    def delete_game(self, *args, **kwargs):
        game_id = kwargs.get('game_id')
        response = requests.delete(f'http://127.0.0.1:5000/games/{game_id}')
        return response.json()

class GameAgent(BaseAgent):
    """Game agent for managing game operations"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the game agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a game agent. Use the tools provided to you to complete the task given to you. Start with reasoning about the task and then use the tools to complete the task.
        """
        
        policy_system.register_api(GameAPI)
        self.game_api = GameAPI(policy_system)
        
        tools = [
            self.game_get_games,
            self.game_get_game,
            self.game_delete_game,
            get_user_input
        ]
        
        super().__init__("Game", system_message, tools, model_client)
        
    async def game_get_games(self) -> str:
        """Get all the games"""
        logger.info(f"Calling GameAPI get_games")
        result = self.game_api.get_games()
        return result
        
    async def game_get_game(self, game_id: Annotated[str, "The id of the game, example '1'"] = None) -> str:
        """Get the game with the given game id"""
        logger.info(f"Calling GameAPI get_game with game_id={game_id}")
        result = self.game_api.get_game(game_id=game_id)
        return result
        
    async def game_delete_game(self, game_id: Annotated[str, "The id of the game, example '1'"] = None) -> str:
        """Delete the game with the given game id"""
        logger.info(f"Calling GameAPI delete_game with game_id={game_id}")
        result = self.game_api.delete_game(game_id=game_id)
        return result