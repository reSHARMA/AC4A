from datetime import datetime
from src.utils.attribute_tree import AttributeTree

class PolicySystem:
    def __init__(self):
        self.policy_rules = []
        self.attribute_definitions = {}

    def register_api(self, api_class):
        # Pass the current instance of policy_system to the CalendarAPI constructor
        api_instance = api_class(self)
        # Define the list of allowed attributes
        allowed_attributes = ['granular_data', 'actions', 'data_access', 'time']

        # Extract attribute definitions from the API instance
        if hasattr(api_instance, 'get_attributes'):
            attributes = api_instance.get_attributes()
            for attr_type, values in attributes.items():
                if attr_type in allowed_attributes:
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
                else:
                    print(f"Warning: Attribute '{attr_type}' is not allowed and will be ignored.")

    def add_policy(self, policy_rule):
        # Calculate and store fixed times for symbolic expressions
        for attr, value in policy_rule.items():
            if callable(value):
                policy_rule[attr] = value()
        self.policy_rules.append(policy_rule)

    def is_action_allowed(self, attributes):
        for rule in self.policy_rules:
            if self.check_subsumption(rule, attributes):
                return True
        return False

    def check_subsumption(self, rule, attributes):
        for attr in rule:
            rule_value = rule[attr]

            # Handle expiry datetime objects separately
            if attr == 'expiry':
                # Compare datetime values directly
                if datetime.now() >= rule_value:
                    return False
                continue

            attribute_value = attributes.get(attr)
            # Handle time attribute with Past, Present, Future
            if attr == 'time':
                if rule_value != attribute_value and rule_value != '*':
                    return False
                continue

            # Split the resource type and value for comparison
            if ':' in rule_value:
                rule_resource, rule_specific = rule_value.split(':')
                attr_resource, attr_specific = attribute_value.split(':')

                # Check for namespace match or wildcard
                if rule_resource != attr_resource and rule_resource != '*':
                    return False

                # Check for specific match or wildcard
                if rule_specific != attr_specific and rule_specific != '*':
                    return False

            if not self.validate_attribute(rule_value, attribute_value, attr):
                return False
        return True

    def validate_attribute(self, rule_value, attribute_value, attribute_type):
        if attribute_type in self.attribute_definitions:
            hierarchy = self.attribute_definitions[attribute_type]
            if isinstance(hierarchy[0], AttributeTree):
                # Hierarchical structure, convert to flat list and check subsumption
                values_list = hierarchy[0].to_list()
                
                namespace = values_list[0].split(':')[0]
                if rule_value == f'{namespace}:*' and attribute_value.startswith(namespace):
                    return True

                return values_list.index(rule_value) <= values_list.index(attribute_value)
            elif isinstance(hierarchy, list):
                # Disjoint sets, must match exactly
                return rule_value == attribute_value or rule_value == '*'
        return False

    def export_attributes(self):
        return self.attribute_definitions