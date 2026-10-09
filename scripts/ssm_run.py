#!/usr/bin/env python3
"""Run something on a Linux instance through SSM Run Command, wait for it, and print the output.
No SSH, no key pair, no inbound port: the instance's SSM agent pulls the command.

  python3 scripts/ssm_run.py sh <instance-id> "<shell command>"

Other scripts import run() to get the output back as text.
"""
import json
import subprocess
import sys
import time

from kit_aws import aws


def wait_online(iid, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        info = aws("ssm", "describe-instance-information",
                   "--filters", f"Key=InstanceIds,Values={iid}")["InstanceInformationList"]
        if info and info[0]["PingStatus"] == "Online":
            return
        print(f"  waiting for {iid} to register with Systems Manager ...", flush=True)
        time.sleep(15)
    sys.exit(f"{iid} did not come Online in SSM within {timeout // 60} minutes")


def _quiet(*args):
    r = subprocess.run(["aws", *args, "--output", "json"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def run(iid, command, timeout=3600, echo=True):
    """Run one shell command on the instance; return its stdout. Exits if the command fails."""
    wait_online(iid)
    cid = aws("ssm", "send-command", "--instance-ids", iid, "--document-name", "AWS-RunShellScript",
              "--comment", command[:100], "--timeout-seconds", "600",
              "--parameters", json.dumps({"commands": [command], "executionTimeout": [str(timeout)]}))["Command"]["CommandId"]
    t0 = time.time()
    while True:
        time.sleep(3)
        res = _quiet("ssm", "get-command-invocation", "--command-id", cid, "--instance-id", iid)
        if not res or res["Status"] in ("Pending", "InProgress", "Delayed"):
            continue
        out, err = res.get("StandardOutputContent", "").rstrip(), res.get("StandardErrorContent", "").rstrip()
        if echo:
            print(f"[{iid}] {res['Status']} in {time.time() - t0:.0f} s")
            if out:
                print(out)
            if err:
                print("----- stderr -----\n" + err)
        if res["Status"] != "Success":
            sys.exit(f"command failed on {iid}: {res['Status']}")
        return out


def main():
    if len(sys.argv) != 4 or sys.argv[1] != "sh":
        sys.exit(__doc__)
    run(sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
