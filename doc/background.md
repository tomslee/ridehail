
# Table of Contents

1.  [Inspiration](#orgd6653b9)
2.  [Capacity utilization: city reports](#orgb5e77ea)
    1.  [Driver phases](#org34525c0)
    2.  [Schaller, The New Automobility](#org13fe031)
    3.  [John Barrios](#org2827734)
    4.  [Cramer and Krueger](#orgd22223d)
    5.  [TNCs Today: SFCTA report (2017)](#orgd2702dc)
    6.  [Alejandro Henao, University of Colorado at Denver, Master&rsquo;s Thesis (2013)](#orge5eea09)
    7.  [Uber blog](#org4c0b851)
    8.  [Fehr & Peers in Boston (2019)](#org0ea72ef)
    9.  [Competing reports in Seattle](#orgd298470)
    10. [Summary](#org7854e66)
    11. [Is my model compatible with these figures?](#orge8d547c)
3.  [Simulating Manhattan](#org3c29655)
    1.  [Grid size (50\*50)](#orgf04332a)
    2.  [Traffic speed (1 block per minute)](#orgd2798c1)
    3.  [Trip request rates (250)](#org063a9d5)
    4.  [Number of drivers (7000)](#orga956020)
4.  [Dynamic pricing and matching](#org48a600c)
    1.  [Simulations and theory 1](#orgdea1b1f)
    2.  [Simulations and theory II](#orgeddb5ac)
    3.  [Simulations and theory III](#org3546b75)
    4.  [Simulations and theory IV](#org32bac5d)


<a id="orgd6653b9"></a>

# Inspiration

This project was inspired by a New York Times animation with this title, published on April 2, 2017. The animation was a simple simulation of a ridehail system for exploring how wait times and driver efficiency (fraction busy) are related.

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


<a id="orgb5e77ea"></a>

# Capacity utilization: city reports

Deadheading refers to the time or distance without a rider in the car. If a driver waits where they are between rides, these two measures may be quite different.


<a id="org34525c0"></a>

## Driver phases

Ride-hail insurance commonly uses these phases

-   Phase 0: App is off. Your personal policy covers you.
-   Phase 1: App is on, you&rsquo;re waiting for ride request.
-   Phase 2: Request accepted, and you&rsquo;re en route to pick up a passenger.
-   Phase 3: You have passengers in the car.


<a id="org13fe031"></a>

## Schaller, The New Automobility

From Bruce Schaller (*The New Automobility*) [here](http://www.schallerconsult.com/rideservices/automobility.pdf).

> Working against the efficiency of Uber and Lyft is the large proportion of mileage without a paying passenger in the vehicle. For a typical passenger trip of 5.2 miles, a TNC driver travels three miles waiting to get pinged and then going to pick up the fare.

This corresponds to a P3 fraction of about 65% by distance.

Here is a table, modified from Schaller:

Table 7. Passenger miles and total miles for TNC trips

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">City</th>
<th scope="col" class="org-right">P3</th>
<th scope="col" class="org-right">P2</th>
<th scope="col" class="org-right">P1</th>
<th scope="col" class="org-right"><trip> (driver-miles)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">New York City</td>
<td class="org-right">59</td>
<td class="org-right">08</td>
<td class="org-right">33</td>
<td class="org-right">8.6</td>
</tr>


<tr>
<td class="org-left">Chicago</td>
<td class="org-right">59</td>
<td class="org-right">10</td>
<td class="org-right">31</td>
<td class="org-right">7.9</td>
</tr>


<tr>
<td class="org-left">San Francisco</td>
<td class="org-right">67</td>
<td class="org-right">10</td>
<td class="org-right">23</td>
<td class="org-right">6.1</td>
</tr>


<tr>
<td class="org-left">Denver</td>
<td class="org-right">71</td>
<td class="org-right">14</td>
<td class="org-right">15</td>
<td class="org-right">9.9</td>
</tr>
</tbody>
</table>

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

> In 2017 TNCs had 55K hours with passengers in the Manhattan Central Business District (CBD), and 37K hours without passengers (60% busy).
> 
> While yellow cabs were occupied with passengers 67 percent of the time in 2013, the utilization rate for combined taxi/TNC operations dropped to 62 percent in 2017.


<a id="org2827734"></a>

## John Barrios

> “Rideshare companies often subsidize drivers to stay on the road even when utilization is low, to ensure that supply is quickly available,” they wrote.


<a id="orgd22223d"></a>

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


<a id="orgd2702dc"></a>

## TNCs Today: SFCTA report (2017)

The report is [here](https://archive.sfcta.org/sites/default/files/content/Planning/TNCs/TNCs_Today_112917.pdf). In the report, &ldquo;In-service VMT refers to the vehicle miles traveled when transporting a passenger. Out-of-service VMT [vehicle miles travelled] refers to the vehicle miles traveled while circulating to pickup a passenger.&rdquo; It is not clear if this includes P3 time and distance.

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


<a id="orge5eea09"></a>

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


<a id="org4c0b851"></a>

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


<a id="org0ea72ef"></a>

## Fehr & Peers in Boston (2019)

See [Streetsblog](https://mass.streetsblog.org/2019/08/08/uberlyft-admit-responsibility-for-a-significant-share-of-bostons-traffic/) report or the full report by Fehr and Peers [here](https://drive.google.com/file/d/1FIUskVkj9lsAnWJQ6kLhAhNoVLjfFdx3/view). The study was jointly commissioned by Uber and Lyft

&ldquo;In the 4-county Boston metropolitan region (which encompasses Suffolk, Norfolk, Middlesex and Essex counties), Uber and Lyft drivers drove between 20 million and 26 million miles without any passengers in the month of September 2018 – nearly as much driving as they did with passengers.&rdquo;

Reminder: P1 = idle; P2 = picking up; P3  with passenger.

Table 3 of the report. TNC Vehicle Miles Traveled (VMT), in millions. The Total and percentage columns use the mid-point.

Note that P3 values **by time** (as opposed to by distance) may be lower. During P1 time drivers may drive less quickly (if at all) and so P3 time by distance will be higher.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Region</th>
<th scope="col" class="org-right">P1 (low)</th>
<th scope="col" class="org-right">P1 (High)</th>
<th scope="col" class="org-right">P1 (Mid)</th>
<th scope="col" class="org-right">P2</th>
<th scope="col" class="org-right">P3</th>
<th scope="col" class="org-right">Total</th>
<th scope="col" class="org-right">P3 %</th>
<th scope="col" class="org-right">P2 %</th>
<th scope="col" class="org-right">P1 %</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Boston</td>
<td class="org-right">14.7</td>
<td class="org-right">20.6</td>
<td class="org-right">17.6</td>
<td class="org-right">5.3</td>
<td class="org-right">28.3</td>
<td class="org-right">51.2</td>
<td class="org-right">0.55</td>
<td class="org-right">0.10</td>
<td class="org-right">0.34</td>
</tr>


<tr>
<td class="org-left">Chicago</td>
<td class="org-right">29.7</td>
<td class="org-right">40.8</td>
<td class="org-right">35.3</td>
<td class="org-right">9.1</td>
<td class="org-right">54.6</td>
<td class="org-right">99.0</td>
<td class="org-right">0.55</td>
<td class="org-right">0.09</td>
<td class="org-right">0.36</td>
</tr>


<tr>
<td class="org-left">Los Angeles</td>
<td class="org-right">38.3</td>
<td class="org-right">63.2</td>
<td class="org-right">50.7</td>
<td class="org-right">17.7</td>
<td class="org-right">104.1</td>
<td class="org-right">172.5</td>
<td class="org-right">0.60</td>
<td class="org-right">0.10</td>
<td class="org-right">0.29</td>
</tr>


<tr>
<td class="org-left">San Francisco</td>
<td class="org-right">31.5</td>
<td class="org-right">46.6</td>
<td class="org-right">30.1</td>
<td class="org-right">11.9</td>
<td class="org-right">75.2</td>
<td class="org-right">117.2</td>
<td class="org-right">0.64</td>
<td class="org-right">0.10</td>
<td class="org-right">0.26</td>
</tr>


<tr>
<td class="org-left">Seattle</td>
<td class="org-right">9.7</td>
<td class="org-right">15.6</td>
<td class="org-right">12.7</td>
<td class="org-right">2.9</td>
<td class="org-right">17.6</td>
<td class="org-right">33.2</td>
<td class="org-right">0.53</td>
<td class="org-right">0.09</td>
<td class="org-right">0.38</td>
</tr>


<tr>
<td class="org-left">Washington DC</td>
<td class="org-right">24.4</td>
<td class="org-right">33.5</td>
<td class="org-right">28.9</td>
<td class="org-right">8.1</td>
<td class="org-right">46.0</td>
<td class="org-right">83.0</td>
<td class="org-right">0.55</td>
<td class="org-right">0.10</td>
<td class="org-right">0.35</td>
</tr>
</tbody>

<tbody>
<tr>
<td class="org-left">Average %</td>
<td class="org-right">28%</td>
<td class="org-right">37%</td>
<td class="org-right">33%</td>
<td class="org-right">10%</td>
<td class="org-right">58%</td>
<td class="org-right">1.0</td>
<td class="org-right">0.58</td>
<td class="org-right">0.10</td>
<td class="org-right">0.33</td>
</tr>
</tbody>
</table>


<a id="orgd298470"></a>

## Competing reports in Seattle

In July 2020 two reports on ride-hailing in Seattle were released.

-   [Platform Driving in Seattle](https://digitalcommons.ilr.cornell.edu/cgi/viewcontent.cgi?article=1070&context=reports) by Louis Hyman, Erica L. Groshen, Adam Seth Litwin, Martin T. Wells and Kwelina P. Thompson was a collaboration with Uber and the authors had access to detailed (ride-level) data for one week.
-   [A Minimum Compensation Standard for Seattle TNC Drivers](https://irle.berkeley.edu/files/2020/07/Parrott-Reich-Seattle-Report_July-2020.pdf) by James A. Parrott and Michael Reich was commissioned by the City of Seattle.

While they disagree on many things, the picture they paint of capacity utilization is not that different.

Here is Hyman et al. (adapted from Chart 1.7, p 35): median weekly hours by period by driver type:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Driver Type</th>
<th scope="col" class="org-right">P3</th>
<th scope="col" class="org-right">P2</th>
<th scope="col" class="org-right">P1</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Full-time</td>
<td class="org-right">57%</td>
<td class="org-right">14%</td>
<td class="org-right">30%</td>
</tr>


<tr>
<td class="org-left">Part-time</td>
<td class="org-right">56%</td>
<td class="org-right">15%</td>
<td class="org-right">30%</td>
</tr>


<tr>
<td class="org-left">Committed Casual</td>
<td class="org-right">60%</td>
<td class="org-right">10%</td>
<td class="org-right">30%</td>
</tr>


<tr>
<td class="org-left">Casual</td>
<td class="org-right">0</td>
<td class="org-right">1</td>
<td class="org-right">0</td>
</tr>


<tr>
<td class="org-left">All</td>
<td class="org-right">60%</td>
<td class="org-right">10%</td>
<td class="org-right">30%</td>
</tr>
</tbody>
</table>

And here is P&R (Exhibit 30, p52):

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Data source</th>
<th scope="col" class="org-right">P3</th>
<th scope="col" class="org-right">P2</th>
<th scope="col" class="org-right">P1</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Uber</td>
<td class="org-right">51%</td>
<td class="org-right">13%</td>
<td class="org-right">36%</td>
</tr>


<tr>
<td class="org-left">Lyft</td>
<td class="org-right">47%</td>
<td class="org-right">13%</td>
<td class="org-right">40%</td>
</tr>
</tbody>
</table>

Between a third (H) and a half (P&R) of drivers use both Lyft and Uber apps. As a result, P&R may be double-counting some of the P1 time. If we say that a third of the drivers use both apps all the time, then this would lead to over-counting by 1/6, which brings the P&R figures into close agreement with LH.


<a id="org7854e66"></a>

## Summary

From several North American cities, we have approximate numbers like this:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">City</th>
<th scope="col" class="org-right">Year</th>
<th scope="col" class="org-left">Source</th>
<th scope="col" class="org-right">P3 %</th>
<th scope="col" class="org-right">P2 %</th>
<th scope="col" class="org-right">P1 %</th>
<th scope="col" class="org-left">Note</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Seattle</td>
<td class="org-right">2020</td>
<td class="org-left">Hyman</td>
<td class="org-right">57</td>
<td class="org-right">14</td>
<td class="org-right">30</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">Seattle</td>
<td class="org-right">2020</td>
<td class="org-left">P&R\*</td>
<td class="org-right">55</td>
<td class="org-right">15</td>
<td class="org-right">30</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">London</td>
<td class="org-right">2015</td>
<td class="org-left">Uber</td>
<td class="org-right">57</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">London</td>
<td class="org-right">2013</td>
<td class="org-left">Uber</td>
<td class="org-right">17</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">San Francisco</td>
<td class="org-right">2017</td>
<td class="org-left">SFCTA</td>
<td class="org-right">79</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">21</td>
<td class="org-left">by miles</td>
</tr>


<tr>
<td class="org-left">Boston</td>
<td class="org-right">2014?</td>
<td class="org-left">Cramer & Krueger</td>
<td class="org-right">47</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">Los Angeles</td>
<td class="org-right">2014?</td>
<td class="org-left">Cramer & Krueger</td>
<td class="org-right">52</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">New York City</td>
<td class="org-right">2014?</td>
<td class="org-left">Cramer & Krueger</td>
<td class="org-right">51</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">San Francisco</td>
<td class="org-right">2014?</td>
<td class="org-left">Cramer & Krueger</td>
<td class="org-right">55</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">New York City</td>
<td class="org-right">2018</td>
<td class="org-left">Schaller</td>
<td class="org-right">65</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">by miles</td>
</tr>


<tr>
<td class="org-left">Manhattan CBD</td>
<td class="org-right">2017</td>
<td class="org-left">Schaller</td>
<td class="org-right">60</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-left">by miles</td>
</tr>


<tr>
<td class="org-left">New York City</td>
<td class="org-right">2017</td>
<td class="org-left">Schaller</td>
<td class="org-right">59</td>
<td class="org-right">08</td>
<td class="org-right">33</td>
<td class="org-left">by miles</td>
</tr>


<tr>
<td class="org-left">Chicago</td>
<td class="org-right">2017</td>
<td class="org-left">Henao</td>
<td class="org-right">59</td>
<td class="org-right">10</td>
<td class="org-right">31</td>
<td class="org-left">by miles</td>
</tr>


<tr>
<td class="org-left">San Francisco</td>
<td class="org-right">2017</td>
<td class="org-left">Said</td>
<td class="org-right">67</td>
<td class="org-right">10</td>
<td class="org-right">23</td>
<td class="org-left">by miles</td>
</tr>


<tr>
<td class="org-left">Denver</td>
<td class="org-right">2017</td>
<td class="org-left">Henao</td>
<td class="org-right">71</td>
<td class="org-right">14</td>
<td class="org-right">15</td>
<td class="org-left">by miles</td>
</tr>
</tbody>
</table>


<a id="orge8d547c"></a>

## Is my model compatible with these figures?

Some possibilities for city<sub>size</sub>=40, request<sub>rate</sub>=1.2. Reading off P1 30%:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Trip Distribution</th>
<th scope="col" class="org-right">Min trip</th>
<th scope="col" class="org-right">Drivers</th>
<th scope="col" class="org-right">P3</th>
<th scope="col" class="org-right">P2</th>
<th scope="col" class="org-right">P1</th>
<th scope="col" class="org-right">(Wait time)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Uniform</td>
<td class="org-right">0</td>
<td class="org-right">50</td>
<td class="org-right">50</td>
<td class="org-right">18</td>
<td class="org-right">30</td>
<td class="org-right">28</td>
</tr>


<tr>
<td class="org-left">Uniform</td>
<td class="org-right">20</td>
<td class="org-right">60</td>
<td class="org-right">55</td>
<td class="org-right">15</td>
<td class="org-right">30</td>
<td class="org-right">22</td>
</tr>


<tr>
<td class="org-left">Beta</td>
<td class="org-right">0</td>
<td class="org-right">62</td>
<td class="org-right">54</td>
<td class="org-right">20</td>
<td class="org-right">30</td>
<td class="org-right">29</td>
</tr>


<tr>
<td class="org-left">Beta</td>
<td class="org-right">20</td>
<td class="org-right">-</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">30</td>
<td class="org-right">&#xa0;</td>
</tr>
</tbody>
</table>

For a lower request rate, of 0.8:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Trip Distribution</th>
<th scope="col" class="org-right">Min trip</th>
<th scope="col" class="org-right">Drivers</th>
<th scope="col" class="org-right">P3</th>
<th scope="col" class="org-right">P2</th>
<th scope="col" class="org-right">P1</th>
<th scope="col" class="org-right">(Wait time)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Uniform</td>
<td class="org-right">0</td>
<td class="org-right">36</td>
<td class="org-right">50</td>
<td class="org-right">20</td>
<td class="org-right">30</td>
<td class="org-right">30</td>
</tr>


<tr>
<td class="org-left">Uniform</td>
<td class="org-right">20</td>
<td class="org-right">42</td>
<td class="org-right">55</td>
<td class="org-right">15</td>
<td class="org-right">30</td>
<td class="org-right">24</td>
</tr>


<tr>
<td class="org-left">Beta</td>
<td class="org-right">0</td>
<td class="org-right">62</td>
<td class="org-right">54</td>
<td class="org-right">20</td>
<td class="org-right">30</td>
<td class="org-right">29</td>
</tr>


<tr>
<td class="org-left">Beta</td>
<td class="org-right">20</td>
<td class="org-right">-</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">&#xa0;</td>
<td class="org-right">30</td>
<td class="org-right">&#xa0;</td>
</tr>
</tbody>
</table>

So: long trips and uniform distribution are needed for this level of capacity utilization. It&rsquo;s at the upper end of what is geometrically possible.

Also: for the uniform cases, the results are independent of request rate: it takes more drivers, but they end up at the same distribution. This is surprising to me.

For uniform distributions, longer trips require more drivers to reach the 30% P1 rate, but when they do so there is a higher capacity utilization and lower pick-up time. Also a lower wait time. This may be said better as: for uniform distributions, longer trips lead to higher P3 rates at a given number of drivers, higher P2 values (they have to drive further to get their next drive), and corresponding lower P1 values.

P3 percentages and number of drivers to support a steady state may both be measures of efficiency.


<a id="org3c29655"></a>

# Simulating Manhattan


<a id="orgf04332a"></a>

## Grid size (50\*50)

According to [William Helmreich](https://en.wikipedia.org/wiki/William_B._Helmreich), New York City has 120,000 blocks, and he should know because he walked them all over the course of four years, for a total of 6163 miles (about 10K kilometers).

The figure of 120,000 blocks is reported in [a 2013 New Yorker article](https://www.newyorker.com/books/page-turner/a-walker-in-the-city) on Helmreich.

Manhattan is much smaller: from a [Quora question](https://www.quora.com/Approximately-how-many-blocks-are-there-on-the-island-of-Manhattan): 220th street is the northernmost street, and some say it&rsquo;s about 250 blocks north to south. Another way to think about it is that Manhattan is about 13 miles with 20 blocks to the mile (1 block ~ 100 yards). At its widest point Manhattan is 2.3 miles, but it is much narrower in other places. Someone else says 2872 blocks.

One approach is area. Manhattan is 59.1 km<sup>2</sup> (call it 60), or 6\*10<sup>7</sup> m<sup>2</sup>. That&rsquo;s equivalent to 23 square miles (or 13 \* 1.75).

According to [Wikipedia](https://en.wikipedia.org/wiki/City_block): &ldquo;the standard block in Manhattan is about 264 by 900 feet (80 m × 274 m)&rdquo;, so call that 100 \* 250m = 2.5\*10<sup>4</sup> m<sup>2</sup>. 

Number of blocks = (6 \* 10<sup>7</sup>)/(2.5 \* 10<sup>4</sup>) ~ 2.5 \* 10<sup>3</sup>, which is the same as a 50\*50 grid.


<a id="orgd2798c1"></a>

## Traffic speed (1 block per minute)

In midtown Manhattan the average traffic speed is 4.7mph ([LA Times 2018](https://www.latimes.com/nation/la-na-new-york-traffic-manhattan-20180124-story.html#:~:text=The%20average%20speed%20of%20traffic%20in%20Midtown%20Manhattan%20is%204.7%20mph.,-New%20York%20thinks)). Overall the average is probably higher though.

A block is the equivalent of 160m on one side (100 \* 250 ~ 160 \* 160) and 1 mile is 1600 meters, so 1 mile is 10 blocks. That suggests average traffic speed is about 50 blocks (5 miles) per hour, which is close to one block per minute.

There are 1440 minutes in a day.


<a id="org063a9d5"></a>

## Trip request rates (250)

First look at overall volumes per day, using data collected by Todd Schneider from NYC TLC and others, and presented on [Todd W. Schneider&rsquo;s web site](https://toddwschneider.com/dashboards/nyc-taxi-ridehailing-uber-lyft-data/). Schneider provides the code [On GitHub](https://github.com/toddwschneider/nyc-taxi-data). These are all &ldquo;pre-pandemic&rdquo; figures, from 2019 or so, and they are for all NYC, not just for Manhattan.

-   Number of ride-hail rides per day ~ 750K. (Does not include taxis)
-   Number of Uber rides per day ~ 500K (2/3 of all ridehail rides)
-   Number of unique ride-hail vehicles per month ~ 80K, most of which drove for Uber (quite a lot do both Uber and Lyft)
-   Number of unique drivers per month is similar
-   Number of monthly trips per vehicle ~ 200 (mean of 7 per day)
-   Mean number of vehicles (or drivers) per day ~ 60K
-   Mean daily trips per active vehicle ~ 13. (so total trips per day ~ 60K \* 13 = 780K, which matches number of ride-hail rides per day.
-   Average days per month on the road ~ 19
-   Average hours per day per vehicle ~ 6.
-   Trips per vehicle per active hour ~ 2.
-   Minutes per trip ~ 20 (hence utilization rate of 2/3 by hour)
-   Trips-in-progress hours per day ~ 3.7
-   Shared trips per day ~ 100K (fell off dramatically from 150K in 2018 to 100K in 2019, from 25% of trips to 15%).
-   Shared trips per day: Uber went from 125K in 2018 to 50K in 2019; Lyft from 30K in 2018 to 50K in 2019.

From all these numbers, we can say about 750K rides per day is about 500 rides per minute for all of NYC.

If 60K vehicles drive on 2/3 of the days in a month, then there may be 40K on the roads any one day. If each drives for 6 hours, that&rsquo;s 1/4 of the available hours, so there is a mean of 10K vehicles on the road in NYC at any one time.

In 2017, Carol Atkinson-Palombo [concluded](https://trid.trb.org/view/1586848) that &ldquo;Having surged 40-fold, ridesourcing trips originating in the outer boroughs now constitute 56% of the overall market.&rdquo; The &ldquo;outer boroughs&rdquo; are all apart from Manhattan (that is, Brooklyn, Queens, The Bronx, and Staten Island). 

If this is true then using 50% we end up with, *on Manhattan* (computing from trip volume, 20 minutes per trip, and 2/3 utilization rate:

-   350K trips per day (= 250 trips per minute \* 1440 minutes per day)
-   About 2 trips per vehicle hour, so that&rsquo;s about 180K vehicle hours or about 10M vehicle minutes.
-   7K drivers on the road each minute \* 1.4K minutes / day gives 10M, so that&rsquo;s about 7K on the road at once.
-   Schaller (below) concludes 100K vehicle hours per day in Manhattan CBD so that&rsquo;s not too different, given different years and that the CBD is only part of Manhattan.


<a id="orga956020"></a>

## Number of drivers (7000)

In December 2017, Bruce Schaller [concluded](http://www.schallerconsult.com/rideservices/emptyseats.pdf) that 200K trips per day started or ended in the Manhattan Central Business District (CBD), and that there are about 100K vehicle hours per day. He also concludes that &ldquo;setting aside overnight hours, there were an average of 9100 taxis or TNCs in the CBD weekdays between 8 am and midnight in June 2017.

Another source ([ny.curbed.com](https://ny.curbed.com/2020/3/13/21178259/coronavirus-new-york-city-uber-lyft-transportation-drivers), pulling from the NYT) says the ride-hailing industry &ldquo;employs roughly 80,000 drivers in New York City&rdquo;. This maps well to Schneider above. If half drive in Manhattan, and 1/4 are on the roads at any one time, then that would be about 10K.

Another approach: 

    request rate * trip length = cars * busy fraction

so

    cars = request rate * trip length / busy fraction

    cars = 250 trips per minute * 20 minutes per trip / (2/3) = 7500 


<a id="org48a600c"></a>

# Dynamic pricing and matching


<a id="orgdea1b1f"></a>

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


<a id="orgeddb5ac"></a>

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


<a id="org3546b75"></a>

## Simulations and theory III

Shapiro: [Density of Demand and the Benefit of Uber](http://www.shapiromh.com/uploads/8/6/4/0/8640674/mshapiro_jmp.pdf)

Page 13: A consumer has a choice of transportation options. Utility from choosing a ride hail trip is:

    U = \alpha . p + \beta . w + \gamma

where \\alpha is the relative value of time and money, \\beta is time sensitivity (w is wait time) and \\gamma is everything else.


<a id="org32bac5d"></a>

## Simulations and theory IV

Tam and Liu: [Demand and Consumer Surplus in the On-demand Economy: the Case of Ride Sharing](https://pdfs.semanticscholar.org/e36b/05d96b81340ad3c480e38e8df4e1e1f1eef3.pdf    )

p 13:

    U = -\alpha .p + \beta (t_outside - (t_w + t_d)) + \gamma

