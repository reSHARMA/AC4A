import logging
from datetime import datetime
from .base_agent import BaseAgent
from ..web_input import web_input_func
from mock_app import ExpediaAPI

# Set up logging
logger = logging.getLogger(__name__)

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
        You are an Expedia agent.

        Use the tool `expedia_search_flights` to search for flights. The tool takes the following parameters:
        - origin: The origin airport code (e.g., 'SFO')
        - destination: The destination airport code (e.g., 'JFK')
        - departure_date: The departure date in YYYY-MM-DD format
        - return_date: The return date in YYYY-MM-DD format (optional)
        - passengers: The number of passengers (default: 1)
        - class: The class of the flight (e.g., 'economy', 'business', 'first') (default: 'economy')

        Use the tool `expedia_book_flight` to book a flight. The tool takes the following parameters:
        - flight_id: The ID of the flight to book
        - passengers: The number of passengers (default: 1)
        - class: The class of the flight (e.g., 'economy', 'business', 'first') (default: 'economy')
        - payment_method: The payment method to use (e.g., 'credit_card', 'debit_card', 'paypal')

        Use the tool `expedia_search_hotels` to search for hotels. The tool takes the following parameters:
        - location: The location to search for hotels
        - check_in_date: The check-in date in YYYY-MM-DD format
        - check_out_date: The check-out date in YYYY-MM-DD format
        - room_type: The type of room to search for (optional)

        Use the tool `expedia_book_hotel` to book a hotel. The tool takes the following parameters:
        - hotel_name: The name of the hotel to book
        - location: The location of the hotel
        - check_in_date: The check-in date in YYYY-MM-DD format
        - check_out_date: The check-out date in YYYY-MM-DD format
        - room_type: The type of room to book (optional)

        Use the tool `expedia_rent_car` to rent a car. The tool takes the following parameters:
        - car_type: The type of car to rent
        - pickup_location: The pickup location
        - pickup_date: The pickup date in YYYY-MM-DD format
        - return_date: The return date in YYYY-MM-DD format
        - rental_company: The rental company (optional)

        Use the tool `expedia_book_experience` to book an experience. The tool takes the following parameters:
        - experience_name: The name of the experience
        - location: The location of the experience
        - date: The date of the experience in YYYY-MM-DD format
        - participants: The number of participants (default: 1)

        Use the tool `expedia_book_cruise` to book a cruise. The tool takes the following parameters:
        - cruise_name: The name of the cruise
        - departure_port: The departure port
        - departure_date: The departure date in YYYY-MM-DD format
        - return_date: The return date in YYYY-MM-DD format
        - cabin_type: The cabin type (optional)

        Use the tool `expedia_search_rental_cars` to search for rental cars. The tool takes the following parameters:
        - pickup_location: The pickup location
        - pickup_date: The pickup date in YYYY-MM-DD format
        - return_date: The return date in YYYY-MM-DD format
        - car_type: The type of car (optional)
        - rental_company: The rental company (optional)

        Use the tool `expedia_search_experience` to search for experiences. The tool takes the following parameters:
        - experience_name: The name of the experience
        - location: The location of the experience
        - date: The date of the experience in YYYY-MM-DD format
        - participants: The number of participants (default: 1)

        Use the tool `expedia_search_cruise` to search for cruises. The tool takes the following parameters:
        - departure_port: The departure port
        - destination: The destination
        - departure_date: The departure date in YYYY-MM-DD format
        - return_date: The return date in YYYY-MM-DD format
        - cabin_type: The cabin type (optional)

        Use the tool `expedia_get_cruise_info` to get cruise information. The tool takes the following parameters:
        - cruise_id: The ID of the cruise

        Use the tool `expedia_get_cruise_addons` to get cruise add-ons. The tool takes the following parameters:
        - cruise_id: The ID of the cruise

        Use the tool `expedia_get_cruise_policies` to get cruise policies. The tool takes the following parameters:
        - cruise_id: The ID of the cruise

        Use the tool `expedia_get_cruise_payment_options` to get cruise payment options. The tool takes the following parameters:
        - cruise_id: The ID of the cruise

        Use the tool `expedia_pay_for_itenary` to pay for an itinerary. The tool takes the following parameters:
        - booking_id: The ID of the booking
        - payment_method: The payment method
        - amount: The amount to pay
        - card_number: The card number
        - card_expiry: The card expiry date
        - card_cvv: The card CVV
        - billing_address: The billing address

        Use the tool `expedia_add_guest_info` to add guest information. The tool takes the following parameters:
        - booking_id: The ID of the booking
        - guest_name: The guest name
        - guest_email: The guest email
        - guest_phone: The guest phone
        - guest_address: The guest address (optional)

        use `get_user_input` tool to ask the user for user input.

        Return "done" when your work is completed.
        """
        
        self.expedia_api = ExpediaAPI(policy_system)
        
        tools = [
            self.expedia_search_flights,
            self.expedia_book_flight,
            self.expedia_search_hotels,
            self.expedia_book_hotel,
            self.expedia_rent_car,
            self.expedia_book_experience,
            self.expedia_book_cruise,
            self.expedia_search_rental_cars,
            self.expedia_search_experience,
            self.expedia_search_cruise,
            self.expedia_get_cruise_info,
            self.expedia_get_cruise_addons,
            self.expedia_get_cruise_policies,
            self.expedia_get_cruise_payment_options,
            self.expedia_pay_for_itenary,
            self.expedia_add_guest_info,
            web_input_func
        ]
        
        super().__init__("Expedia", system_message, tools, model_client)
        
    async def expedia_search_flights(self, from_location: str, to_location: str, departure_date: str, return_date: str = None, airline: str = None, round_trip: bool = True) -> str:
        """
        Search for flights
        
        Args:
            from_location: The origin airport code
            to_location: The destination airport code
            departure_date: The departure date in YYYY-MM-DD format
            return_date: The return date in YYYY-MM-DD format
            airline: The airline to search for (optional)
            round_trip: Whether to search for round trip flights (default: True)
            
        Returns:
            The search results
        """
        logger.info(f"Calling ExpediaAPI search_flights with from_location={from_location}, to_location={to_location}, departure_date={departure_date}, return_date={return_date}, airline={airline}, round_trip={round_trip}")
        result = self.expedia_api.search_flights(from_location=from_location, to_location=to_location, departure_date=departure_date, return_date=return_date, airline=airline, round_trip=round_trip)
        return result
        
    async def expedia_book_flight(self, from_location: str, to_location: str, departure_date: str, return_date: str = None, airline: str = None, round_trip: bool = True) -> str:
        """
        Book a flight
        
        Args:
            from_location: The origin airport code
            to_location: The destination airport code
            departure_date: The departure date in YYYY-MM-DD format
            return_date: The return date in YYYY-MM-DD format (optional)
            airline: The airline to book with (optional)
            round_trip: Whether to book a round trip flight (default: True)
            
        Returns:
            The booking result
        """
        logger.info(f"Calling ExpediaAPI book_flight with from_location={from_location}, to_location={to_location}, departure_date={departure_date}, return_date={return_date}, airline={airline}, round_trip={round_trip}")
        result = self.expedia_api.book_flight(from_location=from_location, to_location=to_location, departure_date=departure_date, return_date=return_date, airline=airline, round_trip=round_trip)
        return result
        
    async def expedia_search_hotels(self, location: str, check_in_date: str, check_out_date: str, room_type: str = None) -> str:
        """
        Search for hotels
        
        Args:
            location: The location to search for hotels
            check_in_date: The check-in date in YYYY-MM-DD format
            check_out_date: The check-out date in YYYY-MM-DD format
            room_type: The type of room to search for (optional)
            
        Returns:
            The search results
        """
        logger.info(f"Calling ExpediaAPI search_hotels with location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}")
        result = self.expedia_api.search_hotels(location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
        return result
        
    async def expedia_book_hotel(self, hotel_name: str, location: str, check_in_date: str, check_out_date: str, room_type: str = None) -> str:
        """
        Book a hotel
        
        Args:
            hotel_name: The name of the hotel to book
            location: The location of the hotel
            check_in_date: The check-in date in YYYY-MM-DD format
            check_out_date: The check-out date in YYYY-MM-DD format
            room_type: The type of room to book (optional)
            
        Returns:
            The booking result
        """
        logger.info(f"Calling ExpediaAPI book_hotel with hotel_name={hotel_name}, location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}")
        result = self.expedia_api.book_hotel(hotel_name=hotel_name, location=location, check_in_date=check_in_date, check_out_date=check_out_date, room_type=room_type)
        return result
        
    async def expedia_rent_car(self, car_type: str, pickup_location: str, pickup_date: str, return_date: str, rental_company: str = None) -> str:
        """
        Rent a car
        
        Args:
            car_type: The type of car to rent
            pickup_location: The pickup location
            pickup_date: The pickup date in YYYY-MM-DD format
            return_date: The return date in YYYY-MM-DD format
            rental_company: The rental company (optional)
            
        Returns:
            The rental result
        """
        logger.info(f"Calling ExpediaAPI rent_car with car_type={car_type}, pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, rental_company={rental_company}")
        result = self.expedia_api.rent_car(car_type=car_type, pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, rental_company=rental_company)
        return result
        
    async def expedia_book_experience(self, experience_name: str, location: str, date: str, participants: int = 1) -> str:
        """
        Book an experience
        
        Args:
            experience_name: The name of the experience
            location: The location of the experience
            date: The date of the experience in YYYY-MM-DD format
            participants: The number of participants
            
        Returns:
            The booking result
        """
        logger.info(f"Calling ExpediaAPI book_experience with experience_name={experience_name}, location={location}, date={date}, participants={participants}")
        result = self.expedia_api.book_experience(experience_name=experience_name, location=location, date=date, participants=participants)
        return result
        
    async def expedia_book_cruise(self, cruise_name: str, departure_port: str, departure_date: str, return_date: str, cabin_type: str = None) -> str:
        """
        Book a cruise
        
        Args:
            cruise_name: The name of the cruise
            departure_port: The departure port
            departure_date: The departure date in YYYY-MM-DD format
            return_date: The return date in YYYY-MM-DD format
            cabin_type: The cabin type (optional)
            
        Returns:
            The booking result
        """
        logger.info(f"Calling ExpediaAPI book_cruise with cruise_name={cruise_name}, departure_port={departure_port}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}")
        result = self.expedia_api.book_cruise(cruise_name=cruise_name, departure_port=departure_port, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
        return result
        
    async def expedia_search_rental_cars(self, pickup_location: str, pickup_date: str, return_date: str, car_type: str = None, rental_company: str = None) -> str:
        """
        Search for rental cars
        
        Args:
            pickup_location: The pickup location
            pickup_date: The pickup date in YYYY-MM-DD format
            return_date: The return date in YYYY-MM-DD format
            car_type: The type of car (optional)
            rental_company: The rental company (optional)
            
        Returns:
            The search results
        """
        logger.info(f"Calling ExpediaAPI search_rental_cars with pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, car_type={car_type}, rental_company={rental_company}")
        result = self.expedia_api.search_rental_cars(pickup_location=pickup_location, pickup_date=pickup_date, return_date=return_date, car_type=car_type, rental_company=rental_company)
        return result
        
    async def expedia_search_experience(self, experience_name: str, location: str, date: str, participants: int = 1) -> str:
        """
        Search for experiences
        
        Args:
            experience_name: The name of the experience
            location: The location of the experience
            date: The date of the experience in YYYY-MM-DD format
            participants: The number of participants
            
        Returns:
            The search results
        """
        logger.info(f"Calling ExpediaAPI search_experience with experience_name={experience_name}, location={location}, date={date}, participants={participants}")
        result = self.expedia_api.search_experience(experience_name=experience_name, location=location, date=date, participants=participants)
        return result
        
    async def expedia_search_cruise(self, departure_port: str, destination: str, departure_date: str, return_date: str, cabin_type: str = None) -> str:
        """
        Search for cruises
        
        Args:
            departure_port: The departure port
            destination: The destination
            departure_date: The departure date in YYYY-MM-DD format
            return_date: The return date in YYYY-MM-DD format
            cabin_type: The cabin type (optional)
            
        Returns:
            The search results
        """
        logger.info(f"Calling ExpediaAPI search_cruise with departure_port={departure_port}, destination={destination}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}")
        result = self.expedia_api.search_cruise(departure_port=departure_port, destination=destination, departure_date=departure_date, return_date=return_date, cabin_type=cabin_type)
        return result
        
    async def expedia_get_cruise_info(self, cruise_id: str) -> str:
        """
        Get cruise information
        
        Args:
            cruise_id: The ID of the cruise
            
        Returns:
            The cruise information
        """
        logger.info(f"Calling ExpediaAPI get_cruise_info with cruise_id={cruise_id}")
        result = self.expedia_api.get_cruise_info(cruise_id=cruise_id)
        return result
        
    async def expedia_get_cruise_addons(self, cruise_id: str) -> str:
        """
        Get cruise add-ons
        
        Args:
            cruise_id: The ID of the cruise
            
        Returns:
            The cruise add-ons
        """
        logger.info(f"Calling ExpediaAPI get_cruise_addons with cruise_id={cruise_id}")
        result = self.expedia_api.get_cruise_addons(cruise_id=cruise_id)
        return result
        
    async def expedia_get_cruise_policies(self, cruise_id: str) -> str:
        """
        Get cruise policies
        
        Args:
            cruise_id: The ID of the cruise
            
        Returns:
            The cruise policies
        """
        logger.info(f"Calling ExpediaAPI get_cruise_policies with cruise_id={cruise_id}")
        result = self.expedia_api.get_cruise_policies(cruise_id=cruise_id)
        return result
        
    async def expedia_get_cruise_payment_options(self, cruise_id: str) -> str:
        """
        Get cruise payment options
        
        Args:
            cruise_id: The ID of the cruise
            
        Returns:
            The cruise payment options
        """
        logger.info(f"Calling ExpediaAPI get_cruise_payment_options with cruise_id={cruise_id}")
        result = self.expedia_api.get_cruise_payment_options(cruise_id=cruise_id)
        return result
        
    async def expedia_pay_for_itenary(self, booking_id: str, payment_method: str, amount: float, card_number: str, card_expiry: str, card_cvv: str, billing_address: str) -> str:
        """
        Pay for an itinerary
        
        Args:
            booking_id: The ID of the booking
            payment_method: The payment method
            amount: The amount to pay
            card_number: The card number
            card_expiry: The card expiry date
            card_cvv: The card CVV
            billing_address: The billing address
            
        Returns:
            The payment result
        """
        logger.info(f"Calling ExpediaAPI pay_for_itenary with booking_id={booking_id}, payment_method={payment_method}, amount={amount}, card_number={card_number}, card_expiry={card_expiry}, card_cvv={card_cvv}, billing_address={billing_address}")
        result = self.expedia_api.pay_for_itenary(booking_id=booking_id, payment_method=payment_method, amount=amount, card_number=card_number, card_expiry=card_expiry, card_cvv=card_cvv, billing_address=billing_address)
        return result
        
    async def expedia_add_guest_info(self, booking_id: str, guest_name: str, guest_email: str, guest_phone: str, guest_address: str = None) -> str:
        """
        Add guest information
        
        Args:
            booking_id: The ID of the booking
            guest_name: The guest name
            guest_email: The guest email
            guest_phone: The guest phone
            guest_address: The guest address (optional)
            
        Returns:
            The result of adding guest information
        """
        logger.info(f"Calling ExpediaAPI add_guest_info with booking_id={booking_id}, guest_name={guest_name}, guest_email={guest_email}, guest_phone={guest_phone}, guest_address={guest_address}")
        result = self.expedia_api.add_guest_info(booking_id=booking_id, guest_name=guest_name, guest_email=guest_email, guest_phone=guest_phone, guest_address=guest_address)
        return result 