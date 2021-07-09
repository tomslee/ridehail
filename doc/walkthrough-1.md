# Ride Hail Walkthrough

- [Ride Hail Walkthrough](#ride-hail-walkthrough)
  - [Driving around](#driving-around)
  - [Taking a trip](#taking-a-trip)
  - [Matching requests with vehicles](#matching-requests-with-vehicles)
  - [Graphing the city](#graphing-the-city)

## Driving around

First, let's see a city and a vehicle. The city is simply a square grid with a size. It could be any city, and that means can use it to compare cities without getting tangled in detail. Right now it just has a *size*, given by the length of one side, _C_ (for City).

The vehicle is represented by the blue triangle. It drives around the city, turning at random, at a constant speed. One odd thing is that if it goes off one edge of the city it reappears opposite. The city is shaped like a doughnut and, for now at any rate, this means that all the blocks in the city are identical.

```bash
python ridehail.py walkthrough/one_vehicle.config
```

[![IMAGE ALT TEXT](http://img.youtube.com/vi/3fOJkNjOK2M/0.jpg)](http://www.youtube.com/watch?v=3fOJkNjOK2M "One vehicle animation")

## Taking a trip

In this video, a ride is requested, the car accepts the request, takes the passenger to their destination, and drops them off. Then the process repeats.

The ride request is shown by a red disc. The destination doesn't show up right away, to reflect that fact that in most cases, ridehail platforms do not show drivers the destination when they get a ride request.

The request is routed to the driver, who accepts it. The vehicle changes to an amber or orange triangle. The blue triangle shows a vehicle in its "idle" state, while the orange shows it is "dispatched" or "picking up" the passenger.

Once the vehicle picks up the passenger, it changes to green and the destination appears as a purple star. The vehicle takes the passenger to the destination, drops them off, and turns blue again to show that it has returned to the idle state.

In this case, the pickup and dropoff locations are chosen randomly, although zero-length trips are not allowed. A little thought shows that the the longest trip is length _C_ (e.g., from the "centre" intersection to one of the corners), and the average trip length <_L_> is going to converge on _C_/2.

In the ridehail world, these three phases of a vehicle's activity have names:

- _P1_ is the idle phase (blue).
- _P2_ is the dispatch phase (orange). The _P1_ and _P2_ phases together are sometimes called "headless".
- _P3_ is the busy or paid phase (green), where there is actually a passenger in the vehicle.

 These phases have been the subject of disputes within the industry. In the early days there were insurance questions (is a driver in phase _P2_ driving commercially?) Is a driver in phase _P1_ working?

 For now, we just watch what happens. I find it a bit hypnotic.

```bash
python ridehail.py walkthrough/take_a_trip.config
```

[![IMAGE ALT TEXT](http://img.youtube.com/vi/QtOE7FKcNoM/0.jpg)](https://youtu.be/watch?v=QtOE7FKcNoM "Taking a trip")

This gives us all the essentials for the model: a city, a vehicle, a trip; vehicles in _P1_, _P2_, and _P3_ phases; a passenger requesting, waiting, getting picked up, riding, getting dropped off. And then it all starts again.

## Matching requests with vehicles

The next video shows five vehicles, and trip requests are a bit more frequent. When a request is made it it directed to the nearest available (blue / _P1_) vehicle, who always accepts it. You can see that over time, vehicles spend some time in each of the phases; also that the time a request has to wait is variable depending on where the nearest vehicle is.

```bash
python ridehail.py walkthrough/five_vehicles.config
```

[![IMAGE ALT TEXT](http://img.youtube.com/vi/7KJ0XWdDZRo/0.jpg)](https://youtu.be/watch?v=7KJ0XWdDZRo "Matching requests: five vehicles")

## Graphing the city

At this point, the map visualization becomes cluttered. To glean more useful information from the simulation, it is better to graph city-wide averages, and that's what the next video does.

As all the vehicles are driving at a constant pace, showing them drive smoothly between the intersections is purely for visual effect. The natural unit of time for this simulation is the time it takes a vehicle to travel one block. A "block" is both a time and a distance here - you may want to think of it as roughly a minute. Once we drop the map visualization and just plot the graph we can get rid of all those intermediate steps and jump from intersection to intersection, which makes the simulation a lot faster. Most of the time up in what we've seen up to now is actually doing the visualization.

At each time step (each "block"), the chart plots the fraction of vehicles in each state as solid lines. It also shows the average trip length (as a fraction of city size _C_), and the wait time _W_ (as a fraction of the overall trip length). All these values are factional and so fit onto the same graph naturally, and they are averaged over 20 periods for smoothness.

```bash
python ridehail.py walkthrough/five_vehicles_graph.config
```

[![IMAGE ALT TEXT](http://img.youtube.com/vi/6cTbIy3Ayxo/0.jpg)](https://youtu.be/watch?v=6cTbIy3Ayxo "Graphing the city")

At the beginning of the simulation the vehicles are all idle, which is artificial, but after 50 intervals the values are starting to average out -- although not completely. Some observations:

- This is still a very small simulation. The average trip length is <_L_> = 0.37 * _C_. If we take one block as a minute, this is about a two or three minute trip.
- The fraction of the total trip that the passenger spends waiting is significant: _W_ = <(_w_ / (_w_ + _L_))> = 0.29, so the actual wait time _w_ is about a minute.
- The drivers here are only being paid for about a fifth of the time they are driving (_P1_ = 0.2). The fare that the passenger pays has to cover the driver's expenses for all those other minutes as well as for the minutes on the trip.

Later on, each of these will be investigated more.
