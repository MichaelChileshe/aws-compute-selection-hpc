#!/usr/bin/env python3
"""Where the Spot job is: progress from the checkpoint, every event the workers recorded, the
Auto Scaling group's launches and terminations, and the result once it exists.

  python3 scripts/spot_status.py              # once
  python3 scripts/spot_status.py --watch 30   # every 30 s until result.json exists
  python3 scripts/spot_status.py --final      # also writes build/results/spot.json
"""
import argparse
import datetime as dt
import json
import subprocess
import time

from kit_aws import aws, tf_output, write_result


def utc(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%H:%M:%S")


def s3_json(bucket, key):
    r = subprocess.run(["aws", "s3", "cp", f"s3://{bucket}/{key}", "-"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def events(bucket):
    keys = aws("s3api", "list-objects-v2", "--bucket", bucket, "--prefix", "spot-job/events/").get("Contents", []) or []
    return sorted((s3_json(bucket, k["Key"]) for k in keys), key=lambda e: e["at"])


def activities(asg):
    acts = aws("autoscaling", "describe-scaling-activities", "--auto-scaling-group-name", asg)["Activities"]
    return sorted(({"start": a["StartTime"], "end": a.get("EndTime"), "status": a["StatusCode"],
                    "what": a["Description"], "cause": a["Cause"][:220]} for a in acts), key=lambda a: a["start"])


def snapshot(bucket, asg, show=True):
    ckpt, result, evs = s3_json(bucket, "spot-job/checkpoint.json"), s3_json(bucket, "spot-job/result.json"), events(bucket)
    job = s3_json(bucket, "spot-job/job.json")
    if show:
        print(f"--- {dt.datetime.now(dt.timezone.utc):%H:%M:%S} UTC")
        if ckpt:
            print(f"checkpoint: {ckpt['next_start']:,} of {job['years']:,} years ({100 * ckpt['next_start'] / job['years']:.1f}%), "
                  f"{ckpt['chunks']} chunks, saved {utc(ckpt['saved_at'])} by {ckpt['instance']} ({ckpt['type']})")
        else:
            print("checkpoint: none yet")
        for e in evs:
            extra = {k: v for k, v in e.items() if k not in ("event", "at", "instance", "type", "az", "lifecycle")}
            print(f"  {utc(e['at'])}  {e['event']:26} {e['instance']} {e['type']} {e['az']} {e['lifecycle']}  {json.dumps(extra)[:160]}")
        if asg:
            for a in activities(asg):
                print(f"  ASG {a['start'][11:19]}  {a['status']:11} {a['what'][:90]}")
        if result:
            print(f"RESULT spot: finished, {result['years']:,} years in {result['chunks']} chunks, digest {result['digest']}, "
                  f"gross AAL R{result['gross_aal_rand']:,}, 1-in-200 R{result['one_in_200_gross_rand']:,}")
    return ckpt, result, evs


def timeline(evs):
    """The interruption, measured from the events."""
    by = {}
    for e in evs:
        by.setdefault(e["event"], []).append(e)
    out = {}
    if "interruption-notice" in by and "stopped-for-interruption" in by:
        n, s = by["interruption-notice"][0], by["stopped-for-interruption"][0]
        out["notice_at"] = utc(n["at"])
        out["notice_says_terminate_at"] = n["body"].get("time")
        out["stopped_seconds_after_notice"] = round(s["at"] - n["at"], 1)
        out["stopped_at_year"] = s["next_start"]
        out["interrupted_instance"] = f"{n['instance']} ({n['type']}, {n['az']})"
    if "rebalance-recommendation" in by and "interruption-notice" in by:
        out["rebalance_before_notice_s"] = round(by["interruption-notice"][0]["at"] - by["rebalance-recommendation"][0]["at"], 1)
    if "resumed" in by and "stopped-for-interruption" in by:
        r, s = by["resumed"][0], by["stopped-for-interruption"][0]
        out["resumed_at"] = utc(r["at"])
        out["resumed_from_year"] = r["from_year"]
        out["years_lost_or_repeated"] = r["from_year"] - s["next_start"]
        out["gap_stop_to_resume_s"] = round(r["at"] - s["at"], 1)
        out["replacement_instance"] = f"{r['instance']} ({r['type']}, {r['az']})"
    if "started" in by and "finished" in by:
        out["wall_clock_s"] = round(by["finished"][0]["at"] - by["started"][0]["at"], 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    bucket, asg = tf_output("bucket"), tf_output("spot_asg")
    while True:
        ckpt, result, evs = snapshot(bucket, asg)
        if not a.watch or result:
            break
        time.sleep(a.watch)
    tl = timeline(evs)
    if tl:
        print("interruption: " + json.dumps(tl))
    if a.final:
        write_result("spot", {"result": result, "timeline": tl, "events": evs,
                              "asg_activities": activities(asg) if asg else []})


if __name__ == "__main__":
    main()
