from datetime import datetime
from src.utils.resource_type_tree import ResourceTypeTree
from src.utils.logger import get_logger
from src.utils.dummy_data import call_openai_api
from src.utils.rule_parser import parse_rule_value
from src.prompts import POLICY_TEXT, POLICY_TRANSLATION
from web.utils.custom_logger import send_custom_log
from flask import Flask, request, jsonify
from flask_cors import CORS
# Set up logger for policy system
logger = get_logger(__name__)


def _format_access_denied_log(attributes):
    """Extract namespace from resource_value_specification and return (category, message) for Access Denied log."""
    rv = attributes.get('resource_value_specification') or ''
    if not rv or ':' not in rv:
        return "❌ Access Denied for", f"{attributes}"
    namespace = rv.split(':')[0]
    # Strip namespace prefix from each segment: "Calendar:Year(2026)" -> "Year(2026)"
    shortened = '::'.join(part.split(':', 1)[-1] if ':' in part else part for part in rv.split('::'))
    display_attrs = dict(attributes)
    display_attrs['resource_value_specification'] = shortened
    category = f"❌ Access to {namespace} Denied"
    return category, f"{display_attrs}"

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
        self.attribute_schema = {}
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
            response = call_openai_api(POLICY_TEXT, policy_text, "perm")
            return response
        else:
            policy_text = f"""
            {mode}
            {', '.join(f"{key}: {value}" for key, value in policy.items())}
            """
            response = call_openai_api(POLICY_TEXT, policy_text, "perm")
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
        allowed_attributes = ['resource_value_specification', 'action']
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
                                if isinstance(value, ResourceTypeTree):
                                    # Check if this tree already exists
                                    key, _ = list(value.value.items())[0]
                                    is_duplicate = False
                                    
                                    for existing_tree in existing_values:
                                        if isinstance(existing_tree, ResourceTypeTree):
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

        if hasattr(api_instance, 'get_attributes_schema'):
            logger.info("🔍 Extracting attributes schema from API instance")
            attributes_schema = api_instance.get_attributes_schema()
            logger.info(f"📊 Found {len(attributes_schema)} attribute types: {list(attributes_schema.keys())}")
            self.attribute_schema.update(attributes_schema)

        logger.info(f"✅ API REGISTRATION COMPLETE: {api_class.__name__}")
        return api_instance

    def get_all_policy_prompts(self):
        prompts = []
        for policy in self.policy_rules:
            prompts.append(self.text(policy=policy, mode="prompt"))
        return prompts

    def get_all_policy_rules(self):
        return self.policy_rules

    def add_policy(self, policy_rule):
        # Validate resource_value_specification hierarchy
        if 'resource_value_specification' in policy_rule and 'resource_value_specification' in self.attribute_definitions:
            resource_value_specification = policy_rule['resource_value_specification']
            if resource_value_specification:
                # First validate the format of each part
                values = resource_value_specification.split("::")
                for value in values:
                    if "(" not in value or ")" not in value:
                        error_msg = f"Invalid format: {value} must follow the format key(value), value can be * or a specific string"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                    
                    key, val = value.split("(", 1)
                    val = val.rstrip(")")
                    if not key or not val:
                        error_msg = f"Invalid format: {value} must have both key and value"
                        logger.error(error_msg)
                        raise ValueError(error_msg)

                current_node = None
                
                def find_node_in_tree(tree, target_key):
                    if list(tree.value.keys())[0] == target_key:
                        return tree
                    for child in tree.children:
                        result = find_node_in_tree(child, target_key)
                        if result:
                            return result
                    return None
                
                for i in range(len(values)):
                    # Extract key, ignoring value
                    key = values[i].split("(")[0] if "(" in values[i] else values[i]
                    
                    if i == 0:
                        # For first node, find it anywhere in any tree
                        for tree in self.attribute_definitions['resource_value_specification']:
                            if isinstance(tree, ResourceTypeTree):
                                found_node = find_node_in_tree(tree, key)
                                if found_node:
                                    current_node = found_node
                                    break
                        
                        if not current_node:
                            error_msg = f"Invalid hierarchy: {key} is not a valid node in the hierarchy"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                    else:
                        # For subsequent nodes, check if they are children of current_node
                        found = False
                        for child in current_node.children:
                            if list(child.value.keys())[0] == key:
                                current_node = child
                                found = True
                                break
                        
                        if not found:
                            error_msg = f"Invalid hierarchy: {key} cannot be a child of {list(current_node.value.keys())[0]}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)

        if self.is_action_allowed([policy_rule], False):
            logger.info("Policy rule already subsumed by existing policies. Skipping addition.")
            send_custom_log("Permission Subsumed", f"{policy_rule}")
            return

        if policy_rule['resource_value_specification']:
            values = policy_rule['resource_value_specification'].split("::")
            logger.info(f"Split granular data into values: {values}")
            
            value_idx = None
            # iterate values in reverse order
            for i in range(len(values) - 1, -1, -1):
                if values[i].split("(")[0] + "?)" != values[i]:
                    value_idx = i

            if value_idx is None:
                logger.info("Only wildcard pattern found, using first value")
                value_idx = 0
            else:
                logger.info(f"Found non-wildcard pattern at index: {value_idx}")
            
            policy_rule['resource_value_specification'] = (
                "::".join(values[value_idx:]) if value_idx is not None 
                else values[0]
            )
            logger.info(f"Updated granular data to: {policy_rule['resource_value_specification']}")

        # Check for duplicate policy using the same key matching logic as remove_policy
        target_key = f"{policy_rule['resource_value_specification'].lower()}-{policy_rule['action'].lower()}"
        
        for rule in self.policy_rules:
            rule_key = f"{rule['resource_value_specification'].lower()}-{rule['action'].lower()}"
            if rule_key == target_key:
                logger.info(f"Duplicate policy found with key: {target_key}, skipping addition")
                return

        # Calculate and store fixed times for symbolic expressions
        for attr, value in policy_rule.items():
            if callable(value):
                policy_rule[attr] = value()
        self.policy_rules.append(policy_rule)
        send_custom_log("Permission Added", f"{target_key}")
        logger.info(f"Added new policy with key: {target_key}")

    def is_action_allowed(self, attributes, print_policy=True, resource_difference=None):
        if not self.status:
            logger.warning("Policy system is DISABLED - allowing action by default")
            return True

        # Handle list of attribute objects with OR logic
        if not isinstance(attributes, list):
            logger.error(f"POLICY ERROR - Expected list of attributes, got: {type(attributes)}")
            return False
            
        logger.info(f"POLICY CHECK - Multiple Attributes: {attributes}")
        
        # Check each attribute and return True if any match (OR logic)
        for attr in attributes:
            if self._check_single_attribute(attr, print_policy, resource_difference):
                logger.info(f"✅ POLICY ALLOWED - Action is allowed by attribute: {attr}")
                return True
                
        logger.error(f"❌ POLICY DENIED - Action not allowed for any attribute in: {attributes}")
        return False

    def _check_single_attribute(self, attributes, print_policy=True, resource_difference=None):
        """Check a single attribute object against policy rules"""
        print_policy = True
        logger.info(f"POLICY CHECK - Single Attribute: {attributes}")

        needs = [attributes]

        for rule in self.policy_rules:
            if print_policy:
                logger.info(f"POLICY RULE CHECK - Rule: {rule}")
                while(len(needs) > 0):
                    need = needs.pop(0)
                    logger.info(f"Checking need: {need}")
                    required = self.check_subsumption(rule, need, resource_difference)
                    for req in required:
                        needs.append(req)

        if len(needs) == 0:
            if print_policy:
                logger.info(f"✅ POLICY ALLOWED - Action is allowed by rule: {rule}")
                send_custom_log("✅ Access Granted by", f"{rule}")
            return True
        else:
            if print_policy:
                logger.error(f"❌ POLICY DENIED - Action not allowed for attributes: {attributes}")
                category, message = _format_access_denied_log(attributes)
                send_custom_log(category, message)
            return False

    def check_subsumption(self, rule, attributes, resource_difference=None):
        logger.info(f"Checking rule: {rule}")
        logger.info(f"For attributes: {attributes}")

        skip_attr = ['expiry']
        new_need = {}
        for attr in rule:
            if attr in skip_attr:
                continue

            logger.info(f"Checking attribute: {attr}")
            rule_value = rule[attr]
            logger.info(f"Rule value: {rule_value}")

            if attr == 'expiry':
                # Compare datetime values directly
                if datetime.now() >= rule_value:
                    return attributes
                continue  

            if rule_value == '?':
                continue

            parsed_rule_value = parse_rule_value(rule_value)
            attr_value = parse_rule_value(attributes.get(attr))

            logger.info(f"Attribute value for {attr}: {attr_value}")
            logger.info(f"Rule value for {attr}: {parsed_rule_value}")
            
            valid = self.validate_attribute(parsed_rule_value, attr_value, attr, resource_difference)
            new_need[attr] = valid

        # Use min length so we never index an empty list (empty = rule satisfied for that attr)
        lengths = [len(value) for value in new_need.values()]
        max_length_attr = min(lengths) if lengths else 0

        new_attributes_list = []
        for x in range(max_length_attr):
            new_attr = {}
            for attr, value in new_need.items():
                new_attr[attr] = value[x]
            new_attributes_list.append(new_attr)

        logger.info(f"New needs generated: {new_attributes_list}")
        return new_attributes_list

    def validate_attribute(self, rule_value, attribute_value, attribute_type, resource_difference=None):
        logger.info(f"Validating attribute {attribute_type}")
        logger.info(f"Rule value: {rule_value}")
        logger.info(f"Attribute value: {attribute_value}")
        
        valid = [attribute_value]
        
        if not rule_value:
            logger.info("No rule value provided")
            return [attribute_value]

        if attribute_type in self.attribute_definitions:

            if callable(resource_difference) and attribute_type == 'resource_value_specification':
                valid = resource_difference(rule_value, attribute_value)
                return valid

            hierarchy = self.attribute_definitions[attribute_type]
            for root in hierarchy:
                if isinstance(root, ResourceTypeTree):
                    # Hierarchical structure, convert to flat list and check subsumption
                    logger.info("Processing root of hierarchy")
                    values_list = root
                    logger.info("Printing attribute definition")
                    root.print_tree()
                    logger.info(f"Rule value: {rule_value}")
                    rule_tree = self.build_tree_from_values(root, rule_value)

                    if not rule_tree:
                        continue

                    logger.info("Built rule tree from values")
                    rule_tree.print_tree()  # Print the rule tree
                    # Create an attribute tree from the rule_value
                    attribute_tree = self.build_tree_from_values(root, attribute_value)

                    if not attribute_tree:
                        continue

                    logger.info("Built attribute tree from values")
                    attribute_tree.print_tree()  # Print the attribute tree
                    
                    valid = rule_tree.check_subtree(attribute_tree)
                    logger.info(f"Validation result for current root: {valid}")
                    
                    if valid >= 0:
                        return []
                
        logger.info(f"Final validation result: {valid}")
        return valid

    def build_tree_from_values(self, hierarchy_tree, values):
        # Check if any value is not '?', 'default', or ''
        has_special_value = False
        for val in values:
            for v in val.values():
                if v not in ['?', 'default', '']:
                    has_special_value = True
                    break
            if has_special_value:
                break

        logger.info(f"Special value check result: {has_special_value}")
        logger.info(f"Input values: {values}")

        if has_special_value:
            # Special case: Create tree with only paths containing nodes from values
            def build_special_tree(node, values, parent_has_special=False):
                node_key = list(node.value.keys())[0]
                logger.info(f"Processing node with key: {node_key}")
                
                # Find if this node exists in values
                try:
                    node_value = next((v[node_key] for v in values if node_key in v), None)
                    logger.info(f"Found value for {node_key}: {node_value}")
                except Exception as e:
                    logger.error(f"Error finding value for {node_key}: {str(e)}")
                    node_value = None

                # If parent has special value, this node should be '?' unless it has its own special value
                if parent_has_special and node_value is None:
                    node_value = '?'
                    logger.info(f"Using '?' for {node_key} as parent has special value")

                # Process children first to check if any have special values
                children_with_values = []
                for child in node.children:
                    logger.info(f"Processing child of {node_key}")
                    # Pass True if this node has a special value
                    new_child = build_special_tree(child, values, node_value is not None)
                    if new_child:
                        logger.info(f"Adding child {list(new_child.value.keys())[0]} to {node_key}")
                        children_with_values.append(new_child)

                # If we have children with values or this node has a value, create the node
                if children_with_values or node_value is not None:
                    # If this node doesn't have a specific value but is part of a path with special values,
                    # use '?' as the value
                    if node_value is None:
                        node_value = '?'
                        logger.info(f"Using '?' for {node_key} as it's part of a path with special values")
                    
                    logger.info(f"Creating new node for {node_key} with value {node_value}")
                    new_node = ResourceTypeTree(node_key, data=node_value)
                    new_node.children.extend(children_with_values)
                    return new_node

                logger.info(f"No value found for {node_key} and no children with values, returning None")
                return None

            result = build_special_tree(hierarchy_tree, values)
            logger.info("Final tree structure:")
            if result:
                result.print_tree()
            else:
                logger.info("No tree was created")
            return result

        # Original logic for non-special case
        root = None
        def dfs(node, values, append):
            node_key = list(node.value.keys())[0]
            node_value = next((v[node_key] for v in values if node_key in v), '?')
            all_values = [list(val.keys())[0] for val in values]

            new_node = None
            if node_key in all_values or append:
                new_node = ResourceTypeTree(node_key, data=node_value)
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

    def export_attributes_schema(self):
        return self.attribute_schema

    def remove_policy(self, policy_rule):
        """Remove a policy from the policy system based on its composite key"""
        logger.info(f"Attempting to remove policy: {policy_rule}")
        
        # Create composite key for the policy to remove
        target_key = f"{policy_rule['resource_value_specification'].lower()}-{policy_rule['action'].lower()}"
        send_custom_log("Permission Removed", f"{target_key}")
        
        # Find and remove the matching policy
        for i, rule in enumerate(self.policy_rules):
            rule_key = f"{rule['resource_value_specification'].lower()}-{rule['action'].lower()}"
            if rule_key == target_key:
                logger.info(f"Found matching policy at index {i}, removing it")
                removed_policy = self.policy_rules.pop(i)
                logger.info(f"Removed policy: {removed_policy}")
                return True
        
        logger.warning(f"No matching policy found for key: {target_key}")
        return False

    def add_policies_from_text(self, policy_text: str, agent_manager=None, attempt=1) -> bool:
        """
        Generate and add policies from text input.
        
        Args:
            policy_text (str): Text describing the policies to generate and add
            agent_manager: The agent manager instance to get attribute trees from
            attempt (int): Current attempt number (starts at 1)
            
        Returns:
            bool: True if all policies were added successfully, False otherwise
        """
        logger.info(f"Generating and adding policies from text (Attempt {attempt})")
        
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

        all_data_schema = "<ALL DATA SCHEMA>\n"
        all_data_schema += str(self.attribute_schema)
        all_data_schema += "</ALL DATA SCHEMA>"

        # Generate policy code
        generated_code = call_openai_api(POLICY_TRANSLATION + all_data + all_data_schema, policy_text, "perm")
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
        error_info = ""
        for snippet in snippets:
            try:
                # Create a dictionary with policy_system for exec
                exec_globals = {"policy_system": self}
                exec(snippet, exec_globals)
            except ValueError as ve:
                # This is the hierarchy validation error from add_policy
                error_msg = str(ve)
                logger.error(error_msg)
                error_info += f"\nHierarchy Error: {error_msg}"
                success = False
            except Exception as e:
                error_msg = f"Error executing policy: {str(e)}"
                logger.error(error_msg, exc_info=True)
                error_info += f"\nError: {error_msg}"
                success = False
        
        if not success:
            if attempt >= 5:
                logger.error("Maximum retry attempts (5) reached. Giving up.")
                return False
                
            # If any policy failed, append error information to the original policy text
            retry_text = f"""For permission request: {policy_text}
Attempt {attempt} failed. The following permissions were generated but failed:
{generated_code}
The following is the error information:
{error_info}
Please generate the permission again for the request: {policy_text}
Do not repeat the same mistake.
"""
            logger.info(f"Retrying entire policy text with error information appended (Attempt {attempt + 1})")
            return self.add_policies_from_text(retry_text, agent_manager, attempt + 1)
                
        return success