from PolicySystem import PolicySystem

if __name__ == "__main__":
    policy_system = PolicySystem()

    # Register CalendarAPI with the policy system
    policy_system.register_api(CalendarAPI)

    # Add example policy rules
    policy_system.add_policy({"resource_value_specification": "Year", "action": "Read", "time": "Future"})
    policy_system.add_policy({"resource_value_specification": "Month", "action": "Read", "time": "Future"})

    calendar_api = CalendarAPI()

    # Test a valid read operation (should be allowed because "Month" subsumes "Hour")
    try:
        start_time = datetime.now() + timedelta(days=30)  # Future date
        duration = timedelta(hours=1)
        calendar_api.read(start_time=start_time, duration=duration)
        print("Read operation allowed.")
    except PermissionError as e:
        print(e)

    # Test an invalid write operation (should not be allowed for past dates)
    try:
        start_time = datetime.now() - timedelta(days=365)  # Past date
        duration = timedelta(hours=1)
        calendar_api.reserve(start_time=start_time, duration=duration, desc="Meeting")
        print("Reserve operation allowed.")
    except PermissionError as e:
        print(e)
