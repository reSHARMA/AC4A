from datetime import datetime, timedelta
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree

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
            'data_access': [
                AttributeTree('Read'),
                AttributeTree('Write')
            ],
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
            'granular_data': {self.get_hierarchy(start_time, duration): '*'},
            'data_access': {self.get_access_level(endpoint_name): '*'},
            'time': self.get_time_period(start_time, duration),
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
        pass

    @CalendarAPIAnnotation.annotate
    def read(self, *args, **kwargs):
        pass

    @CalendarAPIAnnotation.annotate
    # start_time, duration
    def check_available(self, *args, **kwargs):
        pass