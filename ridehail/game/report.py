"""
The end-of-shift debrief: the player's results, set against the bots and the
rest of the fleet.
"""

from ridehail.game import offer_model
from ridehail.game.params import HST_RATE, MIN_FLEET_MINUTES


def shift_results(game):
    """Everything the end-of-shift debrief needs."""
    p = game.params
    minutes = game.shift_minutes()
    player = game.ledgers[game.player].summary(p)
    bots = []
    for index, bot in game.bots.items():
        row = game.ledgers[index].summary(p)
        row.update({"key": bot.key, "name": bot.name})
        bots.append(row)
    # Every other driver, each over their own time on shift (see
    # on_shift), leaving out any who joined too late to be comparable.
    others = [
        game.ledgers[i]
        for i in sorted(game.on_shift)
        if i != game.player
        and sum(game.ledgers[i].minutes.values()) >= MIN_FLEET_MINUTES
    ]
    fleet = [ledger.summary(p)["net_per_hour"] for ledger in others]
    # Their pooled share of what riders paid before HST
    fleet_fares = sum(ledger.rider_fares for ledger in others) / (1 + HST_RATE)
    fleet_share = (
        round(sum(ledger.earnings for ledger in others) / fleet_fares, 3)
        if fleet_fares > 0
        else None
    )
    beaten = sum(1 for value in fleet if value < player["net_per_hour"])
    log = game.offer_log
    accepted = [e for e in log if e["decision"] == "accept"]
    declined = [e for e in log if e["decision"] != "accept"]
    return {
        "player": player,
        "bots": bots,
        "fleet_net_per_hour": sorted(fleet),
        "fleet_mean_net_per_hour": round(sum(fleet) / len(fleet), 2) if fleet else 0.0,
        "fleet_percentile": round(beaten / len(fleet), 3) if fleet else None,
        "fleet_driver_share": fleet_share,
        # Those drivers' pooled time in each phase, for the debrief's
        # "Where your time went" comparison
        "fleet_minutes": {
            phase: round(sum(ledger.minutes[phase] for ledger in others), 1)
            for phase in ("P1", "P2", "P3")
        },
        "offer_log": log,
        "insights": {
            "declined_above_rate_card": sum(
                1 for e in declined if e["offer"] >= e["rate_card"]
            ),
            "accepted_below_rate_card": sum(
                1 for e in accepted if e["offer"] < e["rate_card"]
            ),
            "unpaid_share": (
                round(
                    (player["minutes"]["P1"] + player["minutes"]["P2"]) / minutes,
                    3,
                )
                if minutes
                else None
            ),
            "pickup_share": (
                round(player["minutes"]["P2"] / minutes, 3) if minutes else None
            ),
            "best_per_min": max((e["per_min"] for e in accepted), default=None),
            "worst_per_min": min((e["per_min"] for e in accepted), default=None),
            "idle_minutes_per_offer": (
                round(player["minutes"]["P1"] / len(log), 2) if log else None
            ),
            "rider_extra_wait": sum(e.get("rider_extra_wait", 0) for e in declined),
            "declined_never_taken": sum(
                1 for e in declined if "taken_after_minutes" not in e
            ),
        },
        "params": {
            "shift_blocks": p.shift_blocks,
            "rate_base": p.rate_base,
            "rate_per_km": p.rate_per_km,
            "rate_per_min": p.rate_per_min,
            "ops_cost_per_km": p.ops_cost_per_km,
            "offer_study_offers": offer_model.N_OFFERS,
            "rider_fare_base": offer_model.RIDER_FARE_BASE,
            "rider_fare_per_km": offer_model.RIDER_FARE_PER_KM,
            "rider_fare_months": offer_model.RIDER_FARE_MONTHS,
            "hst_rate": HST_RATE,
            "city_km": round(game.sim.city.city_size * p.km_per_block, 1),
        },
    }
