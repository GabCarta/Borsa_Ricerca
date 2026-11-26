"""
Template for a new Digital Twin service.

Fill in SERVICE and run(), try it with `python prova_locale.py`, then upload THIS file
from the dashboard (page "Request service"). The admin reviews the code: once approved,
the service appears in the catalog of "Create DT" for every user.

How it runs
- The platform calls run() every `interval` seconds, once for each input chosen when the
  service is added to a DT (a parameter of one of its Digital Replicas).
  With "min_inputs": 0 and no inputs chosen, run() is called once per cycle with inp=None.
- Whatever dict run() returns is saved in the DT (collection service_output) and shown in
  the "Service" page. Return None when there is nothing to save this time.
- Do not write your own loop, threads or web server: the platform already does that.

Rules (checked automatically when you upload the file)
- Allowed imports: math, statistics, datetime, time, json, re, random, collections,
  itertools, functools, numpy, urllib.request / urllib.error / urllib.parse.
- Not allowed: os, sys, subprocess, socket, open, eval, exec, __import__, getattr and
  attributes with "__".
- SERVICE must contain only fixed values; the file must be at most 100 KB.
"""

import datetime

# ------------------------------------------------------------------------------------
# 1. Description of the service: the dashboard builds the configuration form from here
# ------------------------------------------------------------------------------------
SERVICE = {
    "name": "Rate of change",  # max 40 characters
    "description": "How fast a parameter is changing (units per minute) over a time window",
    "min_inputs": 1,  # minimum number of DR parameters to choose (0 = none needed)
    # parameters the user sets when adding the service to a DT.
    # type: "int", "float" or "str". "interval" (seconds between two runs) is added by
    # the platform with default 10 s if you do not define it.
    # (optional) the DR parameters this service works on, by name as in the parameter list
    # of the platform. Leave it empty ({}) to accept any numeric parameter.
    # A parameter that is not in the list yet needs type ("float" or "int") and unit:
    # the admin adds it to the list when approving the service, e.g.
    #     "parameters": {"Temperature": {}, "Solar radiation": {"type": "float", "unit": "W/m²"}},
    "parameters": {},
    "params": [
        {"name": "minutes", "type": "int", "default": 30, "min": 1, "label": "Time window (minutes)"},
        {"name": "interval", "type": "int", "default": 30, "min": 1, "label": "Interval between two runs (s)"},
    ],
}


# ------------------------------------------------------------------------------------
# 2. The function called at every cycle
# ------------------------------------------------------------------------------------
def run(db, inp, params, instance_id):
    """
    db          database of the DT (pymongo). The measures of a DR are in db[inp["collection"]],
                one document per measure: {"dr_id", <parameter>: value, "orario_invio": datetime}
    inp         {"dr_id": ..., "parameter": ..., "collection": ...}  (None if the service has no inputs)
    params      values of the parameters in SERVICE, with the defaults already applied
                (without "interval")
    instance_id id of this service in the DT (e.g. "svc-1"): use it if you save a state,
                so two copies of the service in the same DT do not mix their data
    return      a dict with the result, or None
    """
    minutes = int(params["minutes"])
    since = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
    measures = list(
        db[inp["collection"]]
        .find({"dr_id": inp["dr_id"], inp["parameter"]: {"$type": "number"}, "orario_invio": {"$gte": since}})
        .sort("orario_invio", 1)
    )
    if len(measures) < 2:
        return None  # not enough data yet

    first, last = measures[0], measures[-1]
    elapsed_min = (last["orario_invio"] - first["orario_invio"]).total_seconds() / 60
    if elapsed_min == 0:
        return None
    change = float(last[inp["parameter"]]) - float(first[inp["parameter"]])
    return {
        "rate_per_minute": round(change / elapsed_min, 4),
        "change": round(change, 4),
        "samples": len(measures),
        "minutes": minutes,
    }
