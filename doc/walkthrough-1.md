# Ride Hail Walkthrough

# Driving around

First, let's see a city and a vehicle. The city is simply a square grid with a size. It could be any city, and that means can use it to compare cities without getting tangled in detail. Right now it just has a *size*, given by the length of one side, _L_.

The vehicle is represented by the blue triangle. It drives around the city, turning at random, at a constant speed. One odd thing is that if it goes off one edge of the city it reappears opposite. The city is shaped like a doughnut and, for now at any rate, this means that all the blocks in the city are identical.

```bash
python ridehail.py walkthrough/one_vehicle.config
```

[![IMAGE ALT TEXT](http://img.youtube.com/vi/3fOJkNjOK2M/0.jpg)](http://www.youtube.com/watch?v=3fOJkNjOK2M "One vehicle animation")

# Taking a trip

In this video, a ride is requested, the car accepts the request, takes the passenger to their destination, and drops them off. Then the process repeats.

The ride request is shown by a red disc. The destination doesn't show up right away, to reflect that fact that in most cases, ridehail platforms do not show drivers the destination when they get a ride request.

The request is routed to the driver, who accepts it. The vehicle changes to an amber or orange triangle. The blue triangle shows a vehicle in its "idle" state, while the orange shows it is "dispatched" or "picking up" the passenger.

Once the vehicle picks up the passenger, it changes to green and the destination appears as a purple star. The vehicle takes the passenger to the destination, drops them off, and turns blue again to show that it has returned to the idle state.

In the ridehail world, these three phases of a vehicle's activity have names:

- _P1_ is the idle (blue) phase.
- _P2_ is the dispatched (orange) phase. The _P1_ and _P2_ phases together are sometimes called "headless".
- _P3_ is the busy (green) phase, where there is actually a passenger in the vehicle.

 These phases have been the subject of disputes within the industry. In the early days there were insurance questions (is a driver in phase _P2_ driving commercially?) Is a driver in phase _P1_ working?

 For now, we just watch what happens. I find it a bit hypnotic.

```bash
python ridehail.py walkthrough/take_a_trip.config
```

[![IMAGE ALT TEXT](http://img.youtube.com/vi/QtOE7FKcNoM/0.jpg)](https://youtu.be/watch?v=QtOE7FKcNoM "Taking a trip")

