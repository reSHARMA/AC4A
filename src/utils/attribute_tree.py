# AttributeTree class to represent hierarchical attribute definitions

class AttributeTree:
    def __init__(self, value, data='*', children=None):
        self.value = {'value': value, 'data': data}
        self.children = children if children else []

    def to_list(self):
        if not self.children:
            return [self.value]
        result = [self.value]
        for child in self.children:
            result.extend(child.to_list())
        return result
