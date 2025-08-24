from datetime import datetime, timedelta
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data

class CalendarAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("Calendar", {
            'granular_data': [
                AttributeTree(f'Calendar:Year', [
                    AttributeTree(f'Calendar:Month', [
                        AttributeTree(f'Calendar:Week', [
                            AttributeTree(f'Calendar:Day', [
                                AttributeTree(f'Calendar:Hour')
                            ])
                        ])
                    ])
                ])
            ],
            'data_access': [
                AttributeTree('Read'),
                AttributeTree('Write'),
                AttributeTree('Create')
            ]
        })

    def get_hierarchy(self, start_time, duration, use_wildcard):
        end_time = start_time + duration
        
        time_hierarchy = [
            (365, 'Year', start_time.year),
            (30, 'Month', start_time.month),
            (7, 'Week', start_time.isocalendar()[1]),
            (1, 'Day', start_time.day),
            (0, 'Hour', start_time.hour)
        ]

        composite_data = None
        for days, label, value in time_hierarchy:
            if (end_time - start_time).days >= days:
                if use_wildcard:
                    composite_data = f'{self.namespace}:{label}(*)'
                else:
                    composite_data = f'{self.namespace}:{label}({value})'
                break

        return composite_data

    def get_access_level(self, endpoint_name):
        if 'reserve' in endpoint_name or 'create' in endpoint_name or 'add' in endpoint_name:
            return 'Create'
        elif 'update' in endpoint_name or 'edit' in endpoint_name or 'modify' in endpoint_name:
            return 'Write'
        else:
            return 'Read'

    def get_time_period(self, start_time, duration, use_wildcard):
        current_time = datetime.now()
        end_time = start_time + duration

        if start_time < current_time < end_time:
            return "Current"
        
        time_hierarchy = [
            (365, 'Year', end_time.year - start_time.year),
            (30, 'Month', (end_time.year - start_time.year) * 12 + end_time.month - start_time.month),
            (7, 'Week', (end_time - start_time).days // 7),
            (1, 'Day', (end_time - start_time).days),
            (0, 'Hour', (end_time - start_time).seconds // 3600)
        ]

        composite_data = None
        for days, label, value in time_hierarchy:
            if (end_time - start_time).days >= days:
                if start_time < current_time and current_time < end_time:
                    composite_data = "Current"
                elif current_time < start_time:
                    if use_wildcard:
                        composite_data = f"Next(*)"
                    else:
                        composite_data = f"Next({value})"
                else:
                    if use_wildcard:
                        composite_data = f"Previous(*)"
                    else:
                        composite_data = f"Previous({value})"
                break

        result = composite_data if composite_data else "Current"
        return result

    def generate_attributes(self, kwargs, endpoint_name, use_wildcard):
        start_time = datetime.now()
        duration = timedelta(hours=1)
        
        if 'start_time' in kwargs:
            start_time = kwargs['start_time']
        if 'duration' in kwargs:
            duration = kwargs['duration']
        
        return {
            'granular_data': self.get_hierarchy(endpoint_name, kwargs, use_wildcard),
            'data_access': self.get_access_level(endpoint_name)
        }

class CalendarAPI:
    def __init__(self, policy_system):
        self.annotation = CalendarAPIAnnotation()
        self.policy_system = policy_system

    @CalendarAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @CalendarAPIAnnotation.annotate
    def reserve(self, *args, **kwargs):
        return generate_dummy_data("reserve: This method reserves a time slot in the calendar.", **kwargs)

    @CalendarAPIAnnotation.annotate
    def read(self, *args, **kwargs):
        return generate_dummy_data("read: This method reads calendar events within a specified time range.", **kwargs)

    @CalendarAPIAnnotation.annotate
    # start_time, duration
    def check_available(self, *args, **kwargs):
        return generate_dummy_data("check_availability: This method checks the availability of a time slot in the calendar.", **kwargs)