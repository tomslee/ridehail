
# Table of Contents

1.  [Ridehail simulation](#orgfa08c31)
2.  [Running a simulation](#orgaef00bb)
3.  [Inspiration](#org6a62b96)
4.  [Capacity utilization: city reports](#orgc0c227c)
    1.  [Driver phases](#org9fa3488)
    2.  [Schaller, The New Automobility](#orgc22c109)
    3.  [John Barrios](#org0b843e9)
    4.  [Cramer and Krueger](#org90a82b7)
    5.  [TNCs Today: SFCTA report (2017)](#org37366ea)
    6.  [Alejandro Henao, University of Colorado at Denver, Master&rsquo;s Thesis (2013)](#org9687f66)
    7.  [Uber blog](#orgf14238e)
5.  [Dynamic pricing and matching](#org8f09c86)
    1.  [Simulations and theory 1](#org9606fbb)
    2.  [Simulations and theory II](#orgc68dde5)


<a id="orgfa08c31"></a>

# Ridehail simulation

This is a personal project. You&rsquo;re welcome to use it but don&rsquo;t expect anything.


<a id="orgaef00bb"></a>

# Running a simulation

-   Read example.config
-   Make a copy of example.config, eg <username>.config
-   Run &ldquo;python ridehail.py -@ <username>.config&rdquo; (or whatever you called it)
-   Try making other changes to your config files

There is also a set of example files in the config directory. You can run these with, for example:

    python ridehail.py -@ config/lesson_1.config

Arguments supplied on the command line (not available for all configuration options, but for some) override those in the configuration file. You can, for example, suppress graphical display by using &ldquo;-dr None&rdquo; no matter what is in the configuration file. For information command line options, run 

    python ridehail.py --help


<a id="org6a62b96"></a>

# Inspiration

This project is inspired by a New York Times animation with this title, published on April 2, 2017. The animation was a simple simulation of a ridehail system for exploring how wait times and driver efficiency (fraction busy) are related.

The NYT animation is [here](https://www.nytimes.com/interactive/2017/04/02/technology/uber-drivers-psychological-tricks.html), but in case the link is broken I captured the video [here](output/nyt_ridehail.mp4). It shows a 9 \* 40 grid city with around 50 requests at the beginning. The number of drivers can be chosen from 50, 75, 125, or 250. The wait time and percent of drivers idling goes as follows:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">Drivers</th>
<th scope="col" class="org-right">Wait time (mins)</th>
<th scope="col" class="org-right">Drivers idle (%)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">50</td>
<td class="org-right">18</td>
<td class="org-right">2</td>
</tr>


<tr>
<td class="org-right">75</td>
<td class="org-right">12</td>
<td class="org-right">5</td>
</tr>


<tr>
<td class="org-right">125</td>
<td class="org-right">5</td>
<td class="org-right">50</td>
</tr>


<tr>
<td class="org-right">250</td>
<td class="org-right">3</td>
<td class="org-right">71</td>
</tr>
</tbody>
</table>

Idle time does not include time heading to pick up the passenger. At the end of each trip the riders vanish and the drivers stay still.

There is also a rider at the top of the bottom-left block, who vanishes.

A rider in the very bottom left edge gets picked up after three seconds, and it taken all the way to the top, along to the right edge, and back down to the bottom right corner before being dropped off.

At the beginning of the simulation there is a rider in the top left corner. Not picked up after several seconds, the rider just vanishes.

In reply, Uber, [here](https://www.uber.com/newsroom/faster-pickup-times-mean-busier-drivers/), argues that &ldquo;This is simply not true&#x2026; When Uber grows in a city: riders enjoy lower pick-up times *and* drivers benefit from less downtime between trips. It&rsquo;s a virtuous cycle that is widely acknowledged in [business](https://twitter.com/davidsacks/status/475073311383105536?lang=en) and [academia](https://www.nber.org/papers/w22083), and which is backed up by data.&rdquo;

The &ldquo;business&rdquo; link is to a tweet with a napkin sketch. The &ldquo;academia&rdquo; link is to Cramer and Kruger, of which more below. The links are accompanied by charts&#x2014;with no y axis labels&#x2014;showing that in major cities the driver idle time (median percent of time not with a rider) has shrunk, along with ETA (wait time), in five major US cities from June 2014 to June 2015 to June 2016 as the number of drivers has grown.

This is a comparisons of apples to oranges, and the lack of a Y axis scale makes the Uber claims dubious, but it still suggests something worth investigating.

Here is the rest of Uber&rsquo;s explanation:

> How is this happening? First, as the number of passengers and drivers using Uber grows, any individual driver is more likely to be close to a rider. This means shorter pickup times and more time spent with a paying passenger in the back of the car. In addition, new features like uberPOOL and Back-to-Back trips have meant longer trips, while incentives to drive during the busiest times and in the busiest locations help keep drivers earning for a greater share of their time online. And that should be no surprise: drivers are our customers just as much as riders. So although the Times article suggests that Uber’s interest is misaligned with drivers’, the opposite is true: it’s in our interest to ensure that drivers have a paying passenger as often as possible because they’re more likely to keep using our app to earn money. (And Uber doesn’t earn money until drivers do.)


<a id="orgc0c227c"></a>

# Capacity utilization: city reports

Deadheading refers to the time or distance without a rider in the car. If a driver waits where they are between rides, these two measures may be quite different.


<a id="org9fa3488"></a>

## Driver phases

Ride-hail insurance commonly uses these phases

-   Phase 0: App is off. Your personal policy covers you.
-   Phase 1: App is on, you&rsquo;re waiting for ride request.
-   Phase 2: Request accepted, and you&rsquo;re en route to pick up a passenger.
-   Phase 3: You have passengers in the car.


<a id="orgc22c109"></a>

## Schaller, The New Automobility

From Bruce Schaller (*The New Automobility*) [here](http://www.challerconsult.::com/rideservices/automobility.pdf).

> Working against the efficiency of Uber and Lyft is the large proportion of mileage without a paying passenger in the vehicle. For a typical passenger trip of 5.2 miles, a TNC driver travels three miles waiting to get pinged and then going to pick up the fare.

This corresponds to a P3 fraction of about 65%.

Schaller from Empty Seats, Full Streets:

> In 2017 TNCs had 55K hours with passengers in the Manhattan Central Business District (CBD), and 37K hours without passengers (60% busy).
> 
> While yellow cabs were occupied with passengers 67 percent of the time in 2013, the utilization rate for combined taxi/TNC operations dropped to 62 percent in 2017.


<a id="org0b843e9"></a>

## John Barrios

> “Rideshare companies often subsidize drivers to stay on the road even when utilization is low, to ensure that supply is quickly available,” they wrote.


<a id="org90a82b7"></a>

## Cramer and Krueger

In [Disruptive Change in the Taxi Business: The Case of Uber](https://www.nber.org/papers/w22083.pdf), Cramer and Krueger write:

> Capacity utilization is measured either by the fraction of time that drivers have a farepaying passenger in the car or by the fraction of miles that drivers log in which a passenger is in the car. Because we are only able to obtain estimates of capacity utilization for taxis for a handful of major cities – Boston, Los Angeles, New York, San Francisco and Seattle – our estimates should be viewed as suggestive. Nonetheless, the results indicate that UberX drivers, on average, have a passenger in the car about half the time that they have their app turned on, and this average varies relatively little across cities, probably due to relatively elastic labor supply given the ease of entry and exit of Uber drivers at various times of the day. In contrast, taxi drivers have a passenger in the car an average of anywhere from 30 percent to 50 percent of the time they are working, depending on the city. Our results also point to higher productivity for UberX drivers than taxi drivers when the share of miles driven with a passenger in the car is used to measure capacity utilization. On average, the capacity utilization rate is 30 percent higher for UberX drivers than taxi drivers when measured by time, and 50 percent higher when measured by miles, although taxi data are not available to calculate both measures for the same set of cities.
> 
> Four factors likely contribute to the higher utilization rate of UberX drivers: 1) Uber’s more efficient driver-passenger matching technology; 2) Uber’s larger scale, which supports faster matches; 3) inefficient taxi regulations; and 4) Uber’s flexible labor supply model and surge pricing, which more closely match supply with demand throughout the day.

They report these capacity utilizations (% of hours with a passenger).

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">City</th>
<th scope="col" class="org-right">TNC</th>
<th scope="col" class="org-left">Taxi</th>
<th scope="col" class="org-right">TNC Distance</th>
<th scope="col" class="org-right">Taxi Distance</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Boston</td>
<td class="org-right">47%</td>
<td class="org-left">NA</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
</tr>


<tr>
<td class="org-left">LA</td>
<td class="org-right">52%</td>
<td class="org-left">NA</td>
<td class="org-right">64%</td>
<td class="org-right">41%</td>
</tr>


<tr>
<td class="org-left">NYC</td>
<td class="org-right">51%</td>
<td class="org-left">48%</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
</tr>


<tr>
<td class="org-left">SF</td>
<td class="org-right">55%</td>
<td class="org-left">38%</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
</tr>


<tr>
<td class="org-left">Seattle</td>
<td class="org-right">44%</td>
<td class="org-left">NA</td>
<td class="org-right">55%</td>
<td class="org-right">39%</td>
</tr>
</tbody>
</table>

Also, for LA and Seattle, they report capacity utilization rates by distance (percent of miles driven with a passenger). These have been added in above. The higher distance values show that some drivers may stay still when waiting for a ride.


<a id="org37366ea"></a>

## TNCs Today: SFCTA report (2017)

The report is [here](https://archive.sfcta.org/sites/default/files/content/Planning/TNCs/TNCs_Today_112917.pdf). In the report, &ldquo;Out-of-service VMT [vehicle miles travelled] refers to the vehicle miles traveled while circulating to pickup a passenger.&rdquo; It is not clear if this includes P3 time and distance.

> Approximately 20% of total TNC VMT are out-of-service miles. This is significantly lower than the more than 40% of taxi VMT that are out-of-service miles&#x2026; The greater efficiencies of TNCs, as
> reflected in a lower share of out-of-service miles, are likely
> primarily a reflection of the larger fleets of TNC drivers operating on the road at any given time, enabling shorter distances to pickup locations. 

Table 4 (weekdays) is similar to tables 5 and 6 (weekends).

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Quantity</th>
<th scope="col" class="org-left">TNC</th>
<th scope="col" class="org-left">Taxi</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Trips</td>
<td class="org-left">170K</td>
<td class="org-left">14K</td>
</tr>


<tr>
<td class="org-left">Average trip length</td>
<td class="org-left">3.3 miles</td>
<td class="org-left">4.6 miles</td>
</tr>


<tr>
<td class="org-left">Average in-service trip length</td>
<td class="org-left">2.6 miles</td>
<td class="org-left">2.6 miles</td>
</tr>


<tr>
<td class="org-left">Average out-of-service trip length</td>
<td class="org-left">0.7 miles</td>
<td class="org-left">2.0 miles</td>
</tr>


<tr>
<td class="org-left">Percent out-of-service trip length</td>
<td class="org-left">21%</td>
<td class="org-left">44%</td>
</tr>
</tbody>
</table>

The data used in this study was collected from the Uber API. &ldquo;Sending a request to the API returns a text file response containing this information [nearby vehicle locations, estimated times-to-pickup, and more]. I am sceptical of the data here.


<a id="org9687f66"></a>

## Alejandro Henao, University of Colorado at Denver, Master&rsquo;s Thesis (2013)

Based on his own experience.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Phase</th>
<th scope="col" class="org-right">Time (minutes)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Available</td>
<td class="org-right">12</td>
</tr>


<tr>
<td class="org-left">Pickup</td>
<td class="org-right">6</td>
</tr>


<tr>
<td class="org-left">Wait for pax</td>
<td class="org-right">1</td>
</tr>


<tr>
<td class="org-left">Ride</td>
<td class="org-right">15</td>
</tr>


<tr>
<td class="org-left">Going home at end of day</td>
<td class="org-right">22</td>
</tr>
</tbody>
</table>

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Phase</th>
<th scope="col" class="org-right">Distance (miles)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Available</td>
<td class="org-right">1.5</td>
</tr>


<tr>
<td class="org-left">Pickup</td>
<td class="org-right">1.5</td>
</tr>


<tr>
<td class="org-left">Trip</td>
<td class="org-right">7</td>
</tr>


<tr>
<td class="org-left">Going home at end of day</td>
<td class="org-right">12</td>
</tr>
</tbody>
</table>

> The time efficiency rate of a ridesourcing driver based on the time a passenger is in the car and total time from driver log-in to log-out (not accounting for the commute at the end of the shift) is 41.3%, meaning that I, as a driver, during my shift hours spent more time without a passenger than with one in the car&#x2026; When accounting for commuting time at end of shift, the time efficiency rate drops to 39.3% of total time&#x2026; Lyft and Uber drivers travel an additional 69.0 miles in deadheading for every 100 miles they are with passengers.


<a id="orgf14238e"></a>

## Uber blog

This Uber blog post from 2015 is about [efficiency](https://www.uber.com/en-GB/blog/london/how-efficiency-benefits-riders-and-partners/).

> Since uberX launched in London in July 2013, average pick-up times – the time between requesting and your car arriving – have reduced from 6 and a half minutes to just over 3 minutes.
> 
> <table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">
> 
> 
> <colgroup>
> <col  class="org-right" />
> 
> <col  class="org-right" />
> 
> <col  class="org-right" />
> </colgroup>
> <thead>
> <tr>
> <th scope="col" class="org-right">Year</th>
> <th scope="col" class="org-right">pick-up time (minutes)</th>
> <th scope="col" class="org-right">P3 % by time</th>
> </tr>
> </thead>
> 
> <tbody>
> <tr>
> <td class="org-right">2013</td>
> <td class="org-right">6.3</td>
> <td class="org-right">17</td>
> </tr>
> 
> 
> <tr>
> <td class="org-right">2014</td>
> <td class="org-right">4.3</td>
> <td class="org-right">&#xa0;</td>
> </tr>
> 
> 
> <tr>
> <td class="org-right">2015</td>
> <td class="org-right">3.1</td>
> <td class="org-right">57</td>
> </tr>
> </tbody>
> </table>
> 
> Back in 2013, when uberX launched in London, partners had a passenger in their car for 16 minutes of every hour. Now that number has more than doubled to 34 minutes.


<a id="org8f09c86"></a>

# Dynamic pricing and matching


<a id="org9606fbb"></a>

## Simulations and theory 1

Yan et al [Dynamic Pricing and Matching in Ride-Hailing Platforms](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3258234). 

Steady-state conditions

If number of drivers = L, Number of open drivers (available) = O, and the number of trips per unit time is Y then

    L = O + \eta . Y + T . Y

where \\eta = en-route time and T = length of trip. This is something I&rsquo;ve derived earlier.

Apparently there is a result (Larson and Odoni 1981) that if open drivers are distributed uniformly in an n-dimensional space, with constant travel speed and a straight line between two points, then the expected en-route time is \\eta(O) and satisfies

    \eta(O) ~ O ^ (-1/n)

So for two-dimensional roads, the en-route time is proportional to one over the square root of the number of open drivers.

Uber data from San Francisco, with L = 30 per km<sup>2</sup> and T = 15 minutes, goes more linearly. Here is a summary

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">Open Drivers</th>
<th scope="col" class="org-right">ETA (minutes)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">4</td>
<td class="org-right">3.8</td>
</tr>


<tr>
<td class="org-right">6</td>
<td class="org-right">3.2</td>
</tr>


<tr>
<td class="org-right">8</td>
<td class="org-right">2.6</td>
</tr>


<tr>
<td class="org-right">10</td>
<td class="org-right">2.2</td>
</tr>


<tr>
<td class="org-right">12</td>
<td class="org-right">2.0</td>
</tr>


<tr>
<td class="org-right">14</td>
<td class="org-right">1.8</td>
</tr>
</tbody>
</table>

Little&rsquo;s Law:  Y represents the long-run average trip throughput, which equals the long-run average number of busy drivers in the system (L − O) divided by the average time required for a driver to complete a trip. The latter is equal to the sum of en route time η(O) and trip duration T.

    Y = (L - O) / (\eta(O) + T)

\(O*\) maximizes Y.

Supply elasticity: 

    L = l(1 - \theta).p.Q/L  or L = l(1 - \theta).p.Y/L

where \\theta is the fraction of the price collected by the platform, Q is the trip throughput, and l is the number of drivers who will participate at earnings level e. That is, l(.) is the supply elasticity curve.


<a id="orgc68dde5"></a>

## Simulations and theory II

Feng et al: [We are on the Way: Analysis of On-Demand Ride-Hailing Systems](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2960991)

Variables chosen:

-   R = road length (size)
-   d = average trip distance
-   \\rho = system utilization level (request rate??)
-   k = number of drivers

Little&rsquo;s Law says average waiting time is proportional to the number of passengers waiting. Effective utilization level is:

    \rho = \lambda . (1 - \theta_a) / (k * \mu)

-   \\theta<sub>a</sub> is the abandonment rate: I don&rsquo;t bother with this
-   \\lambda is request rate (Poisson process: average time is known but exact timing is random and uncorrelated)
-   \\mu is the service rate v/d (v = speed)
-   \\rho = \\lambda / (k \\mu) = (\\lambda d/k) is the utilization rate (traffic intensity)

