from datetime import datetime, timedelta
from app.calendar import CalendarAPI
from src.utils.time_utils import TimeUtils
from src.policy_system.policy_system import PolicySystem
import time

if __name__ == "__main__":
    policy_system = PolicySystem()

    # Register CalendarAPI with the policy system
    policy_system.register_api(CalendarAPI)

    # Add example policy rules with fixed time calculations
    policy_system.add_policy({
        "granular_data": "Calendar:*",
        "actions": "*",
        "data_access": "r",
        "time": "Future",  # Allow actions in the present time
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
    print("\nTesting policy expiry in 10 seconds:")

    # Test a valid read operation (should be allowed immediately)
    try:
        start_time = datetime.now() + timedelta(seconds=65)  # Within the next 10 seconds
        duration = timedelta(seconds=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed immediately.")
    except PermissionError as e:
        print("Read operation not allowed immediately:", e)

    # Wait for 10 seconds to let the policy expire
    time.sleep(13)

    # Test an invalid read operation (should not be allowed after 10 seconds)
    try:
        start_time = datetime.now() + timedelta(seconds=111)  # After the policy expiry
        duration = timedelta(seconds=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed after expiry.")
    except PermissionError as e:
        print("Read operation not allowed after expiry:", e)
