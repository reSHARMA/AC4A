from datetime import datetime
from src.utils.attribute_tree import AttributeTree
from src.utils.logger import get_logger
from src.utils.dummy_data import call_openai_api
from src.prompts import POLICY_TEXT, POLICY_TRANSLATION
from flask import Flask, request, jsonify
from flask_cors import CORS
# Set up logger for policy system
logger = get_logger(__name__)

app = Flask(__name__)
CORS(app, resources={
    r"/get_attribute_trees": {"origins": "*"},
    r"/get_policies": {"origins": "*"},
    r"/add_policy": {"origins": "*"},
    r"/delete_policy": {"origins": "*"},
    r"/convert_to_text": {"origins": "*"},
    r"/generate_policies_from_text": {"origins": "*"},
    r"/add_policies_from_text": {"origins": "*"}
})

class PolicySystem:
    def __init__(self):
        self.policy_rules = []
        self.attribute_definitions = {}
        self.status = True
        self.prompt = False
        logger.debug("PolicySystem initialized")
        logger.info("PolicySystem ready with status: enabled")

    def reset(self):
        self.policy_rules.clear()

    def disable(self):
        self.status = False
        logger.info("PolicySystem disabled")

    def enable(self):
        self.status = True
        logger.info("PolicySystem enabled")

    def ask(self):
        self.prompt = True

    def quite(self):
        self.prompt = False 

    def text(self, policy=None, mode="decl"):
        if policy is None:
            policy_txt = ""
            policy_text = mode + "\n"
            for policy in self.policy_rules:
                policy_text = policy_text + ', '.join(f"{key}: {value}" for key, value in policy.items()) + "\n"
            response = call_openai_api(POLICY_TEXT, policy_text)
            return response
        else:
            policy_text = f"""
            {mode}
            {', '.join(f"{key}: {value}" for key, value in policy.items())}
            """
            response = call_openai_api(POLICY_TEXT, policy_text)
            return response

    def register_api(self, api_class):
        """
        Register an API class with the policy system.
        This extracts attribute definitions from the API class for policy enforcement.
        """
        # Log API registration at INFO level
        logger.info(f"🔌 REGISTERING API: {api_class.__name__}")
        
        # Pass the current instance of policy_system to the API constructor
        api_instance = api_class(self)
        logger.info(f"📦 Created API instance: {api_instance}")
        
        # Define the list of allowed attributes
        allowed_attributes = ['granular_data', 'data_access', 'position']
        logger.info(f"📋 Allowed attributes: {allowed_attributes}")

        # Extract attribute definitions from the API instance
        if hasattr(api_instance, 'get_attributes'):
            logger.info("🔍 Extracting attributes from API instance")
            attributes = api_instance.get_attributes()
            
            logger.info(f"📊 Found {len(attributes)} attribute types: {list(attributes.keys())}")
            
            for attr_type, values in attributes.items():
                logger.info(f"⚙️ Processing attribute type: {attr_type}")
                
                if attr_type in allowed_attributes:
                    logger.info(f"✅ Attribute '{attr_type}' is allowed")
                    
                    if attr_type in self.attribute_definitions:
                        # Merge attributes without duplication
                        existing_values = self.attribute_definitions[attr_type]
                        logger.info(f"🔄 Merging with existing values for '{attr_type}'")
                        
                        if isinstance(values, list):
                            for value in values:
                                if isinstance(value, AttributeTree):
                                    # Check if this tree already exists
                                    key, _ = list(value.value.items())[0]
                                    is_duplicate = False
                                    
                                    for existing_tree in existing_values:
                                        if isinstance(existing_tree, AttributeTree):
                                            existing_key, _ = list(existing_tree.value.items())[0]
                                            if key == existing_key:
                                                is_duplicate = True
                                                logger.info(f"🔄 Skipping duplicate AttributeTree '{key}'")
                                                break
                                    
                                    if not is_duplicate:
                                        existing_values.append(value)
                                        logger.info(f"📈 Added AttributeTree '{key}' to '{attr_type}'")
                                else:
                                    if value not in existing_values:
                                        existing_values.append(value)
                                        logger.info(f"➕ Added value '{value}' to '{attr_type}'")
                        
                        self.attribute_definitions[attr_type] = existing_values
                    else:
                        self.attribute_definitions[attr_type] = values
                        logger.info(f"🆕 Created new attribute definition for '{attr_type}'")
                else:
                    logger.warning(f"⛔ Attribute '{attr_type}' is not allowed and will be ignored")
        
        logger.info(f"✅ API REGISTRATION COMPLETE: {api_class.__name__}")
        return api_instance

    def add_policy(self, policy_rule):
        if self.prompt:
            if self.is_action_allowed(policy_rule, False):
                logger.info("Policy rule already subsumed by existing policies. Skipping addition.")
                return
            txt = self.text(policy=policy_rule, mode="prompt")
            user_response = input(f"{txt} (yes/no): ").strip().lower()
            if user_response != "yes":
                return

        # Check for duplicate policy using the same key matching logic as remove_policy
        target_key = f"{policy_rule['granular_data'].lower()}-{policy_rule['data_access'].lower()}-{policy_rule['position'].lower()}"
        
        for rule in self.policy_rules:
            rule_key = f"{rule['granular_data'].lower()}-{rule['data_access'].lower()}-{rule['position'].lower()}"
            if rule_key == target_key:
                logger.info(f"Duplicate policy found with key: {target_key}, skipping addition")
                return

        # Calculate and store fixed times for symbolic expressions
        for attr, value in policy_rule.items():
            if callable(value):
                policy_rule[attr] = value()
        self.policy_rules.append(policy_rule)
        logger.info(f"Added new policy with key: {target_key}")

    def is_action_allowed(self, attributes, print_policy=True):
        if not self.status:
            logger.warning("Policy system is DISABLED - allowing action by default")
            return True

        # Force policy logs at the INFO level to make them more visible
        logger.info(f"POLICY CHECK - Attributes: {attributes}")
        
        for rule in self.policy_rules:
            if print_policy:
                logger.info(f"POLICY RULE CHECK - Rule: {rule}")
            if self.check_subsumption(rule, attributes):
                if print_policy:
                    logger.info(f"✅ POLICY ALLOWED - Action is allowed by rule: {rule}")
                return True
        if print_policy:
            logger.error(f"❌ POLICY DENIED - Action not allowed for attributes: {attributes}")
        return False

    def check_subsumption(self, rule, attributes):
        logger.debug(f"Checking rule: {rule}")
        logger.debug(f"For attributes: {attributes}")

        for attr in rule:
            logger.debug(f"Checking attribute: {attr}")
            rule_value = rule[attr]
            logger.debug(f"Rule value: {rule_value}")

            if attr == 'expiry':
                # Compare datetime values directly
                if datetime.now() >= rule_value:
                    return False
                continue  

            if rule_value == '*':
                continue

            def parse_rule_value(rule_value):
                parsed_values = []
                if "::" in rule_value:
                    parts = rule_value.split("::")
                    logger.debug(f"Split rule value into parts: {parts}")
                    for part in parts:
                        if "(" in part and ")" in part:
                            key, value = part.split("(")
                            value = value.rstrip(")")
                            # Handle empty value as default
                            if value == "":
                                parsed_values.append({key: "default"})
                                logger.debug(f"Parsed empty value as default for key: {key}")
                            # Handle * as all values
                            elif value == "*":
                                parsed_values.append({key: "*"})
                                logger.debug(f"Parsed wildcard value for key: {key}")
                            # Handle specific value
                            else:
                                parsed_values.append({key: value})
                                logger.debug(f"Parsed specific value '{value}' for key: {key}")
                            logger.debug(f"Parsed part with key-value: {key} - {value}")
                        else:
                            # No parentheses means default value
                            parsed_values.append({part: "default"})
                            logger.debug(f"Parsed part with default value: {part} - default")
                else:
                    if "(" in rule_value and ")" in rule_value:
                        key, value = rule_value.split("(")
                        value = value.rstrip(")")
                        # Handle empty value as default
                        if value == "":
                            parsed_values.append({key: "default"})
                            logger.debug(f"Parsed empty value as default for key: {key}")
                        # Handle * as all values
                        elif value == "*":
                            parsed_values.append({key: "*"})
                            logger.debug(f"Parsed wildcard value for key: {key}")
                        # Handle specific value
                        else:
                            parsed_values.append({key: value})
                            logger.debug(f"Parsed specific value '{value}' for key: {key}")
                        logger.debug(f"Parsed single rule with key-value: {key} - {value}")
                    else:
                        # No parentheses means default value
                        parsed_values.append({rule_value: "default"})
                        logger.debug(f"Parsed single rule with default value: {rule_value} - default")
                
                logger.debug(f"Final parsed rule value: {parsed_values}")
                return parsed_values

            parsed_rule_value = parse_rule_value(rule_value)
            attr_value = parse_rule_value(attributes.get(attr))

            logger.debug(f"Attribute value for {attr}: {attr_value}")
            logger.debug(f"Rule value for {attr}: {parsed_rule_value}")

            if not self.validate_attribute(parsed_rule_value, attr_value, attr):
                logger.debug(f"Validation failed for attribute: {attr}")
                return False
        logger.debug("Validation successful, returning True")
        return True

    def validate_attribute(self, rule_value, attribute_value, attribute_type):
        logger.debug(f"Validating attribute {attribute_type}")
        logger.debug(f"Rule value: {rule_value}")
        logger.debug(f"Attribute value: {attribute_value}")
        
        valid = False  # Initialize valid at the start
        
        if not rule_value:
            logger.debug("No rule value provided")
            return True

        if attribute_type in self.attribute_definitions:
            hierarchy = self.attribute_definitions[attribute_type]
            for root in hierarchy:
                if isinstance(root, AttributeTree):
                    # Hierarchical structure, convert to flat list and check subsumption
                    logger.debug("Processing root of hierarchy")
                    values_list = root
                    logger.debug("Printing attribute definition")
                    root.print_tree()
                    logger.debug(f"Rule value: {rule_value}")
                    rule_tree = self.build_tree_from_values(root, rule_value)

                    if not rule_tree:
                        continue

                    logger.debug("Built rule tree from values")
                    rule_tree.print_tree()  # Print the rule tree
                    # Create an attribute tree from the rule_value
                    attribute_tree = self.build_tree_from_values(root, attribute_value)

                    if not attribute_tree:
                        continue

                    logger.debug("Built attribute tree from values")
                    attribute_tree.print_tree()  # Print the attribute tree

                    valid = valid or rule_tree.check_subtree(attribute_tree)
                    logger.debug(f"Validation result for current root: {valid}")
                    
                    if valid:
                        return valid
                
        logger.debug(f"Final validation result: {valid}")
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

    def remove_policy(self, policy_rule):
        """Remove a policy from the policy system based on its composite key"""
        logger.info(f"Attempting to remove policy: {policy_rule}")
        
        # Create composite key for the policy to remove
        target_key = f"{policy_rule['granular_data'].lower()}-{policy_rule['data_access'].lower()}-{policy_rule['position'].lower()}"
        
        # Find and remove the matching policy
        for i, rule in enumerate(self.policy_rules):
            rule_key = f"{rule['granular_data'].lower()}-{rule['data_access'].lower()}-{rule['position'].lower()}"
            if rule_key == target_key:
                logger.info(f"Found matching policy at index {i}, removing it")
                self.policy_rules.pop(i)
                return True
                
        logger.warning(f"No matching policy found for key: {target_key}")
        return False

    def add_policies_from_text(self, policy_text: str, agent_manager=None) -> bool:
        """
        Generate and add policies from text input.
        
        Args:
            policy_text (str): Text describing the policies to generate and add
            agent_manager: The agent manager instance to get attribute trees from
            
        Returns:
            bool: True if all policies were added successfully, False otherwise
        """
        logger.info("Generating and adding policies from text")
        
        if policy_text == "":
            logger.info("[policy_system.py] Empty policy text")
            return True

        all_data = "<ALL DATA>\n"
        # Get and print attribute trees
        if agent_manager:
            attribute_trees = agent_manager.get_attribute_trees()
            for i, tree in enumerate(attribute_trees):
                all_data += f"{tree.get_tree_string()}\n"
            all_data += "</ALL DATA>"

        # Generate policy code
        generated_code = call_openai_api(POLICY_TRANSLATION + all_data, policy_text)
        logger.error(f"[policy_system.py] Generated code: {generated_code}")
        # Extract code blocks from the response
        import re
        def extract_code_blocks(code: str) -> list:
            pattern = r"```python(.*?)```"
            code_blocks = re.findall(pattern, code, re.DOTALL)
            return [block.strip() for block in code_blocks]
            
        snippets = extract_code_blocks(generated_code)
        
        # Execute each policy snippet
        success = True
        for snippet in snippets:
            try:
                # Create a dictionary with policy_system for exec
                exec_globals = {"policy_system": self}
                exec(snippet, exec_globals)
            except Exception as e:
                logger.error(f"Error executing policy: {str(e)}", exc_info=True)
                success = False
                
        return success