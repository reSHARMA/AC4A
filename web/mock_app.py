#!/usr/bin/env python3
"""
Mock implementations of the app modules needed by agent.py.
This file provides mock implementations of the CalendarAPI, ExpediaAPI, WalletAPI, and ContactManagerAPI classes.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Create a mock app module if it doesn't exist
if 'app' not in sys.modules:
    # Create a mock app module
    app_module = type('app', (), {})
    sys.modules['app'] = app_module

# Mock CalendarAPI class
class CalendarAPI:
    def __init__(self, policy_system=None):
        self.policy_system = policy_system
        print("Mock CalendarAPI initialized")
    
    def reserve(self, start_time, duration, description):
        print(f"Mock CalendarAPI.reserve called with start_time={start_time}, duration={duration}, description={description}")
        return f"Reserved calendar slot: {start_time} for {duration} with description: {description}"
    
    def read(self, start_time, duration):
        print(f"Mock CalendarAPI.read called with start_time={start_time}, duration={duration}")
        return f"Calendar entries from {start_time} for {duration}: No entries found"
    
    def check_available(self, start_time, duration):
        print(f"Mock CalendarAPI.check_available called with start_time={start_time}, duration={duration}")
        return f"Availability check for {start_time} for {duration}: Available"

# Mock ExpediaAPI class
class ExpediaAPI:
    def __init__(self, policy_system=None):
        self.policy_system = policy_system
        print("Mock ExpediaAPI initialized")
    
    def search_flights(self, from_location, to_location, departure_date, return_date=None, airline=None, round_trip=True):
        print(f"Mock ExpediaAPI.search_flights called with from_location={from_location}, to_location={to_location}, departure_date={departure_date}, return_date={return_date}, airline={airline}, round_trip={round_trip}")
        return f"Found flights from {from_location} to {to_location} on {departure_date}"
    
    def book_hotel(self, hotel_name, location, check_in_date, check_out_date, room_type=None):
        print(f"Mock ExpediaAPI.book_hotel called with hotel_name={hotel_name}, location={location}, check_in_date={check_in_date}, check_out_date={check_out_date}, room_type={room_type}")
        return f"Booked hotel {hotel_name} in {location} from {check_in_date} to {check_out_date}"
    
    def rent_car(self, car_type, pickup_location, pickup_date, return_date, rental_company=None):
        print(f"Mock ExpediaAPI.rent_car called with car_type={car_type}, pickup_location={pickup_location}, pickup_date={pickup_date}, return_date={return_date}, rental_company={rental_company}")
        return f"Rented {car_type} from {pickup_location} from {pickup_date} to {return_date}"
    
    def book_experience(self, experience_name, location, date, participants=1):
        print(f"Mock ExpediaAPI.book_experience called with experience_name={experience_name}, location={location}, date={date}, participants={participants}")
        return f"Booked experience {experience_name} in {location} on {date} for {participants} participants"
    
    def book_cruise(self, cruise_name, departure_port, departure_date, return_date, cabin_type=None):
        print(f"Mock ExpediaAPI.book_cruise called with cruise_name={cruise_name}, departure_port={departure_port}, departure_date={departure_date}, return_date={return_date}, cabin_type={cabin_type}")
        return f"Booked cruise {cruise_name} from {departure_port} from {departure_date} to {return_date}"

# Mock WalletAPI class
class WalletAPI:
    def __init__(self, policy_system=None):
        self.policy_system = policy_system
        print("Mock WalletAPI initialized")
    
    def add_credit_card(self, card_name, card_type, card_number, card_pin):
        print(f"Mock WalletAPI.add_credit_card called with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}")
        return f"Added credit card {card_name} of type {card_type}"
    
    def remove_credit_card(self, card_name):
        print(f"Mock WalletAPI.remove_credit_card called with card_name={card_name}")
        return f"Removed credit card {card_name}"
    
    def update_credit_card(self, card_name, card_type=None, card_number=None, card_pin=None):
        print(f"Mock WalletAPI.update_credit_card called with card_name={card_name}, card_type={card_type}, card_number={card_number}, card_pin={card_pin}")
        return f"Updated credit card {card_name}"
    
    def get_credit_card_info(self, card_name):
        print(f"Mock WalletAPI.get_credit_card_info called with card_name={card_name}")
        return f"Credit card info for {card_name}: Type: Visa, Number: ****-****-****-1234, Expiry: 12/25"

# Mock ContactManagerAPI class
class ContactManagerAPI:
    def __init__(self, policy_system=None):
        self.policy_system = policy_system
        print("Mock ContactManagerAPI initialized")
    
    def add_contact(self, name, phone, address, email, relation, birthday=None, notes=None):
        print(f"Mock ContactManagerAPI.add_contact called with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}")
        return f"Added contact {name} with relation {relation}"
    
    def remove_contact(self, name):
        print(f"Mock ContactManagerAPI.remove_contact called with name={name}")
        return f"Removed contact {name}"
    
    def update_contact(self, name, phone=None, address=None, email=None, relation=None, birthday=None, notes=None):
        print(f"Mock ContactManagerAPI.update_contact called with name={name}, phone={phone}, address={address}, email={email}, relation={relation}, birthday={birthday}, notes={notes}")
        return f"Updated contact {name}"
    
    def get_contact_info(self, name):
        print(f"Mock ContactManagerAPI.get_contact_info called with name={name}")
        return f"Contact info for {name}: Phone: 123-456-7890, Email: {name.lower()}@example.com, Address: 123 Main St"
    
    def get_names_by_relation(self, relation):
        print(f"Mock ContactManagerAPI.get_names_by_relation called with relation={relation}")
        return f"Contacts with relation {relation}: John Doe, Jane Smith"

# Register the mock classes with the app module
sys.modules['app.calendar'] = type('calendar', (), {'CalendarAPI': CalendarAPI})
sys.modules['app.expedia'] = type('expedia', (), {'ExpediaAPI': ExpediaAPI})
sys.modules['app.wallet'] = type('wallet', (), {'WalletAPI': WalletAPI})
sys.modules['app.contact_manager'] = type('contact_manager', (), {'ContactManagerAPI': ContactManagerAPI})

# Export the mock classes
app_module = sys.modules['app']
app_module.calendar = sys.modules['app.calendar']
app_module.expedia = sys.modules['app.expedia']
app_module.wallet = sys.modules['app.wallet']
app_module.contact_manager = sys.modules['app.contact_manager']

# Print a message to confirm that the mock modules are loaded
print("Mock app modules loaded successfully") 