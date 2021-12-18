# Inspiration

This project was inspired by a New York Times animation with this title,
published on April 2, 2017. The animation was a simple simulation of a ridehail
system for exploring how wait times and driver efficiency (fraction busy) are
related.

The NYT animation is
[here](https://www.nytimes.com/interactive/2017/04/02/technology/uber-drivers-psychological-tricks.html),
but in case the link is broken I captured the video
[here](output/nyt_ridehail.mp4). It shows a 9 \* 40 grid city with around 50
requests at the beginning. The number of drivers can be chosen from 50, 75,
125, or 250. The wait time and percent of drivers idling goes as follows:

| Drivers | Wait time (mins) | Drivers idle (%) |
| ------- | ---------------- | ---------------- |
| 50      | 18               | 2                |
| 75      | 12               | 5                |
| 125     | 5                | 50               |
| 250     | 3                | 71               |

Idle time does not include time heading to pick up the passenger. At the end of
each trip the riders vanish and the drivers stay still.

There is also a rider at the top of the bottom-left block, who vanishes.

A rider in the very bottom left edge gets picked up after three seconds, and it
taken all the way to the top, along to the right edge, and back down to the
bottom right corner before being dropped off.

At the beginning of the simulation there is a rider in the top left corner. Not
picked up after several seconds, the rider just vanishes.

In reply, Uber,
[here](https://www.uber.com/newsroom/faster-pickup-times-mean-busier-drivers/),
argues that &ldquo;This is simply not true&#x2026; When Uber grows in a city:
riders enjoy lower pick-up times _and_ drivers benefit from less downtime
between trips. It&rsquo;s a virtuous cycle that is widely acknowledged in
[business](https://twitter.com/davidsacks/status/475073311383105536?lang=en)
and [academia](https://www.nber.org/papers/w22083), and which is backed up by
data.&rdquo;

The &ldquo;business&rdquo; link is to a tweet with a napkin sketch. The
&ldquo;academia&rdquo; link is to Cramer and Kruger, of which more below. The
links are accompanied by charts&#x2014;with no y axis labels&#x2014;showing
that in major cities the driver idle time (median percent of time not with
a rider) has shrunk, along with ETA (wait time), in five major US cities from
June 2014 to June 2015 to June 2016 as the number of drivers has grown.

This is a comparisons of apples to oranges, and the lack of a Y axis scale
makes the Uber claims dubious, but it still suggests something worth
investigating.

Here is the rest of Uber&rsquo;s explanation:

> How is this happening? First, as the number of passengers and drivers using
> Uber grows, any individual driver is more likely to be close to a rider. This
> means shorter pickup times and more time spent with a paying passenger in the
> back of the car. In addition, new features like uberPOOL and Back-to-Back
> trips have meant longer trips, while incentives to drive during the busiest
> times and in the busiest locations help keep drivers earning for a greater
> share of their time online. And that should be no surprise: drivers are our
> customers just as much as riders. So although the Times article suggests that
> Uber’s interest is misaligned with drivers’, the opposite is true: it’s in
> our interest to ensure that drivers have a paying passenger as often as
> possible because they’re more likely to keep using our app to earn money.
> (And Uber doesn’t earn money until drivers do.)

## John Barrios

“Rideshare companies often subsidize drivers to stay on the road even when
utilization is low, to ensure that supply is quickly available,” they wrote.
