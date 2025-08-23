from datetime import datetime
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data

class ContactManagerAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("ContactManager", {
            'granular_data': [
                AttributeTree('ContactManager:Contact', [
                    AttributeTree('ContactManager:ContactName'),
                    AttributeTree('ContactManager:ContactPhone'),
                    AttributeTree('ContactManager:ContactAddress'),
                    AttributeTree('ContactManager:ContactEmail'),
                    AttributeTree('ContactManager:ContactRelation'),
                    AttributeTree('ContactManager:ContactBirthday'),
                    AttributeTree('ContactManager:ContactNotes')
                ])
            ],
            'data_access': [
                AttributeTree('Read'),
                AttributeTree('Write')
            ],
            'position': [
                AttributeTree('Previous'),
                AttributeTree('Current'),
                AttributeTree('Next')
            ]
        })

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'add_contact': ('Contact', kwargs.get('name', '*')),
            'remove_contact': ('Contact', kwargs.get('name', '*')),
            'update_contact': ('Contact', kwargs.get('name', '*')),
            'get_contact_info': ('Contact', kwargs.get('name', '*')),
            'get_names_by_relation': ('Contact', '*')
        }
        label, detail = api_to_granular_data.get(endpoint_name, ('Contact', '*'))
        if use_wildcard:
            return f"{self.namespace}:{label}(*)"
        else:
            return f"{self.namespace}:{label}({detail})"

    def get_access_level(self, endpoint_name):
        return 'Write' if 'add' in endpoint_name or 'remove' in endpoint_name or 'update' in endpoint_name else 'Read'

    def get_time_period(self, start_time, end_time, use_wildcard):
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, use_wildcard):
        start_time = datetime.now()
        end_time = start_time  # For contact operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, use_wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, use_wildcard)
        
        return [{
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
        }]

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
