
# Table of Contents

1.  [Benchmark tests for large simulations](#benchmark-tests-for-large-simulations)
    1.  [Converting stat lists to numpy arrays](#org8e62e37)
        1.  [numpy](#numpy)
        2.  [dev (Python lists)](#dev-python-lists)
    2.  [Memory profiling](#org54befce)
2.  [CProfile](#org59a1c33)


<a id="benchmark-tests-for-large-simulations"></a>

# Benchmark tests for large simulations

Using the Manhattan config file.

-   Manhattan has about 2500 blocks, which is 50 \* 50
-   NYC overall has 120,000 blocks (according to the man who walked them
    all), which is more like 350 \* 350.
-   Average traffic speed in midtown Manhattan is 5 mph.
-   There are about 12 city blocks to the mile, so that&rsquo;s about one block
    per minute.
-   In a day, there are 1440 minutes.
-   In NYC, ridehailing did about 750K rides per day pre-pandemic
    (<https://toddwschneider.com/dashboards/nyc-taxi-ridehailing-uber-lyft-data/>)
-   In Dec 2017, Bruce Schaller reported that 200K trips per day started
    or ended in the Manhattan Central Business District
    (<http://www.schallerconsult.com/rideservices/emptyseats.pdf>)

Maybe Manhattan as a whole has somewhere around 400K trips?? That would
translated into about 300 trips per minute.

The number of vehicle hours in Manhattan CBD is (Schaller) about 100K.
If the number of vehicles on the road is constant, each driving 24 hours
then the number of vehicles on the road at any one time is about 4K. If
they each drive two hours that would be 50K per day. The mayor&rsquo;s report
says an average of about 50K vehicles per day.

The NYC mayor says there are about 80K unique vehicles in NYC, averaging
about 250 monthly trips each (that&rsquo;s about 10 trips per day).


<a id="org8e62e37"></a>

## Converting stat lists to numpy arrays

Summary: the stat list conversion does not help. At large scales, once rides start being taken, statistics collection is not a major time contributor.

I would presume that maintaining individual trip and driver information is the challenge. Perhaps we can speed those up.

The stat list conversion was done in the &ldquo;numpy&rdquo; branch, while python lists were used in the &ldquo;dev&rdquo; branch.

CPU use is typically only around 20%, and memory is only about 30MB, even though overall memory consumption is at about 60%. Which is strange and makes me wonder if it is swapping out data to disk, even though it does not need to.


<a id="numpy"></a>

### numpy

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-left" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">Period</th>
<th scope="col" class="org-left">Time</th>
<th scope="col" class="org-right">Period length</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">0</td>
<td class="org-left">2020-08-23 21:51:02</td>
<td class="org-right">0</td>
</tr>


<tr>
<td class="org-right">1</td>
<td class="org-left">2020-08-23 21:51:07</td>
<td class="org-right">0:05</td>
</tr>


<tr>
<td class="org-right">2</td>
<td class="org-left">2020-08-23 21:51:12</td>
<td class="org-right">0:05</td>
</tr>


<tr>
<td class="org-right">3</td>
<td class="org-left">2020-08-23 21:51:17</td>
<td class="org-right">0:05</td>
</tr>


<tr>
<td class="org-right">4</td>
<td class="org-left">2020-08-23 21:51:21</td>
<td class="org-right">0:04</td>
</tr>


<tr>
<td class="org-right">5</td>
<td class="org-left">2020-08-23 21:51:24</td>
<td class="org-right">0:03</td>
</tr>


<tr>
<td class="org-right">6</td>
<td class="org-left">2020-08-23 21:51:29</td>
<td class="org-right">0:05</td>
</tr>


<tr>
<td class="org-right">7</td>
<td class="org-left">2020-08-23 21:51:39</td>
<td class="org-right">0:10</td>
</tr>


<tr>
<td class="org-right">8</td>
<td class="org-left">2020-08-23 21:51:55</td>
<td class="org-right">0:16</td>
</tr>


<tr>
<td class="org-right">9</td>
<td class="org-left">2020-08-23 21:52:19</td>
<td class="org-right">0:26</td>
</tr>


<tr>
<td class="org-right">10</td>
<td class="org-left">2020-08-23 21:52:59</td>
<td class="org-right">0:40</td>
</tr>


<tr>
<td class="org-right">11</td>
<td class="org-left">2020-08-23 21:53:39</td>
<td class="org-right">0:40</td>
</tr>


<tr>
<td class="org-right">12</td>
<td class="org-left">2020-08-23 21:54:17</td>
<td class="org-right">0:38</td>
</tr>


<tr>
<td class="org-right">13</td>
<td class="org-left">2020-08-23 21:55:17</td>
<td class="org-right">1:00</td>
</tr>


<tr>
<td class="org-right">14</td>
<td class="org-left">2020-08-23 21:56:19</td>
<td class="org-right">1:02</td>
</tr>


<tr>
<td class="org-right">15</td>
<td class="org-left">2020-08-23 21:58:04</td>
<td class="org-right">1:45</td>
</tr>


<tr>
<td class="org-right">16</td>
<td class="org-left">2020-08-23 21:59:43</td>
<td class="org-right">1:39</td>
</tr>


<tr>
<td class="org-right">17</td>
<td class="org-left">2020-08-23 22:01:45</td>
<td class="org-right">2:32</td>
</tr>


<tr>
<td class="org-right">18</td>
<td class="org-left">2020-08-23 22:05:15</td>
<td class="org-right">3:30</td>
</tr>


<tr>
<td class="org-right">19</td>
<td class="org-left">2020-08-23 22:08:53</td>
<td class="org-right">3:38</td>
</tr>


<tr>
<td class="org-right">20</td>
<td class="org-left">2020-08-23 22:13:42</td>
<td class="org-right">3:49</td>
</tr>


<tr>
<td class="org-right">21</td>
<td class="org-left">2020-08-23 22:18:35</td>
<td class="org-right">4:53</td>
</tr>


<tr>
<td class="org-right">22</td>
<td class="org-left">2020-08-23 22:25:55</td>
<td class="org-right">7:20</td>
</tr>


<tr>
<td class="org-right">23</td>
<td class="org-left">2020-08-23 22:35:29</td>
<td class="org-right">9:34</td>
</tr>


<tr>
<td class="org-right">24</td>
<td class="org-left">2020-08-23 22:44:58</td>
<td class="org-right">9:29</td>
</tr>
</tbody>

<tbody>
<tr>
<td class="org-right">Elapsed</td>
<td class="org-left">53:56</td>
<td class="org-right">&#xa0;</td>
</tr>
</tbody>
</table>

Second run from numpy branch:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">Period</th>
<th scope="col" class="org-left">Time</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">0</td>
<td class="org-left">2021-08-24 12:50:41</td>
</tr>


<tr>
<td class="org-right">24</td>
<td class="org-left">2020-08-24 13:38:32</td>
</tr>
</tbody>

<tbody>
<tr>
<td class="org-right">Elapsed</td>
<td class="org-left">47:51</td>
</tr>
</tbody>
</table>


<a id="dev-python-lists"></a>

### dev (Python lists)

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-left" />

<col  class="org-right" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">Period</th>
<th scope="col" class="org-left">Time</th>
<th scope="col" class="org-right">Period length</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">0</td>
<td class="org-left">2020-08-24 09:14:01</td>
<td class="org-right">0</td>
</tr>


<tr>
<td class="org-right">1</td>
<td class="org-left">2020-08-24 09:14:11</td>
<td class="org-right">0:10</td>
</tr>


<tr>
<td class="org-right">2</td>
<td class="org-left">2020-08-24 09:14:18</td>
<td class="org-right">0:06</td>
</tr>


<tr>
<td class="org-right">3</td>
<td class="org-left">2020-08-24 09:14:26</td>
<td class="org-right">0:08</td>
</tr>


<tr>
<td class="org-right">4</td>
<td class="org-left">2020-08-24 09:14:33</td>
<td class="org-right">0:07</td>
</tr>


<tr>
<td class="org-right">5</td>
<td class="org-left">2020-08-24 09:14:43</td>
<td class="org-right">0:10</td>
</tr>


<tr>
<td class="org-right">6</td>
<td class="org-left">2020-08-24 09:14:56</td>
<td class="org-right">0:13</td>
</tr>


<tr>
<td class="org-right">7</td>
<td class="org-left">2020-08-24 09:15:06</td>
<td class="org-right">0:10</td>
</tr>


<tr>
<td class="org-right">8</td>
<td class="org-left">2020-08-24 09:15:24</td>
<td class="org-right">0:18</td>
</tr>


<tr>
<td class="org-right">9</td>
<td class="org-left">2020-08-24 09:15:51</td>
<td class="org-right">0:27</td>
</tr>


<tr>
<td class="org-right">10</td>
<td class="org-left">2020-08-24 09:16:44</td>
<td class="org-right">0:53</td>
</tr>


<tr>
<td class="org-right">11</td>
<td class="org-left">2020-08-24 09:17:47</td>
<td class="org-right">1:03</td>
</tr>


<tr>
<td class="org-right">12</td>
<td class="org-left">2020-08-24 09:18:33</td>
<td class="org-right">0:46</td>
</tr>


<tr>
<td class="org-right">13</td>
<td class="org-left">2020-08-24 09:20:06</td>
<td class="org-right">1:33</td>
</tr>


<tr>
<td class="org-right">14</td>
<td class="org-left">2020-08-24 09:21:52</td>
<td class="org-right">1:46</td>
</tr>


<tr>
<td class="org-right">15</td>
<td class="org-left">2020-08-24 09:22:54</td>
<td class="org-right">1:02</td>
</tr>


<tr>
<td class="org-right">16</td>
<td class="org-left">2020-08-24 09:24:16</td>
<td class="org-right">1:22</td>
</tr>


<tr>
<td class="org-right">17</td>
<td class="org-left">2020-08-24 09:27:31</td>
<td class="org-right">3:15</td>
</tr>


<tr>
<td class="org-right">18</td>
<td class="org-left">2020-08-24 09:30:19</td>
<td class="org-right">2:48</td>
</tr>


<tr>
<td class="org-right">19</td>
<td class="org-left">2020-08-24 09:34:15</td>
<td class="org-right">3:56</td>
</tr>


<tr>
<td class="org-right">20</td>
<td class="org-left">2020-08-24 09:38:10</td>
<td class="org-right">3:55</td>
</tr>


<tr>
<td class="org-right">21</td>
<td class="org-left">2020-08-24 09:42:48</td>
<td class="org-right">4:38</td>
</tr>


<tr>
<td class="org-right">22</td>
<td class="org-left">2020-08-24 09:47:23</td>
<td class="org-right">4:35</td>
</tr>


<tr>
<td class="org-right">23</td>
<td class="org-left">2020-08-24 09:52:56</td>
<td class="org-right">5:33</td>
</tr>


<tr>
<td class="org-right">24</td>
<td class="org-left">2020-08-24 09:58:55</td>
<td class="org-right">5:59</td>
</tr>
</tbody>

<tbody>
<tr>
<td class="org-right">Elapsed</td>
<td class="org-left">44:54</td>
<td class="org-right">&#xa0;</td>
</tr>
</tbody>
</table>

Second run from dev branch:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">Period</th>
<th scope="col" class="org-left">Time</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">0</td>
<td class="org-left">2021-08-24 10:17:36</td>
</tr>


<tr>
<td class="org-right">24</td>
<td class="org-left">2020-08-24 11:03:10</td>
</tr>
</tbody>

<tbody>
<tr>
<td class="org-right">Elapsed</td>
<td class="org-left">46:34</td>
</tr>
</tbody>
</table>


<a id="org54befce"></a>

## Memory profiling

Here is how to install and run memory profiling.

    conda install memory_profiler
    python -m memory_profiler ridehail.py -@ config/manhattan.config


<a id="org59a1c33"></a>

# CProfile

With 15 periods of Manhattan run, here is the CProfile output, simplified and sorted:

    120524852 function calls (120524822 primitive calls) in 433.610 seconds

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">ncalls</th>
<th scope="col" class="org-right">tottime</th>
<th scope="col" class="org-right">percall</th>
<th scope="col" class="org-right">cumtime</th>
<th scope="col" class="org-right">percall</th>
<th scope="col" class="org-left">filename:lineno(function)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">0</td>
<td class="org-right">.000</td>
<td class="org-right">0.000</td>
<td class="org-right">433.610</td>
<td class="org-right">433.610</td>
<td class="org-left">ridehail.py:201(main)</td>
</tr>


<tr>
<td class="org-right">15</td>
<td class="org-right">0.079</td>
<td class="org-right">0.005</td>
<td class="org-right">433.548</td>
<td class="org-right">28.903</td>
<td class="org-left">ridehail\simulation.py:122(<sub>next</sub><sub>period</sub>)</td>
</tr>


<tr>
<td class="org-right">0</td>
<td class="org-right">.000</td>
<td class="org-right">0.000</td>
<td class="org-right">433.548</td>
<td class="org-right">433.548</td>
<td class="org-left">ridehail\simulation.py:108(simulate)</td>
</tr>


<tr>
<td class="org-right">162</td>
<td class="org-right">378.815</td>
<td class="org-right">2.338</td>
<td class="org-right">379.043</td>
<td class="org-right">2.340</td>
<td class="org-left">ridehail\simulation.py:435(<sub>collect</sub><sub>garbage</sub>)</td>
</tr>


<tr>
<td class="org-right">15</td>
<td class="org-right">0.064</td>
<td class="org-right">0.004</td>
<td class="org-right">52.725</td>
<td class="org-right">3.515</td>
<td class="org-left">ridehail\simulation.py:210(<sub>assign</sub><sub>drivers</sub>)</td>
</tr>


<tr>
<td class="org-right">4576</td>
<td class="org-right">5.848</td>
<td class="org-right">0.001</td>
<td class="org-right">52.520</td>
<td class="org-right">0.011</td>
<td class="org-left">ridehail\simulation.py:235(<sub>assign</sub><sub>driver</sub>)</td>
</tr>


<tr>
<td class="org-right">8114691</td>
<td class="org-right">7.221</td>
<td class="org-right">0.000</td>
<td class="org-right">14.114</td>
<td class="org-right">0.000</td>
<td class="org-left">ridehail\atom.py:321(<listcomp>)</td>
</tr>


<tr>
<td class="org-right">8123691</td>
<td class="org-right">9.203</td>
<td class="org-right">0.000</td>
<td class="org-right">13.650</td>
<td class="org-right">0.000</td>
<td class="org-left">ridehail\atom.py:297(distance)</td>
</tr>
</tbody>
</table>

So the major work is done in: 

-   garbage collection (this could be avoided)
-   assigning drivers
-   computing distances

Looks like garbage collection was being called inside a driver loop. Terrible! Took it out of the loop and then fixed it to be only every now and then. For 25 periods:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-right" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-right">ncalls</th>
<th scope="col" class="org-right">tottime</th>
<th scope="col" class="org-right">percall</th>
<th scope="col" class="org-right">cumtime</th>
<th scope="col" class="org-right">percall</th>
<th scope="col" class="org-left">filename:lineno(function)</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-right">1</td>
<td class="org-right">0.000</td>
<td class="org-right">0.000</td>
<td class="org-right">84.263</td>
<td class="org-right">84.263</td>
<td class="org-left">ridehail.py:201(main)</td>
</tr>


<tr>
<td class="org-right">1</td>
<td class="org-right">0.000</td>
<td class="org-right">0.000</td>
<td class="org-right">84.204</td>
<td class="org-right">84.204</td>
<td class="org-left">ridehail\simulation.py:109(simulate)</td>
</tr>


<tr>
<td class="org-right">25</td>
<td class="org-right">0.137</td>
<td class="org-right">0.005</td>
<td class="org-right">84.204</td>
<td class="org-right">3.368</td>
<td class="org-left">ridehail\simulation.py:123(<sub>next</sub><sub>period</sub>)</td>
</tr>


<tr>
<td class="org-right">25</td>
<td class="org-right">0.110</td>
<td class="org-right">0.004</td>
<td class="org-right">75.643</td>
<td class="org-right">3.026</td>
<td class="org-left">ridehail\simulation.py:211(<sub>assign</sub><sub>drivers</sub>)</td>
</tr>


<tr>
<td class="org-right">22017</td>
<td class="org-right">7.125</td>
<td class="org-right">0.000</td>
<td class="org-right">75.321</td>
<td class="org-right">0.003</td>
<td class="org-left">ridehail\simulation.py:236(<sub>assign</sub><sub>driver</sub>)</td>
</tr>


<tr>
<td class="org-right">8131803</td>
<td class="org-right">6.634</td>
<td class="org-right">0.000</td>
<td class="org-right">40.407</td>
<td class="org-right">0.000</td>
<td class="org-left">ridehail\atom.py:312(travel<sub>distance</sub>)</td>
</tr>


<tr>
<td class="org-right">8131803</td>
<td class="org-right">9.827</td>
<td class="org-right">0.000</td>
<td class="org-right">18.034</td>
<td class="org-right">0.000</td>
<td class="org-left">ridehail\atom.py:321(<listcomp>)</td>
</tr>


<tr>
<td class="org-right">22017</td>
<td class="org-right">15.773</td>
<td class="org-right">0.001</td>
<td class="org-right">15.773</td>
<td class="org-right">0.001</td>
<td class="org-left">ridehail\simulation.py:246(<listcomp>)</td>
</tr>


<tr>
<td class="org-right">8146803</td>
<td class="org-right">10.718</td>
<td class="org-right">0.000</td>
<td class="org-right">15.767</td>
<td class="org-right">0.000</td>
<td class="org-left">ridehail\atom.py:297(distance)</td>
</tr>


<tr>
<td class="org-right">4895</td>
<td class="org-right">3.966</td>
<td class="org-right">0.001</td>
<td class="org-right">11.983</td>
<td class="org-right">0.002</td>
<td class="org-left">random.py:264(shuffle)</td>
</tr>


<tr>
<td class="org-right">17108293</td>
<td class="org-right">6.509</td>
<td class="org-right">0.000</td>
<td class="org-right">8.630</td>
<td class="org-right">0.000</td>
<td class="org-left">types.py:164(<span class="underline"><span class="underline">get</span></span>)</td>
</tr>


<tr>
<td class="org-right">8293315</td>
<td class="org-right">5.634</td>
<td class="org-right">0.000</td>
<td class="org-right">8.193</td>
<td class="org-right">0.000</td>
<td class="org-left">random.py:224(<sub>randbelow</sub>)</td>
</tr>


<tr>
<td class="org-right">25</td>
<td class="org-right">5.581</td>
<td class="org-right">0.223</td>
<td class="org-right">5.585</td>
<td class="org-right">0.223</td>
<td class="org-left">ridehail\simulation.py:436(<sub>collect</sub><sub>garbage</sub>)</td>
</tr>
</tbody>
</table>

So now it is down to assigning drivers and calculating travel distances.

With display, assigning drivers is still the big time consumer, and in that the effort of collecting a list of available drivers is the biggest contributor.

Each time a driver is assigned, the list of available drivers is computed, which means many times per period. Let&rsquo;s compute it once per period and then update the list during the assignment phase.

