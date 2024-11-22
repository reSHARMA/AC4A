# Policy System class to manage policy rules and attribute definitions

class PolicySystem:
    def __init__(self):
        self.policy_rules = []
        self.attribute_definitions = {}

    def register_api(self, api_class):
        # Extract attribute definitions from the API class
        api_class = api_class()
        if hasattr(api_class, 'get_attributes'):
            attributes = api_class.get_attributes()
            for attr_type, values in attributes.items():
                if attr_type in self.attribute_definitions:
                    # Merge attributes without duplication
                    existing_values = self.attribute_definitions[attr_type]
                    if isinstance(values, list):
                        for value in values:
                            if isinstance(value, AttributeTree):
                                existing_values.append(value)
                            else:
                                if value not in existing_values:
                                    existing_values.append(value)
                else:
                    self.attribute_definitions[attr_type] = values

    def add_policy(self, policy_rule):
        self.policy_rules.append(policy_rule)

    def is_action_allowed(self, attributes):
        for rule in self.policy_rules:
            if self.check_subsumption(rule, attributes):
                return True
        return False

    def check_subsumption(self, rule, attributes):
        for attr in rule:
            if not self.validate_attribute(rule[attr], attributes.get(attr), attr):
                return False
        return True

    def validate_attribute(self, rule_value, attribute_value, attribute_type):
        if attribute_type in self.attribute_definitions:
            hierarchy = self.attribute_definitions[attribute_type]
            if isinstance(hierarchy[0], AttributeTree):
                # Hierarchical structure, convert to flat list and check subsumption
                values_list = hierarchy[0].to_list()
                return values_list.index(rule_value) <= values_list.index(attribute_value)
            elif isinstance(hierarchy, list):
                # Disjoint sets, must match exactly
                return rule_value == attribute_value
        return False

    def export_attributes(self):
        return self.attribute_definitions

def policy_interceptor(api_func):
    def wrapper(self, attributes, *args, **kwargs):
        if policy_system.is_action_allowed(attributes):
            return api_func(self, *args, **kwargs)
        else:
            raise PermissionError("Action not authorized for given resource.")
    wrapper.original_name = api_func.__name__
    return wrapper


