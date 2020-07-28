# Ridehail animation

Personal project. You're welcome to use it but don't expect anything.

- [Wait / Busy tradeoff](#wait-/-busy-tradeoff)
- [Deadheading](#deadheading)
  - [Schaller](#schaller)
  - [John Barrios:](#john-barrios:)
  - [Cramer and Kruger](#cramer-and-kruger)
  - [TNCs Today: SFCTA report (2017)](<#tncs-today:-sfcta-report-(2017)>)
  - [Alejandro Henao, University of Colorado at Denver, Master's Thesis (2013)](<#alejandro-henao,-university-of-colorado-at-denver,-master's-thesis-(2013)>)
  - [Uber blog (https://www.uber.com/en-GB/blog/london/how-efficiency-benefits-riders-and-partners/)](<#uber-blog-(https://www.uber.com/en-gb/blog/london/how-efficiency-benefits-riders-and-partners/)>)

## Wait / Busy tradeoff

Inspired by a New York Times animation of several years ago, this is a simple simulation of a ridehail system, for exploring how wait times and driver efficiency (fraction busy) are related.

- NYT simulation: [here](https://www.nytimes.com/interactive/2017/04/.0technology/uber-drivers-psychological-tricks.html)
- Uber reply: [here](https://www.uber.com/newsroom/faster-pickup-times-mean-busier-drivers/)

## Deadheading

Deadheading refers to the time or distance without a rider in the car. If a driver waits where they are between rides, these two measures may be quite different.

### Schaller

From Bruce Schaller ("The New Automobility") [here][.http://www.challerconsult.::com/rideservices/automobility.pdf]

> Working against the efficiency of Uber and Lyft is the large proportion of mileage without a paying passenger in the vehicle. For a typical passenger trip of 5.2 miles, a TNC driver travels three miles waiting to get pinged and then going to pick up the fare.

This corresponds to a P3 fraction of about 65%.

Insurance commonly uses these phases

- Phase 0: App is off. Your personal policy covers you.
- Phase 1: App is on, you're waiting for ride request. ...
- Phase 2: Request accepted, and you're en route to pick up a passenger. ...
- Phase 3: You have passengers in the car.

Schaller from Empty Seats, Full Streets:

In 2017 TNCs had 55K hours with passengers in the Manhattan Central Business District (CBD), and 37K hours without passengers.

> While yellow cabs were occupied with passengers 67 percent of the time in 2013, the utilization rate for combined taxi/TNC operations dropped to 62 percent in 2017.

### John Barrios:

> “Rideshare companies often subsidize drivers to stay on the road even when utilization is low, to ensure that supply is quickly available,” they wrote.

### Cramer and Kruger

In [Disruptive Change In The Taxi Business: The Case Of Uber](https://www.nber.org/papers/w22083.pdf), the authors write:

> Capacity utilization is measured either by the fraction of time that drivers have a farepaying passenger in the car or by the fraction of miles that drivers log in which a passenger is in the car. Because we are only able to obtain estimates of capacity utilization for taxis for a handful of major cities – Boston, Los Angeles, New York, San Francisco and Seattle – our estimates should be viewed as suggestive. Nonetheless, the results indicate that UberX drivers, on average, have a passenger in the car about half the time that they have their app turned on, and this average varies relatively little across cities, probably due to relatively elastic labor supply given the ease of entry and exit of Uber drivers at various times of the day. In contrast, taxi drivers have a passenger in the car an average of anywhere from 30 percent to 50 percent of the time they are working, depending on the city. Our results also point to higher productivity for UberX drivers than taxi drivers when the share of miles driven with a passenger in the car is used to measure capacity utilization. On average, the capacity utilization rate is 30 percent higher for UberX drivers than taxi drivers when measured by time, and 50 percent higher when measured by miles, although taxi data are not available to calculate both measures for the same set of cities.

> Four factors likely contribute to the higher utilization rate of UberX drivers: 1) Uber’s more efficient driver-passenger matching technology; 2) Uber’s larger scale, which supports faster matches; 3) inefficient taxi regulations; and 4) Uber’s flexible labor supply model and surge pricing, which more closely match supply with demand throughout the day.

Capacity utilization (% of hours with a passenger).

- Boston: 47% TNC, NA Taxi
- LA: 52% TNC, NA Taxi
- NYC: 51% TNC, 48% Taxi
- SF: 55% TNC, 38% Taxi
- Seattle: 44% TNC, NA Taxi

### TNCs Today: SFCTA report (2017)

The report is [here](https://archive.sfcta.org/sites/default/files/content/Planning/TNCs/TNCs_Today_112917.pdf).

In the report, "Out-of-service VMT [vehicle miles travelled] refers to the vehicle miles traveled while circulating to pickup a passenger." It is not clear if this includes P3 time and distance.

> Approximately 20% of total TNC VMT are out-of-service miles. This is significantly lower than the more than 40% of taxi VMT that are out-of-service miles.

Table 4 (weekdays) is similar to tables 5 and 6 (weekends).

- Trips: 170K (TNC), 14K (Taxi)
- Average trip length: 3/3 miles (TNC), 4/6 miles (taxi)
- Average in-service trip length: 2.6 miles (TNC), 2.6 miles (taxi)
- Average out-of-service trip length: 0.7 miles (TNC), 2.0 miles (taxi)
- Percent out-of-service trip length: 21% (TNC), 44% (taxi)

### Alejandro Henao, University of Colorado at Denver, Master's Thesis (2013)

Time (mins):

- Available: 12
- Pickup: 6
- Wait for pax: 1
- Ride: 15
- Going home at end of day: 22

Distance (miles)

- Available: 1.5
- Pickup: 1.5
- Trip: 7
- Going home at end of day: 12

> The time efficiency rate of a ridesourcing driver based on the time a passenger is in the car and total time from driver log-in to log-out (not accounting for the commute at the end of the shift) is 41.3%, meaning that I, as a driver, during my shift hours spent more time without a passenger than with one in the car... When accounting for commuting time at end of shift, the time efficiency rate drops to 39.3% of total time... Lyft and Uber drivers travel an additional 69.0 miles in deadheading for every 100 miles they are with passengers.

### Uber blog

This Uber blog post from 2015 is about [efficiency](https://www.uber.com/en-GB/blog/london/how-efficiency-benefits-riders-and-partners/).

> Since uberX launched in London in July 2013, average pick-up times – the time between requesting and your car arriving – have reduced from 6 and a half minutes to just over 3 minutes.

(2013 - 6.3 minutes, 2014 - 4.3, 2015 - 3.1)

> Back in 2013, when uberX launched in London, partners had a passenger in their car for 16 minutes of every hour. Now that number has more than doubled to 34 minutes.
