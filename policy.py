from datetime import datetime, timedelta
import time

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
        # Calculate and store fixed times for symbolic expressions
        for attr, value in policy_rule.items():
            if callable(value):
                policy_rule[attr] = value()
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

            # Handle expiry datetime objects separately
            if attr == 'expiry':
                if not isinstance(attribute_value, datetime):
                    return False
                # Compare datetime values directly
                if datetime.now() >= rule_value:
                    return False
                continue

            # Handle time attribute with Past, Present, Future
            if attr == 'time':
                if rule_value != attribute_value and rule_value != '*':
                    return False
                continue

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
                return rule_value == attribute_value or rule_value == '*'
        return False

    def export_attributes(self):
        return self.attribute_definitions

def policy_interceptor(api_func):
    def wrapper(self, attributes, *args, **kwargs):
        if policy_system.is_action_allowed(attributes):
            return api_func(self, *args, **kwargs)
        else:
            raise PermissionError(f"Action not authorized for given resources.")
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
            'time': ['Past', 'Present', 'Future']
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
        return 'r' if 'read' in endpoint_name else 'w'

    def get_time_period(self, start_time, duration):
        current_time = datetime.now()
        end_time = start_time + duration
        if start_time < current_time < end_time:
            return 'Present'
        elif current_time < start_time:
            return 'Future'
        else:
            return 'Past'

    def generate_attributes(self, kwargs, endpoint_name):
        start_time = kwargs['start_time']
        duration = kwargs['duration']
        return {
            'granular_data': self.get_hierarchy(start_time, duration),
            'data_access': self.get_access_level(endpoint_name),
            'time': self.get_time_period(start_time, duration),
            'actions': endpoint_name,
            # TODO: expiry must not be set by the API dev
            'expiry': datetime.now()
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
        pass

    @CalendarAPIAnnotation.annotate
    @policy_interceptor
    def read(self, *args, **kwargs):
        pass

    @CalendarAPIAnnotation.annotate
    @policy_interceptor
    def check_available(self, *args, **kwargs):
        pass

class TimeUtils:
    @staticmethod
    def next_seconds(n):
        """Returns a datetime object n seconds from now."""
        return datetime.now() + timedelta(seconds=n)

    @staticmethod
    def past_seconds(n):
        """Returns a datetime object n seconds in the past."""
        return datetime.now() - timedelta(seconds=n)

    @staticmethod
    def next_minutes(n):
        """Returns a datetime object n minutes from now."""
        return datetime.now() + timedelta(minutes=n)

    @staticmethod
    def past_minutes(n):
        """Returns a datetime object n minutes in the past."""
        return datetime.now() - timedelta(minutes=n)

    @staticmethod
    def next_hours(n):
        """Returns a datetime object n hours from now."""
        return datetime.now() + timedelta(hours=n)

    @staticmethod
    def past_hours(n):
        """Returns a datetime object n hours in the past."""
        return datetime.now() - timedelta(hours=n)

    @staticmethod
    def next_days(n):
        """Returns a datetime object n days from now."""
        return datetime.now() + timedelta(days=n)

    @staticmethod
    def past_days(n):
        """Returns a datetime object n days in the past."""
        return datetime.now() - timedelta(days=n)

    @staticmethod
    def next_weeks(n):
        """Returns a datetime object n weeks from now."""
        return datetime.now() + timedelta(weeks=n)

    @staticmethod
    def past_weeks(n):
        """Returns a datetime object n weeks in the past."""
        return datetime.now() - timedelta(weeks=n)

if __name__ == "__main__":
    policy_system = PolicySystem()

    # Register CalendarAPI with the policy system
    policy_system.register_api(CalendarAPI)

    # Add example policy rules with fixed time calculations
    policy_system.add_policy({
        "granular_data": "Calendar:*",
        "actions": "*",
        "data_access": "r",
        "time": "Future",  # Allow actions in the present time
        "expiry": TimeUtils.next_seconds(10)  # Policy expires in 10 seconds
    })

    calendar_api = CalendarAPI()

    # Test a valid read operation (should be allowed if within 5 minutes)
    try:
        start_time = datetime.now() + timedelta(minutes=3)  # Within the next 5 minutes
        duration = timedelta(minutes=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test an invalid read operation (should not be allowed if after 5 minutes)
    try:
        start_time = datetime.now() + timedelta(minutes=10)  # After the next 5 minutes
        duration = timedelta(minutes=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test case for policy expiry in 10 seconds
    print("\nTesting policy expiry in 10 seconds:")

    # Test a valid read operation (should be allowed immediately)
    try:
        start_time = datetime.now() + timedelta(seconds=65)  # Within the next 10 seconds
        duration = timedelta(seconds=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed immediately.")
    except PermissionError as e:
        print("Read operation not allowed immediately:", e)

    # Wait for 10 seconds to let the policy expire
    time.sleep(13)

    # Test an invalid read operation (should not be allowed after 10 seconds)
    try:
        start_time = datetime.now() + timedelta(seconds=111)  # After the policy expiry
        duration = timedelta(seconds=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed after expiry.")
    except PermissionError as e:
        print("Read operation not allowed after expiry:", e)
