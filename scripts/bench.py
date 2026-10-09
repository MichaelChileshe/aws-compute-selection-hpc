#!/usr/bin/env python3
"""The price-performance benchmark: the same catsim run on every bench node, with 1 process and
with one per vCPU, then today's on-demand and Spot prices turned into "cost per million
simulated years". Also checks that every node produced the identical answer (digest).

  python3 scripts/bench.py --years 60000
"""
import argparse
import csv
import os
import threading

from kit_aws import RESULTS, result_lines, tf_output, write_result
from prices import prices
from ssm_run import run


def bench_node(name, node, years, out):
    res = {}
    for procs in (1, 2):    # 2 = the default: one process per vCPU
        flag = "--procs 1" if procs == 1 else ""
        text = run(node["id"], f"catsim bench --years {years} {flag}", echo=False)
        res[procs] = result_lines(text)[0]
        print(f"  {name:9} {node['type']:10} procs {res[procs]['procs']}: {res[procs]['years_per_second']:>8,.1f} years/s "
              f"({res[procs]['seconds']} s, {res[procs]['arch']}, python {res[procs]['python']}, digest {res[procs]['digest']})",
              flush=True)
    out[name] = res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=60000)
    a = ap.parse_args()
    nodes = tf_output("bench_nodes")
    if not nodes:
        raise SystemExit("no bench nodes: is bench_lab = true applied?")
    out, threads = {}, []
    print(f"catsim bench, {a.years:,} years, on {len(nodes)} nodes at once:")
    for name, node in nodes.items():
        t = threading.Thread(target=bench_node, args=(name, node, a.years, out))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    rows = []
    for name, node in nodes.items():
        p = prices(node["type"])
        r1, r2 = out[name][1], out[name][2]
        full = r2["years_per_second"]
        per_m = lambda usd: round(usd / (full * 3600) * 1e6, 4) if usd else None
        rows.append({"node": name, "instance_type": node["type"], "arch": r2["arch"], "vcpus": r2["cpus"],
                     "years_per_s_1_proc": r1["years_per_second"], "years_per_s_all_vcpus": full,
                     "scaling_1_to_all": round(full / r1["years_per_second"], 2),
                     "on_demand_usd_hr": p["on_demand_usd_hr"], "spot_min_usd_hr": p["spot_min_usd_hr"],
                     "usd_per_million_years_on_demand": per_m(p["on_demand_usd_hr"]),
                     "usd_per_million_years_spot": per_m(p["spot_min_usd_hr"]),
                     "digest": r2["digest"], "digest_1_proc": r1["digest"]})
    digests = {r["digest"] for r in rows} | {r["digest_1_proc"] for r in rows}
    best = min(rows, key=lambda r: r["usd_per_million_years_on_demand"] or 1e9)
    for r in rows:
        r["cost_vs_best_on_demand"] = round(r["usd_per_million_years_on_demand"] / best["usd_per_million_years_on_demand"], 2)
    write_result("bench", {"years": a.years, "rows": rows, "raw": out, "identical_answers": len(digests) == 1})
    with open(os.path.join(RESULTS, "bench.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nnode | type | years/s 1 proc | years/s all vCPUs | scaling | on-demand $/h | Spot $/h | "
          "$ per M years on-demand | $ per M years Spot")
    for r in rows:
        print(f"{r['node']} | {r['instance_type']} | {r['years_per_s_1_proc']:,.1f} | {r['years_per_s_all_vcpus']:,.1f} | "
              f"{r['scaling_1_to_all']}x | {r['on_demand_usd_hr']} | {r['spot_min_usd_hr']} | "
              f"{r['usd_per_million_years_on_demand']} | {r['usd_per_million_years_spot']}")
    print(f"RESULT bench: cheapest per simulated year on-demand = {best['node']} ({best['instance_type']}); "
          f"answers {'IDENTICAL on every node and process count' if len(digests) == 1 else 'DIFFERENT: ' + str(digests)}")


if __name__ == "__main__":
    main()
