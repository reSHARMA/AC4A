import logging
from datetime import timedelta
from typing import Annotated

from ..base_agent import BaseAgent
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree


logger = logging.getLogger(__name__)


class ExampleAPIAnnotation(APIAnnotationBase):
    """Minimal resource definition following the policy annotation pattern.

    Defines a single resource hierarchy `Example:Item` and basic data access levels.
    """

    def __init__(self):
    item = ResourceTypeTree.create_resource(
            'Example:Item',
            description='A generic example resource item',
            examples=['WidgetA', 'WidgetB']
        )

        super().__init__(
            "Example",
            [item],
            [ResourceTypeTree('Read')]
        )

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        name = kwargs.get('name', '*')
        if wildcard:
            name = '*'
        # Map endpoint name to access level
        data_access = 'Read'
        return [{
            'granular_data': f"Example:Item({name})",
            'data_access': data_access
        }]


class ExampleAPI:
    """Minimal API with one annotated endpoint and attribute exports."""

    def __init__(self, policy_system):
        self.annotation = ExampleAPIAnnotation()
        self.policy_system = policy_system

    def resource_difference(self, needs, have):
        """
        Application-provided hook used by the policy system.
        Returns the difference between required (needs) and provided (have) resources.
        Empty/falsey => subsumption holds. Here we default to empty to allow all.
        """
        return {}

    @ExampleAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @ExampleAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @ExampleAPIAnnotation.annotate
    def read_item(self, **kwargs):
        name = kwargs.get('name', 'unknown')
        return {"message": f"read_item called for {name}"}


class TemplateAgent(BaseAgent):
    """Minimal example agent template with one resource and one tool."""

    def __init__(self, model_client, policy_system):
        system_message = (
            "You are an example agent. Replace this with your agent's instructions."
        )
        policy_system.register_api(ExampleAPI)
        self.example_api = ExampleAPI(policy_system)

        tools = [
            self.example_read_item,
        ]
        super().__init__("Template", system_message, tools, model_client)

    async def example_read_item(self, name: Annotated[str, "The example item name"]) -> str:
        """Read an example item by name (demonstrates one resource access)."""
        result = self.example_api.read_item(name=name)
        return result