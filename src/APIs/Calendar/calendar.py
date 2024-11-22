class CalendarAPI:
    @annotate_calendar
    @policy_interceptor
    def reserve(self, *args, **kwargs):
        print("Reserving an entry with:", kwargs)

    @annotate_calendar
    @policy_interceptor
    def read(self, *args, **kwargs):
        print("Reading entries with:", kwargs)

    @annotate_calendar
    @policy_interceptor
    def check_available(self, *args, **kwargs):
        print("Checking availability with:", kwargs)

    @export_attributes
    def get_attributes(self):
        return self.get_attributes.attributes
