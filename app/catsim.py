"""catsim: Themba Insurance's property catastrophe model (hail, flood, windstorm) for South Africa.

Simulates N years of catastrophe events against Themba's book of 2,000 insured zones and reports:
  gross and net average annual loss (AAL), the largest year, how often a year's loss exceeds
  fixed thresholds, and the 1-in-200-year loss (the 99.5th percentile the solvency capital
  calculation needs).

Every year has its own random seed (seed, year number), so the answer does not depend on how the
years are split: 1 process or 8, one machine or 40 Batch jobs, interrupted and resumed or not.
The model only uses +, -, *, / and comparisons on floats (no exp/log/pow at run time), which
IEEE 754 defines exactly, so Graviton (arm64), Intel and AMD give bit-for-bit the same totals.

  python3 catsim.py run   --years 100000 --procs 2          # print the result (and its digest)
  python3 catsim.py bench --years 100000 --procs 2          # same, plus years per second
  AWS Batch array child:  python3 catsim.py run --years 100000 --array   (start = index x years)
"""
import argparse
import hashlib
import json
import os
import platform
import random
import sys
import time

BIN = 10_000_000                      # histogram bin: R10 million of annual gross loss
THRESHOLDS = [250_000_000, 500_000_000, 1_000_000_000, 2_000_000_000]
RETENTION, LIMIT = 250_000_000, 1_000_000_000   # catastrophe excess-of-loss reinsurance, per event

# peril: (events per year, P(0 events) = exp(-rate) precomputed, footprint radius km, zone cutoff km)
PERILS = {
    "hail":  (2.2, 0.11080315836233387, 25.0, 100.0),
    "flood": (0.8, 0.44932896411722156, 60.0, 240.0),
    "wind":  (1.1, 0.33287108369807955, 120.0, 480.0),
}
# Damage ratio at the centre of an event: inverse CDF as straight lines between these points.
SEVERITY = [(0.0, 0.0004), (0.5, 0.0025), (0.8, 0.007), (0.95, 0.018), (0.99, 0.045), (0.999, 0.09), (1.0, 0.14)]
# Province "hubs" (x, y in km on a flat grid) with their share of the 400 zones.
HUBS = [(950, 1150, 600), (900, 1080, 350), (1050, 1350, 200), (700, 300, 250), (1350, 650, 250),
        (600, 900, 125), (1150, 1000, 100), (250, 250, 75), (850, 600, 50)]


def book(seed=2026):
    """The insured zones: (x, y, sum insured in Rand). Fixed: the same 2,000 zones every run."""
    rng, zones = random.Random(seed), []
    for hx, hy, n in HUBS:
        for _ in range(n):
            x = hx + (rng.random() - 0.5) * 160.0
            y = hy + (rng.random() - 0.5) * 160.0
            zones.append((x, y, 5_000_000 + rng.randrange(95_000_000)))
    return zones


def poisson_table(rate, p0, kmax=15):
    cdf, p, acc = [], p0, 0.0
    for k in range(kmax + 1):
        acc += p
        cdf.append(acc)
        p = p * rate / (k + 1)
    return cdf


TABLES = {name: poisson_table(r, p0) for name, (r, p0, _, _) in PERILS.items()}


def severity(u):
    for (u0, d0), (u1, d1) in zip(SEVERITY, SEVERITY[1:]):
        if u <= u1:
            return d0 + (d1 - d0) * (u - u0) / (u1 - u0)
    return SEVERITY[-1][1]


def simulate_year(zones, seed, year):
    """One year: (gross loss, net loss after reinsurance), whole Rand."""
    rng = random.Random(seed * 1_000_003 + year)
    gross = net = 0
    for name, (_, _, radius, cutoff) in PERILS.items():
        u, n = rng.random(), 0
        for n, c in enumerate(TABLES[name]):
            if u <= c:
                break
        r2, c2 = radius * radius, cutoff * cutoff
        for _ in range(n):
            cx, cy, _si = zones[rng.randrange(len(zones))]
            cx += (rng.random() - 0.5) * 2.0 * radius
            cy += (rng.random() - 0.5) * 2.0 * radius
            dr = severity(rng.random())
            loss = 0.0
            for x, y, si in zones:
                dx, dy = x - cx, y - cy
                d2 = dx * dx + dy * dy
                if d2 < c2:
                    loss += si * dr / (1.0 + d2 / r2)
            event = int(loss)
            gross += event
            net += min(event, RETENTION) + max(0, event - RETENTION - LIMIT)
    return gross, net


def empty():
    return {"years": 0, "gross_total": 0, "net_total": 0, "max_gross": 0,
            "exceed": {str(t): 0 for t in THRESHOLDS}, "hist": {}}


def add_year(agg, gross, net):
    agg["years"] += 1
    agg["gross_total"] += gross
    agg["net_total"] += net
    agg["max_gross"] = max(agg["max_gross"], gross)
    for t in THRESHOLDS:
        if gross > t:
            agg["exceed"][str(t)] += 1
    b = str(gross // BIN)
    agg["hist"][b] = agg["hist"].get(b, 0) + 1


def merge(a, b):
    out = empty()
    for agg in (a, b):
        out["years"] += agg["years"]
        out["gross_total"] += agg["gross_total"]
        out["net_total"] += agg["net_total"]
        out["max_gross"] = max(out["max_gross"], agg["max_gross"])
        for t, c in agg["exceed"].items():
            out["exceed"][t] += c
        for k, c in agg["hist"].items():
            out["hist"][k] = out["hist"].get(k, 0) + c
    return out


def run_range(args):
    seed, start, years = args
    zones, agg = book(), empty()
    for y in range(start, start + years):
        add_year(agg, *simulate_year(zones, seed, y))
    return agg


def run(seed, start, years, procs):
    """Split [start, start+years) into procs slices, one process each, and merge."""
    if procs <= 1:
        return run_range((seed, start, years))
    from multiprocessing import Pool
    step = -(-years // procs)
    parts = [(seed, s, min(step, start + years - s)) for s in range(start, start + years, step)]
    with Pool(len(parts)) as pool:
        out = empty()
        for agg in pool.map(run_range, parts):
            out = merge(out, agg)
    return out


def summary(agg):
    """Headline numbers. The 1-in-200 loss is read from the histogram (to the R10m bin)."""
    years, total, run_ = agg["years"], 0, 0
    target = years - years // 200          # the year at the 99.5th percentile, counted from the bottom
    var995 = None
    for k in sorted(agg["hist"], key=int):
        run_ += agg["hist"][k]
        if run_ >= target:
            var995 = (int(k) + 1) * BIN
            break
    canon = json.dumps(agg, sort_keys=True, separators=(",", ":"))
    return {"years": years,
            "gross_aal_rand": agg["gross_total"] // years if years else 0,
            "net_aal_rand": agg["net_total"] // years if years else 0,
            "gross_total_rand": agg["gross_total"], "net_total_rand": agg["net_total"],
            "max_year_gross_rand": agg["max_gross"],
            "one_in_200_gross_rand": var995,
            "years_over": agg["exceed"],
            "digest": hashlib.sha256(canon.encode()).hexdigest()[:16]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["run", "bench"])
    ap.add_argument("--years", type=int, default=100_000)
    ap.add_argument("--start", type=int, default=0, help="first year number")
    ap.add_argument("--seed", type=int, default=26)
    ap.add_argument("--procs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--array", action="store_true", help="AWS Batch array child: start = index x years")
    ap.add_argument("--raw", action="store_true", help="also print the full aggregate (for merging)")
    a = ap.parse_args()
    start = a.start
    if a.array:
        start = int(os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX", "0")) * a.years
    t0 = time.time()
    agg = run(a.seed, start, a.years, a.procs)
    secs = time.time() - t0
    out = {"mode": a.mode, "seed": a.seed, "start": start, "procs": a.procs, "cpus": os.cpu_count(),
           "arch": platform.machine(), "python": platform.python_version(), "seconds": round(secs, 2),
           "years_per_second": round(a.years / secs, 1)}
    out.update(summary(agg))
    print("RESULT " + json.dumps(out), flush=True)
    if a.raw:
        print("AGG " + json.dumps(agg, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
