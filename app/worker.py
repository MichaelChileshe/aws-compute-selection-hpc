"""catsim-worker: runs the Spot job in chunks, saves a checkpoint after each one, and stops
cleanly when AWS says the instance is about to be interrupted.

State lives in S3 (the instance can disappear at any moment), under spot-job/:
  job.json          what to run: seed, years, chunk (written by Terraform)
  checkpoint.json   next year to run + the merged totals so far
  events/*.json     one small file per thing that happened (start, notice, stop, finish)
  result.json       the final answer, written once

A background thread asks the instance metadata service every 2 seconds for
spot/instance-action (the 2-minute interruption notice) and events/recommendations/rebalance
(the earlier "this capacity is at risk" signal). When the notice arrives, the worker finishes
the chunk in progress (seconds), saves the checkpoint and exits: no year is lost or counted
twice. The replacement instance's worker finds the checkpoint and carries on.
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

import catsim

CONF = "/etc/themba-hpc.conf"
IMDS = "http://169.254.169.254/latest"


def conf():
    out = {}
    for line in open(CONF):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            out[k] = v
    return out


SETTINGS = conf()
BUCKET, REGION = SETTINGS["BUCKET"], SETTINGS["REGION"]


def s3_get(key):
    r = subprocess.run(["aws", "s3", "cp", "--region", REGION, f"s3://{BUCKET}/{key}", "-"],
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def s3_put(key, obj):
    data = json.dumps(obj, sort_keys=True).encode()
    for attempt in range(5):
        r = subprocess.run(["aws", "s3", "cp", "--region", REGION, "--content-type", "application/json",
                            "-", f"s3://{BUCKET}/{key}"], input=data, capture_output=True)
        if r.returncode == 0:
            return
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"could not write s3://{BUCKET}/{key}: {r.stderr.decode()[:300]}")


def imds(path):
    """IMDSv2 GET. Returns the body, or None for 404 (nothing there) and errors."""
    try:
        req = urllib.request.Request(f"{IMDS}/api/token", method="PUT",
                                     headers={"X-aws-ec2-metadata-token-ttl-seconds": "300"})
        token = urllib.request.urlopen(req, timeout=2).read().decode()
        req = urllib.request.Request(f"{IMDS}/meta-data/{path}", headers={"X-aws-ec2-metadata-token": token})
        return urllib.request.urlopen(req, timeout=2).read().decode()
    except Exception:
        return None


IID = imds("instance-id") or "unknown"
ITYPE = imds("instance-type") or "unknown"
AZ = imds("placement/availability-zone") or "unknown"
LIFECYCLE = imds("instance-life-cycle") or "unknown"


def now():
    return round(time.time(), 3)


def event(kind, **extra):
    rec = {"event": kind, "at": now(), "instance": IID, "type": ITYPE, "az": AZ, "lifecycle": LIFECYCLE}
    rec.update(extra)
    s3_put(f"spot-job/events/{int(rec['at'] * 1000)}-{IID}-{kind}.json", rec)
    print("EVENT " + json.dumps(rec), flush=True)


class Watcher(threading.Thread):
    """Polls the metadata service for the rebalance recommendation and the interruption notice."""

    def __init__(self):
        super().__init__(daemon=True)
        self.notice = None          # (seen at, body)
        self.rebalance = None

    def run(self):
        while True:
            if self.rebalance is None:
                body = imds("events/recommendations/rebalance")
                if body:
                    self.rebalance = (now(), body)
                    event("rebalance-recommendation", body=json.loads(body))
            if self.notice is None:
                body = imds("spot/instance-action")
                if body:
                    self.notice = (now(), body)
                    event("interruption-notice", body=json.loads(body))
            time.sleep(2)


def main():
    if s3_get("spot-job/result.json"):
        print("result.json already exists: the job is finished, nothing to do.", flush=True)
        return 0
    job = s3_get("spot-job/job.json")
    if not job:
        print("no spot-job/job.json yet", flush=True)
        return 1
    seed, years, chunk = job["seed"], job["years"], job["chunk"]
    ckpt = s3_get("spot-job/checkpoint.json")
    if ckpt:
        start, agg, chunks = ckpt["next_start"], ckpt["agg"], ckpt["chunks"]
        event("resumed", from_year=start, chunks_done=chunks, checkpoint_saved_at=ckpt["saved_at"],
              checkpoint_by=ckpt["instance"])
    else:
        start, agg, chunks = 0, catsim.empty(), 0
        event("started", years=years, chunk=chunk)
    watcher = Watcher()
    watcher.start()
    procs = os.cpu_count() or 1
    while start < years:
        if watcher.notice:
            event("stopped-for-interruption", next_start=start, chunks_done=chunks,
                  seconds_after_notice=round(now() - watcher.notice[0], 1))
            return 0
        n = min(chunk, years - start)
        t0 = time.time()
        part = catsim.run(seed, start, n, procs)
        agg = catsim.merge(agg, part)
        start += n
        chunks += 1
        s3_put("spot-job/checkpoint.json", {"next_start": start, "agg": agg, "chunks": chunks,
                                             "saved_at": now(), "instance": IID, "type": ITYPE})
        print(f"chunk {chunks}: years to {start:,} of {years:,} in {time.time() - t0:.1f} s "
              f"({n / (time.time() - t0):,.0f} years/s) on {ITYPE} {IID}", flush=True)
    result = {"job": job, "finished_at": now(), "instance": IID, "type": ITYPE, "chunks": chunks}
    result.update(catsim.summary(agg))
    s3_put("spot-job/result.json", result)
    event("finished", **{k: result[k] for k in ("years", "digest", "gross_aal_rand", "one_in_200_gross_rand")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
