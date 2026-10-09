#!/usr/bin/env python3
"""Submit the catastrophe run to AWS Batch as one array job: --size children, each simulating
--years years (child i runs years i x years ... (i+1) x years - 1).

  python3 scripts/batch_submit.py --arch graviton --size 40 --years 60000
"""
import argparse
import time

from kit_aws import aws, tf_output, write_result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", required=True, choices=["graviton", "x86"])
    ap.add_argument("--size", type=int, default=40)
    ap.add_argument("--years", type=int, default=60000)
    a = ap.parse_args()
    queue, jobdef = tf_output("batch_queues")[a.arch], tf_output("batch_job_definition")
    name = f"catsim-{a.arch}-{time.strftime('%H%M%S')}"
    job = aws("batch", "submit-job", "--job-name", name, "--job-queue", queue, "--job-definition", jobdef,
              "--array-properties", f"size={a.size}", "--parameters", f"years={a.years}")
    write_result(f"batch-{a.arch}-submit", {"job_id": job["jobId"], "name": name, "queue": queue,
                                             "job_definition": jobdef, "size": a.size, "years_per_child": a.years,
                                             "total_years": a.size * a.years, "submitted_utc": time.strftime("%H:%M:%S", time.gmtime())})
    print(f"submitted {name}: {a.size} children x {a.years:,} years = {a.size * a.years:,} years -> {queue}")
    print(f"RESULT batch-submit {a.arch}: job id {job['jobId']}")


if __name__ == "__main__":
    main()
