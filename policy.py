from datetime import datetime, timedelta

# Policy System class to manage policy rules and attribute definitions

class PolicySystem:
    def __init__(self):
        self.policy_rules = []
        self.attribute_definitions = {}

    def register_api(self, api_class):
        # Define the list of allowed attributes
        allowed_attributes = ['granular_data', 'actions', 'data_access', 'time']

        # Extract attribute definitions from the API class
        api_class = api_class()
        if hasattr(api_class, 'get_attributes'):
            attributes = api_class.get_attributes()
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
        self.policy_rules.append(policy_rule)

    def is_action_allowed(self, attributes):
        for rule in self.policy_rules:
            if self.check_subsumption(rule, attributes):
                return True
        return False

    def check_subsumption(self, rule, attributes):
        for attr in rule:
            rule_value = rule[attr]
            attribute_value = attributes.get(attr)

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
                return rule_value == attribute_value
            elif attribute_type == 'actions':
                # Direct comparison for actions
                return rule_value in attribute_value
        return False

    def export_attributes(self):
        return self.attribute_definitions

def policy_interceptor(api_func):
    def wrapper(self, attributes, *args, **kwargs):
        if policy_system.is_action_allowed(attributes):
            return api_func(self, *args, **kwargs)
        else:
            raise PermissionError("Action not authorized for given resource.")
    wrapper.original_name = api_func.__name__
    return wrapper

# AttributeTree class to represent hierarchical attribute definitions

class AttributeTree:
    def __init__(self, value, children=None):
        self.value = value
        self.children = children if children else []

    def to_list(self):
        if not self.children:
            return [self.value]
        result = [self.value]
        for child in self.children:
            result.extend(child.to_list())
        return result

class APIAnnotationBase:
    def __init__(self, namespace, attributes):
        self.namespace = namespace
        self.attributes = attributes

    def export_attributes(self):
        return self.attributes

    @staticmethod
    def annotate(endpoint_func):
        def wrapper(self, *args, **kwargs):
            attributes = self.annotation.generate_attributes(kwargs, endpoint_func.original_name)
            return endpoint_func(self, attributes, *args, **kwargs)

        wrapper.original_name = endpoint_func.__name__
        return wrapper

    def export(endpoint_func):
        def wrapper(self, *args, **kwargs):
            wrapper.attributes = self.annotation.export_attributes()
            return endpoint_func(self, *args, **kwargs)
        return wrapper

    def generate_attributes(self, kwargs, endpoint_name):
        raise NotImplementedError("Subclasses should implement this method.")


class CalendarAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("Calendar", {
            'granular_data': [AttributeTree(f'Calendar:Year', [
                AttributeTree(f'Calendar:Month', [
                    AttributeTree(f'Calendar:Week', [
                        AttributeTree(f'Calendar:Day', [
                            AttributeTree(f'Calendar:Hour')
                        ])
                    ])
                ])
            ])],
            'actions': ['reserve', 'read', 'check_available'],
            'data_access': ['Read', 'Write'],
            'time': ['Past', 'Present', 'Future'],
            'expiration': ['Expired', 'Valid']
        })

    def get_hierarchy(self, start_time, duration):
        end_time = start_time + duration
        if (end_time - start_time).days >= 365:
            return f'{self.namespace}:Year'
        elif (end_time - start_time).days >= 30:
            return f'{self.namespace}:Month'
        elif (end_time - start_time).days >= 7:
            return f'{self.namespace}:Week'
        elif (end_time - start_time).days >= 1:
            return f'{self.namespace}:Day'
        else:
            return f'{self.namespace}:Hour'

    def get_access_level(self, endpoint_name):
        return 'Read' if 'read' in endpoint_name else 'Write'

    def get_time_period(self, start_time):
        current_time = datetime.now()
        if start_time < current_time:
            return 'Past'
        elif start_time.date() == current_time.date():
            return 'Present'
        else:
            return 'Future'

    def generate_attributes(self, kwargs, endpoint_name):
        return {
            'granular_data': self.get_hierarchy(kwargs['start_time'], kwargs['duration']),
            'data_access': self.get_access_level(endpoint_name),
            'time': self.get_time_period(kwargs['start_time']),
            'actions': endpoint_name
        }
# Combined Calendar API class with policy annotations and attribute management
class CalendarAPI:
    def __init__(self):
        self.annotation = CalendarAPIAnnotation()

    @CalendarAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarAPIAnnotation.annotate
    @policy_interceptor
    def reserve(self, *args, **kwargs):
        print("Reserving an entry with:", kwargs)

    @CalendarAPIAnnotation.annotate
    @policy_interceptor
    def read(self, *args, **kwargs):
        print("Reading entries with:", kwargs)

    @CalendarAPIAnnotation.annotate
    @policy_interceptor
    def check_available(self, *args, **kwargs):
        print("Checking availability with:", kwargs)

if __name__ == "__main__":
    policy_system = PolicySystem()

    # Register CalendarAPI with the policy system
    policy_system.register_api(CalendarAPI)

    # Add example policy rules with more specific resource identifiers
    policy_system.add_policy({"granular_data": "Calendar:*", "actions": "reserve", "data_access": "Read", "time": "Future"})
    policy_system.add_policy({"granular_data": "Calendar:Month", "data_access": "Read", "time": "Future"})

    calendar_api = CalendarAPI()

    # Test a valid read operation (should be allowed because "Calendar:Month" subsumes "Calendar:Hour")
    try:
        start_time = datetime.now() + timedelta(days=30)  # Future date
        duration = timedelta(hours=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test an invalid write operation (should not be allowed for past dates)
    try:
        start_time = datetime.now() - timedelta(days=365)  # Past date
        duration = timedelta(hours=1)
        calendar_api.reserve(start_time=start_time, duration=duration, desc="Meeting")
        print("Reserve operation allowed.")
    except PermissionError as e:
        print(e)
