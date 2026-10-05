"""
Offer prices and rider fares.

Offer prices come from a model fitted to the offer study (Uber offer cards
shown to Toronto drivers), weighted to Toronto's mix of trip lengths; see
ridehail/game/offer_model.py and claude/game-mode.md, Part 3:

    offer = F(trip_km, pickup_km) * luck

F falls per km as trips get longer and rises with long pickups. The luck is
drawn once per trip from the offer study's spread, so every driver offered a
trip shares it, but each driver's offer depends on their own pickup
distance. Each trip also has a rate card (base + per km + per minute, for the
trip only), which is a reference for the debrief and the rate-card bot, not
the source of the offer.

Rider fares: what the rider probably paid for each trip (claude/game-mode.md,
Part 4). The typical fare for the trip's length comes from the City of
Toronto's 2026 trip data (base + per km, including City fees and HST, excluding
tips). The trip's luck scales it as it scales the driver's offer, normalised
so the average fare is unchanged: the platform's take on real trips varies far
less than offers do, so a trip that pays the driver well also cost the rider
more. The debrief compares it with what the driver was paid.
"""

import bisect
import math

from ridehail.game import offer_model

# Mean of e^luck in each luck band, so that scaling a typical rider fare by
# e^luck / this leaves the average fare unchanged
MEAN_EXP_LUCK = [
    sum(math.exp(q) for q in band) / len(band) for band in offer_model.LUCK_QUANTILES
]


class OfferPricing:
    """
    Prices for one shift. The luck draws use the shift's random number
    generator, shared with the GameController, so a shift code always gives
    the same prices.
    """

    def __init__(self, params, rng):
        self.params = params
        self.rng = rng
        # trip id -> (rate_card, luck): drawn once per trip
        self.prices = {}
        # Set to a list to collect every offer priced (for validation)
        self.record_offers = None

    def rate_card(self, trip_blocks):
        p = self.params
        return (
            p.rate_base
            + p.rate_per_km * trip_blocks * p.km_per_block
            + p.rate_per_min * trip_blocks * p.minutes_per_block
        )

    def _round_price(self, value):
        step = self.params.price_step
        return round(round(value / step) * step, 2)

    def price(self, trip):
        """(rate_card, luck) for a trip, drawn the first time it is needed."""
        if trip.index not in self.prices:
            km = trip.distance * self.params.km_per_block
            band = bisect.bisect_right(offer_model.LUCK_BAND_EDGES, km)
            self.prices[trip.index] = (
                round(self.rate_card(trip.distance), 2),
                self._draw_luck(band),
            )
        return self.prices[trip.index]

    def _draw_luck(self, band):
        """log(offer / F), by inverse CDF from the stored quantiles."""
        probs = offer_model.LUCK_PROBS
        quantiles = offer_model.LUCK_QUANTILES[band]
        u = min(max(self.rng.random(), probs[0]), probs[-1])
        i = min(bisect.bisect_right(probs, u), len(probs) - 1)
        p0, p1 = probs[i - 1], probs[i]
        q0, q1 = quantiles[i - 1], quantiles[i]
        return q0 + (q1 - q0) * (u - p0) / (p1 - p0)

    @staticmethod
    def typical_offer(trip_km, pickup_km):
        """F: the typical offer for a trip and pickup (before the trip's luck)."""
        c = offer_model.COEF
        log_km = math.log(max(trip_km, 0.1))
        log_f = c[0] + c[1] * log_km + c[2] * log_km * log_km
        if offer_model.FORM == "log1p":
            log_f += c[3] * math.log1p(pickup_km)
        else:
            log_f += c[3] * pickup_km + c[4] * max(0.0, pickup_km - offer_model.KNEE_KM)
        return math.exp(log_f)

    def offer_price(self, trip, dispatch_distance):
        """The offer to a driver dispatch_distance blocks from the pickup."""
        p = self.params
        trip_km = trip.distance * p.km_per_block
        pickup_km = dispatch_distance * p.km_per_block
        luck = self.price(trip)[1]
        value = max(
            offer_model.MIN_OFFER,
            self.typical_offer(trip_km, pickup_km) * math.exp(luck),
        )
        offer = self._round_price(value)
        if self.record_offers is not None:
            self.record_offers.append(
                {"offer": offer, "trip_km": trip_km, "pickup_km": pickup_km}
            )
        return offer

    @staticmethod
    def typical_rider_fare(trip_km):
        """The City's typical fare for a trip this long (City fees and HST in)."""
        return offer_model.RIDER_FARE_BASE + offer_model.RIDER_FARE_PER_KM * trip_km

    def rider_fare(self, trip):
        """
        What the rider probably paid for a trip: the typical fare, scaled by
        the trip's luck as the driver's offer is, with the average unchanged.
        """
        trip_km = trip.distance * self.params.km_per_block
        band = bisect.bisect_right(offer_model.LUCK_BAND_EDGES, trip_km)
        luck = self.price(trip)[1]
        return round(
            self.typical_rider_fare(trip_km) * math.exp(luck) / MEAN_EXP_LUCK[band], 2
        )
