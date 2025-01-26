from config import debug_print

# AttributeTree class to represent hierarchical attribute definitions

class AttributeTree:
    def __init__(self, value, children=None, data='*'):
        self.value = {value : data}
        self.children = children if children else []

    def print_tree(self, level=0):
        indent = "  " * level
        for key, value in self.value.items():
            debug_print(f"{indent}{key}: {value}")
        for child in self.children:
            child.print_tree(level + 1)

    def check_subtree(self, other_tree):
        def compare_subtrees(node1, node2):
            # Compare the current node values
            key1, value1 = list(node1.value.items())[0]
            key2, value2 = list(node2.value.items())[0]

            debug_print(f"Comparing nodes: {key1} with value {value1} and {key2} with value {value2}")

            if key1 != key2:
                debug_print(f"Keys do not match: {key1} != {key2}")
                # Check for subtree with child of key1 as node1 with same node2
                for child1 in node1.children:
                    if compare_subtrees(child1, node2):
                        return True
                return False

                       
            if key1 == key2 and (value1 == value2 or value1 == '*'):
                return True

             # Check if the value of the current node in self is greater than or equal to the value in other_tree
            if value1 != value2:
                debug_print(f"Value of node1 is less than node2: {value1} < {value2}")
                return False

            # Compare children
            for child1 in node1.children:
                # Find corresponding child in node2
                corresponding_child = next((child2 for child2 in node2.children if list(child2.value.keys())[0] == list(child1.value.keys())[0]), None)
                if corresponding_child:
                    debug_print(f"Found corresponding child for {list(child1.value.keys())[0]}")
                    if not compare_subtrees(child1, corresponding_child):
                        return False
                else:
                    debug_print(f"No corresponding child found for {list(child1.value.keys())[0]} in node2")
                    # If no corresponding child is found in node2, continue
                    continue

            return True

        debug_print("Starting subtree comparison")
        result = compare_subtrees(self, other_tree)
        debug_print(f"Subtree comparison result: {result}")
        return result

    def to_list(self):
        if not self.children:
            return [self.value]
        result = [self.value]
        for child in self.children:
            result.extend(child.to_list())
        return result