"""nettest: network latency and bandwidth from this node to another lab node.

  python3 nettest.py <other node's private IP>

  ping     1,000 ICMP echoes 2 ms apart: round-trip min / avg / max / mdev (milliseconds)
  iperf3   10 s, one TCP stream (the per-flow limit) and 10 s, eight streams (the instance limit)
Prints one RESULT line (JSON). The other node runs an iperf3 server (iperf3-server.service).
"""
import json
import re
import subprocess
import sys


def ping(ip):
    out = subprocess.run(["ping", "-c", "1000", "-i", "0.002", "-q", ip], capture_output=True, text=True).stdout
    m = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms", out)
    loss = re.search(r"([\d.]+)% packet loss", out)
    return {"rtt_min_ms": float(m.group(1)), "rtt_avg_ms": float(m.group(2)), "rtt_max_ms": float(m.group(3)),
            "rtt_mdev_ms": float(m.group(4)), "loss_pct": float(loss.group(1)) if loss else None}


def iperf(ip, streams):
    out = subprocess.run(["iperf3", "-c", ip, "-t", "10", "-P", str(streams), "-J"], capture_output=True, text=True).stdout
    d = json.loads(out)
    if "error" in d:
        raise SystemExit(f"iperf3: {d['error']}")
    end = d["end"]
    return {"gbps": round(end["sum_received"]["bits_per_second"] / 1e9, 3),
            "retransmits": end["sum_sent"].get("retransmits")}


def main():
    ip = sys.argv[1]
    res = {"to": ip, "ping": ping(ip), "tcp_1_stream": iperf(ip, 1), "tcp_8_streams": iperf(ip, 8)}
    print("RESULT " + json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
