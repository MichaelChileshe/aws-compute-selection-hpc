#!/usr/bin/env python3
"""Wait for a Batch array job, then put its answer together and measure the run:

  - every child's RESULT and AGG lines from CloudWatch Logs, merged into one answer (digest)
  - wall clock (submitted -> last child done), time to first start, total container seconds
  - attempts per child (a retry = a child whose Spot instance went away), exit reasons
  - the instances Batch launched (type, Spot or not, AZ, how long each ran) and their Spot cost
  - the same answer as the interrupted Spot job? (build/results/spot.json, if it exists)

  python3 scripts/batch_collect.py --arch graviton
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time

from kit_aws import RESULTS, aws, write_result
from prices import spot

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
import catsim  # noqa: E402

LOG_GROUP = "/aws/batch/themba-cat"


def wait(job_id):
    while True:
        job = aws("batch", "describe-jobs", "--jobs", job_id)["jobs"][0]
        summary = job.get("arrayProperties", {}).get("statusSummary", {})
        print(f"  {time.strftime('%H:%M:%S')}  {job['status']:10} " +
              " ".join(f"{k}={v}" for k, v in sorted(summary.items()) if v), flush=True)
        if job["status"] in ("SUCCEEDED", "FAILED"):
            return job
        time.sleep(30)


def children(job_id):
    ids = []
    for status in ("SUCCEEDED", "FAILED"):
        ids += [j["jobId"] for j in aws("batch", "list-jobs", "--array-job-id", job_id, "--job-status", status)["jobSummaryList"]]
    out = []
    for i in range(0, len(ids), 100):
        out += aws("batch", "describe-jobs", "--jobs", *ids[i:i + 100])["jobs"]
    return sorted(out, key=lambda j: j.get("arrayProperties", {}).get("index", 0))


def log_lines(stream):
    evs = aws("logs", "get-log-events", "--log-group-name", LOG_GROUP, "--log-stream-name", stream,
              "--start-from-head")["events"]
    return [e["message"] for e in evs]


def ended(inst):
    m = re.search(r"\((\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) GMT\)", inst.get("StateTransitionReason", ""))
    if inst["State"]["Name"] in ("terminated", "shutting-down", "stopped") and m:
        return dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", required=True, choices=["graviton", "x86"])
    a = ap.parse_args()
    sub = json.load(open(os.path.join(RESULTS, f"batch-{a.arch}-submit.json")))
    print(f"waiting for {sub['name']} ({sub['job_id']}) ...")
    parent = wait(sub["job_id"])
    kids = children(sub["job_id"])
    agg, per_child, retried, rates, archs = catsim.empty(), [], [], [], set()
    for k in kids:
        att = k.get("attempts", [])
        if len(att) > 1:
            retried.append({"index": k["arrayProperties"]["index"],
                            "attempts": [{"reason": x.get("statusReason"), "exit": x["container"].get("exitCode")} for x in att]})
        if k["status"] != "SUCCEEDED":
            per_child.append({"index": k["arrayProperties"]["index"], "status": k["status"], "reason": k.get("statusReason")})
            continue
        last = att[-1]
        lines = log_lines(last["container"]["logStreamName"])
        res = [json.loads(l[7:]) for l in lines if l.startswith("RESULT ")][0]
        child_agg = [json.loads(l[4:]) for l in lines if l.startswith("AGG ")][0]
        agg = catsim.merge(agg, child_agg)
        rates.append(res["years_per_second"])
        archs.add(res["arch"])
        per_child.append({"index": k["arrayProperties"]["index"], "status": "SUCCEEDED", "attempts": len(att),
                          "start_year": res["start"], "seconds": res["seconds"], "years_per_second": res["years_per_second"],
                          "arch": res["arch"], "run_s": round((last["stoppedAt"] - last["startedAt"]) / 1000, 1)})
    done = [c for c in per_child if c["status"] == "SUCCEEDED"]
    starts = [x["startedAt"] for k in kids for x in k.get("attempts", []) if x.get("startedAt")]
    if not starts:
        reasons = sorted({k.get("statusReason", "?") for k in kids})
        raise SystemExit(f"no child ever started: {parent['status']}, reasons {reasons}")
    first_start = min(starts)
    # The array parent may have no stoppedAt: the run ends when its last child stops.
    last_stop = max(x["stoppedAt"] for k in kids for x in k.get("attempts", []) if x.get("stoppedAt"))
    summ = catsim.summary(agg)

    insts = aws("ec2", "describe-instances", "--filters", f"Name=tag:Name,Values=themba-batch-{a.arch}",
                "--query", "Reservations[].Instances[]")
    inst_rows, cost = [], 0.0
    price_cache = {}
    for i in insts:
        t = i["InstanceType"]
        if t not in price_cache:
            price_cache[t] = spot(t)["by_az"]
        launched = dt.datetime.fromisoformat(i["LaunchTime"].replace("Z", "+00:00"))
        secs = (ended(i) - launched).total_seconds()
        usd_hr = price_cache[t].get(i["Placement"]["AvailabilityZone"])
        c = secs / 3600 * usd_hr if usd_hr else 0.0
        cost += c
        inst_rows.append({"id": i["InstanceId"], "type": t, "lifecycle": i.get("InstanceLifecycle", "on-demand"),
                          "az": i["Placement"]["AvailabilityZone"], "state": i["State"]["Name"],
                          "seconds": round(secs), "spot_usd_hr_now": usd_hr, "est_usd": round(c, 5)})

    spot_digest = None
    spot_path = os.path.join(RESULTS, "spot.json")
    if os.path.exists(spot_path):
        r = json.load(open(spot_path)).get("result") or {}
        spot_digest = r.get("digest")
    out = {"arch": a.arch, "job_id": sub["job_id"], "status": parent["status"], "children": len(kids),
           "succeeded": len(done), "retried_children": retried,
           "wall_clock_s": round((last_stop - parent["createdAt"]) / 1000, 1),
           "submit_to_first_start_s": round((first_start - parent["createdAt"]) / 1000, 1),
           "container_seconds_total": round(sum(c["run_s"] for c in done), 1),
           "child_years_per_second_avg": round(sum(rates) / len(rates), 1) if rates else None,
           "container_archs": sorted(archs), "instances": inst_rows,
           "instance_types": sorted({r["type"] for r in inst_rows}),
           "instance_seconds_total": sum(r["seconds"] for r in inst_rows),
           "est_spot_cost_usd": round(cost, 4), "answer": summ,
           "same_as_spot_job": (summ["digest"] == spot_digest) if spot_digest else None, "per_child": per_child}
    write_result(f"batch-{a.arch}", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_child", "instances")}, indent=1))
    for r in inst_rows:
        print(f"  instance {r['id']} {r['type']:10} {r['lifecycle']:9} {r['az']} {r['state']:11} {r['seconds']:>5} s  ~US${r['est_usd']}")
    print(f"RESULT batch {a.arch}: {out['succeeded']}/{out['children']} children, {summ['years']:,} years, "
          f"wall clock {out['wall_clock_s']} s (first start after {out['submit_to_first_start_s']} s), "
          f"{len(retried)} retried, {len(inst_rows)} instances {out['instance_types']}, ~US${out['est_spot_cost_usd']}, "
          f"digest {summ['digest']}" + ("" if spot_digest is None else
                                         f", {'SAME' if out['same_as_spot_job'] else 'DIFFERENT'} answer as the Spot job"))


if __name__ == "__main__":
    main()
