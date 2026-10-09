#!/usr/bin/env python3
"""The placement group test: the same measurements between three pairs of identical nodes.

  cluster-a -> cluster-b   both in the cluster placement group (same AZ, packed together)
  spread-a  -> spread-b    spread group, same AZ (different racks)
  spread-a  -> spread-c    spread group, different AZ

Each pair: ping (latency) and iperf3 with 1 and 8 TCP streams (bandwidth), run on the first
node through SSM against the second node's private IP. Also records where AWS put each node.

  python3 scripts/placement_test.py
"""
import csv
import os

from kit_aws import RESULTS, aws, result_lines, tf_output, write_result
from ssm_run import run

PAIRS = [("cluster-a", "cluster-b", "cluster group, same AZ"),
         ("spread-a", "spread-b", "spread group, same AZ"),
         ("spread-a", "spread-c", "spread group, other AZ")]


def main():
    nodes = tf_output("placement_nodes")
    if not nodes:
        raise SystemExit("no placement nodes: is placement_lab = true applied?")
    ids = [n["id"] for n in nodes.values()]
    desc = aws("ec2", "describe-instances", "--instance-ids", *ids, "--query",
               "Reservations[].Instances[].{id:InstanceId,type:InstanceType,az:Placement.AvailabilityZone,"
               "group:Placement.GroupName,ip:PrivateIpAddress}")
    print("where AWS put them:")
    for d in sorted(desc, key=lambda x: (x["group"], x["az"])):
        name = next(k for k, v in nodes.items() if v["id"] == d["id"])
        print(f"  {name:10} {d['id']}  {d['type']}  {d['az']}  group {d['group']}  {d['ip']}")
    rows = []
    for src, dst, label in PAIRS:
        print(f"\n{src} -> {dst}  ({label})")
        out = run(nodes[src]["id"], f"python3 /opt/themba-hpc/nettest.py {nodes[dst]['ip']}", echo=False)
        r = result_lines(out)[0]
        row = {"pair": f"{src} -> {dst}", "placement": label,
               "src_az": nodes[src]["az"], "dst_az": nodes[dst]["az"],
               "rtt_avg_ms": r["ping"]["rtt_avg_ms"], "rtt_min_ms": r["ping"]["rtt_min_ms"],
               "rtt_max_ms": r["ping"]["rtt_max_ms"], "rtt_mdev_ms": r["ping"]["rtt_mdev_ms"],
               "loss_pct": r["ping"]["loss_pct"],
               "gbps_1_stream": r["tcp_1_stream"]["gbps"], "gbps_8_streams": r["tcp_8_streams"]["gbps"],
               "retransmits_1": r["tcp_1_stream"]["retransmits"], "retransmits_8": r["tcp_8_streams"]["retransmits"]}
        rows.append(row)
        print(f"  ping avg {row['rtt_avg_ms']} ms (min {row['rtt_min_ms']}, max {row['rtt_max_ms']}, "
              f"mdev {row['rtt_mdev_ms']}), loss {row['loss_pct']}%")
        print(f"  TCP 1 stream {row['gbps_1_stream']} Gbit/s, 8 streams {row['gbps_8_streams']} Gbit/s")
    write_result("placement", {"nodes": desc, "pairs": rows})
    with open(os.path.join(RESULTS, "placement.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\n" + " | ".join(["pair", "placement", "avg RTT ms", "1 stream Gbit/s", "8 streams Gbit/s"]))
    for r in rows:
        print(f"{r['pair']} | {r['placement']} | {r['rtt_avg_ms']} | {r['gbps_1_stream']} | {r['gbps_8_streams']}")
    base = rows[0]["rtt_avg_ms"]
    print("RESULT placement: " + "; ".join(
        f"{r['placement']} avg RTT {r['rtt_avg_ms']} ms ({r['rtt_avg_ms'] / base:.2f}x cluster), "
        f"{r['gbps_1_stream']} / {r['gbps_8_streams']} Gbit/s" for r in rows))


if __name__ == "__main__":
    main()
