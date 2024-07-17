class Dispatch:

    def __init__(self):
        pass

    def dispatch_vehicles(self, unassigned_trips):
        """
        All trips without an assigned vehicle make a request.
        Dispatch a vehicle to each trip.
        """
        dispatcher = self._get_dispatch_function()
        city_size = self.city.city_size
        return dispatcher(unassigned_trips, city_size)

    def _get_dispatch_function(self):
        """
        All trips without an assigned vehicle make a request.
        Dispatch a vehicle to each trip.
        """
        if self.dispatch_method == DispatchMethod.DEFAULT:
            dispatcher = self._dispatch_vehicles_default
        elif self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
            dispatcher = self._dispatch_vehicles_forward_dispatch
        elif self.dispatch_method == DispatchMethod.P1_LEGACY:
            dispatcher = self._dispatch_vehicles_p1_legacy
        elif self.dispatch_method == DispatchMethod.RANDOM:
            dispatcher = self._dispatch_vehicles_random
        else:
            logging.error(f"Unrecognized dispatch method {self.dispatch_method}")
            sys.exit(-1)
        return dispatcher
