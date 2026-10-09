"""
Fit the game's offer-price model (claude/game-mode.md, Part 3) and write it
to ridehail/game/offer_model.py.

The price of a trip given its length and pickup comes from the offer study
(Uber offer cards shown to Toronto drivers); the mix of trip lengths it is
fitted over comes from the City of Toronto's trip records, so the fit
concentrates where Toronto's trips are rather than where the offer study's
are (it has too many long and airport trips).

    offer = F(trip_km, pickup_km) * luck,   log F = a + b*L + c*L^2 + g(pickup_km)

with L = log(trip_km), g chosen between log(1 + pickup_km) and a piecewise
linear form, and luck drawn from the empirical residual quantiles (by trip
length band).

Needs duckdb, which the game itself does not:

    uv run --with duckdb python utils/fit_offer_model.py
    uv run --with duckdb python utils/fit_offer_model.py --validate 20

--validate N plays N Normal shifts with the new model and compares the
offers the game makes with the reweighted offer study (trips <= 12 km).
--city big validates in the big city instead (trips <= 15 km, the fit's
limit, as the big city has longer trips).
"""

import argparse
import datetime
import importlib
from pathlib import Path

import numpy as np

HOME = Path.home()
OFFER_DB = HOME / "src/uberdriver/duckdb/uberdriver.duckdb"
TORONTO_DB = HOME / "src/ridehail-toronto/duckdb/toronto.duckdb"
OPENDATA_DB = HOME / "src/ridehail-toronto/duckdb/toronto_opendata.duckdb"
# Rider fares are fitted to trips from this date on (claude/game-mode.md, Part 4)
RIDER_FARE_FROM = "2026-01-01"
OUT = Path(__file__).resolve().parent.parent / "ridehail" / "game" / "offer_model.py"

# Fit over trips a little longer than the game's 12 km city, so the curve is
# steady at the edge
MAX_FIT_KM = 15.0
MAX_GAME_KM = 12.0
# Residual quantiles are stored per trip-length band (km edges)
LUCK_BAND_EDGES = [2.0, 6.0]
LUCK_PROBS = [round(0.01 * k, 2) for k in range(1, 100)]
KNEES = [2.0, 3.0, 4.0, 5.0, 6.0]
TORONTO_SAMPLE_PERCENT = 2
SEED = 42


def load_offers(path):
    import duckdb

    con = duckdb.connect(str(path), read_only=True)
    df = con.execute(
        f"""
        select o.fare, o.pickup_km, o.trip_km, o.trip_min
        from offer.offers_included o
        where o.platform = 'Uber'
          and o.pickup_in_toronto
          and o.fare > 0 and o.trip_km > 0 and o.trip_km <= {MAX_FIT_KM}
          and o.pickup_km is not null and o.pickup_km >= 0
          and not exists (
              select 1 from offer.landmark_match l
              where l.offer_id = o.offer_id and l.pattern like 'pearson%')
        """
    ).df()
    provenance = con.execute(
        "select max(synced_at)::varchar, arg_max(git_commit, synced_at) from offer.sync_run"
    ).fetchone()
    return df, provenance


def load_toronto_band_shares(path):
    """Share of Toronto trips (<= MAX_FIT_KM) in each 1 km band."""
    import duckdb

    con = duckdb.connect(str(path), read_only=True)
    rows = con.execute(
        f"""
        select floor(distance)::int band, count(*) n,
               min(requestmonth) first_month, max(requestmonth) last_month
        from (select * from uberx_completed_trips
              using sample {TORONTO_SAMPLE_PERCENT} percent (system, {SEED}))
        where distance > 0 and distance <= {MAX_FIT_KM}
        group by 1 order by 1
        """
    ).fetchall()
    total = sum(r[1] for r in rows)
    shares = {r[0]: r[1] / total for r in rows}
    months = (min(r[2] for r in rows), max(r[3] for r in rows))
    return shares, total, months


def band_weights(trip_km, toronto_shares):
    bands = np.floor(trip_km).astype(int)
    bands = np.minimum(bands, int(MAX_FIT_KM) - 1)
    offer_shares = {b: np.mean(bands == b) for b in np.unique(bands)}
    w = np.array([toronto_shares.get(b, 0.0) / offer_shares[b] for b in bands])
    return w / w.mean()


def design(trip_km, pickup_km, form, knee=None):
    L = np.log(trip_km)
    cols = [np.ones_like(L), L, L * L]
    if form == "log1p":
        cols.append(np.log1p(pickup_km))
    else:
        cols += [pickup_km, np.maximum(0.0, pickup_km - knee)]
    return np.column_stack(cols)


def wls(X, y, w):
    sw = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    resid = y - X @ coef
    return coef, resid, float(np.sum(w * resid**2) / np.sum(w))


def weighted_quantiles(values, weights, probs):
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = (np.cumsum(w) - 0.5 * w) / np.sum(w)
    return np.interp(probs, cum, v)


def luck_band(km):
    return int(np.searchsorted(LUCK_BAND_EDGES, km, side="right"))


def fit(df, weights):
    y = np.log(df.fare.to_numpy())
    km = df.trip_km.to_numpy()
    pu = df.pickup_km.to_numpy()
    candidates = [("log1p", None)] + [("piecewise", k) for k in KNEES]
    results = []
    for form, knee in candidates:
        coef, resid, mse = wls(design(km, pu, form, knee), y, weights)
        results.append((mse, form, knee, coef, resid))
        label = form if knee is None else f"{form} knee {knee:g} km"
        print(f"  g = {label:<24} weighted residual sd {np.sqrt(mse):.4f}")
    mse, form, knee, coef, resid = min(results, key=lambda r: r[0])
    print(f"  chosen: {form}" + ("" if knee is None else f", knee {knee:g} km"))
    return form, knee, coef, resid


def diagnostics(df, weights, resid):
    km = df.trip_km.to_numpy()
    pu = df.pickup_km.to_numpy()

    def table(title, groups):
        print(f"\n  Residuals by {title} (weighted): n, median, 10%, 90%")
        for label, mask in groups:
            if mask.sum() < 20:
                continue
            q = weighted_quantiles(resid[mask], weights[mask], [0.1, 0.5, 0.9])
            print(
                f"    {label:<10} {mask.sum():>6} {q[1]:+.3f} {q[0]:+.3f} {q[2]:+.3f}"
            )

    edges = [0, 1, 2, 3, 4, 6, 8, 10, 12, MAX_FIT_KM]
    table(
        "trip km",
        [(f"{a:g}-{b:g}", (km > a) & (km <= b)) for a, b in zip(edges[:-1], edges[1:])],
    )
    pedges = [-0.01, 0.5, 1, 2, 3, 5, 8, 100]
    table(
        "pickup km",
        [
            (f"{max(a, 0):g}-{b:g}", (pu > a) & (pu <= b))
            for a, b in zip(pedges[:-1], pedges[1:])
        ],
    )


def luck_tables(df, weights, resid):
    km = df.trip_km.to_numpy()
    bands = np.array([luck_band(k) for k in km])
    tables = []
    for b in range(len(LUCK_BAND_EDGES) + 1):
        mask = bands == b
        q = weighted_quantiles(resid[mask], weights[mask], LUCK_PROBS)
        tables.append([round(float(v), 4) for v in q])
        print(
            f"  luck band {b}: n {mask.sum()}, 10/50/90% "
            f"{q[9]:+.3f} {q[49]:+.3f} {q[89]:+.3f}"
        )
    return tables


def fit_rider_fare(path):
    """
    What riders paid for a trip of a given length (claude/game-mode.md,
    Part 4): fare = base + per_km * km, by weighted least squares on the City
    of Toronto's hourly origin-destination cells (mean fare, mean distance,
    weight = trips), Toronto to Toronto, cells averaging <= MAX_FIT_KM. The fare
    is trip fare + City fees + HST, excluding tips and promotional discounts,
    for all platforms and products together. Linear in km, so the fit on cell
    means is unbiased if fares are linear within a cell.
    """
    import duckdb

    con = duckdb.connect(str(path), read_only=True)
    df = con.execute(
        f"""
        select strftime(dt, '%Y-%m') as month, trips_total n, fare_avg fare,
               distance_avg km
        from trips
        where dt >= DATE '{RIDER_FARE_FROM}'
          and pickup_municipality = 'Toronto' and dropoff_municipality = 'Toronto'
          and fare_avg > 0 and distance_avg > 0 and duration_avg > 0
          and trips_total > 0 and distance_avg <= {MAX_FIT_KM}
        """
    ).df()
    w = df.n.to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(df)), df.km.to_numpy()])
    coef, resid, mse = wls(X, df.fare.to_numpy(), w)
    print(
        f"\nRider fares, {df.month.min()} to {df.month.max()}: {int(w.sum())} trips "
        f"(Toronto to Toronto, <= {MAX_FIT_KM:g} km): "
        f"${coef[0]:.2f} + ${coef[1]:.3f}/km; cell rse ${np.sqrt(mse):.2f}"
    )
    for month, d in df.groupby("month"):
        c, *_ = wls(
            np.column_stack([np.ones(len(d)), d.km.to_numpy()]),
            d.fare.to_numpy(),
            d.n.to_numpy(dtype=float),
        )
        print(f"  {month}: ${c[0]:.2f} + ${c[1]:.3f}/km; 5 km ${c[0] + 5 * c[1]:.2f}")
    return {
        "base": round(float(coef[0]), 3),
        "per_km": round(float(coef[1]), 4),
        "months": f"{df.month.min()} to {df.month.max()}",
        "trips": int(w.sum()),
    }


def write_module(model, provenance_lines):
    lines = [
        '"""',
        "Offer-price model for ridehail.game. GENERATED by utils/fit_offer_model.py:",
        "do not edit by hand; re-run the script instead. See claude/game-mode.md,",
        "Part 3.",
        "",
        *provenance_lines,
        '"""',
        "",
        "# fmt: off",
        f"FORM = {model['form']!r}",
        f"KNEE_KM = {model['knee']!r}",
        "# log F = COEF[0] + COEF[1]*L + COEF[2]*L^2 + g(pickup_km), L = log(trip_km);",
        "# g = COEF[3]*log(1 + pickup_km), or (piecewise)",
        "# COEF[3]*pickup_km + COEF[4]*max(0, pickup_km - KNEE_KM)",
        f"COEF = {model['coef']!r}",
        "# Trip-length bands (km edges) for the luck tables",
        f"LUCK_BAND_EDGES = {LUCK_BAND_EDGES!r}",
        "# Probabilities of the stored quantiles, the same for every band",
        f"LUCK_PROBS = {LUCK_PROBS!r}",
        "# log(offer / F) quantiles, one list per band",
        "LUCK_QUANTILES = [",
        *[f"    {row!r}," for row in model["luck"]],
        "]",
        "# Offers the model was fitted to (cited in the debrief)",
        f"N_OFFERS = {model['n_offers']!r}",
        "# What riders paid (trip fare + City fees + HST, no tips): base + per km",
        f"RIDER_FARE_BASE = {model['rider_fare']['base']!r}",
        f"RIDER_FARE_PER_KM = {model['rider_fare']['per_km']!r}",
        f"RIDER_FARE_MONTHS = {model['rider_fare']['months']!r}",
        f"RIDER_FARE_TRIPS = {model['rider_fare']['trips']!r}",
        "# No offer below this (the offer study's 1st percentile fare)",
        f"MIN_OFFER = {model['min_offer']!r}",
        "# fmt: on",
        "",
    ]
    OUT.write_text("\n".join(lines))
    print(f"\nWrote {OUT}")


def validate(shifts, study, weights, city="standard"):
    """Offers the game makes (every driver, every dispatch) against the study."""
    import ridehail.game
    import ridehail.game.offer_model
    import ridehail.game.pricing

    # Pick up the model just written. pricing computes a table from it at
    # import, so it is reloaded too (in place, so the controller sees it).
    importlib.reload(ridehail.game.offer_model)
    importlib.reload(ridehail.game.pricing)
    from ridehail.game import create_game

    offers = []
    for i in range(shifts):
        _, game = create_game("normal", f"validate-{i}", city=city)
        game.pricing.record_offers = offers
        while not game.shift_over:
            game.step(lambda offer: True)
    max_km = MAX_GAME_KM if city == "standard" else MAX_FIT_KM
    n_all = len(offers)
    offers = [o for o in offers if o["trip_km"] <= max_km]
    offer = np.array([o["offer"] for o in offers])
    trip_km = np.array([o["trip_km"] for o in offers])
    pickup_km = np.array([o["pickup_km"] for o in offers])
    per_km = offer / (trip_km + pickup_km)
    # Game minutes: one block per minute
    minutes_per_km = 1.0 / ridehail.game.KM_PER_BLOCK
    per_hr = 60 * offer / (minutes_per_km * (trip_km + pickup_km))

    mask = study.trip_km.to_numpy() <= max_km
    s = study[mask]
    w = weights[mask]
    s_offer = s.fare.to_numpy()
    s_per_km = s_offer / (s.trip_km.to_numpy() + s.pickup_km.to_numpy())
    s_per_hr = 60 * s_offer / (
        s.trip_min.to_numpy() + minutes_per_km * s.pickup_km.to_numpy()
    )

    probs = [0.1, 0.25, 0.5, 0.75, 0.9]
    print(
        f"\nValidation ({city} city): {len(offer)} game offers <= {max_km:g} km "
        f"({n_all - len(offer)} longer left out) from {shifts} Normal shifts, "
        f"against {mask.sum()} study offers (<= {max_km:g} km, weighted)"
    )
    print(
        "  (study $/hr uses the card's trip minutes, and the game's minutes per "
        "pickup km)"
    )
    for name, g, sv in [
        ("offer $", offer, s_offer),
        ("$/km", per_km, s_per_km),
        ("$/hr", per_hr, s_per_hr),
    ]:
        gq = np.quantile(g, probs)
        sq = weighted_quantiles(sv, w, probs)
        print(f"  {name:<8} game " + " ".join(f"{v:7.2f}" for v in gq))
        print(f"  {'':<8} data " + " ".join(f"{v:7.2f}" for v in sq))
    print("  Median offer by trip km band: game vs data")
    edges = [0, 2, 4, 6, 8, 10, 12] + ([] if max_km <= 12 else [max_km])
    for a, b in zip(edges[:-1], edges[1:]):
        gm = (trip_km > a) & (trip_km <= b)
        sm = (s.trip_km.to_numpy() > a) & (s.trip_km.to_numpy() <= b)
        if gm.sum() and sm.sum():
            print(
                f"    {a:>2g}-{b:<2g} km  game {np.median(offer[gm]):6.2f} (n {gm.sum():>5})"
                f"   data {weighted_quantiles(s_offer[sm], w[sm], [0.5])[0]:6.2f}"
                f" (n {sm.sum():>5})"
            )
    print(
        f"  Game pickup km: median {np.median(pickup_km):.1f}, 90% {np.quantile(pickup_km, 0.9):.1f}"
    )
    print(
        f"  Data pickup km: median {weighted_quantiles(s.pickup_km.to_numpy(), w, [0.5])[0]:.1f}, "
        f"90% {weighted_quantiles(s.pickup_km.to_numpy(), w, [0.9])[0]:.1f}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--offer-db", type=Path, default=OFFER_DB)
    parser.add_argument("--toronto-db", type=Path, default=TORONTO_DB)
    parser.add_argument("--opendata-db", type=Path, default=OPENDATA_DB)
    parser.add_argument("--validate", type=int, default=0, metavar="SHIFTS")
    parser.add_argument("--city", choices=["standard", "big"], default="standard")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    df, (synced_at, commit) = load_offers(args.offer_db)
    print(
        f"Offer study: {len(df)} Uber offers (Toronto pickups, no Pearson, "
        f"trips <= {MAX_FIT_KM:g} km); last sync {synced_at}, commit {commit}"
    )
    shares, n_toronto, months = load_toronto_band_shares(args.toronto_db)
    print(
        f"Toronto: {n_toronto} trips <= {MAX_FIT_KM:g} km in a {TORONTO_SAMPLE_PERCENT}% "
        f"sample, months {months[0]}-{months[1]}"
    )
    weights = band_weights(df.trip_km.to_numpy(), shares)

    print("\nFit (weighted to Toronto's trip-length mix):")
    form, knee, coef, resid = fit(df, weights)
    y = np.log(df.fare.to_numpy())
    unweighted, *_ = np.linalg.lstsq(
        design(df.trip_km.to_numpy(), df.pickup_km.to_numpy(), form, knee),
        y,
        rcond=None,
    )
    print("  coefficients, weighted:  ", np.round(coef, 4))
    print("  coefficients, unweighted:", np.round(unweighted, 4))
    diagnostics(df, weights, resid)
    print()
    luck = luck_tables(df, weights, resid)
    min_offer = round(
        float(weighted_quantiles(df.fare.to_numpy(), weights, [0.01])[0]), 2
    )
    print(f"  minimum offer (weighted 1st percentile fare): ${min_offer:.2f}")

    rider_fare = fit_rider_fare(args.opendata_db)
    model = {
        "form": form,
        "knee": knee,
        "coef": [round(float(c), 5) for c in coef],
        "luck": luck,
        "min_offer": min_offer,
        "n_offers": len(df),
        "rider_fare": rider_fare,
    }
    def shown(path):
        """A path as ~/..., so the package doesn't carry a home directory."""
        try:
            return "~/" + str(path.resolve().relative_to(HOME))
        except ValueError:
            return str(path)

    provenance = [
        f"Fitted {datetime.date.today().isoformat()} from:",
        f"- the offer study ({shown(args.offer_db)}): {len(df)} Uber offers with a",
        f"  Toronto pickup, no Pearson pickup or drop-off, trips <= {MAX_FIT_KM:g} km;",
        f"  last sync {synced_at}, commit {commit};",
        f"- Toronto trip records ({shown(args.toronto_db)}, uberx_completed_trips,",
        f"  {TORONTO_SAMPLE_PERCENT}% sample, months {months[0]}-{months[1]}): each offer",
        "  weighted by Toronto's share of trips in its 1 km band over the",
        "  offer study's share.",
        f"- rider fares: City of Toronto open data ({shown(args.opendata_db)},",
        f"  trips), {rider_fare['months']}, {rider_fare['trips']} trips Toronto to",
        f"  Toronto, cells averaging <= {MAX_FIT_KM:g} km.",
    ]
    if not args.no_write:
        write_module(model, provenance)
    if args.validate:
        validate(args.validate, df, weights, args.city)


if __name__ == "__main__":
    main()
