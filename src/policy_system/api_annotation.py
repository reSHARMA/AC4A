from src.utils.time_utils import TimeUtils
from src.policy_system.policy_system import PolicySystem
from config import WILDCARD
from web.utils.custom_logger import send_custom_log

class APIAnnotationBase:
    def __init__(self, namespace, granular_data_trees, data_access_trees, position_trees=None, attributes_schema=None):
        self.namespace = namespace
        # New three-list API
        self.attributes = {
            'granular_data': granular_data_trees or [],
            'data_access': data_access_trees or []
        }
        # Default position: Previous->Current, Next->Current
        if position_trees is None:
            from src.utils.resource_type_tree import ResourceTypeTree
            self.attributes['position'] = [
                ResourceTypeTree('Previous', [ResourceTypeTree('Current')]),
                ResourceTypeTree('Next', [ResourceTypeTree('Current')])
            ]
        else:
            self.attributes['position'] = position_trees

        # Build or accept schema
        if attributes_schema is not None:
            self.attributes_schema = attributes_schema
        else:
            # Derive schema from resource trees if metadata present
            derived = {}
            for tree_list_key in ['granular_data']:
                for tree in self.attributes.get(tree_list_key, []):
                    if hasattr(tree, 'collect_schema'):
                        derived.update(tree.collect_schema())
            self.attributes_schema = derived

    def export_attributes(self):
        return self.attributes

    def export_attributes_schema(self):
        return self.attributes_schema

    @staticmethod
    def annotate(endpoint_func):
        wildcard = WILDCARD
        def wrapper(self, *args, **kwargs):
            attributes = self.annotation.generate_attributes(kwargs, wrapper.original_name, wildcard)
            intercepted_func = policy_interceptor(endpoint_func)
            return intercepted_func(self, attributes, *args, **kwargs)

        wrapper.original_name = endpoint_func.__name__
        return wrapper

    def export(endpoint_func):
        def wrapper(self, *args, **kwargs):
            wrapper.attributes = self.annotation.export_attributes()
            return endpoint_func(self, *args, **kwargs)
        return wrapper

    def schema(endpoint_func):
        def wrapper(self, *args, **kwargs):
            wrapper.attributes_schema = self.annotation.export_attributes_schema()
            return endpoint_func(self, *args, **kwargs)
        return wrapper

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        raise NotImplementedError("Subclasses should implement this method.")

def policy_interceptor(api_func):
    def wrapper(self, attributes, *args, **kwargs):
        send_custom_log("Calling", f"{self.__class__.__name__}.{api_func.__name__} with {args} and {kwargs}")
        # Allow apps to optionally provide a resource_difference(needs, have) hook on the API instance
        resource_difference = getattr(self, 'resource_difference', None)
        if self.policy_system.is_action_allowed(attributes, resource_difference=resource_difference):
            return api_func(self, *args, **kwargs)
        else:
            raise PermissionError(f"Action not authorized for given resources.")
    wrapper.original_name = api_func.__name__
    return wrapper