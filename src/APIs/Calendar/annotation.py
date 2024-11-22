# Calendar API class with policy annotations
class CalendarAPIAttributes__:
    def __init__(self):
        pass

    def export_attributes(self):
        return {
            'granular_data': [AttributeTree('Year', [
                AttributeTree('Month', [
                    AttributeTree('Week', [
                        AttributeTree('Day', [
                            AttributeTree('Hour')
                        ])
                    ])
                ])
            ])],
            'data_access': ['Read', 'Write'],
            'time': ['Past', 'Present', 'Future']
        }

    def get_hierarchy(self, start_time, duration):
        end_time = start_time + duration
        if (end_time - start_time).days >= 365:
            return 'Year'
        elif (end_time - start_time).days >= 30:
            return 'Month'
        elif (end_time - start_time).days >= 7:
            return 'Week'
        elif (end_time - start_time).days >= 1:
            return 'Day'
        else:
            return 'Hour'

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

def annotate_calendar(endpoint_func):
    CalendarAPIAttributes = CalendarAPIAttributes__()
    def wrapper(self, *args, **kwargs):
        attributes = {
            'granular_data': CalendarAPIAttributes.get_hierarchy(kwargs['start_time'], kwargs['duration']),
            'data_access': CalendarAPIAttributes.get_access_level(endpoint_func.original_name),
            'time': CalendarAPIAttributes.get_time_period(kwargs['start_time'])
        }
        return endpoint_func(self, attributes, *args, **kwargs)

    wrapper.original_name = endpoint_func.__name__
    return wrapper

def export_attributes(endpoint_func):
    CalendarAPIAttributes = CalendarAPIAttributes__()
    def wrapper(self, *args, **kwargs):
        return endpoint_func(self, *args, **kwargs)
    wrapper.attributes = CalendarAPIAttributes.export_attributes()
    return wrapper
