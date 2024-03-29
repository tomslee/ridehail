# Cities

Deadheading refers to the time or distance without a rider in the car. If
a driver waits where they are between rides, these two measures may be quite
different.

Ride-hail insurance commonly uses these phases

- Phase 0: App is off. Your personal policy covers you.
- Phase 1: App is on, you're waiting for ride request.
- Phase 2: Request accepted, and you're en route to pick up a passenger.
- Phase 3: You have passengers in the car.

## City simulations

General approaches.

- [Toronto](toronto.md)

## Chicago

### Chicago open data

Todd W Schneider has built some dashboards from Chicago open data: [Taxi and Ridehailing Usage in Chicago](https://toddwschneider.com/dashboards/chicago-taxi-ridehai a ling-data/ HeHe p ). He points to several data sets:

#### Transportation Network Providers - Trips 

The data set is [here](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips/m6dm-72p): "All trips, starting November 2018, reported by Transportation Network Providers (sometimes called rideshare companies) to the City of Chicago as part of routine reporting required by ordinance".

Columns are:
- Trip ID
- Trip Start Timestamp
- Trip End Timestamp
- Trip Seconds
- Trip Miles
- Pickup Census Tract
- Dropoff Census Tract
- Pickup Community Area
- Dropoff Community Area
- Fare
- Tip
- Additional Charges
- Trip Total
- Shared Trip Authorized
- Trips Pooled
- Pickup Centroid Latitude
- Pickup Centroid Longitude
- Pickup Centroid Location
- Dropoff Centroid Latitude
- Dropoff Centroid Longitude
- Dropoff Centroid Location

While the daa includes the fare, it does not seem to include the pay for the driver. Also, it does not include any driver/vehicle-related information

#### Transportation Network Providers - Drivers

The data set is [here](https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Drivers/j6wf-. Each834c). Each row is a driver. 

Columns are:
- MONTH_REPORTED
- DRIVER_START_MONTH
- CITY
- STATE
- ZIP
- NUMBER_OF_TRIPS
- MULTIPLE_TNPs

## Reports

### Schaller, The New Automobility

From Bruce Schaller (_The New Automobility_) [here](http://www.schallerconsult.com/rideservices/automobility.pdf).

> Working against the efficiency of Uber and Lyft is the large proportion of
> mileage without a paying passenger in the vehicle. For a typical passenger
> trip of 5.2 miles, a TNC driver travels three miles waiting to get pinged and
> then going to pick up the fare.

This corresponds to a P3 fraction of about 65% by distance.

Here is a table, modified from Schaller:

Table 7. Passenger miles and total miles for TNC trips

| City          | P3  | P2  | P1  | (driver-miles) |
| ------------- | --- | --- | --- | -------------- |
| New York City | 59  | 08  | 33  | 8.6            |
| Chicago       | 59  | 10  | 31  | 7.9            |
| San Francisco | 67  | 10  | 23  | 6.1            |
| Denver        | 71  | 14  | 15  | 9.9            |

Sources: Carolyn Said, “Lyft trips in San Francisco more efficient than
personal cars, study finds,” San Francisco Chronicle, January 5, 2018;
Alejandro Henao, “Impacts of Ridesourcing–Lyft and Uber –on Transportation
including VMT, Mode Replacement, Parking, and Travel Behavior,” Doctoral
Dissertation Defense, January 2017; and author’s analysis of NYC Taxi and
Limousine Commission TNC trip data. Mileage with passenger of 63% is
consistent with statewide California average of 61%; see Simi Rose George
and Marzia Zafar, “Electrifying the Ride-Sourcing Sector in California,”
California Public Utilities Commission, April 2018.

Schaller from Empty Seats, Full Streets:

> In 2017 TNCs had 55K hours with passengers in the Manhattan Central Business
> District (CBD), and 37K hours without passengers (60% busy).

> While yellow cabs were occupied with passengers 67 percent of the time in
> 2013, the utilization rate for combined taxi/TNC operations dropped to 62
> percent in 2017.

## Cramer and Krueger

In [Disruptive Change in the Taxi Business: The Case of Uber](https://www.nber.org/papers/w22083.pdf), Cramer and Krueger write:

> Capacity utilization is measured either by the fraction of time that drivers
> have a farepaying passenger in the car or by the fraction of miles that
> drivers log in which a passenger is in the car. Because we are only able to
> obtain estimates of capacity utilization for taxis for a handful of major
> cities – Boston, Los Angeles, New York, San Francisco and Seattle – our
> estimates should be viewed as suggestive. Nonetheless, the results indicate
> that UberX drivers, on average, have a passenger in the car about half the
> time that they have their app turned on, and this average varies relatively
> little across cities, probably due to relatively elastic labor supply given
> the ease of entry and exit of Uber drivers at various times of the day. In
> contrast, taxi drivers have a passenger in the car an average of anywhere
> from 30 percent to 50 percent of the time they are working, depending on the
> city. Our results also point to higher productivity for UberX drivers than
> taxi drivers when the share of miles driven with a passenger in the car is
> used to measure capacity utilization. On average, the capacity utilization
> rate is 30 percent higher for UberX drivers than taxi drivers when measured
> by time, and 50 percent higher when measured by miles, although taxi data are
> not available to calculate both measures for the same set of cities.
>
> Four factors likely contribute to the higher utilization rate of UberX
> drivers: 1) Uber’s more efficient driver-passenger matching technology; 2)
> Uber’s larger scale, which supports faster matches; 3) inefficient taxi
> regulations; and 4) Uber’s flexible labor supply model and surge pricing,
> which more closely match supply with demand throughout the day.

They report these capacity utilizations (% of hours with a passenger).

| City    | TNC | Taxi | TNC Distance | Taxi Distance |
| ------- | --- | ---- | ------------ | ------------- |
| Boston  | 47% | NA   |              |               |
| LA      | 52% | NA   | 64%          | 41%           |
| NYC     | 51% | 48%  |              |               |
| SF      | 55% | 38%  |              |               |
| Seattle | 44% | NA   | 55%          | 39%           |

Also, for LA and Seattle, they report capacity utilization rates by distance
(percent of miles driven with a passenger). These have been added in above. The
higher distance values show that some drivers may stay still when waiting for
a ride.

### TNCs Today: SFCTA report (2017)

The report is
[here](https://archive.sfcta.org/sites/default/files/content/Planning/TNCs/TNCs_Today_112917.pdf).
In the report, "In-service VMT refers to the vehicle miles traveled when
transporting a passenger. Out-of-service VMT [vehicle miles travelled] refers
to the vehicle miles traveled while circulating to pickup a passenger."
It is not clear if this includes P3 time and distance.

> Approximately 20% of total TNC VMT are out-of-service miles. This is
> significantly lower than the more than 40% of taxi VMT that are
> out-of-service miles... The greater efficiencies of TNCs, as reflected
> in a lower share of out-of-service miles, are likely primarily a reflection
> of the larger fleets of TNC drivers operating on the road at any given time,
> enabling shorter distances to pickup locations.

Table 4 (weekdays) is similar to tables 5 and 6 (weekends).

| Quantity                           | TNC       | Taxi      |
| ---------------------------------- | --------- | --------- |
| Trips                              | 170K      | 14K       |
| Average trip length                | 3.3 miles | 4.6 miles |
| Average in-service trip length     | 2.6 miles | 2.6 miles |
| Average out-of-service trip length | 0.7 miles | 2.0 miles |
| Percent out-of-service trip length | 21%       | 44%       |

### Alejandro Henao, University of Colorado at Denver, Master's Thesis (2013)

Based on his own experience.

| Phase                    | Time (minutes) |
| ------------------------ | -------------- |
| Available                | 12             |
| Pickup                   | 6              |
| Wait for pax             | 1              |
| Ride                     | 15             |
| Going home at end of day | 22             |

| Phase                    | Distance (miles) |
| ------------------------ | ---------------- |
| Available                | 1.5              |
| Pickup                   | 1.5              |
| Trip                     | 7                |
| Going home at end of day | 12               |

### Uber blog

This Uber blog post from 2015 is about [efficiency](https://www.uber.com/en-GB/blog/london/how-efficiency-benefits-riders-and-partners/).

> Since uberX launched in London in July 2013, average pick-up times – the time
> between requesting and your car arriving – have reduced from 6 and a half
> minutes to just over 3 minutes.

| Year | pick-up time (minutes) | P3 % by time |
| ---- | ---------------------- | ------------ |
| 2013 | 6.3                    | 17           |
| 2014 | 4.3                    |              |
| 2015 | 3.1                    | 57           |

> Back in 2013, when uberX launched in London, partners had a passenger in
> their car for 16 minutes of every hour. Now that number has more than doubled
> to 34 minutes.

### Fehr & Peers in Boston (2019)

See
[Streetsblog](https://mass.streetsblog.org/2019/08/08/uberlyft-admit-responsibility-for-a-significant-share-of-bostons-traffic/)
report or the full report by Fehr and Peers
[here](https://drive.google.com/file/d/1FIUskVkj9lsAnWJQ6kLhAhNoVLjfFdx3/view).
The study was jointly commissioned by Uber and Lyft

"In the 4-county Boston metropolitan region (which encompasses Suffolk,
Norfolk, Middlesex and Essex counties), Uber and Lyft drivers drove between 20
million and 26 million miles without any passengers in the month of September
2018 – nearly as much driving as they did with passengers."

Reminder: P1 = idle; P2 = picking up; P3 with passenger.

Table 3 of the report. TNC Vehicle Miles Traveled (VMT), in millions. The Total
and percentage columns use the mid-point.

Note that P3 values **by time** (as opposed to by distance) may be lower.
During P1 time drivers may drive less quickly (if at all) and so P3 time by
distance will be higher.

| Region        | P1 (low) | P1 (High) | P1 (Mid) | P2   | P3    | Total | P3 % | P2 % | P1 % |
| ------------- | -------- | --------- | -------- | ---- | ----- | ----- | ---- | ---- | ---- |
| Boston        | 14.7     | 20.6      | 17.6     | 5.3  | 28.3  | 51.2  | 0.55 | 0.10 | 0.34 |
| Chicago       | 29.7     | 40.8      | 35.3     | 9.1  | 54.6  | 99.0  | 0.55 | 0.09 | 0.36 |
| Los Angeles   | 38.3     | 63.2      | 50.7     | 17.7 | 104.1 | 172.5 | 0.60 | 0.10 | 0.29 |
| San Francisco | 31.5     | 46.6      | 30.1     | 11.9 | 75.2  | 117.2 | 0.64 | 0.10 | 0.26 |
| Seattle       | 9.7      | 15.6      | 12.7     | 2.9  | 17.6  | 33.2  | 0.53 | 0.09 | 0.38 |
| Washington DC | 24.4     | 33.5      | 28.9     | 8.1  | 46.0  | 83.0  | 0.55 | 0.10 | 0.35 |
| Average %     | 28%      | 37%       | 33%      | 10%  | 58%   | 1.0   | 0.58 | 0.10 | 0.33 |

### Competing reports in Seattle

In July 2020 two reports on ride-hailing in Seattle were released.

- [Platform Driving in Seattle](https://digitalcommons.ilr.cornell.edu/cgi/viewcontent.cgi?article=1070&context=reports) by Louis Hyman, Erica L. Groshen, Adam Seth Litwin, Martin T. Wells and
  Kwelina P. Thompson was a collaboration with Uber and the authors had access
  to detailed (ride-level) data for one week.

- [A Minimum Compensation Standard for Seattle TNC Drivers](https://irle.berkeley.edu/files/2020/07/Parrott-Reich-Seattle-Report_July-2020.pdf)
  by James A. Parrott and Michael Reich was commissioned by the City of Seattle.

While they disagree on many things, the picture they paint of capacity
utilization is not that different.

Here is Hyman et al. (adapted from Chart 1.7, p 35): median weekly hours by
period by driver type:

| Driver Type      | P3  | P2  | P1  |
| ---------------- | --- | --- | --- |
| Full-time        | 57% | 14% | 30% |
| Part-time        | 56% | 15% | 30% |
| Committed Casual | 60% | 10% | 30% |
| Casual           | 0   | 1   | 0   |
| All              | 60% | 10% | 30% |

And here is P&R (Exhibit 30, p52):

| Data source | P3  | P2  | P1  |
| ----------- | --- | --- | --- |
| Uber        | 51% | 13% | 36% |
| Lyft        | 47% | 13% | 40% |

### Summary

From several North American cities, we have approximate numbers like this:

| City          | Year  | Source           | P3 % | P2 % | P1 % | Note     |
| ------------- | ----- | ---------------- | ---- | ---- | ---- | -------- |
| Seattle       | 2020  | Hyman            | 57   | 14   | 30   |          |
| Seattle       | 2020  | P&R\*            | 55   | 15   | 30   |          |
| London        | 2015  | Uber             | 57   |      |      |          |
| London        | 2013  | Uber             | 17   |      |      |          |
| San Francisco | 2017  | SFCTA            | 79   |      | 21   | by miles |
| Boston        | 2014? | Cramer & Krueger | 47   |      |      |          |
| Los Angeles   | 2014? | Cramer & Krueger | 52   |      |      |          |
| New York City | 2014? | Cramer & Krueger | 51   |      |      |          |
| San Francisco | 2014? | Cramer & Krueger | 55   |      |      |          |
| New York City | 2018  | Schaller         | 65   |      |      | by miles |
| Manhattan CBD | 2017  | Schaller         | 60   |      |      | by miles |
| New York City | 2017  | Schaller         | 59   | 08   | 33   | by miles |
| Chicago       | 2017  | Henao            | 59   | 10   | 31   | by miles |
| San Francisco | 2017  | Said             | 67   | 10   | 23   | by miles |
| Denver        | 2017  | Henao            | 71   | 14   | 15   | by miles |

## Is my model compatible with these figures?

Some possibilities for city_size=40, request_rate</sub>=1.2. Reading off P1 30%:

For a lower request rate, of 0.8:

So: long trips and uniform distribution are needed for this level of capacity
utilization. It's at the upper end of what is geometrically possible.

Also: for the uniform cases, the results are independent of request rate: it
takes more drivers, but they end up at the same distribution. This is
surprising to me.

For uniform distributions, longer trips require more drivers to reach the 30%
P1 rate, but when they do so there is a higher capacity utilization and lower
pick-up time. Also a lower wait time. This may be said better as: for uniform
distributions, longer trips lead to higher P3 rates at a given number of
drivers, higher P2 values (they have to drive further to get their next drive),
and corresponding lower P1 values.

P3 percentages and number of drivers to support a steady state may both be
measures of efficiency.

## Simulating Manhattan

### Grid size (50\*50)

According to [William
Helmreich](https://en.wikipedia.org/wiki/William_B._Helmreich), New York City
has 120,000 blocks, and he should know because he walked them all over the
course of four years, for a total of 6163 miles (about 10K kilometers).

The figure of 120,000 blocks is reported in [a 2013 New Yorker
article](https://www.newyorker.com/books/page-turner/a-walker-in-the-city) on
Helmreich.

Manhattan is much smaller: from a [Quora
question](https://www.quora.com/Approximately-how-many-blocks-are-there-on-the-island-of-Manhattan):
220th street is the northernmost street, and some say it's about 250
blocks north to south. Another way to think about it is that Manhattan is about
13 miles with 20 blocks to the mile (1 block ~ 100 yards). At its widest point
Manhattan is 2.3 miles, but it is much narrower in other places. Someone else
says 2872 blocks.

One approach is area. Manhattan is 59.1 km<sup>2</sup> (call it 60), or
6\*10<sup>7</sup> m<sup>2</sup>. That's equivalent to 23 square miles (or
13 \* 1.75).

According to [Wikipedia](https://en.wikipedia.org/wiki/City_block): "the
standard block in Manhattan is about 264 by 900 feet (80 m × 274 m)", so
call that 100 \* 250m = 2.5\*10<sup>4</sup> m<sup>2</sup>.

Number of blocks = (6 \* 10<sup>7</sup>)/(2.5 \* 10<sup>4</sup>) ~ 2.5 \*
10<sup>3</sup>, which is the same as a 50\*50 grid.

### Traffic speed (1 block per minute)

In midtown Manhattan the average traffic speed is 4.7mph ([LA Times
2018](https://www.latimes.com/nation/la-na-new-york-traffic-manhattan-20180124-story.html#:~:text=The%20average%20speed%20of%20traffic%20in%20Midtown%20Manhattan%20is%204.7%20mph.,-New%20York%20thinks)).
Overall the average is probably higher though.

A block is the equivalent of 160m on one side (100 \* 250 ~ 160 \* 160) and
1 mile is 1600 meters, so 1 mile is 10 blocks. That suggests average traffic
speed is about 50 blocks (5 miles) per hour, which is close to one block per
minute.

There are 1440 minutes in a day.

### Trip request rates (250)

First look at overall volumes per day, using data collected by Todd Schneider
from NYC TLC and others, and presented on [Todd W. Schneider's web
site](https://toddwschneider.com/dashboards/nyc-taxi-ridehailing-uber-lyft-data/).
Schneider provides the code [On
GitHub](https://github.com/toddwschneider/nyc-taxi-data). These are all
"pre-pandemic" figures, from 2019 or so, and they are for all NYC,
not just for Manhattan.

- Number of ride-hail rides per day ~ 750K. (Does not include taxis)
- Number of Uber rides per day ~ 500K (2/3 of all ridehail rides)
- Number of unique ride-hail vehicles per month ~ 80K, most of which drove for Uber (quite a lot do both Uber and Lyft)
- Number of unique drivers per month is similar
- Number of monthly trips per vehicle ~ 200 (mean of 7 per day)
- Mean number of vehicles (or drivers) per day ~ 60K
- Mean daily trips per active vehicle ~ 13. (so total trips per day ~ 60K \* 13 = 780K, which matches number of ride-hail rides per day.
- Average days per month on the road ~ 19
- Average hours per day per vehicle ~ 6.
- Trips per vehicle per active hour ~ 2.
- Minutes per trip ~ 20 (hence utilization rate of 2/3 by hour)
- Trips-in-progress hours per day ~ 3.7
- Shared trips per day ~ 100K (fell off dramatically from 150K in 2018 to 100K in 2019, from 25% of trips to 15%).
- Shared trips per day: Uber went from 125K in 2018 to 50K in 2019; Lyft from 30K in 2018 to 50K in 2019.

From all these numbers, we can say about 750K rides per day is about 500 rides
per minute for all of NYC.

If 60K vehicles drive on 2/3 of the days in a month, then there may be 40K on
the roads any one day. If each drives for 6 hours, that's 1/4 of the
available hours, so there is a mean of 10K vehicles on the road in NYC at any
one time.

In 2017, Carol Atkinson-Palombo [concluded](https://trid.trb.org/view/1586848)
that "Having surged 40-fold, ridesourcing trips originating in the outer
boroughs now constitute 56% of the overall market." The "outer
boroughs" are all apart from Manhattan (that is, Brooklyn, Queens, The
Bronx, and Staten Island).

If this is true then using 50% we end up with, _on Manhattan_ (computing from
trip volume, 20 minutes per trip, and 2/3 utilization rate:

- 350K trips per day (= 250 trips per minute \* 1440 minutes per day)

- About 2 trips per vehicle hour, so that's about 180K vehicle hours or
  about 10M vehicle minutes.

- 7K drivers on the road each minute \* 1.4K minutes / day gives 10M, so
  that's about 7K on the road at once.

- Schaller (below) concludes 100K vehicle hours per day in Manhattan CBD so
  that's not too different, given different years and that the CBD is
  only part of Manhattan.

### Number of drivers (7000)

In December 2017, Bruce Schaller
[concluded](http://www.schallerconsult.com/rideservices/emptyseats.pdf) that
200K trips per day started or ended in the Manhattan Central Business District
(CBD), and that there are about 100K vehicle hours per day. He also concludes
that "setting aside overnight hours, there were an average of 9100 taxis
or TNCs in the CBD weekdays between 8 am and midnight in June 2017.

Another source
([ny.curbed.com](https://ny.curbed.com/2020/3/13/21178259/coronavirus-new-york-city-uber-lyft-transportation-drivers),
pulling from the NYT) says the ride-hailing industry "employs roughly
80,000 drivers in New York City". This maps well to Schneider above. If
half drive in Manhattan, and 1/4 are on the roads at any one time, then that
would be about 10K.

Another approach:

request rate _ trip length = cars _ busy fraction

cars = 250 trips per minute \* 20 minutes per trip / (2/3) = 7500

### Town simulation and maximum utilization rates

Demand = Request Rate; predicted = R \* <l> / Cost (<l> = 15)

| City size | Demand (R/period) | Cost | Drivers | Stable? | Predicted |
| --------- | ----------------- | ---- | ------- | ------- | --------- |
| 30        | 10                | 0.45 | 370     | Y       |           |
| 30        | 10                | 0.50 | 320     | Y       |           |
| 30        | 10                | 0.55 | 293     | Y       |           |
| 30        | 10                | 0.60 | 267     | Y       |           |
| 30        | 10                | 0.65 | 255     | Y       |           |
| 30        | 5                 | 0.45 | 180     | Y       | 167       |
| 30        | 5                 | 0.60 | 131     | Y       | 125       |
| 30        | 5                 | 0.65 | 125     | Y       | 116       |
| 30        | 5                 | 0.70 | &lt; 25 | N       | 107       |
| 30        | 3                 | 0.45 | 108     | Y       |           |
| 30        | 3                 | 0.55 | 88      | Y       |           |
| 30        | 3                 | 0.60 | 80      | Y       |           |
| 30        | 3                 | 0.65 | &lt; 40 | N       |           |
| 30        | 2                 | 0.50 | 64      | Y       |           |
| 30        | 2                 | 0.45 | 70      | Y       |           |
| 30        | 2                 | 0.55 | 60      | Y       |           |
| 30        | 2                 | 0.60 | &lt; 40 | N       |           |
| 30        | 1                 | 0.45 | 36      | Y       |           |
| 30        | 1                 | 0.50 | 33      | Y       |           |
| 30        | 1                 | 0.55 | 31      | Y       |           |
| 30        | 1                 | 0.60 | &lt; 25 | N       |           |
| 30        | 0.5               | 0.45 | 19      | Y       |           |
| 30        | 0.5               | 0.50 | 16      | Y       |           |
| 30        | 0.5               | 0.55 | 15      | Y       |           |
| 30        | 0.5               | 0.60 | 13      | ?       |           |

## Simulations and theory

### Simulations and theory 1

Yan et al [Dynamic Pricing and Matching in Ride-Hailing Platforms](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3258234).

Steady-state conditions

If number of drivers = L, Number of open drivers (available) = O, and the
number of trips per unit time is Y then

    L = O + \eta . Y + T . Y

where \\eta = en-route time and T = length of trip. This is something
I've derived earlier.

Apparently there is a result (Larson and Odoni 1981) that if open drivers are
distributed uniformly in an n-dimensional space, with constant travel speed and
a straight line between two points, then the expected en-route time is \\eta(O)
and satisfies

    \eta(O) ~ O ^ (-1/n)

So for two-dimensional roads, the en-route time is proportional to one over the
square root of the number of open drivers.

Uber data from San Francisco, with L = 30 per km^2 and T = 15 minutes, goes more linearly. Here is a summary

| Open Drivers | ETA (minutes) |
| ------------ | ------------- |
| 4            | 3.8           |
| 6            | 3.2           |
| 8            | 2.6           |
| 10           | 2.2           |
| 12           | 2.0           |
| 14           | 1.8           |

Little's Law: Y represents the long-run average trip throughput, which
equals the long-run average number of busy drivers in the system (L − O)
divided by the average time required for a driver to complete a trip. The
latter is equal to the sum of en route time η(O) and trip duration T.

Y = (L - O) / (\eta(O) + T)

\(O\*\) maximizes Y.

Supply elasticity:

L = l(1 - \theta).p.Q/L or L = l(1 - \theta).p.Y/L

where \\theta is the fraction of the price collected by the platform, Q is the
trip throughput, and l is the number of drivers who will participate at
earnings level e. That is, l(.) is the supply elasticity curve.

### Simulations and theory II

Feng et al: [We are on the Way: Analysis of On-Demand Ride-Hailing Systems](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2960991)

Variables chosen:

- R = road length (size)
- d = average trip distance
- \\rho = system utilization level (request rate??)
- k = number of drivers

Little's Law says average waiting time is proportional to the number of
passengers waiting. Effective utilization level is:

\rho = \lambda . (1 - \theta_a) / (k \* \mu)

- \\theta<sub>a</sub> is the abandonment rate: I don't bother with this
- \\lambda is request rate (Poisson process: average time is known but exact timing is random and uncorrelated)
- \\mu is the service rate v/d (v = speed)
- \\rho = \\lambda / (k \\mu) = (\\lambda d/k) is the utilization rate (traffic intensity)

### Simulations and theory III

Shapiro: [Density of Demand and the Benefit of Uber](http://www.shapiromh.com/uploads/8/6/4/0/8640674/mshapiro_jmp.pdf)

Page 13: A consumer has a choice of transportation options. Utility from
choosing a ride hail trip is:

    U = \alpha . p + \beta . w + \gamma

where \\alpha is the relative value of time and money, \\beta is time
sensitivity (w is wait time) and \\gamma is everything else.

## Simulations and theory IV

Tam and Liu: [Demand and Consumer Surplus in the On-demand Economy: the Case of
Ride
Sharing](https://pdfs.semanticscholar.org/e36b/05d96b81340ad3c480e38e8df4e1e1f1eef3.pdf)

p 13:

    U = -\alpha .p + \beta (t_outside - (t_w + t_d)) + \gamma
