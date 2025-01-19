from datetime import datetime, timedelta
from app.calendar import CalendarAPI
from src.utils.time_utils import TimeUtils
from src.policy_system.policy_system import PolicySystem
import time

def test1():
    policy_system = PolicySystem()

    # Register CalendarAPI with the policy system
    policy_system.register_api(CalendarAPI)

    # Add example policy rules with fixed time calculations
    policy_system.add_policy({
        "granular_data": "Calendar:Year(1995)::Calendar:Month(Oct)",
        "data_access": "r",
        "position": "Next",  # Allow actions in the present time
        "expiry": TimeUtils.next_seconds(10)  # Policy expires in 10 seconds
    })

    calendar_api = CalendarAPI(policy_system)

    # Test a valid read operation (should be allowed if within 5 minutes)
    try:
        start_time = datetime.now() + timedelta(minutes=3)  # Within the next 5 minutes
        duration = timedelta(minutes=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test an invalid read operation (should not be allowed if after 5 minutes)
    try:
        start_time = datetime.now() + timedelta(minutes=10)  # After the next 5 minutes
        duration = timedelta(minutes=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test case for policy expiry in 10 seconds
    print("\nTesting policy expiry in 5 seconds:")
    time.sleep(5)

    # Test a valid read operation (should be allowed immediately)
    try:
        start_time = datetime.now() + timedelta(seconds=65)  # Within the next 10 seconds
        duration = timedelta(seconds=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed immediately.")
    except PermissionError as e:
        print("Read operation not allowed immediately:", e)

    # Wait for 10 seconds to let the policy expire
    print("\nTesting policy expiry in 11 seconds:")
    time.sleep(6)

    # Test an invalid read operation (should not be allowed after 10 seconds)
    try:
        start_time = datetime.now() + timedelta(seconds=111)  # After the policy expiry
        duration = timedelta(seconds=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed after expiry.")
    except PermissionError as e:
        print("Read operation not allowed after expiry:", e)

if __name__ == "__main__":
    policy_system = PolicySystem()
    policy_system.register_api(CalendarAPI)

    policy_system.add_policy({
        "granular_data": "Calendar:Month",
        "data_access": "Read",
        "position": "Next",  # Allow actions in the present time
    })

    calendar_api = CalendarAPI(policy_system)

    try:
        start_time = datetime.now() + timedelta(minutes=15) # Within the next 5 minutes
        duration = timedelta(weeks=13)
        calendar_api.read(start_time=start_time, duration=duration)
        print("\033[1;32;40mRead operation allowed.\033[0m")
    except PermissionError as e:
        print("\033[1;31;40m", e, "\033[0m")

    try:
        start_time = datetime.now() + timedelta(minutes=15) # Within the next 5 minutes
        duration = timedelta(weeks=13)
        calendar_api.reserve(start_time=start_time, duration=duration)
        print("\033[1;32;40mRead operation allowed.\033[0m")
    except PermissionError as e:
        print("\033[1;31;40m", e, "\033[0m")