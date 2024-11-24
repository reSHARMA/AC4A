from datetime import datetime, timedelta
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree

class PhotoAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("Photo", {
            'granular_data': [AttributeTree(f'Photo:Year', [
                AttributeTree(f'Photo:Month', [
                    AttributeTree(f'Photo:Week', [
                        AttributeTree(f'Photo:Day', [
                            AttributeTree(f'Photo:Hour')
                        ])
                    ])
                ])
            ])],
            'actions': ['upload', 'view', 'delete', 'edit', 'share'],
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
        read_actions = ['view', 'share']
        return 'r' if any(action in endpoint_name for action in read_actions) else 'w'

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
        }

class PhotoAPI:
    def __init__(self, policy_system):
        self.annotation = PhotoAPIAnnotation()
        self.policy_system = policy_system

    @PhotoAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @PhotoAPIAnnotation.annotate
    def upload(self, *args, **kwargs):
        # Logic to upload a photo
        pass

    @PhotoAPIAnnotation.annotate
    def view(self, *args, **kwargs):
        # Logic to view a photo
        pass

    @PhotoAPIAnnotation.annotate
    def delete(self, *args, **kwargs):
        # Logic to delete a photo
        pass

    @PhotoAPIAnnotation.annotate
    def edit(self, *args, **kwargs):
        # Logic to edit a photo
        pass

    @PhotoAPIAnnotation.annotate
    def share(self, *args, **kwargs):
        # Logic to share a photo
        pass

