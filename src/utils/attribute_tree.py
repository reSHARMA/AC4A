import logging
from src.utils.logger import get_logger

# Set up logger
logger = get_logger('__name__')

# AttributeTree class to represent hierarchical attribute definitions

class AttributeTree:
    def __init__(self, value, children=None, data='', access='', position=''):
        self.value = {value : data}
        self.children = children if children else []
        self.access = access  # 'read' or 'write' or empty
        self.position = position  # 'previous', 'current', 'next' or empty

    def print_tree(self, level=0):
        indent = "  " * level
        for key, value in self.value.items():
            access_str = f" [access: {self.access}]" if self.access else ""
            position_str = f" [position: {self.position}]" if self.position else ""
            logger.info(f"{indent}{key}: {value}{access_str}{position_str}")
        for child in self.children:
            child.print_tree(level + 1)

    def check_subtree(self, other_tree):
        def compare_subtrees(node1, node2):
            # Compare the current node values
            key1, value1 = list(node1.value.items())[0]
            key2, value2 = list(node2.value.items())[0]

            logger.info(f"Comparing nodes: {key1} with value {value1} and {key2} with value {value2}")

            if key1 != key2:
                logger.info(f"Keys do not match: {key1} != {key2}")
                # Check for subtree with child of key1 as node1 with same node2
                for child1 in node1.children:
                    subtree_result = compare_subtrees(child1, node2)
                    if subtree_result >= 0:
                        return subtree_result
                return -1

            result = -1
            if value1.lower() == value2.lower():
                logger.info(f"Value of node1 is equal to node2: {value1} == {value2}")
                result = 0
            elif value1.lower() == '*':
                logger.info(f"Value of node1 is wildcard: {value1} == *")
                result = 1

            
            if value1.lower() != '*' and value1.lower() != value2.lower():
                logger.info(f"Value of node1 is not equal to node2: {value1} != {value2}")
                return -1

            # Compare children
            for child1 in node1.children:
                # Find corresponding child in node2
                corresponding_child = next((child2 for child2 in node2.children if list(child2.value.keys())[0] == list(child1.value.keys())[0]), None)
                if corresponding_child:
                    logger.info(f"Found corresponding child for {list(child1.value.keys())[0]}")
                    subtree_result = compare_subtrees(child1, corresponding_child)
                    if subtree_result < 0:
                        return -1
                    else:
                        result += subtree_result
                else:
                    logger.info(f"No corresponding child found for {list(child1.value.keys())[0]} in node2")
                    # If no corresponding child is found in node2, continue
                    continue

            return result

        logger.info("Starting subtree comparison")
        result = compare_subtrees(self, other_tree)
        logger.info(f"Subtree comparison result: {result}")
        return result

    def to_list(self):
        if not self.children:
            return [{
                **self.value,
                'access': self.access,
                'position': self.position
            }]
        result = [{
            **self.value,
            'access': self.access,
            'position': self.position
        }]
        for child in self.children:
            result.extend(child.to_list())
        return result

    def __str__(self):
        key, value = list(self.value.items())[0]
        access_str = f" [access: {self.access}]" if self.access else ""
        position_str = f" [position: {self.position}]" if self.position else ""
        if self.children:
            return f"{key}({value}){access_str}{position_str} with {len(self.children)} children"
        else:
            return f"{key}({value}){access_str}{position_str}"
    
    def __repr__(self):
        return self.__str__()

    def get_tree_string(self):
        """Return a string representation of the entire tree"""
        lines = []
        
        def _build_tree_string(node, level=0):
            indent = "  " * level
            key, value = list(node.value.items())[0]
            access_str = f" [access: {node.access}]" if node.access else ""
            position_str = f" [position: {node.position}]" if node.position else ""
            lines.append(f"{indent}{key}: {value}{access_str}{position_str}")
            for child in node.children:
                _build_tree_string(child, level + 1)
        
        _build_tree_string(self)
        return "\n".join(lines)