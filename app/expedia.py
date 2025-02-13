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
                ]),
                AttributeTree(f'Expedia:Payment'),
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
            'search_flights': ('Flight', kwargs.get('airline', '*')),
            'book_flight': ('Flight', kwargs.get('airline', '*')),
            'search_hotels': ('Hotel', kwargs.get('hotel_name', '*')),
            'book_hotel': ('Hotel', kwargs.get('hotel_name', '*')),
            'search_cars': ('CarRental', kwargs.get('car_type', '*')),
            'rent_car': ('CarRental', kwargs.get('car_type', '*')),
            'search_experiences': ('Experience', '*'),
            'book_experience': ('Experience', '*'),
            'search_cruise': ('Cruise', '*'),
            'get_cruise_info': ('Cruise', '*'),
            'book_cruise': ('Cruise', '*'),
            'pay_for_itenary': ('Payment', '*')
        }
        label, detail = api_to_granular_data.get(endpoint_name, ('Destination', '*'))

        if "cruise" in endpoint_name.lower():
            label, detail = ('Cruise', kwargs.get('cruise_id', '*'))
        
        if use_wildcard:
            return f"{self.namespace}:{label}(*)"
        else:
            return f"{self.namespace}:{label}({detail})"

    def get_access_level(self, endpoint_name):
        return 'Read' if 'search' or 'get' in endpoint_name else 'Write'

    def get_time_period(self, start_time, end_time, use_wildcard):
        current_time = datetime.now()
        if start_time < current_time < end_time:
            return 'Current'
        elif current_time < start_time:
            return 'Next'
        else:
            return 'Previous'

    def generate_attributes(self, kwargs, endpoint_name, use_wildcard):
        if 'search_flights' in endpoint_name or 'book_flight' in endpoint_name:
            start_time = kwargs.get('departure_date', datetime.now())
            end_time = kwargs.get('return_date', start_time + timedelta(days=1))
        elif 'search_hotels' in endpoint_name or 'book_hotel' in endpoint_name:
            start_time = kwargs.get('check_in_date', datetime.now())
            end_time = kwargs.get('check_out_date', start_time + timedelta(days=1))
        elif 'rent_car' in endpoint_name:
            start_time = kwargs.get('pickup_date', datetime.now())
            end_time = kwargs.get('return_date', start_time + timedelta(days=1))
        else:
            start_time = datetime.now()
            end_time = start_time + timedelta(days=1)
        
        granular_data = self.get_hierarchy(endpoint_name, kwargs, use_wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, use_wildcard)
        
        return {
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
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
            api_endpoint="search_flights: expedia search flights",
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
            api_endpoint="book_flight: expedia book flight and return booking id",
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
            api_endpoint="search_hotels, expedia search hotels",
            location=location,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            room_type=room_type
        )

    @ExpediaAPIAnnotation.annotate
    def book_hotel(self, hotel_name, location, check_in_date, check_out_date, room_type=None):
        # Args: hotel_name (str), location (str), check_in_date (datetime), check_out_date (datetime), room_type (str, optional)
        return generate_dummy_data(
            api_endpoint="book_hotel, expedia book hotel and return booking id",
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
            api_endpoint="search_rental_cars, expedia search rental cars",
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
            api_endpoint="rent_car, expedia rent car and return booking id",
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
            api_endpoint="book_experience, expedia book experience and return booking id",
            experience_name=experience_name,
            location=location,
            date=date,
            participants=participants
        )

    @ExpediaAPIAnnotation.annotate
    def search_experience(self, experience_name, location, date, participants=1):
        # Args: experience_name (str), location (str), date (datetime), participants (int, optional)
        return generate_dummy_data(
            api_endpoint="search_experience, expedia search experience",
            experience_name=experience_name,
            location=location,
            date=date,
            participants=participants
        )

    @ExpediaAPIAnnotation.annotate
    def book_cruise(self, cruise_name, departure_port, departure_date, return_date, cabin_type=None):
        # Args: cruise_name (str), departure_port (str), departure_date (datetime), return_date (datetime), cabin_type (str, optional)
        return generate_dummy_data(
            api_endpoint="book_cruise, expedia book cruise and return booking id",
            cruise_name=cruise_name,
            departure_port=departure_port,
            departure_date=departure_date,
            return_date=return_date,
            cabin_type=cabin_type
        )

    @ExpediaAPIAnnotation.annotate
    def search_cruise(self, departure_port, destination, departure_date, return_date, cabin_type=None):
        # Args: departure_port (str), destination (str), departure_date (datetime), return_date (datetime), cabin_type (str, optional)
        return generate_dummy_data(
            api_endpoint="search_cruise, expedia search cruise returns cruise id of the cruises with price, destination, depature port and room options",
            departure_port=departure_port,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            cabin_type=cabin_type
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_info(self, cruise_id):
        # Args: cruise_id (str)
        return generate_dummy_data(
            api_endpoint="get_cruise_info, expedia get detailed information about a cruise like itenary, amenities, etc. but not the price or room options as it is already known",
            cruise_id=cruise_id
        )

    @ExpediaAPIAnnotation.annotate
    def pay_for_itenary(self, booking_id, payment_method, amount, card_number, card_expiry, card_cvv, billing_address):
        # Args: booking_id (str), payment_method (str), amount (float), card_number (str), card_expiry (str), card_cvv (str), billing_address (str)
        return generate_dummy_data(
            api_endpoint="pay_for_itenary, expedia pay for itenary",
            booking_id=booking_id,
            payment_method=payment_method,
            amount=amount,
            card_number=card_number,
            card_expiry=card_expiry,
            card_cvv=card_cvv,
            billing_address=billing_address
        )

    @ExpediaAPIAnnotation.annotate
    def add_guest_info(self, booking_id, guest_name, guest_email, guest_phone, guest_address=None):
        # Args: booking_id (str), guest_name (str), guest_email (str), guest_phone (str), guest_address (str, optional)
        return generate_dummy_data(
            api_endpoint="add_guest_info, expedia add guest information to a specific booking id",
            booking_id=booking_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            guest_address=guest_address
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_addons(self, cruise_id):
        # Args: cruise_id (str)
        return generate_dummy_data(
            api_endpoint="get_cruise_addons, expedia get available optional addons for a cruise like insurance, special occasion packages, etc.",
            cruise_id=cruise_id
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_policies(self, cruise_id):
        # Args: cruise_id (str)
        return generate_dummy_data(
            api_endpoint="get_cruise_policies, expedia get refund policy, cancellation policy, and other policies related to the cruise",
            cruise_id=cruise_id
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_payment_options(self, cruise_id):
        # Args: cruise_id (str)
        return generate_dummy_data(
            api_endpoint="get_cruise_payment_options, expedia get available payment options for a cruise like full payment, partial payment, etc.",
            cruise_id=cruise_id
        )