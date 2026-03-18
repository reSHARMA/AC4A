"""
Utility functions for parsing rule values in the policy system.
"""

import logging

logger = logging.getLogger(__name__)


def parse_rule_value(rule_value):
    """
    Parse a rule value string into a list of key-value dictionaries.
    
    Handles formats like:
    - "key(value)" -> [{"key": "value"}]
    - "key(?)" -> [{"key": "?"}]
    - "key()" -> [{"key": "default"}]
    - "key1(value1)::key2(value2)" -> [{"key1": "value1"}, {"key2": "value2"}]
    - "simple_key" -> [{"simple_key": "default"}]
    
    Args:
        rule_value (str): The rule value string to parse
        
    Returns:
        list: List of dictionaries containing parsed key-value pairs
    """
    if not rule_value:
        return []
        
    parsed_values = []
    
    if "::" in rule_value:
        # Handle multiple parts separated by ::
        parts = rule_value.split("::")
        logger.info(f"Split rule value into parts: {parts}")
        
        for part in parts:
            parsed_part = _parse_single_part(part.strip())
            if parsed_part:
                parsed_values.append(parsed_part)
    else:
        # Handle single part
        parsed_part = _parse_single_part(rule_value.strip())
        if parsed_part:
            parsed_values.append(parsed_part)
    
    logger.info(f"Final parsed rule value: {parsed_values}")
    return parsed_values


def _parse_single_part(part):
    """
    Parse a single part of a rule value.
    
    Args:
        part (str): Single part to parse
        
    Returns:
        dict or None: Parsed key-value dictionary, or None if invalid
    """
    if not part:
        return None
        
    if "(" in part and ")" in part:
        # Handle key(value) format
        key, value = part.split("(", 1)
        value = value.rstrip(")")
        
        # Handle empty value as default
        if value == "":
            result = {key: "default"}
            logger.info(f"Parsed empty value as default for key: {key}")
        # Handle ? as all values (wildcard)
        elif value == "?":
            result = {key: "?"}
            logger.info(f"Parsed wildcard value for key: {key}")
        # Handle specific value
        else:
            result = {key: value}
            logger.info(f"Parsed specific value '{value}' for key: {key}")
            
        logger.info(f"Parsed part with key-value: {key} - {value}")
        return result
    else:
        # No parentheses means default value
        result = {part: "default"}
        logger.info(f"Parsed part with default value: {part} - default")
        return result


def parse_resource_string(resource_str):
    """
    Parse a resource string like 'Calendar:Meeting(?)' into type and identifier.
    
    Args:
        resource_str (str): Resource string to parse
        
    Returns:
        tuple: (type, identifier) or (None, None) if invalid
    """
    if not resource_str or not resource_str.startswith('Calendar:'):
        return None, None
        
    resource_str = resource_str[9:]  # Remove 'Calendar:'
    
    if '(' in resource_str and ')' in resource_str:
        type_part, id_part = resource_str.split('(', 1)
        return type_part, id_part.rstrip(')')
    else:
        return resource_str, None
