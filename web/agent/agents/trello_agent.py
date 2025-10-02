import logging
import os
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree
from config import WILDCARD
from typing import Annotated
import requests, dotenv

dotenv.load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# --- TrelloWrapper Helper Class ---
class TrelloWrapper:
    BASE_URL = "https://api.trello.com/1"

    def __init__(self):
        self.api_key = os.getenv('TRELLO_API_KEY')
        self.token = os.getenv('TRELLO_TOKEN')
        self.auth_params = {'key': self.api_key, 'token': self.token}

    def _get(self, endpoint, params=None):
        if params is None:
            params = {}
        all_params = {**self.auth_params, **params}
        response = requests.get(f"{self.BASE_URL}{endpoint}", params=all_params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint, data=None):
        if data is None:
            data = {}
        all_data = {**self.auth_params, **data}
        response = requests.post(f"{self.BASE_URL}{endpoint}", json=all_data)
        response.raise_for_status()
        return response.json()

    def _put(self, endpoint, data=None):
        if data is None:
            data = {}
        all_data = {**self.auth_params, **data}
        response = requests.put(f"{self.BASE_URL}{endpoint}", json=all_data)
        response.raise_for_status()
        return response.json()

    def _delete(self, endpoint):
        response = requests.delete(f"{self.BASE_URL}{endpoint}", params=self.auth_params)
        response.raise_for_status()
        return response.json()

    def _get_workspace_id(self, workspace_name):
        workspaces = self.list_workspaces(return_full_object=True)
        for ws in workspaces:
            if ws['displayName'] == workspace_name:
                return ws['id']
        raise ValueError(f"Workspace '{workspace_name}' not found.")

    def _get_board_id(self, board_name):
        all_boards = self._get("/members/me/boards")
        for board in all_boards:
            if board['name'] == board_name:
                return board['id']
        raise ValueError(f"Board '{board_name}' not found.")

    def _get_list_id(self, board_id, list_name):
        lists = self._get(f"/boards/{board_id}/lists")
        for trello_list in lists:
            if trello_list['name'] == list_name:
                return trello_list['id']
        raise ValueError(f"List '{list_name}' not found on the specified board.")

    def _get_card_id(self, list_id, card_name):
        cards = self._get(f"/lists/{list_id}/cards")
        for card in cards:
            if card['name'] == card_name:
                return card['id']
        raise ValueError(f"Card '{card_name}' not found in the specified list.")

    def list_workspaces(self, return_full_object=False):
        workspaces = self._get("/members/me/organizations")
        if return_full_object:
            return workspaces
        return [ws['displayName'] for ws in workspaces]

    def list_boards(self, workspace_name):
        workspace_id = self._get_workspace_id(workspace_name)
        boards = self._get(f"/organizations/{workspace_id}/boards")
        return [board['name'] for board in boards]

    def create_board(self, workspace_name, board_name):
        workspace_id = self._get_workspace_id(workspace_name)
        return self._post("/boards/", {'name': board_name, 'idOrganization': workspace_id})

    def delete_board(self, board_name):
        board_id = self._get_board_id(board_name)
        return self._delete(f"/boards/{board_id}")

    def list_lists(self, board_name):
        board_id = self._get_board_id(board_name)
        lists = self._get(f"/boards/{board_id}/lists")
        return [trello_list['name'] for trello_list in lists]

    def create_list(self, board_name, list_name):
        board_id = self._get_board_id(board_name)
        return self._post("/lists", {'name': list_name, 'idBoard': board_id})

    def archive_list(self, board_name, list_name):
        board_id = self._get_board_id(board_name)
        list_id = self._get_list_id(board_id, list_name)
        return self._put(f"/lists/{list_id}/closed", {'value': True})

    def list_cards(self, board_name, list_name):
        board_id = self._get_board_id(board_name)
        list_id = self._get_list_id(board_id, list_name)
        cards = self._get(f"/lists/{list_id}/cards")
        return [card['name'] for card in cards]

    def add_card(self, board_name, list_name, card_name, desc=""):
        board_id = self._get_board_id(board_name)
        list_id = self._get_list_id(board_id, list_name)
        return self._post("/cards", {'idList': list_id, 'name': card_name, 'desc': desc})

    def archive_card(self, board_name, list_name, card_name):
        board_id = self._get_board_id(board_name)
        list_id = self._get_list_id(board_id, list_name)
        card_id = self._get_card_id(list_id, card_name)
        return self._put(f"/cards/{card_id}", {'closed': True})

    def mark_card_as_complete(self, board_name, list_name, card_name):
        board_id = self._get_board_id(board_name)
        list_id = self._get_list_id(board_id, list_name)
        card_id = self._get_card_id(list_id, card_name)
        return self._put(f"/cards/{card_id}", {'dueComplete': True})

# --- TrelloAPIAnnotation (already present, unchanged except for generate_attributes) ---
class TrelloAPIAnnotation(APIAnnotationBase):
    def __init__(self):
    workspace = ResourceTypeTree.create_resource('Trello:Workspace', description='The workspace of the trello', examples=['Acme Corporation', 'Marketing Team', 'Q4 Product Launch', 'Personal Life'])
    board = ResourceTypeTree.create_resource('Trello:Board', parent=workspace, description='The board of the trello', examples=['Project Management', 'Company Overview', 'Backlog', 'Marketing Overview', 'Vacation Planning'])
    list_node = ResourceTypeTree.create_resource('Trello:List', parent=board, description='The list of the trello', examples=['To Do', 'In Progress', 'Done', 'Code Review','Ideas'])
    card = ResourceTypeTree.create_resource('Trello:Card', parent=list_node, description='The card of the trello', examples=['Implement new feature', 'Fix bug', 'Write documentation', 'Create new project', 'Search flight tickets', 'Book hotel'])

        super().__init__(
            "Trello",
            [workspace],
            [ResourceTypeTree('Read'), ResourceTypeTree('Write'), ResourceTypeTree('Create')]
        )

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        # Simple mapping for demonstration; can be made more granular
        workspace = kwargs.get('workspace_name', '*')
        board = kwargs.get('board_name', '*')
        list_ = kwargs.get('list_name', '*')
        card = kwargs.get('card_name', '*')
        if wildcard:
            workspace = board = list_ = card = '*'
        if endpoint_name in ['list_workspaces', 'create_board', 'list_boards']:
            granular_data = f"Trello:Workspace({workspace})"
        elif endpoint_name in ['delete_board', 'list_lists', 'create_list']:
            granular_data = f"Trello:Workspace(?)::Trello:Board({board})"
        elif endpoint_name in ['list_cards', 'archive_list']:
            granular_data = f"Trello:Workspace(?)::Trello:Board({board})::Trello:List({list_})"
        elif endpoint_name in ['add_card', 'archive_card', 'mark_card_as_complete']:
            granular_data = f"Trello:Workspace(?)::Trello:Board({board})::Trello:List({list_})::Trello:Card({card})"
        else:
            granular_data = f"Trello:Workspace({workspace})::Trello:Board({board})::Trello:List({list_})::Trello:Card({card})"
        if endpoint_name.startswith('create') or endpoint_name.startswith('add'):
            data_access = 'Create'
        elif endpoint_name.startswith('archive') or endpoint_name.startswith('delete') or endpoint_name.startswith('mark'):
            data_access = 'Write'
        else:
            data_access = 'Read'
        
        # Return a list containing the single attribute object for now
        # This maintains backward compatibility while allowing for future expansion
        return [{
            'granular_data': granular_data,
            'data_access': data_access
        }]

# --- TrelloAPI Class ---
class TrelloAPI:
    def __init__(self, policy_system):
        self.annotation = TrelloAPIAnnotation()
        self.policy_system = policy_system
        self.wrapper = TrelloWrapper()

    @TrelloAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @TrelloAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @TrelloAPIAnnotation.annotate
    def list_workspaces(self, **kwargs):
        return self.wrapper.list_workspaces()

    @TrelloAPIAnnotation.annotate
    def list_boards(self, **kwargs):
        workspace_name = kwargs['workspace_name']
        return self.wrapper.list_boards(workspace_name)

    @TrelloAPIAnnotation.annotate
    def create_board(self, **kwargs):
        workspace_name = kwargs['workspace_name']
        board_name = kwargs['board_name']
        return self.wrapper.create_board(workspace_name, board_name)

    @TrelloAPIAnnotation.annotate
    def delete_board(self, **kwargs):
        board_name = kwargs['board_name']
        return self.wrapper.delete_board(board_name)

    @TrelloAPIAnnotation.annotate
    def list_lists(self, **kwargs):
        board_name = kwargs['board_name']
        return self.wrapper.list_lists(board_name)

    @TrelloAPIAnnotation.annotate
    def create_list(self, **kwargs):
        board_name = kwargs['board_name']
        list_name = kwargs['list_name']
        return self.wrapper.create_list(board_name, list_name)

    @TrelloAPIAnnotation.annotate
    def archive_list(self, **kwargs):
        board_name = kwargs['board_name']
        list_name = kwargs['list_name']
        return self.wrapper.archive_list(board_name, list_name)

    @TrelloAPIAnnotation.annotate
    def list_cards(self, **kwargs):
        board_name = kwargs['board_name']
        list_name = kwargs['list_name']
        return self.wrapper.list_cards(board_name, list_name)

    @TrelloAPIAnnotation.annotate
    def add_card(self, **kwargs):
        board_name = kwargs['board_name']
        list_name = kwargs['list_name']
        card_name = kwargs['card_name']
        desc = kwargs.get('desc', "")
        return self.wrapper.add_card(board_name, list_name, card_name, desc)

    @TrelloAPIAnnotation.annotate
    def archive_card(self, **kwargs):
        board_name = kwargs['board_name']
        list_name = kwargs['list_name']
        card_name = kwargs['card_name']
        return self.wrapper.archive_card(board_name, list_name, card_name)

    @TrelloAPIAnnotation.annotate
    def mark_card_as_complete(self, **kwargs):
        board_name = kwargs['board_name']
        list_name = kwargs['list_name']
        card_name = kwargs['card_name']
        return self.wrapper.mark_card_as_complete(board_name, list_name, card_name)

# --- TrelloAgent Class ---
class TrelloAgent(BaseAgent):
    def __init__(self, model_client, policy_system):
        system_message = """
        You are a Trello agent.
        Output 'done' when the task given to you is completed. Do not suggest any other actions to the user.
        In Trello, a workspace is a collection of boards. A board is a collection of lists. A list is a collection of cards.
        If you are given a task which is not related to Trello, also return 'done'.
        You already have API access to Trello. If you are not able to access the API it will be always be because of the lack of permissions and never because of lack of credentials.
        You can only access the API if you have the correct permissions.
        """
        policy_system.register_api(TrelloAPI)
        self.trello_api = TrelloAPI(policy_system)
        tools = [
            self.trello_list_workspaces,
            self.trello_list_boards,
            self.trello_create_board,
            self.trello_delete_board,
            self.trello_list_lists,
            self.trello_create_list,
            self.trello_archive_list,
            self.trello_list_cards,
            self.trello_add_card,
            self.trello_archive_card,
            self.trello_mark_card_as_complete,
            get_user_input
        ]
        super().__init__("Trello", system_message, tools, model_client)

    async def trello_list_workspaces(self) -> str:
        return self.trello_api.list_workspaces()

    async def trello_list_boards(self, workspace_name: Annotated[str, "The workspace name"]) -> str:
        return self.trello_api.list_boards(workspace_name=workspace_name)

    async def trello_create_board(self, workspace_name: Annotated[str, "The workspace name"], board_name: Annotated[str, "The board name"]) -> str:
        return self.trello_api.create_board(workspace_name=workspace_name, board_name=board_name)

    async def trello_delete_board(self, board_name: Annotated[str, "The board name"]) -> str:
        return self.trello_api.delete_board(board_name=board_name)

    async def trello_list_lists(self, board_name: Annotated[str, "The board name"]) -> str:
        return self.trello_api.list_lists(board_name=board_name)

    async def trello_create_list(self, board_name: Annotated[str, "The board name"], list_name: Annotated[str, "The list name"]) -> str:
        return self.trello_api.create_list(board_name=board_name, list_name=list_name)

    async def trello_archive_list(self, board_name: Annotated[str, "The board name"], list_name: Annotated[str, "The list name"]) -> str:
        return self.trello_api.archive_list(board_name=board_name, list_name=list_name)

    async def trello_list_cards(self, board_name: Annotated[str, "The board name"], list_name: Annotated[str, "The list name"]) -> str:
        return self.trello_api.list_cards(board_name=board_name, list_name=list_name)

    async def trello_add_card(self, board_name: Annotated[str, "The board name"], list_name: Annotated[str, "The list name"], card_name: Annotated[str, "The card name"], desc: Annotated[str, "The card description"] = "") -> str:
        return self.trello_api.add_card(board_name=board_name, list_name=list_name, card_name=card_name, desc=desc)

    async def trello_archive_card(self, board_name: Annotated[str, "The board name"], list_name: Annotated[str, "The list name"], card_name: Annotated[str, "The card name"]) -> str:
        return self.trello_api.archive_card(board_name=board_name, list_name=list_name, card_name=card_name)

    async def trello_mark_card_as_complete(self, board_name: Annotated[str, "The board name"], list_name: Annotated[str, "The list name"], card_name: Annotated[str, "The card name"]) -> str:
        return self.trello_api.mark_card_as_complete(board_name=board_name, list_name=list_name, card_name=card_name) 