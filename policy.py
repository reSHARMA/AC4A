from datetime import datetime, timedelta

# Attribute Annotations
def annotate_calendar(endpoint_func):
    def wrapper(self, *args, **kwargs):
        attributes = {
            'granular_data': get_hierarchy(kwargs['start_time'], kwargs['duration']),
            'data_access': get_access_level(endpoint_func.__name__),
            'time': get_time_period(kwargs['start_time'])
        }
        return endpoint_func(self, attributes, *args, **kwargs)
    return wrapper

def get_hierarchy(start_time, duration):
    end_time = start_time + duration
    if (end_time - start_time).days > 365:
        return 'Year'
    elif (end_time - start_time).days > 30:
        return 'Month'
    elif (end_time - start_time).days > 7:
        return 'Week'
    elif (end_time - start_time).days > 1:
        return 'Day'
    else:
        return 'Hour'

def get_access_level(endpoint_name):
    read_only_endpoints = ['read', 'check_available']
    write_only_endpoints = ['reserve']

    if endpoint_name in read_only_endpoints and endpoint_name in write_only_endpoints:
        return 'Read/Write'
    if endpoint_name in read_only_endpoints:
        return 'Read'
    elif endpoint_name in write_only_endpoints:
        return 'Write'

def get_time_period(start_time):
    current_time = datetime.now()
    if start_time < current_time:
        return 'Past'
    elif start_time.date() == current_time.date():
        return 'Present'
    else:
        return 'Future'

# Policy System
class PolicySystem:
    def __init__(self, policy_rules):
        self.policy_rules = policy_rules

    def is_action_allowed(self, attributes):
        for rule in self.policy_rules:
            if all(rule[attr] == attributes.get(attr) for attr in rule):
                return True
        return False

# Example policy rules
policy_rules = [
    {"granular_data": "Month", "data_access": "Read", "time": "Future"},
    {"granular_data": "Year", "data_access": "Read", "time": "Past"},
    # Other rules can be added here
]

policy_system = PolicySystem(policy_rules)

# Policy Interceptor
def policy_interceptor(api_func):
    def wrapper(self, attributes, *args, **kwargs):
        if policy_system.is_action_allowed(attributes):
            return api_func(self, *args, **kwargs)
        else:
            raise PermissionError("Action not authorized for given resource.")
    return wrapper


# Calendar API class
class CalendarAPI:
    @annotate_calendar
    @policy_interceptor
    def reserve(self, *args, **kwargs):
        print("Reserving an entry with:", kwargs)

    @annotate_calendar
    @policy_interceptor
    def read(self, *args, **kwargs):
        print("Reading entries with:", kwargs)

    @annotate_calendar
    @policy_interceptor
    def check_available(self, *args, **kwargs):
        print("Checking availability with:", kwargs)


# Testing the Implementation
if __name__ == "__main__":
    import pdb; pdb.set_trace()
    calendar_api = CalendarAPI()

    # Test a valid read operation
    try:
        start_time = datetime.now() + timedelta(days=30)  # Future date
        duration = timedelta(days=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test an invalid write operation
    try:
        start_time = datetime.now() - timedelta(days=365)  # Past date
        duration = timedelta(days=1)
        calendar_api.reserve(start_time=start_time, duration=duration, desc="Meeting")
        print("Reserve operation allowed.")
    except PermissionError as e:
        print(e)
