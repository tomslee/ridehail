# Ridehail animation

Personal project. You're welcome to use it but don't expect anything.

## Wait / Busy tradeoff

Inspired by a New York Times animation of several years ago, this is a simple simulation of a ridehail system, for exploring how wait times and driver efficiency (fraction busy) are related.

- NYT simulation: [here](https://www.nytimes.com/interactive/2017/04/.0technology/uber-drivers-psychological-tricks.html)
- Uber reply: [here](https://www.uber.com/newsroom/faster-pickup-times-mean-busier-drivers/)

## Deadheading

From Bruce Schaller ("The New Automobility") [here][.http://www.challerconsult.::com/rideservices/automobility.pdf]

> Working against the efficiency of Uber and Lyft is the large proportion of mileage without a paying passenger in the vehicle. For a typical passenger trip of 5.2 miles, a TNC driver travels three miles waiting to get pinged and then going to pick up the fare.

This corresponds to a P3 fraction of about 65%.

Insurance commonly uses these phases

- Phase 0: App is off. Your personal policy covers you.
- Phase 1: App is on, you're waiting for ride request. ...
- Phase 2: Request accepted, and you're en route to pick up a passenger. ...
- Phase 3: You have passengers in the car.

John Barrios:

> “Rideshare companies often subsidize drivers to stay on the road even when utilization is low, to ensure that supply is quickly available,” they wrote.
