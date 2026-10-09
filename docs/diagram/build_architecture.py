#!/usr/bin/env python3
"""Regenerates docs/architecture.svg + docs/architecture.png using the OFFICIAL AWS Architecture Icons.

The icon pack is not committed (AWS licenses it for diagrams, not redistribution). Download it from
https://aws.amazon.com/architecture/icons/, unzip, then:

    AWS_ICONS_DIR=/path/to/unzipped-icon-package python3 build_architecture.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from awsdiag import Diagram, GREY, INK

NET, BENCH, SPOT, BATCH, IAC, SIM, DATA = ("#8C4FFF", "#2E73B8", "#D45B07", "#E7157B", "#7B42BC", "#7D8998", "#3F8624")
d = Diagram(1900, 1150)
d.text(40, 40, "Compute selection for HPC: placement groups, Graviton vs Intel vs AMD, Spot with a real interruption, "
               "AWS Batch, built and destroyed with Terraform", 19, "bold")
d.text(40, 64, "Themba Insurance catastrophe model  ·  us-east-1  ·  each lab is a Terraform phase switched on, measured "
               "and switched off  ·  the answer is checked by one digest everywhere", 13, "normal", GREY)


def node(key, x, y, title, lines=(), color=INK, size=44):
    d.icon(key, x, y, size)
    d.text(x + size + 10, y + 15, title, 12.5, "bold", color)
    for i, l in enumerate(lines):
        d.text(x + size + 10, y + 32 + i * 15, l, 11, "normal", GREY)


def lab(x, y, w, h, color, title):
    d.box(x, y, w, h, color, fill="#fff", dashed=True)
    d.text(x + 12, y + 20, title, 12.5, "bold", color)


# ---------------------------------------------------------------- my machine
d.box(40, 100, 300, 330, IAC, fill="#F7F2FC", dashed=False)
d.text(56, 126, "My machine (WSL)", 13.5, "bold", IAC)
d.text(56, 150, "terraform plan / apply / destroy", 12, "bold", INK)
d.text(56, 168, "base: 26 resources, kept all day", 11, "normal", GREY)
d.text(56, 186, "labs: one line each in phases.auto.tfvars,", 11, "normal", GREY)
d.text(56, 204, "on for the measurement, off after it", 11, "normal", GREY)
d.text(56, 232, "quality gates before any apply:", 12, "bold", INK)
d.text(56, 250, "fmt · validate · tflint · checkov", 11, "normal", GREY)
d.text(56, 278, "measurements as scripts:", 12, "bold", INK)
d.text(56, 296, "placement_test · bench · prices", 11, "normal", GREY)
d.text(56, 314, "spot_status · batch_submit · batch_collect", 11, "normal", GREY)
d.text(56, 342, "one check for every run:", 12, "bold", INK)
d.text(56, 360, "catsim digest (same years = same", 11, "normal", GREY)
d.text(56, 378, "bit-for-bit answer, any machine,", 11, "normal", GREY)
d.text(56, 396, "any split, interrupted or not)", 11, "normal", GREY)

d.group("cloud", 370, 90, 1100, 1040, "AWS Cloud")
node("s3_bucket", 400, 132, "nkosi-tfstate-(account id)", ["Terraform state, key aws-compute-selection-hpc/",
                                                         "S3-native lock file (use_lockfile)"], IAC, 40)
d.line([(340, 152), (396, 152)], IAC, width=2)

d.group("region", 390, 200, 1060, 910, "us-east-1")
d.group("vpc", 410, 248, 690, 842, "themba-hpc-vpc 10.140.0.0/16 · 3 public subnets")

# ---------------------------------------------------------------- placement lab
lab(430, 292, 650, 210, NET, "placement_lab · 5 x c7i.large")
d.box(446, 318, 190, 120, NET, fill="#F4F0FF", dashed=False)
d.text(456, 336, "cluster group (1a)", 11.5, "bold", NET)
node("ec2_instance", 456, 346, "cluster-a", [], NET, 30)
node("ec2_instance", 456, 390, "cluster-b", [], NET, 30)
d.box(650, 318, 220, 120, NET, fill="#F4F0FF", dashed=False)
d.text(660, 336, "spread group (racks)", 11.5, "bold", NET)
node("ec2_instance", 660, 346, "spread-a (1a)", [], NET, 30)
node("ec2_instance", 660, 390, "spread-b (1a)", [], NET, 30)
node("ec2_instance", 900, 346, "spread-c (1b)", [], NET, 30)
d.line([(472, 378), (472, 388)], NET, width=1.5)
d.line([(676, 378), (676, 388)], NET, width=1.5)
d.line([(812, 362), (896, 362)], NET, width=1.5)
d.text(446, 462, "ping x 1,000 + iperf3 (1 and 8 TCP streams) between each pair", 11, "normal", GREY)
d.text(446, 480, "same AZ: 0.22-0.235 ms, 9.5 Gbit/s per flow  ·  other AZ: 0.494 ms, 4.97 Gbit/s", 11, "bold", NET)

# ---------------------------------------------------------------- bench lab
lab(430, 520, 650, 150, BENCH, "bench_lab · on-demand, 2 vCPUs each, same model")
node("ec2_instance", 446, 548, "c7g.large", ["Graviton3, arm64"], BENCH, 36)
node("ec2_instance", 646, 548, "c7i.large", ["Intel Xeon 8488C"], BENCH, 36)
node("ec2_instance", 846, 548, "c7a.large", ["AMD EPYC 9R14"], BENCH, 36)
d.text(446, 616, "60,000 years, 1 and 2 processes; prices from the Price List API and Spot history", 11, "normal", GREY)
d.text(446, 634, "cheapest per simulated year on-demand: Graviton  ·  every digest 07394c4b0c9564a3", 11, "bold", BENCH)

# ---------------------------------------------------------------- spot lab
lab(430, 688, 650, 170, SPOT, "spot_lab · Auto Scaling group of 1 Spot instance, price-capacity-optimized")
node("ec2_autoscaling", 446, 716, "themba-spot-worker", ["c7g / m7g / c6g / m6g .large", "3 AZs, Graviton AMI"], SPOT, 40)
node("spot_instance", 700, 716, "catsim-worker", ["checkpoint to S3 every 20,000 years",
                                                  "polls IMDS for the 2-min notice"], SPOT, 40)
d.line([(660, 736), (696, 736)], SPOT, width=1.8)
d.text(446, 808, "c6g.large (1a) interrupted at year 620,000, stopped 14.8 s after the notice", 11, "bold", SPOT)
d.text(446, 826, "1st replacement: no Spot capacity; 9 s later m6g.large (1c) resumed at year 620,000", 11, "normal", GREY)
d.text(446, 844, "0 years lost or repeated", 11, "bold", SPOT)

# ---------------------------------------------------------------- batch lab
lab(430, 876, 650, 196, BATCH, "batch_lab · managed Spot compute environments, min 0 vCPUs")
node("ecs", 446, 904, "themba-cat-graviton", ["c7g, m7g, c6g, m6g"], BATCH, 36)
node("ecs", 666, 904, "themba-cat-x86", ["c7i, m7i, c7a, m7a, c6i"], BATCH, 36)
node("spot_instance", 446, 960, "array job: 40 children x 60,000 years", ["public Amazon Linux 2023 image, model in the job",
                                                                            "definition (gzip + base64), retry on Host EC2*"], BATCH, 36)
d.text(446, 1030, "Graviton 236 s, x86 277 s, 0 retries, ~US$0.03 each", 11, "bold", BATCH)
d.text(446, 1048, "both digests 0cb96b0f9d9c5303 = the interrupted Spot job, replayed", 11, "bold", BATCH)

# ---------------------------------------------------------------- regional services
node("s3_bucket", 1124, 252, "themba-hpc-(acct)", ["code/app/*.py (catsim, worker,", "nettest), spot-job/ checkpoint,",
                                                   "events, result"], DATA, 40)
node("vpc_endpoints", 1124, 352, "S3 gateway endpoint", ["no NAT gateway needed"], SIM, 34)
node("ssm", 1124, 420, "SSM Run Command", ["every node command from WSL,", "no SSH, no inbound port"], SIM, 36)
node("fis", 1124, 700, "AWS FIS", ["send-spot-instance-interruptions", "PT2M, COUNT(1), tag Name =",
                                   "themba-spot-worker"], SPOT, 40)
d.line([(1120, 760), (1084, 760)], SPOT, dashed=True, width=1.8)
node("batch", 1124, 880, "AWS Batch", ["queues themba-cat-graviton / -x86", "job definition themba-catsim",
                                       "starts and stops the instances"], BATCH, 40)
d.line([(1120, 900), (1084, 900)], BATCH, width=1.8)
node("cw_logs", 1124, 990, "CloudWatch Logs", ["/aws/batch/themba-cat (7 days)", "each child's RESULT + AGG lines"], BATCH, 36)
d.line([(1084, 1008), (1120, 1008)], BATCH, dashed=True, width=1.4)
d.line([(968, 726), (1110, 726), (1110, 300), (1120, 300)], DATA, dashed=True, width=1.4)

# ---------------------------------------------------------------- measured panel
bx, by = 1490, 90
d.box(bx, by, 390, 1040, "#D5DBDB", fill="#fff", dashed=False)
d.text(bx + 14, by + 26, "Measured (one build, 9 October 2026)", 14, "bold")
res = [
    ("Placement (c7i.large pairs)", NET, ["cluster, same AZ: 0.235 ms, 9.53 / 12.41 Gbit/s",
                                          "spread, same AZ: 0.22 ms, 9.53 / 12.41 Gbit/s",
                                          "spread, other AZ: 0.494 ms, 4.97 / 12.41 Gbit/s",
                                          "(1 stream / 8 streams)"]),
    ("Years per second (1 proc / 2 procs)", BENCH, ["c7a (AMD): 1,036 / 2,187",
                                                    "c7g (Graviton): 827 / 1,659",
                                                    "c7i (Intel): 1,215 / 1,249 (vCPU = hyperthread)"]),
    ("US$ per million simulated years", BENCH, ["on-demand: c7g 0.0121, c7a 0.0130, c7i 0.0198",
                                                "Spot: c7g 0.0042, c7a 0.0042, c7i 0.0065"]),
    ("Spot interruption (AWS FIS)", SPOT, ["rebalance 1.0 s before the notice",
                                           "stopped 14.8 s after it, at year 620,000",
                                           "resumed 159.7 s later on another type / AZ",
                                           "0 years lost or repeated"]),
    ("AWS Batch, 2,400,000 years", BATCH, ["Graviton: 236.2 s, first start 65.8 s",
                                           "x86: 277.1 s, first start 137.1 s",
                                           "40/40 each, 0 retries, ~US$0.0315 / 0.0355"]),
    ("Same answer everywhere", INK, ["60,000 years: 07394c4b0c9564a3 on c7g,",
                                     "c7i, c7a (Python 3.9) and my laptop (3.14)",
                                     "2,400,000 years: 0cb96b0f9d9c5303 on both",
                                     "Batch runs and the Spot split replayed"]),
    ("Terraform", IAC, ["base 26; labs 7, 3, 6, 9, each destroyed", "job definition fix: 1 changed in place",
                        "Destroy complete! 26 destroyed"]),
]
y = by + 58
for title, c, ls in res:
    d.text(bx + 14, y, title, 12, "bold", c)
    for l in ls:
        y += 16
        d.text(bx + 14, y, l, 11.2)
    y += 26

here = os.path.dirname(os.path.abspath(__file__))
d.save(os.path.join(here, "..", "architecture.svg"), os.path.join(here, "..", "architecture.png"))
print("wrote docs/architecture.svg and docs/architecture.png")
