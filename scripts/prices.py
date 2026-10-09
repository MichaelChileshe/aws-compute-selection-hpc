#!/usr/bin/env python3
"""Today's prices for instance types in us-east-1: on-demand Linux (Price List API) and the
current Spot price in each AZ (Spot price history, last hour). Imported by bench.py and
batch_collect.py; also runs on its own:

  python3 scripts/prices.py c7g.large c7i.large c7a.large
"""
import datetime as dt
import json
import sys

from kit_aws import aws

LOCATION = "US East (N. Virginia)"


def on_demand(itype):
    filters = [("instanceType", itype), ("location", LOCATION), ("operatingSystem", "Linux"),
               ("tenancy", "Shared"), ("preInstalledSw", "NA"), ("capacitystatus", "Used"),
               ("licenseModel", "No License required")]
    args = ["pricing", "get-products", "--region", "us-east-1", "--service-code", "AmazonEC2", "--filters"]
    args += [f"Type=TERM_MATCH,Field={k},Value={v}" for k, v in filters]
    for item in aws(*args).get("PriceList", []):
        p = json.loads(item) if isinstance(item, str) else item
        for term in p["terms"].get("OnDemand", {}).values():
            for dim in term["priceDimensions"].values():
                usd = float(dim["pricePerUnit"]["USD"])
                if usd > 0:
                    return usd
    return None


def spot(itype):
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hist = aws("ec2", "describe-spot-price-history", "--instance-types", itype,
               "--product-descriptions", "Linux/UNIX", "--start-time", start)["SpotPriceHistory"]
    latest = {}
    for h in hist:
        az = h["AvailabilityZone"]
        if az not in latest or h["Timestamp"] > latest[az]["Timestamp"]:
            latest[az] = h
    prices = {az: float(h["SpotPrice"]) for az, h in sorted(latest.items())}
    return {"by_az": prices, "min": min(prices.values()) if prices else None,
            "max": max(prices.values()) if prices else None}


def prices(itype):
    od, sp = on_demand(itype), spot(itype)
    return {"instance_type": itype, "on_demand_usd_hr": od, "spot_min_usd_hr": sp["min"],
            "spot_max_usd_hr": sp["max"], "spot_by_az": sp["by_az"],
            "spot_discount_pct": round(100 * (1 - sp["min"] / od), 1) if od and sp["min"] else None}


if __name__ == "__main__":
    for t in sys.argv[1:] or ["c7g.large"]:
        print(json.dumps(prices(t)))
