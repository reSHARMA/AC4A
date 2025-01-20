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
        allowed_attributes = ['granular_data', 'data_access', 'position']

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
            print("\033[1;34;40mChecking rule:\033[0m", rule)
            if self.check_subsumption(rule, attributes):
                print("\033[1;32;40mAction is allowed based on rule:\033[0m", rule)
                return True
        print("\033[1;31;40mAction is not allowed based on current rules.\033[0m")
        return False

    def check_subsumption(self, rule, attributes):
        print("\033[1;34;40mChecking rule:\033[0m\n", rule)
        print("\033[1;34;40mFor attributes:\033[0m\n", attributes)

        for attr in rule:
            rule_value = rule[attr]

            if attr == 'expiry':
                # Compare datetime values directly
                if datetime.now() >= rule_value:
                    return False
                continue  

            print(f"Parsing rule value: {rule_value}")

            if rule_value == '*':
                continue

            def parse_rule_value(rule_value):
                parsed_values = []
                if "::" in rule_value:
                    parts = rule_value.split("::")
                    print(f"Split rule value into parts: {parts}")
                    for part in parts:
                        if "(" in part and ")" in part:
                            key, value = part.split("(")
                            value = value.rstrip(")")
                            parsed_values.append({key: value})
                            print(f"Parsed part with key-value: {key} - {value}")
                        else:
                            parsed_values.append({part: '*'})
                            print(f"Parsed part with wildcard: {part} - *")
                else:
                    if "(" in rule_value and ")" in rule_value:
                        key, value = rule_value.split("(")
                        value = value.rstrip(")")
                        parsed_values.append({key: value})
                        print(f"Parsed single rule with key-value: {key} - {value}")
                    else:
                        parsed_values.append({rule_value: '*'})
                        print(f"Parsed single rule with wildcard: {rule_value} - *")
                
                print(f"Parsed rule value: {parsed_values}")
                return parsed_values

            parsed_rule_value = parse_rule_value(rule_value)
            attr_value = parse_rule_value(attributes.get(attr))

            print(f"Attribute value for {attr}: {attr_value}")

            if not self.validate_attribute(parsed_rule_value, attr_value, attr):
                print(f"Validation failed for attribute: {attr}")
                return False
        print("Returning True")
        return True

    def validate_attribute(self, rule_value, attribute_value, attribute_type):
        if attribute_type in self.attribute_definitions:
            hierarchy = self.attribute_definitions[attribute_type]
            valid = False

            for root in hierarchy:
                if isinstance(root, AttributeTree):
                    # Hierarchical structure, convert to flat list and check subsumption
                    print("\033[94mDebug: Processing root of hierarchy\033[0m")
                    values_list = root
                    rule_tree = self.build_tree_from_values(root, rule_value)

                    if not rule_tree:
                        continue

                    print(f"\033[92mDebug: Built rule tree from values: {rule_value}\033[0m")
                    rule_tree.print_tree()  # Print the rule tree
                    # Create an attribute tree from the rule_value
                    attribute_tree = self.build_tree_from_values(root, attribute_value)

                    if not attribute_tree:
                        continue

                    print(f"\033[93mDebug: Built attribute tree from values: {attribute_value}\033[0m")
                    attribute_tree.print_tree()  # Print the attribute tree

                    valid = valid or rule_tree.check_subtree(attribute_tree)
                    print(f"\033[91mDebug: Validation result for current root: {valid}\033[0m")
                    
                    if valid:
                        return valid
                
        print(f"\033[95mDebug: Final validation result: {valid}\033[0m")
        return valid

    def build_tree_from_values(self, hierarchy_tree, values):
        root = None
        def dfs(node, values, append):
            node_key = list(node.value.keys())[0]
            node_value = next((v[node_key] for v in values if node_key in v), '*')
            all_values = [list(val.keys())[0] for val in values]

            new_node = None
            if node_key in all_values or append:
                new_node = AttributeTree(node_key, data=node_value)
                append = True

            for child in node.children:
                new_child = dfs(child, values, append)
                if new_child:
                    if new_node:
                        new_node.children.append(new_child)
                    else:
                        new_node = new_child
            return new_node

        root = dfs(hierarchy_tree, values, False)
        return root

    def export_attributes(self):
        return self.attribute_definitions