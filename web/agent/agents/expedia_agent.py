import logging
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data
from config import WILDCARD
from typing import Annotated

# Set up logging
logger = logging.getLogger(__name__)

class ExpediaAPIAnnotation(APIAnnotationBase):
    def __init__(self):
        attributes_schema = {
            'Expedia:Destination': {
                'description': 'The destination of the travel, must be a valid destination, can be a city, state, country etc',
                'examples': ['New York', 'Los Angeles', 'San Francisco']
            }, 
            'Expedia:Flight': {
                'description': 'The flight number of the flight, must be a valid flight number',
                'examples': ['AA123', 'UA456', 'DL789']
            },
            'Expedia:Hotel': {
                'description': 'The name of the hotel, must be a valid hotel name',
                'examples': ['Courtyard by Marriott', 'Hilton Garden Inn', 'Hyatt Regency', 'Collegetown Suites', 'Holiday Inn Express']
            },
            'Expedia:CarRental': {
                'description': 'The name of the car to rent, must be a valid car name',
                'examples': ['Toyota Camry', 'Honda Accord', 'Ford Fiesta']
            },
            'Expedia:Experience': {
                'description': 'The name of the experience, must be a valid experience name',
                'examples': ['Theater', 'Cruise', 'Museum', 'Zoo', 'Amusement Park', 'Spas', 'Restaurants', 'Shopping']
            },
            'Expedia:Cruise': {
                'description': 'The name of the cruise',
                'examples': ['Carnival', 'Royal Caribbean', 'Norwegian Cruise Line']
            },
            'Expedia:Payment': {
                'description': 'Represents the ability to pay for the booking, must always be *',
                'examples': ['*']
            }
        }
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
                AttributeTree('Previous', [AttributeTree('Current')]),
                AttributeTree('Next', [AttributeTree('Current')])
            ]
        }, attributes_schema)

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'search_flights': ('Flight', '*'),
            'get_flight_info': ('Flight', kwargs.get('flight_number', '*')),
            'book_flight': ('Flight', kwargs.get('flight_number', '*')),
            'search_hotels': ('Hotel', '*'),
            'get_hotel_info': ('Hotel', kwargs.get('hotel_name', '*')),
            'book_hotel': ('Hotel', kwargs.get('hotel_name', '*')),
            'search_rental_cars': ('CarRental', '*'),
            'get_rental_car_info': ('CarRental', kwargs.get('car_name', '*')),
            'book_rental_car': ('CarRental', kwargs.get('car_name', '*')),
            'search_experience': ('Experience', '*'),
            'book_experience': ('Experience', kwargs.get('experience_name', '*')),
            'search_cruise': ('Cruise', '*'),
            'get_cruise_info': ('Cruise', kwargs.get('cruise_name', '*')),
            'book_cruise': ('Cruise', kwargs.get('cruise_name', '*')),
            'pay_for_itenary': ('Payment', kwargs.get('booking_id', '*'))
        }
        label, detail = api_to_granular_data.get(endpoint_name, ('Destination', '*'))
        
        # Convert None to '*'
        if detail is None:
            detail = '*'
        
        if use_wildcard:
            return f"{self.namespace}:{label}(*)"
        else:
            return f"{self.namespace}:{label}({detail})"

    def get_access_level(self, endpoint_name):
        if endpoint_name == 'pay_for_itenary':
            return 'Write'
        return 'Read' if 'search' in endpoint_name or 'get' in endpoint_name else 'Write'

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        if 'search_flights' in endpoint_name or 'book_flight' in endpoint_name:
            departure_date = kwargs.get('departure_date')
            return_date = kwargs.get('return_date')
            
            if not departure_date:
                start_time = datetime.now()
            else:
                start_time = datetime.strptime(departure_date, '%Y-%m-%d')
                
            if not return_date:
                end_time = start_time + timedelta(days=1)
            else:
                end_time = datetime.strptime(return_date, '%Y-%m-%d')
                
        elif 'search_hotels' in endpoint_name or 'book_hotel' in endpoint_name:
            check_in_date = kwargs.get('check_in_date')
            check_out_date = kwargs.get('check_out_date')
            
            if not check_in_date:
                start_time = datetime.now()
            else:
                start_time = datetime.strptime(check_in_date, '%Y-%m-%d')
                
            if not check_out_date:
                end_time = start_time + timedelta(days=1)
            else:
                end_time = datetime.strptime(check_out_date, '%Y-%m-%d')
                
        elif 'search_rental_cars' in endpoint_name or 'book_rental_car' in endpoint_name:
            pickup_date = kwargs.get('pickup_date')
            return_date = kwargs.get('return_date')
            
            if not pickup_date:
                start_time = datetime.now()
            else:
                start_time = datetime.strptime(pickup_date, '%Y-%m-%d')
                
            if not return_date:
                end_time = start_time + timedelta(days=1)
            else:
                end_time = datetime.strptime(return_date, '%Y-%m-%d')
        else:
            start_time = datetime.now()
            end_time = start_time + timedelta(days=1)
        
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = "Current"
        
        logger.error(f"[expedia_agent.py] Generated attributes: {granular_data}, {data_access}, {position}")
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

    @ExpediaAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @ExpediaAPIAnnotation.annotate
    def search_flights(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="search_flights: expedia search flights and return flight number and basic information of the flight",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def book_flight(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="book_flight: expedia book flight and return booking id and payment status as pending",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_flight_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_flight_info: Get detailed information about a specific flight for a given flight number",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def search_hotels(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="search_hotels: expedia search hotels and return hotel name and basic information of the hotel",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def book_hotel(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="book_hotel: expedia book hotel and return booking id and payment status as pending",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_hotel_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_hotel_info: Get detailed information about a specific hotel for a given hotel name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def search_rental_cars(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="search_rental_cars: expedia search rental cars and return rental car name and basic information of the rental car",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def book_rental_car(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="book_rental_car: expedia rent car and return booking id and payment status as pending",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_rental_car_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_rental_car_info: Get detailed information about a specific rental car for a given rental car name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def search_experience(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="search_experience: expedia search experience and return experience name and basic information of the experience",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def book_experience(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="book_experience: expedia book experience and return booking id and payment status as pending",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_experience_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_experience_info: Get detailed information about a specific experience for a given experience name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def search_cruise(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="search_cruise: expedia search cruise and return basic information of cruises along with cruise name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def book_cruise(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="book_cruise: expedia book cruise and return booking id and payment status as pending",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_cruise_info: Get detailed information about a specific cruise for a given cruise name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_addons(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_cruise_addons: Get available add-ons for a specific cruise for a given cruise name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_policies(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_cruise_policies: Get policies for a specific cruise for a given cruise name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def get_cruise_payment_options(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_cruise_payment_options: Get payment options for a specific cruise for a given cruise name",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def pay_for_itenary(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="pay_for_itenary: Pay for a booked itinerary using payment details for a given booking id",
            **kwargs
        )

    @ExpediaAPIAnnotation.annotate
    def add_guest_info(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="add_guest_info: Add guest information to a booking for a given booking id",
            **kwargs
        )

class ExpediaAgent(BaseAgent):
    """Expedia agent for managing travel bookings"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the Expedia agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a travel booking agent.

        ## This is your general flow:
        First search for the best flight, hotel, rental car, experience, and cruise. You will get the exact name for each of them. Use that name to show detailed information for that flight, hotel, rental car, experience, and cruise. Then book using the name you got from the search. Booking will return a booking id. Use that booking id to add guest information if needed or find the payment options. In the end use the booking id to pay for the itinerary.


        """
        
        policy_system.register_api(ExpediaAPI)
        self.expedia_api = ExpediaAPI(policy_system)
        
        tools = [
            self.expedia_search_flights,
            self.expedia_book_flight,
            self.expedia_get_flight_info,
            self.expedia_search_hotels,
            self.expedia_book_hotel,
            self.expedia_get_hotel_info,
            self.expedia_search_rental_cars,
            self.expedia_book_rental_car,
            self.expedia_get_rental_car_info,
            self.expedia_search_experience,
            self.expedia_book_experience,
            self.expedia_get_experience_info,
            self.expedia_search_cruise,
            self.expedia_book_cruise,
            self.expedia_get_cruise_info,
            self.expedia_get_cruise_addons,
            self.expedia_get_cruise_policies,
            self.expedia_get_cruise_payment_options,
            self.expedia_pay_for_itenary,
            self.expedia_add_guest_info,
            get_user_input
        ]
        
        super().__init__("Expedia", system_message, tools, model_client)
        
    async def expedia_search_flights(self, from_location: Annotated[str, "airport_code"], to_location: Annotated[str, "airport_code"], departure_date: Annotated[str, "date as YYYY-MM-DD"], return_date: Annotated[str, "date as YYYY-MM-DD"] = None, airline: Annotated[str, "airline name (optional)"] = None, round_trip: Annotated[bool, "boolean (default: True)"] = True) -> str:
        """Search for flights from a given origin to a given destination on a given departure date and return the flight number and basic information of the flight"""
        logger.info(f"Calling ExpediaAPI search_flights with from_location={from_location}, to_location={to_location}, departure_date={departure_date}, return_date={return_date}, airline={airline}, round_trip={round_trip}")
        result = self.expedia_api.search_flights(from_location=from_location, to_location=to_location, departure_date=departure_date, return_date=return_date, airline=airline, round_trip=round_trip)
        return result
        
    async def expedia_book_flight(self, flight_number: Annotated[str, "flight number"], passengers: Annotated[int, "number of passengers (default: 1)"], class_type: Annotated[str, "class of the flight (default: 'economy')"]) -> str:
        """Book a flight with a given flight number, number of passengers, and class of the flight and return the booking id and basic information of the booking"""
        logger.info(f"Calling ExpediaAPI book_flight with flight_number={flight_number}, passengers={passengers}, class_type={class_type}")
        result = self.expedia_api.book_flight(flight_number=flight_number, passengers=passengers, class_type=class_type)
        return result
        
    async def expedia_get_flight_info(self, flight_number: Annotated[str, "flight number"]) -> str:
        """Get flight information for a given flight number and return detailed information about a specific flight for a given flight number"""
        logger.info(f"Calling ExpediaAPI get_flight_info with flight_number={flight_number}")
        result = self.expedia_api.get_flight_info(flight_number=flight_number)
        return result
    
    async def expedia_search_hotels(self, location: Annotated[str, "location to search for hotels"], check_in_date: Annotated[str, "date as YYYY-MM-DD"], check_out_date: Annotated[str, "date as YYYY-MM-DD"], room_type: Annotated[str, "room type (optional)"] = None) -> str:
        """Search for hotels in a given location on a given check-in date and check-out date. Return the hotel name and basic information of the hotel."""
        logger.info(f"Calling ExpediaAPI search_hotels with location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}")
        result = self.expedia_api.search_hotels(location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
        return result
        
    async def expedia_book_hotel(self, hotel_name: Annotated[str, "name of the hotel to book"], location: Annotated[str, "location of the hotel"], check_in_date: Annotated[str, "check-in date as YYYY-MM-DD"], check_out_date: Annotated[str, "check-out date as YYYY-MM-DD"], room_type: Annotated[str, "room type (optional)"] = None) -> str:
        """Book a hotel with a given hotel name, location, check-in date, check-out date, and room type and return the booking id and basic information of the booking"""
        logger.info(f"Calling ExpediaAPI book_hotel with hotel_name={hotel_name}, location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}")
        result = self.expedia_api.book_hotel(hotel_name=hotel_name, location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
        return result
        
    async def expedia_get_hotel_info(self, hotel_name: Annotated[str, "name of the hotel"]) -> str:
        """Get hotel information for a given hotel name and return detailed information about a specific hotel for a given hotel name"""
        logger.info(f"Calling ExpediaAPI get_hotel_info with hotel_name={hotel_name}")
        result = self.expedia_api.get_hotel_info(hotel_name=hotel_name)
        return result
        
    async def expedia_search_rental_cars(self, car_type: Annotated[str, "type of car to rent"], pickup_location: Annotated[str, "pickup location"], pickup_date: Annotated[str, "pickup date as YYYY-MM-DD"], return_date: Annotated[str, "return date as YYYY-MM-DD"], rental_company: Annotated[str, "rental company (optional)"] = None) -> str:
        """Search for rental cars in a given pickup location on a given pickup date and return date and return the rental car name and basic information of the rental car"""
        logger.info(f"Calling ExpediaAPI search_rental_cars with car_type={car_type}, pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, rental_company={rental_company}")
        result = self.expedia_api.search_rental_cars(car_type=car_type, pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, rental_company=rental_company)
        return result
        
    async def expedia_book_rental_car(self, car_name: Annotated[str, "name of the car to rent"], pickup_location: Annotated[str, "pickup location"], pickup_date: Annotated[str, "pickup date as YYYY-MM-DD"], return_date: Annotated[str, "return date as YYYY-MM-DD"], rental_company: Annotated[str, "rental company (optional)"] = None) -> str:
        """Book a rental car with a given car name, pickup location, pickup date, return date, and rental company and return the booking id and basic information of the booking"""
        logger.info(f"Calling ExpediaAPI book_rental_car with car_name={car_name}, pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, rental_company={rental_company}")
        result = self.expedia_api.book_rental_car(car_name=car_name, pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, rental_company=rental_company)
        return result
    
    async def expedia_get_rental_car_info(self, car_name: Annotated[str, "name of the car"]) -> str:
        """Get rental car information for a given car name and return detailed information about a specific rental car for a given rental car name"""
        logger.info(f"Calling ExpediaAPI get_rental_car_info with car_name={car_name}")
        result = self.expedia_api.get_rental_car_info(car_name=car_name)
        return result
    
    async def expedia_search_experience(self, experience_name: Annotated[str, "name of the experience to search for"], location: Annotated[str, "location of the experience"], date: Annotated[str, "date as YYYY-MM-DD"], participants: Annotated[int, "number of participants (default: 1)"] = 1) -> str:
        """Search for experiences in a given location on a given date. Return the experience name and basic information of the experience."""
        logger.info(f"Calling ExpediaAPI search_experience with experience_name={experience_name}, location={location}, date={date}, participants={participants}")
        result = self.expedia_api.search_experience(experience_name=experience_name, location=location, date=date, participants=participants)
        return result
    
    async def expedia_book_experience(self, experience_name: Annotated[str, "name of the experience to book"], location: Annotated[str, "location of the experience"], date: Annotated[str, "date as YYYY-MM-DD"], participants: Annotated[int, "number of participants (default: 1)"] = 1) -> str:
        """Book an experience with a given experience name, location, date, and number of participants and return the booking id and basic information of the booking"""
        logger.info(f"Calling ExpediaAPI book_experience with experience_name={experience_name}, location={location}, date={date}, participants={participants}")
        result = self.expedia_api.book_experience(experience_name=experience_name, location=location, date=date, participants=participants)
        return result

    async def expedia_get_experience_info(self, experience_name: Annotated[str, "name of the experience to get information for"]) -> str:
        """Get experience information for a given experience name and return detailed information about a specific experience for a given experience name"""
        logger.info(f"Calling ExpediaAPI get_experience_info with experience_name={experience_name}")
        result = self.expedia_api.get_experience_info(experience_name=experience_name)
        return result

    async def expedia_search_cruise(self, departure_port: Annotated[str, "departure port"], destination: Annotated[str, "destination"], departure_date: Annotated[str, "departure date as YYYY-MM-DD"], return_date: Annotated[str, "return date as YYYY-MM-DD"], cabin_type: Annotated[str, "cabin type (optional)"] = None) -> str:
        """Search for cruises from a given departure port to a given destination on a given departure date. Return the cruise name and basic information of the cruise."""
        logger.info(f"Calling ExpediaAPI search_cruise with departure_port={departure_port}, destination={destination}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}")
        result = self.expedia_api.search_cruise(departure_port=departure_port, destination=destination, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
        return result
    
    async def expedia_book_cruise(self, cruise_name: Annotated[str, "name of the cruise to book"], departure_port: Annotated[str, "departure port"], departure_date: Annotated[str, "departure date as YYYY-MM-DD"], return_date: Annotated[str, "return date as YYYY-MM-DD"], cabin_type: Annotated[str, "cabin type (optional)"] = None) -> str:
        """Book a cruise with a given cruise name, departure port, departure date, return date, and cabin type and return the booking id and basic information of the booking"""
        logger.info(f"Calling ExpediaAPI book_cruise with cruise_name={cruise_name}, departure_port={departure_port}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}")
        result = self.expedia_api.book_cruise(cruise_name=cruise_name, departure_port=departure_port, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
        return result
        
    async def expedia_get_cruise_info(self, cruise_name: Annotated[str, "name of the cruise to get information for"]) -> str:
        """Get cruise information for a given cruise name and return detailed information about a specific cruise for a given cruise name"""
        logger.info(f"Calling ExpediaAPI get_cruise_info with cruise_name={cruise_name}")
        result = self.expedia_api.get_cruise_info(cruise_name=cruise_name)
        return result
    
    async def expedia_get_cruise_addons(self, cruise_name: Annotated[str, "name of the cruise to get add-ons information for"]) -> str:
        """Get cruise add-ons available for a given cruise name and return the cruise add-ons name and basic information of the cruise add-ons"""
        logger.info(f"Calling ExpediaAPI get_cruise_addons with cruise_name={cruise_name}")
        result = self.expedia_api.get_cruise_addons(cruise_name=cruise_name)
        return result
        
    async def expedia_get_cruise_policies(self, cruise_name: Annotated[str, "name of the cruise to get policies for"]) -> str:
        """Get cruise policies for a given cruise name and return the cruise policies like cancellation policy, refund policy, etc."""
        logger.info(f"Calling ExpediaAPI get_cruise_policies with cruise_name={cruise_name}")
        result = self.expedia_api.get_cruise_policies(cruise_name=cruise_name)
        return result
        
    async def expedia_get_cruise_payment_options(self, cruise_name: Annotated[str, "name of the cruise to get payment options for"]) -> str:
        """Get cruise payment options for a given cruise name and return the cruise payment options like credit card, debit card, etc."""
        logger.info(f"Calling ExpediaAPI get_cruise_payment_options with cruise_name={cruise_name}")
        result = self.expedia_api.get_cruise_payment_options(cruise_name=cruise_name)
        return result
        
    async def expedia_pay_for_itenary(self, booking_id: Annotated[str, "booking id"], payment_method: Annotated[str, "payment method"], amount: Annotated[float, "amount to pay"], card_number: Annotated[str, "card number"], card_expiry: Annotated[str, "card expiry date"], card_cvv: Annotated[str, "card CVV"], billing_address: Annotated[str, "billing address"]) -> str:
        """Pay for an itinerary with a given booking id, payment method, amount, card number, card expiry date, card CVV, and billing address and return the payment result"""
        logger.info(f"Calling ExpediaAPI pay_for_itenary with booking_id={booking_id}, payment_method={payment_method}, amount={amount}, card_number={card_number}, card_expiry={card_expiry}, card_cvv={card_cvv}, billing_address={billing_address}")
        result = self.expedia_api.pay_for_itenary(booking_id=booking_id, payment_method=payment_method, amount=amount, card_number=card_number, card_expiry=card_expiry, card_cvv=card_cvv, billing_address=billing_address)
        return result
        
    async def expedia_add_guest_info(self, booking_id: Annotated[str, "booking id"], guest_name: Annotated[str, "guest name"], guest_email: Annotated[str, "guest email"], guest_phone: Annotated[str, "guest phone"], guest_address: Annotated[str, "guest address (optional)"] = None) -> str:
        """Add guest information to a booking with a given booking id, guest name, guest email, guest phone, and guest address and return the result of adding guest information"""
        logger.info(f"Calling ExpediaAPI add_guest_info with booking_id={booking_id}, guest_name={guest_name}, guest_email={guest_email}, guest_phone={guest_phone}, guest_address={guest_address}")
        result = self.expedia_api.add_guest_info(booking_id=booking_id, guest_name=guest_name, guest_email=guest_email, guest_phone=guest_phone, guest_address=guest_address)
        return result 