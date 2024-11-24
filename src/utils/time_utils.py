from datetime import datetime, timedelta

class TimeUtils:
    @staticmethod
    def next_seconds(n):
        """Returns a datetime object n seconds from now."""
        return datetime.now() + timedelta(seconds=n)

    @staticmethod
    def past_seconds(n):
        """Returns a datetime object n seconds in the past."""
        return datetime.now() - timedelta(seconds=n)

    @staticmethod
    def next_minutes(n):
        """Returns a datetime object n minutes from now."""
        return datetime.now() + timedelta(minutes=n)

    @staticmethod
    def past_minutes(n):
        """Returns a datetime object n minutes in the past."""
        return datetime.now() - timedelta(minutes=n)

    @staticmethod
    def next_hours(n):
        """Returns a datetime object n hours from now."""
        return datetime.now() + timedelta(hours=n)

    @staticmethod
    def past_hours(n):
        """Returns a datetime object n hours in the past."""
        return datetime.now() - timedelta(hours=n)

    @staticmethod
    def next_days(n):
        """Returns a datetime object n days from now."""
        return datetime.now() + timedelta(days=n)

    @staticmethod
    def past_days(n):
        """Returns a datetime object n days in the past."""
        return datetime.now() - timedelta(days=n)

    @staticmethod
    def next_weeks(n):
        """Returns a datetime object n weeks from now."""
        return datetime.now() + timedelta(weeks=n)

    @staticmethod
    def past_weeks(n):
        """Returns a datetime object n weeks in the past."""
        return datetime.now() - timedelta(weeks=n)