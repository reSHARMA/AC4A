from datetime import datetime
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.resource_type_tree import ResourceTypeTree
from src.utils.dummy_data import generate_dummy_data

class ContactManagerAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("ContactManager", {
            'resource_value_specification': [
                ResourceTypeTree(f'ContactManager:Contact', [
                    ResourceTypeTree(f'ContactManager:ContactName'),
                    ResourceTypeTree(f'ContactManager:ContactPhone'),
                    ResourceTypeTree(f'ContactManager:ContactAddress'),
                    ResourceTypeTree(f'ContactManager:ContactEmail'),
                    ResourceTypeTree(f'ContactManager:ContactRelation'),
                    ResourceTypeTree(f'ContactManager:ContactBirthday'),
                    ResourceTypeTree(f'ContactManager:ContactNotes')
                ])
            ],
            'action': [
                ResourceTypeTree('Read'),
                ResourceTypeTree('Write'),
                ResourceTypeTree('Create')
            ]
        })

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_resource_value_specification = {
            'add_contact': ('Contact', kwargs.get('name', '?')),
            'remove_contact': ('Contact', kwargs.get('name', '?')),
            'update_contact': ('Contact', kwargs.get('name', '?')),
            'get_contact_info': ('Contact', kwargs.get('name', '?')),
            'get_names_by_relation': ('Contact', '?')
        }
        label, detail = api_to_resource_value_specification.get(endpoint_name, ('Contact', '?'))
        if use_wildcard:
            return f"{self.namespace}:{label}(?)"
        else:
            return f"{self.namespace}:{label}({detail})"

    def get_access_level(self, endpoint_name):
        if 'add' in endpoint_name:
            return 'Create'
        elif 'remove' in endpoint_name or 'update' in endpoint_name:
            return 'Write'
        else:
            return 'Read'

    def get_time_period(self, start_time, end_time, use_wildcard):
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, use_wildcard):
        start_time = datetime.now()
        end_time = datetime.now()
        
        if 'start_time' in kwargs:
            start_time = kwargs['start_time']
        if 'end_time' in kwargs:
            end_time = kwargs['end_time']
        
        return {
            'resource_value_specification': self.get_hierarchy(endpoint_name, kwargs, use_wildcard),
            'action': self.get_access_level(endpoint_name)
        }

class ContactManagerAPI:
    def __init__(self, policy_system):
        self.annotation = ContactManagerAPIAnnotation()
        self.policy_system = policy_system

    @ContactManagerAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @ContactManagerAPIAnnotation.annotate
    def add_contact(self, name, phone, address, email, relation, birthday=None, notes=None):
        # Args: name (str), phone (str), address (str), email (str), relation (str), birthday (str, optional), notes (str, optional)
        return generate_dummy_data(
            api_endpoint="add_contact: add a new contact with the given details like name, phone, address, email, relation, birthday, and notes",
            name=name,
            phone=phone,
            address=address,
            email=email,
            relation=relation,
            birthday=birthday,
            notes=notes
        )

    @ContactManagerAPIAnnotation.annotate
    def remove_contact(self, name):
        # Args: name (str)
        return generate_dummy_data(
            api_endpoint="remove_contact: remove the contact with the given name",
            name=name
        )

    @ContactManagerAPIAnnotation.annotate
    def update_contact(self, name, phone=None, address=None, email=None, relation=None, birthday=None, notes=None):
        # Args: name (str), phone (str, optional), address (str, optional), email (str, optional), relation (str, optional), birthday (str, optional), notes (str, optional)
        return generate_dummy_data(
            api_endpoint="update_contact: update the contact information with the given details",
            name=name,
            phone=phone,
            address=address,
            email=email,
            relation=relation,
            birthday=birthday,
            notes=notes
        )

    @ContactManagerAPIAnnotation.annotate
    def get_contact_info(self, name):
        # Args: name (str)
        return generate_dummy_data(
            api_endpoint="get_contact_info: get all the contact information for the given name like phone, address, email, relation, birthday, and notes",
            name=name
        )

    @ContactManagerAPIAnnotation.annotate
    def get_names_by_relation(self, relation):
        # Args: relation (str)
        return generate_dummy_data(
            api_endpoint="get_names_by_relation: get names of  persons with the given relation, for example, 'spouse', 'child', 'parent', etc.",
            relation=relation
        )
