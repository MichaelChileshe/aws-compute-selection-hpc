#!/usr/bin/env python3
"""Every measured number from build/results/ in one list (and build/results/summary.csv).
Anything not measured yet shows as "-".

  python3 scripts/results.py
"""
import csv
import json
import os
import re

from kit_aws import RESULTS


def j(name):
    p = os.path.join(RESULTS, f"{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    rows = []

    def add(section, item, value):
        rows.append((section, item, "-" if value in (None, "") else value))

    p = j("placement")
    for r in (p or {}).get("pairs", []):
        add("Placement", f"{r['placement']}: avg RTT ms / 1-stream Gbit/s / 8-stream Gbit/s",
            f"{r['rtt_avg_ms']} / {r['gbps_1_stream']} / {r['gbps_8_streams']}")
    b = j("bench")
    for r in (b or {}).get("rows", []):
        add("Benchmark", f"{r['instance_type']} ({r['arch']}): years/s 1 proc / all vCPUs / scaling",
            f"{r['years_per_s_1_proc']} / {r['years_per_s_all_vcpus']} / {r['scaling_1_to_all']}x")
        add("Benchmark", f"{r['instance_type']}: US$ per million years on-demand / Spot",
            f"{r['usd_per_million_years_on_demand']} / {r['usd_per_million_years_spot']}")
    add("Benchmark", "identical answers on every node", None if b is None else b["identical_answers"])
    s = j("spot")
    if s:
        res, tl = s.get("result") or {}, s.get("timeline") or {}
        add("Spot job", "years / chunks / digest", f"{res.get('years')} / {res.get('chunks')} / {res.get('digest')}")
        for k, v in tl.items():
            add("Spot job", k, v)
    for arch in ("graviton", "x86"):
        r = j(f"batch-{arch}")
        if r:
            add("Batch", f"{arch}: children / wall clock s / first start s / retried",
                f"{r['succeeded']}/{r['children']} / {r['wall_clock_s']} / {r['submit_to_first_start_s']} / {len(r['retried_children'])}")
            add("Batch", f"{arch}: instances / types / est. Spot cost US$",
                f"{len(r['instances'])} / {', '.join(r['instance_types'])} / {r['est_spot_cost_usd']}")
            add("Batch", f"{arch}: digest / same as Spot job", f"{r['answer']['digest']} / {r['same_as_spot_job']}")
    for name in sorted(os.listdir(RESULTS)) if os.path.isdir(RESULTS) else []:
        if name.startswith("tf-") and name.endswith(".txt"):
            line = None
            for ln in open(os.path.join(RESULTS, name), errors="replace"):
                if re.search(r"^(Plan:|Destroy complete!|Apply complete!|No changes\.)", ln.strip()):
                    line = ln.strip()
            add("Terraform", name, line)
    if not rows:
        print("nothing measured yet")
        return 0
    width = max(len(r[1]) for r in rows)
    section = None
    for sec, item, value in rows:
        if sec != section:
            print(f"\n{sec}")
            section = sec
        print(f"  {item:<{width}}  {value}")
    with open(os.path.join(RESULTS, "summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["section", "item", "value"])
        w.writerows(rows)
    print("\nwritten: build/results/summary.csv")
    return 0


if __name__ == "__main__":
    main()
