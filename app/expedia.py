from datetime import datetime, timedelta
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data

class ExpediaAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        super().__init__("Expedia", {
            'granular_data': [
                AttributeTree(f'Expedia:Destination', [
                    AttributeTree(f'Expedia:Flight'),
                    AttributeTree(f'Expedia:Hotel'),
                    AttributeTree(f'Expedia:CarRental')
                ]),
                AttributeTree(f'Expedia:Experience', [
                    AttributeTree(f'Expedia:Cruise')
                ])
            ],
            'data_access': [
                AttributeTree('Read'),
                AttributeTree('Write')
            ],
            'time': ['Past', 'Present', 'Future']
        })

    def get_hierarchy(self, **kwargs):
        if 'from_location' in kwargs and 'to_location' in kwargs:
            return f'{self.namespace}:Flight'
        elif 'hotel_name' in kwargs or 'location' in kwargs and 'check_in_date' in kwargs:
            return f'{self.namespace}:Hotel'
        elif 'pickup_location' in kwargs and 'pickup_date' in kwargs:
            return f'{self.namespace}:CarRental'
        elif 'experience_name' in kwargs and 'location' in kwargs:
            return f'{self.namespace}:Experience'
        elif 'cruise_name' in kwargs and 'departure_port' in kwargs:
            return f'{self.namespace}:Cruise'
        else:
            return f'{self.namespace}:Destination'

    def get_access_level(self, endpoint_name):
        return 'r' if 'read' in endpoint_name else 'w'

    def get_time_period(self, start_time, end_time):
        current_time = datetime.now()
        if start_time < current_time < end_time:
            return 'Present'
        elif current_time < start_time:
            return 'Future'
        else:
            return 'Past'

    def generate_attributes(self, kwargs, endpoint_name):
        start_time = kwargs.get('start_time', datetime.now())
        end_time = kwargs.get('end_time', datetime.now() + timedelta(days=1))
        return {
            'granular_data': {self.get_hierarchy(**kwargs): '*'},
            'data_access': {self.get_access_level(endpoint_name): '*'},
            'time': self.get_time_period(start_time, end_time),
        }

class ExpediaAPI:
    def __init__(self, policy_system):
        self.annotation = ExpediaAPIAnnotation()
        self.policy_system = policy_system

    @ExpediaAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes
    # Args: from_location (str), to_location (str), departure_date (datetime), return_date (datetime, optional), airline (str, optional), round_trip (bool)
    @ExpediaAPIAnnotation.annotate
    def search_flights(self, from_location, to_location, departure_date, return_date=None, airline=None, round_trip=True):
        # Args: from_location (str), to_location (str), departure_date (datetime), return_date (datetime, optional), airline (str, optional), round_trip (bool)
        return generate_dummy_data(
            api_endpoint="search_flights",
            from_location=from_location,
            to_location=to_location,
            departure_date=departure_date,
            return_date=return_date,
            airline=airline,
            round_trip=round_trip
        )

    @ExpediaAPIAnnotation.annotate
    def book_flight(self, from_location, to_location, departure_date, return_date=None, airline=None, round_trip=True):
        # Args: from_location (str), to_location (str), departure_date (datetime), return_date (datetime, optional), airline (str, optional), round_trip (bool)
        return generate_dummy_data(
            api_endpoint="book_flight",
            from_location=from_location,
            to_location=to_location,
            departure_date=departure_date,
            return_date=return_date,
            airline=airline,
            round_trip=round_trip
        )

    @ExpediaAPIAnnotation.annotate
    def search_hotels(self, location, check_in_date, check_out_date, room_type=None):
        # Args: location (str), check_in_date (datetime), check_out_date (datetime), room_type (str, optional)
        return generate_dummy_data(
            api_endpoint="search_hotels",
            location=location,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            room_type=room_type
        )

    @ExpediaAPIAnnotation.annotate
    def book_hotel(self, hotel_name, location, check_in_date, check_out_date, room_type=None):
        # Args: hotel_name (str), location (str), check_in_date (datetime), check_out_date (datetime), room_type (str, optional)
        return generate_dummy_data(
            api_endpoint="book_hotel",
            hotel_name=hotel_name,
            location=location,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            room_type=room_type
        )

    @ExpediaAPIAnnotation.annotate
    def search_rental_cars(self, pickup_location, pickup_date, return_date, car_type=None, rental_company=None):
        # Args: pickup_location (str), pickup_date (datetime), return_date (datetime), car_type (str, optional), rental_company (str, optional)
        return generate_dummy_data(
            api_endpoint="search_rental_cars",
            pickup_location=pickup_location,
            pickup_date=pickup_date,
            return_date=return_date,
            car_type=car_type,
            rental_company=rental_company
        )

    @ExpediaAPIAnnotation.annotate
    def rent_car(self, car_type, pickup_location, pickup_date, return_date, rental_company=None):
        # Args: car_type (str), pickup_location (str), pickup_date (datetime), return_date (datetime), rental_company (str, optional)
        return generate_dummy_data(
            api_endpoint="rent_car",
            car_type=car_type,
            pickup_location=pickup_location,
            pickup_date=pickup_date,
            return_date=return_date,
            rental_company=rental_company
        )

    @ExpediaAPIAnnotation.annotate
    def book_experience(self, experience_name, location, date, participants=1):
        # Args: experience_name (str), location (str), date (datetime), participants (int, optional)
        return generate_dummy_data(
            api_endpoint="book_experience",
            experience_name=experience_name,
            location=location,
            date=date,
            participants=participants
        )

    @ExpediaAPIAnnotation.annotate
    def search_experience(self, experience_name, location, date, participants=1):
        # Args: experience_name (str), location (str), date (datetime), participants (int, optional)
        return generate_dummy_data(
            api_endpoint="search_experience",
            experience_name=experience_name,
            location=location,
            date=date,
            participants=participants
        )

    @ExpediaAPIAnnotation.annotate
    def book_cruise(self, cruise_name, departure_port, departure_date, return_date, cabin_type=None):
        # Args: cruise_name (str), departure_port (str), departure_date (datetime), return_date (datetime), cabin_type (str, optional)
        return generate_dummy_data(
            api_endpoint="book_cruise",
            cruise_name=cruise_name,
            departure_port=departure_port,
            departure_date=departure_date,
            return_date=return_date,
            cabin_type=cabin_type
        )

    @ExpediaAPIAnnotation.annotate
    def search_cruise(self, departure_port, departure_date, return_date, cabin_type=None):
        # Args: departure_port (str), departure_date (datetime), return_date (datetime), cabin_type (str, optional)
        return generate_dummy_data(
            api_endpoint="search_cruise",
            departure_port=departure_port,
            departure_date=departure_date,
            return_date=return_date,
            cabin_type=cabin_type
        )
