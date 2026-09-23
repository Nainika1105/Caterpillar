"""
Synthetic dataset generator - Smart Operator Assistant for CAT machinery.

Produces minute-level telemetry plus the relational tables around it
(machines, operators, sites, tasks, weather, alerts, energy events,
training records, incidents) and a 2-hour summary in the exact format
of the sample dataset. Anomalies are planted deliberately and recorded
in anomalies_ground_truth.csv so detection models can be evaluated.

Run:  python generate_dataset.py [--seed 42] [--days 30] [--out data]
"""
import argparse, math, os
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd

from shared.constants import AlertCode, ProximityZone, SeatbeltStatus, TaskStatus

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=42)
p.add_argument("--days", type=int, default=30)
p.add_argument("--start", default="2025-05-01")
p.add_argument("--out", default="data")
args = p.parse_args()
rng = np.random.default_rng(args.seed)
os.makedirs(args.out, exist_ok=True)

SHIFT_START_H = 8
SHIFT_MIN = 540                 # 08:00-17:00
LUNCH = (270, 315)              # 12:30-13:15
SITE_SPEED_LIMIT = 10.0         # km/h

# ----------------------------------------------------------------- sites
SITES = [
    dict(site_id="S01", name="Chennai OMR metro corridor", city="Chennai", lat=12.9010, lon=80.2279,
         soil="sandy_clay", tmax=(37.5, 1.4), tmin=29.0, storm_p=0.07, heatwave_days=[12, 13, 14, 15, 22, 23]),
    dict(site_id="S02", name="Bengaluru ring road package 3", city="Bengaluru", lat=12.9716, lon=77.7500,
         soil="red_soil", tmax=(33.0, 1.2), tmin=22.0, storm_p=0.35, heatwave_days=[]),
    dict(site_id="S03", name="Hosur aggregate quarry", city="Hosur", lat=12.7409, lon=77.8253,
         soil="rocky", tmax=(32.5, 1.2), tmin=21.0, storm_p=0.30, heatwave_days=[]),
]
SITE = {s["site_id"]: s for s in SITES}

# ---------------------------------------------------------- machine classes
# diesel: fuel L/h by state ; electric: kW by state
CLASSES = {
    "mini_excavator":          dict(power="diesel", ref_model="CAT 303 CR", work=(4.2, 5.6), idle=1.0, travel=2.5, tank=45,
                                    cycles=0.15, wspeed=(0, 0.4), tasks={"trenching": 12, "excavation": 15}),
    "excavator":               dict(power="diesel", ref_model="CAT 320", work=(13, 17), idle=2.6, travel=8, tank=345,
                                    cycles=0.12, wspeed=(0, 0.5), tasks={"trenching": 45, "excavation": 70, "truck_loading": 90}),
    "wheel_loader":            dict(power="diesel", ref_model="CAT 950 GC", work=(13, 17), idle=2.4, travel=9, tank=300,
                                    cycles=0.35, wspeed=(2, 9), tasks={"truck_loading": 120, "stockpiling": 150}),
    "dozer":                   dict(power="diesel", ref_model="CAT D6", work=(18, 24), idle=3.0, travel=10, tank=400,
                                    cycles=0.05, wspeed=(2, 6), tasks={"grading": 600, "site_clearing": 400, "spreading": 110}),
    "backhoe_loader":          dict(power="diesel", ref_model="CAT 432", work=(6.5, 8.5), idle=1.5, travel=5, tank=160,
                                    cycles=0.15, wspeed=(0, 3), tasks={"trenching": 20, "backfilling": 35}),
    "electric_mini_excavator": dict(power="electric", ref_model="electric mini excavator (assumed)", work=(10, 14), idle=0.6,
                                    travel=6, battery=64, charge_kw=40, cycles=0.15, wspeed=(0, 0.4),
                                    tasks={"trenching": 12, "excavation": 15}),
    "electric_excavator":      dict(power="electric", ref_model="electric 20t excavator (assumed)", work=(60, 80), idle=3,
                                    travel=30, battery=300, charge_kw=150, cycles=0.12, wspeed=(0, 0.5),
                                    tasks={"trenching": 45, "excavation": 70, "truck_loading": 90}),
}
UNIT = {"trenching": "m3", "excavation": "m3", "truck_loading": "m3", "stockpiling": "m3", "spreading": "m3",
        "backfilling": "m3", "grading": "m2", "site_clearing": "m2"}

MACHINES = [
    ("EXC001", "mini_excavator", "S01", 1523.5, "OP1001"),
    ("EXC002", "excavator", "S01", 6412.0, "OP1002"),
    ("EXC003", "excavator", "S02", 3890.4, "OP1003"),
    ("EXC004", "electric_excavator", "S02", 412.7, "OP1004"),
    ("EXC005", "electric_mini_excavator", "S01", 288.1, "OP1005"),
    ("EXC006", "excavator", "S03", 8120.9, "OP1006"),
    ("WL001", "wheel_loader", "S01", 5230.2, "OP1007"),
    ("WL002", "wheel_loader", "S03", 7011.6, "OP1008"),
    ("DZ001", "dozer", "S02", 4402.3, "OP1009"),
    ("DZ002", "dozer", "S03", 9310.8, "OP1010"),
    ("BH001", "backhoe_loader", "S01", 2210.5, "OP1011"),
    ("BH002", "backhoe_loader", "S02", 3105.0, "OP1012"),
]

# -------------------------------------------------------------- operators
NAMES = ["Arjun Kumar", "Suresh Babu", "Manjunath R", "Priya Shankar", "Karthik Raja", "Venkatesh M",
         "Ravi Teja", "Lakshmi Narayan", "Imran Pasha", "Gopal Krishnan", "Dinesh Selvam", "Harish Gowda",
         "Anand Pillai", "Mohammed Rafiq", "Sathya Moorthy"]
OP_EXP = [6, 11, 4, 3, 5, 14, 2, 9, 7, 17, 8, 5, 12, 10, 1]
# hidden behaviour profiles (NOT exported to operators.csv; visible only via ground truth)
PROFILE = {"OP1007": dict(unbelted_operation=0.35, unattended_running=0.20),
           "OP1011": dict(excessive_idling=0.40),
           "OP1004": dict(harsh_operation=0.25, overspeed_travel=0.20)}
BASE_P = dict(excessive_idling=0.06, unattended_running=0.05, unbelted_operation=0.04, proximity_breach=0.06,
              overspeed_travel=0.04, harsh_operation=0.04, fuel_loss=0.025, overheating=0.10,
              abnormal_fuel_burn=0.015)

operators = []
for i in range(15):
    oid = f"OP{1001+i}"
    exp = OP_EXP[i]
    skill = round(float(np.clip(0.82 + 0.02 * min(exp, 15) + rng.normal(0, 0.03), 0.8, 1.18)), 3)
    idle_prop = round(float(np.clip(rng.normal(1.0, 0.15), 0.7, 1.4)), 2)
    operators.append(dict(operator_id=oid, name=NAMES[i], experience_years=exp,
                          home_site=None, shift="day", _skill=skill, _idle=idle_prop))
OPS = {o["operator_id"]: o for o in operators}
for mid, cls, site, _, op in MACHINES:
    OPS[op]["home_site"] = site
for oid, site in [("OP1013", "S01"), ("OP1014", "S02"), ("OP1015", "S03")]:
    OPS[oid]["home_site"] = site

# certifications
certs = {o["operator_id"]: set() for o in operators}
for mid, cls, site, _, op in MACHINES:
    base = cls.replace("electric_", "")
    certs[op].add(base)
    if cls.startswith("electric"):
        certs[op].add("ev_high_voltage")
all_bases = ["mini_excavator", "excavator", "wheel_loader", "dozer", "backhoe_loader"]
for oid in certs:
    extra = rng.choice(all_bases, size=int(rng.integers(0, 3)), replace=False)
    certs[oid].update(extra)
for oid in ["OP1013", "OP1014", "OP1015"]:
    certs[oid].update(["excavator", "mini_excavator", "backhoe_loader", "wheel_loader"])
certs["OP1014"].add("ev_high_voltage")
certs["OP1013"].add("ev_high_voltage")

def certified(oid, cls):
    need = {cls.replace("electric_", "")}
    if cls.startswith("electric"):
        need.add("ev_high_voltage")
    return need <= certs[oid]

# ---------------------------------------------------------------- weather
start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
days = [start_date + timedelta(d) for d in range(args.days)]
weather_rows, weather_alerts = [], []
WX = {}   # (site, date, hour) -> dict
for s in SITES:
    for di, d in enumerate(days):
        tmax = rng.normal(*s["tmax"]) + (3.2 if (di + 1) in s["heatwave_days"] else 0)
        tmin = s["tmin"] + rng.normal(0, 0.8)
        storm = rng.random() < s["storm_p"]
        rain = np.zeros(24)
        if storm:
            st = int(rng.integers(14, 18)); dur = int(rng.integers(1, 4))
            peak = float(np.clip(rng.lognormal(2.2, 0.6), 2, 45))
            for k in range(dur):
                if st + k < 24:
                    rain[st + k] = round(peak * (1.0 if k == 0 else rng.uniform(0.2, 0.7)), 1)
        # small morning drizzle sometimes
        if rng.random() < 0.08:
            h = int(rng.integers(8, 12)); rain[h] = round(rng.uniform(0.5, 4), 1)
        for h in range(24):
            frac = math.sin(max(0, min(1, (h - 5) / 19)) * math.pi) ** 1.3 if 5 <= h <= 23 else 0
            temp = tmin + (tmax - tmin) * frac
            if rain[h] > 0:
                temp -= min(5, 1 + rain[h] / 5)
            if h > 0 and rain[h - 1] > 0 and rain[h] == 0:
                temp -= 2
            hum = float(np.clip(55 + (40 if s["city"] == "Chennai" else 25) * (1 - frac) + rain[h] * 2
                                + rng.normal(0, 4), 25, 100))
            wind = float(np.clip(rng.normal(12 if s["city"] == "Chennai" else 9, 3) + rain[h] * 1.2, 0, 70))
            row = dict(site_id=s["site_id"], timestamp=datetime(d.year, d.month, d.day, h),
                       temp_c=round(temp, 1), humidity_pct=round(hum), wind_kmh=round(wind, 1),
                       rain_mm_hr=float(rain[h]))
            weather_rows.append(row)
            WX[(s["site_id"], d, h)] = row
        # alerts (IMD-style, simulated)
        if tmax >= 40:
            weather_alerts.append(dict(site_id=s["site_id"], date=d, alert_type="heatwave", severity="orange",
                                       start=datetime(d.year, d.month, d.day, 11), end=datetime(d.year, d.month, d.day, 16),
                                       advisory="Mandatory 15-min shaded rest every 2 h; hydration checks; watch coolant temp"))
        if rain.max() >= 15:
            h0 = int(np.argmax(rain))
            weather_alerts.append(dict(site_id=s["site_id"], date=d, alert_type="thunderstorm_lightning", severity="orange",
                                       start=datetime(d.year, d.month, d.day, h0) - timedelta(minutes=20),
                                       end=datetime(d.year, d.month, d.day, h0, 40),
                                       advisory="Suspend boom/elevated work; operators stay in cab or shelter"))
        if rain.sum() >= 25:
            weather_alerts.append(dict(site_id=s["site_id"], date=d, alert_type="heavy_rain", severity="yellow",
                                       start=datetime(d.year, d.month, d.day, int(np.argmax(rain))),
                                       end=datetime(d.year, d.month, d.day, 23, 59),
                                       advisory="Check trench walls and slopes before next shift; expect soft ground"))

def alert_active(site, ts, kind):
    for a in weather_alerts:
        if a["site_id"] == site and a["alert_type"] == kind and a["start"] <= ts < a["end"]:
            return True
    return False

def rain_last_24h(site, d):
    tot = 0.0
    for h in range(24):
        prev = d - timedelta(1)
        if (site, prev, h) in WX:
            tot += WX[(site, prev, h)]["rain_mm_hr"] if h >= 8 else 0
        if h < 8:
            tot += WX[(site, d, h)]["rain_mm_hr"]
    return tot

# --------------------------------------------------------------- simulation
telemetry, tasks_out, energy_events, gt_minutes = [], [], [], []
task_counter = 0
anomaly_counter = 0
state_by_machine = {}
for mid, cls, site, eh, op in MACHINES:
    c = CLASSES[cls]
    state_by_machine[mid] = dict(engine_hours=eh,
                                 fuel=rng.uniform(0.5, 0.95) * c["tank"] if c["power"] == "diesel" else None,
                                 soc=100.0 if c["power"] == "electric" else None)
maint_day = {m[0]: int(rng.integers(3, args.days)) for m in MACHINES}

def ground_factor(cls, task, cond):
    f = 1.0
    if cond == "wet":
        f *= 0.82
    if cond == "rocky" and task in ("trenching", "excavation", "site_clearing"):
        f *= 0.78
    if cond == "rocky" and task not in ("trenching", "excavation", "site_clearing"):
        f *= 0.92
    return f

for di, d in enumerate(days):
    if d.weekday() == 6:
        continue  # Sundays off
    for mid, cls, site, _, primary in MACHINES:
        if di == maint_day[mid]:
            continue
        c = CLASSES[cls]
        S = state_by_machine[mid]
        # operator
        op = primary
        if rng.random() < 0.12:
            cands = [o for o in OPS if o != primary and certified(o, cls) and OPS[o]["home_site"] == site]
            if cands:
                op = str(rng.choice(cands))
        O = OPS[op]
        base_ts = datetime(d.year, d.month, d.day, SHIFT_START_H)

        # start-of-day energy
        if c["power"] == "diesel" and S["fuel"] < 0.45 * c["tank"]:
            added = c["tank"] - S["fuel"]
            energy_events.append(dict(machine_id=mid, site_id=site, event="refuel", point_id=f"{site}-FB1",
                                      start=base_ts - timedelta(minutes=12), end=base_ts - timedelta(minutes=4),
                                      duration_min=8, amount=round(added, 1), unit="L", level_before_pct=round(100 * S["fuel"] / c["tank"], 1),
                                      level_after_pct=100.0, reason="pre-shift top-up"))
            S["fuel"] = c["tank"]
        if c["power"] == "electric":
            before = S["soc"]
            if before < 99:
                energy_events.append(dict(machine_id=mid, site_id=site, event="charge", point_id=f"{site}-DC1",
                                          start=base_ts - timedelta(hours=10), end=base_ts - timedelta(hours=2),
                                          duration_min=480, amount=round((100 - before) / 100 * c["battery"], 1), unit="kWh",
                                          level_before_pct=round(before, 1), level_after_pct=100.0, reason="overnight AC charge"))
            S["soc"] = 100.0

        # plan tasks
        rain24 = rain_last_24h(site, d)
        soil = SITE[site]["soil"]
        cond = "rocky" if soil == "rocky" else ("wet" if rain24 >= 5 else "dry")
        plan, naive_total = [], 0.0
        target = rng.uniform(4.3, 5.1)   # admin books ~4.3-5.1 h of 'ideal' work
        while naive_total < target:
            tt = str(rng.choice(list(c["tasks"])))
            base = c["tasks"][tt]
            hrs = rng.uniform(1.3, 3.2)
            qty = max(5, round(base * hrs / 5) * 5)
            task_counter += 1
            plan.append(dict(task_id=f"T{task_counter:05d}", task_type=tt, unit=UNIT[tt], quantity=qty,
                             base=base, noise=float(rng.lognormal(0, 0.07)),
                             planned_min=round(60 * qty / base * 1.2)))   # admin rule of thumb: ideal rate + 20%
            naive_total += qty / base
        # planned (naive) schedule
        t_cursor = 8
        for tk in plan:
            if t_cursor < LUNCH[0] <= t_cursor + tk["planned_min"]:
                t_cursor += LUNCH[1] - LUNCH[0]
            tk["planned_start"] = base_ts + timedelta(minutes=t_cursor)
            t_cursor += tk["planned_min"] + 10
            tk.update(actual_start=None, actual_end=None, progress=0.0, productive_min=0, rain_mm=0.0, temps=[])

        # plan anomalies
        probs = dict(BASE_P)
        for k, v in PROFILE.get(op, {}).items():
            probs[k] = max(probs[k], v)
        hot_day = max(WX[(site, d, h)]["temp_c"] for h in range(8, 17)) >= 36
        planned_anoms = []
        for atype, pr in probs.items():
            if atype in ("fuel_loss", "abnormal_fuel_burn") and c["power"] != "diesel":
                continue
            if atype == "overheating" and (c["power"] != "diesel" or not hot_day):
                continue
            if rng.random() < pr:
                anomaly_counter += 1
                aid = f"A{anomaly_counter:04d}"
                if atype == "excessive_idling":
                    a = dict(kind="block", state="idle", present=1, belt=1, dur=int(rng.integers(25, 61)))
                elif atype == "unattended_running":
                    a = dict(kind="block", state="idle", present=0, belt=0, dur=int(rng.integers(10, 41)))
                elif atype == "unbelted_operation":
                    a = dict(kind="overlay", allowed=("working", "travel", "idle"), dur=int(rng.integers(8, 35)))
                elif atype == "proximity_breach":
                    a = dict(kind="overlay", allowed=("working", "travel"), dur=int(rng.integers(1, 4)))
                elif atype == "overspeed_travel":
                    a = dict(kind="overlay", allowed=("travel",), dur=int(rng.integers(2, 6)))
                elif atype == "harsh_operation":
                    a = dict(kind="overlay", allowed=("working",), dur=int(rng.integers(20, 45)))
                elif atype == "fuel_loss":
                    a = dict(kind="lunch", dur=5, loss=float(rng.uniform(0.12, 0.25)) * c["tank"])
                elif atype == "overheating":
                    a = dict(kind="overlay", allowed=("working", "idle", "travel"), dur=int(rng.integers(35, 70)))
                elif atype == "abnormal_fuel_burn":
                    a = dict(kind="day", factor=float(rng.uniform(1.28, 1.42)))
                trig = int(rng.integers(20, 250)) if rng.random() < 0.5 else int(rng.integers(320, 500))
                if atype == "overheating":
                    trig = int(rng.integers(330, 440))
                a.update(id=aid, type=atype, trigger=trig, active=False, left=a.get("dur", 0), done=False)
                planned_anoms.append(a)

        # minute loop
        ti, sub = 0, "warmup"
        warm_left = int(rng.integers(5, 9))
        travel_left, after_travel = 0, None
        idle_left, refuel_left, charge_active = 0, 0, False
        block = None
        hyd_t = WX[(site, d, 8)]["temp_c"] + 5
        cool_t = hyd_t
        last_rest = -999
        rest_left = 0
        S["_cs"] = None
        day_burn = next((a["factor"] for a in planned_anoms if a["type"] == "abnormal_fuel_burn"), 1.0)
        burn_id = next((a["id"] for a in planned_anoms if a["type"] == "abnormal_fuel_burn"), None)

        for i in range(SHIFT_MIN):
            ts = base_ts + timedelta(minutes=i)
            w = WX[(site, d, ts.hour)]
            temp, rain = w["temp_c"], w["rain_mm_hr"]
            lightning = alert_active(site, ts, "thunderstorm_lightning")
            heat_alert = alert_active(site, ts, "heatwave")
            labels = []
            state, present, belt = "off", 0, 0
            task_id = plan[ti]["task_id"] if ti < len(plan) else None

            in_lunch = LUNCH[0] <= i < LUNCH[1]
            if charge_active:
                state = "charging"
            elif refuel_left > 0:
                state = "refueling"; refuel_left -= 1; present = 1
            elif in_lunch:
                state = "off"
                if c["power"] == "electric" and S["soc"] < 70:
                    state = "charging"
                    if not charge_active:
                        charge_active = "lunch"
            elif rain >= 12 or lightning:
                state, present = "weather_hold", 1
            elif rest_left > 0:
                state = "heat_rest"; rest_left -= 1
            elif heat_alert and i - last_rest >= 120 and 240 <= i < 480:
                last_rest = i; state = "heat_rest"; rest_left = 14
            elif block is not None:
                state, present, belt = block["state"], block["present"], block["belt"]
                labels.append((block["id"], block["type"]))
                block["left"] -= 1
                if block["left"] <= 0:
                    block = None
            elif sub == "warmup":
                state, present, belt = "idle", 1, 1
                warm_left -= 1
                if warm_left <= 0:
                    sub = "task"
            elif travel_left > 0:
                state, present, belt = "travel", 1, 1
                travel_left -= 1
                if travel_left == 0 and after_travel == "charge":
                    charge_active = "low"; after_travel = None
            elif ti < len(plan):
                tk = plan[ti]
                # trigger idle/unattended blocks
                for a in planned_anoms:
                    if a["kind"] == "block" and not a["done"] and i >= a["trigger"] and i + a["dur"] < SHIFT_MIN:
                        if not (i < LUNCH[0] < i + a["dur"]):
                            block = dict(a); a["done"] = True
                            break
                if block is not None:
                    state, present, belt = block["state"], block["present"], block["belt"]
                    labels.append((block["id"], block["type"]))
                    block["left"] -= 1
                else:
                    if tk["actual_start"] is None:
                        tk["actual_start"] = ts
                    present, belt = 1, 1
                    if idle_left > 0:
                        state = "idle"; idle_left -= 1
                    else:
                        p_idle = (0.09 if tk["task_type"] in ("truck_loading", "stockpiling") else 0.055) * O["_idle"]
                        if rng.random() < p_idle:
                            idle_left = int(rng.geometric(0.35)); state = "idle"
                        else:
                            state = "working"
                    if state == "working":
                        wf = 1 - 0.02 * rain
                        wf *= 0.93 if temp >= 38 else 1.0
                        fatigue = 0.95 if i > 360 else 1.0
                        rate = tk["base"] / 60 * O["_skill"] * ground_factor(cls, tk["task_type"], cond) * wf * fatigue * tk["noise"]
                        tk["progress"] += rate * rng.normal(1, 0.1)
                        tk["productive_min"] += 1
                    tk["rain_mm"] += rain / 60
                    tk["temps"].append(temp)
                    if tk["progress"] >= tk["quantity"]:
                        tk["actual_end"] = ts + timedelta(minutes=1)
                        ti += 1
                        if ti < len(plan):
                            travel_left = int(rng.integers(4, 13))
            else:
                state = "off"   # all tasks done - parked

            if state == "heat_rest":
                present = 0
            if in_lunch or state in ("off",):
                present = 0

            power_on = int(state in ("idle", "working", "travel"))
            # overlays
            for a in planned_anoms:
                if a["kind"] == "overlay" and not a["done"]:
                    if not a["active"] and i >= a["trigger"] and state in a["allowed"]:
                        a["active"] = True
                    if a["active"]:
                        if state in a["allowed"]:
                            labels.append((a["id"], a["type"]))
                        a["left"] -= 1
                        if a["left"] <= 0:
                            a["done"] = True
            types = {t for _, t in labels}
            if "unbelted_operation" in types and power_on:
                belt = 0
            # normal noise: brief unbuckle while idling
            if state == "idle" and present and not labels and rng.random() < 0.01:
                belt = 0

            # ---- sensors
            rpm = speed = hyd_p = 0.0
            cycles = harsh = 0
            if state == "working":
                rpm = rng.uniform(1550, 1900); speed = rng.uniform(*c["wspeed"])
                hyd_p = rng.uniform(180, 310); cycles = int(rng.poisson(c["cycles"]))
                harsh = int(rng.poisson(0.01))
            elif state == "idle":
                rpm = rng.uniform(800, 950); hyd_p = rng.uniform(20, 40)
            elif state == "travel":
                rpm = rng.uniform(1400, 1650); speed = rng.uniform(3, 8); hyd_p = rng.uniform(60, 120)
            if "overspeed_travel" in types:
                speed = rng.uniform(13, 19)
            if "harsh_operation" in types:
                harsh = int(rng.poisson(0.7)); hyd_p = rng.uniform(320, 360)
            if c["power"] == "electric":
                rpm = np.nan
            # proximity
            if power_on and rng.random() < 0.35:
                prox = float(np.clip(rng.lognormal(math.log(8), 0.5), 2.5, 20))
            else:
                prox = 20.0
            if "proximity_breach" in types:
                prox = rng.uniform(0.6, 1.8)
            zone = ProximityZone.DANGER if prox < 2 else (ProximityZone.CAUTION if prox < 5 else ProximityZone.CLEAR)
            # temperatures (first-order lag)
            tgt_h = {"working": 62, "idle": 50, "travel": 55}.get(state, temp)
            hyd_t += (tgt_h - hyd_t) * 0.04
            tgt_c = {"working": 88, "idle": 82, "travel": 85}.get(state, temp)
            if "overheating" in types:
                tgt_c = 114
            if temp >= 38 and power_on:
                tgt_c += 3
            cool_t += (tgt_c - cool_t) * (0.08 if power_on else 0.03)
            # energy
            e_used = np.nan
            fuel_rate = power_kw = np.nan
            if c["power"] == "diesel":
                fuel_rate = {"working": rng.uniform(*c["work"]), "idle": c["idle"] * rng.uniform(0.9, 1.1),
                             "travel": c["travel"] * rng.uniform(0.9, 1.1)}.get(state, 0.0)
                if "harsh_operation" in types:
                    fuel_rate *= 1.15
                if power_on and day_burn > 1:
                    fuel_rate *= day_burn
                    labels.append((burn_id, "abnormal_fuel_burn"))
                e_used = fuel_rate / 60
                S["fuel"] = max(0.0, S["fuel"] - e_used)
                for a in planned_anoms:
                    if a["kind"] == "lunch" and in_lunch and LUNCH[0] + 8 <= i < LUNCH[0] + 8 + a["dur"]:
                        S["fuel"] = max(0.0, S["fuel"] - a["loss"] / a["dur"])
                        labels.append((a["id"], "fuel_loss"))
                if S["fuel"] < 0.12 * c["tank"] and state not in ("refueling",) and refuel_left == 0 and not in_lunch:
                    refuel_left = 8
                    energy_events.append(dict(machine_id=mid, site_id=site, event="refuel", point_id=f"{site}-FB1",
                                              start=ts + timedelta(minutes=1), end=ts + timedelta(minutes=9), duration_min=8,
                                              amount=round(c["tank"] - S["fuel"], 1), unit="L",
                                              level_before_pct=round(100 * S["fuel"] / c["tank"], 1), level_after_pct=100.0,
                                              reason="low fuel mid-shift"))
                if state == "refueling" and refuel_left == 0:
                    S["fuel"] = c["tank"]
                level = 100 * S["fuel"] / c["tank"]
            else:
                if state == "charging":
                    pk = c["charge_kw"] if S["soc"] < 80 else c["charge_kw"] * max(0.15, 1 - (S["soc"] - 80) / 22)
                    if S.get("_cs") is None:
                        S["_cs"] = (ts, S["soc"])
                    S["soc"] = min(100.0, S["soc"] + pk / 60 * 0.93 / c["battery"] * 100)
                    power_kw = -pk
                    e_used = -pk / 60
                    target = 90 if charge_active == "low" else 85
                    if S["soc"] >= target or (charge_active == "lunch" and i == LUNCH[1] - 1):
                        cs_ts, cs_soc = S["_cs"]
                        dur = int((ts - cs_ts).total_seconds() // 60) + 1
                        energy_events.append(dict(machine_id=mid, site_id=site, event="charge", point_id=f"{site}-DC1",
                                                  start=cs_ts, end=ts + timedelta(minutes=1), duration_min=dur,
                                                  amount=round((S["soc"] - cs_soc) / 100 * c["battery"], 1), unit="kWh",
                                                  level_before_pct=round(cs_soc, 1), level_after_pct=round(S["soc"], 1),
                                                  reason="low battery mid-shift" if charge_active == "low" else "opportunity charge at lunch"))
                        S["_cs"] = None
                        if charge_active == "low" and not in_lunch:
                            travel_left = 3
                        charge_active = False
                else:
                    power_kw = {"working": rng.uniform(*c["work"]), "idle": c["idle"], "travel": c["travel"]}.get(state, 0.0)
                    if "harsh_operation" in types:
                        power_kw *= 1.15
                    e_used = power_kw / 60
                    S["soc"] = max(0.0, S["soc"] - e_used / c["battery"] * 100)
                    if S["soc"] < 25 and not charge_active and after_travel != "charge" and power_on:
                        travel_left, after_travel = 3, "charge"
                level = S["soc"]

            if power_on:
                S["engine_hours"] += 1 / 60

            aid = ";".join(sorted({a for a, _ in labels}))
            atype = ";".join(sorted({t for _, t in labels}))
            telemetry.append((ts, site, mid, op, task_id if state in ("working", "idle", "travel") and ti < len(plan) else None,
                              state, power_on, present, SeatbeltStatus.FASTENED if belt else SeatbeltStatus.UNFASTENED,
                              None if np.isnan(rpm) else round(rpm), round(speed, 1),
                              round(level, 1) if c["power"] == "diesel" else np.nan,
                              round(level, 1) if c["power"] == "electric" else np.nan,
                              round(fuel_rate, 2) if c["power"] == "diesel" else np.nan,
                              round(power_kw, 1) if c["power"] == "electric" else np.nan,
                              round(e_used, 3) if c["power"] == "diesel" else np.nan,
                              round(-e_used, 3) if c["power"] == "electric" else np.nan,
                              round(hyd_p), round(hyd_t, 1), round(cool_t, 1),
                              cycles, round(prox, 1), zone, harsh, temp, rain, round(S["engine_hours"], 2),
                              aid, atype))

        for tk in plan:
            status = TaskStatus.COMPLETED if tk["actual_end"] else (TaskStatus.PARTIAL if tk["actual_start"] else TaskStatus.SCHEDULED)
            dur = int((tk["actual_end"] - tk["actual_start"]).total_seconds() // 60) if tk["actual_end"] else None
            tasks_out.append(dict(task_id=tk["task_id"], date=d, site_id=site, machine_id=mid, machine_class=cls,
                                  operator_id=op, task_type=tk["task_type"], unit=tk["unit"], quantity=tk["quantity"],
                                  ground_condition=cond, rain_prev_24h_mm=round(rain24, 1),
                                  planned_start=tk["planned_start"], planned_duration_min=tk["planned_min"],
                                  actual_start=tk["actual_start"], actual_end=tk["actual_end"], actual_duration_min=dur,
                                  productive_min=tk["productive_min"],
                                  completed_quantity=round(min(tk["progress"], tk["quantity"]), 1),
                                  status=status, avg_temp_c=round(float(np.mean(tk["temps"])), 1) if tk["temps"] else None,
                                  rain_during_task_mm=round(tk["rain_mm"], 1),
                                  assigned_by="ADM01"))

# ------------------------------------------------------------------ frames
TCOLS = ["timestamp", "site_id", "machine_id", "operator_id", "task_id", "state", "is_power_on", "is_operator_present",
         "seatbelt_status", "engine_rpm", "ground_speed_kmh", "fuel_level_pct", "battery_soc_pct", "fuel_rate_lph",
         "power_kw", "fuel_used_l", "energy_used_kwh", "hydraulic_pressure_bar", "hydraulic_oil_temp_c", "coolant_temp_c",
         "load_cycles", "proximity_min_m", "proximity_zone", "harsh_events", "ambient_temp_c", "rain_mm_hr",
         "engine_hours", "anomaly_id", "anomaly_type"]
tel = pd.DataFrame(telemetry, columns=TCOLS)
tel["anomaly_id"] = tel["anomaly_id"].replace("", np.nan)
tel["anomaly_type"] = tel["anomaly_type"].replace("", np.nan)

# ground truth events from labelled minutes
gt = (tel.dropna(subset=["anomaly_id"]).assign(anomaly_id=lambda x: x["anomaly_id"].str.split(";"))
      .explode("anomaly_id"))
atype_map = {}
for _, r in tel.dropna(subset=["anomaly_id"]).iterrows():
    for a, t in zip(r["anomaly_id"].split(";"), r["anomaly_type"].split(";")):
        atype_map[a] = t
gt["anomaly_type"] = gt["anomaly_id"].map(atype_map)
SEV = dict(unbelted_operation="high", proximity_breach="critical", unattended_running="high",
           overspeed_travel="medium", harsh_operation="medium", excessive_idling="low", fuel_loss="high",
           overheating="high", abnormal_fuel_burn="medium")
DESC = dict(unbelted_operation="Machine operated with seatbelt unfastened",
            proximity_breach="Person/object inside 2 m danger zone while machine moving",
            unattended_running="Engine running at idle with operator out of seat",
            overspeed_travel="Travel speed above 10 km/h site limit",
            harsh_operation="Abrupt control inputs; hydraulic pressure spikes",
            excessive_idling="Continuous idle block beyond 25 min",
            fuel_loss="Fuel level drop while engine off (leak or theft)",
            overheating="Coolant temperature above safe band on hot day",
            abnormal_fuel_burn="Fuel consumption 28-42% above class norm for whole shift (e.g. clogged filter)")
gt_events = (gt.groupby("anomaly_id").agg(anomaly_type=("anomaly_type", "first"), machine_id=("machine_id", "first"),
                                          operator_id=("operator_id", "first"), site_id=("site_id", "first"),
                                          start=("timestamp", "min"), end=("timestamp", "max"),
                                          labelled_minutes=("timestamp", "count")).reset_index())
gt_events["end"] = gt_events["end"] + pd.Timedelta(minutes=1)
gt_events["severity"] = gt_events["anomaly_type"].map(SEV)
gt_events["description"] = gt_events["anomaly_type"].map(DESC)

# rule-based alerts (what a simple edge/cloud rule engine would emit)
tel = tel.sort_values(["machine_id", "timestamp"]).reset_index(drop=True)
alerts = []
def runs(mask, g):
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    splits = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    return [(g.iloc[s[0]]["timestamp"], g.iloc[s[-1]]["timestamp"] + pd.Timedelta(minutes=1), len(s)) for s in splits]
for mid, g in tel.groupby("machine_id"):
    g = g.reset_index(drop=True)
    moving = g["state"].isin(["working", "travel"])
    rules = [
        (AlertCode.SEATBELT_UNFASTENED_MOVING, "critical", (g["seatbelt_status"] == SeatbeltStatus.UNFASTENED) & moving, 1),
        (AlertCode.UNATTENDED_RUNNING, "high", (g["is_power_on"] == 1) & (g["is_operator_present"] == 0), 5),
        (AlertCode.PROXIMITY_DANGER, "critical", (g["proximity_zone"] == ProximityZone.DANGER) & moving, 1),
        (AlertCode.OVERSPEED, "medium", g["ground_speed_kmh"] > SITE_SPEED_LIMIT, 1),
        (AlertCode.COOLANT_HIGH, "high", g["coolant_temp_c"] > 103, 3),
        (AlertCode.EXCESSIVE_IDLE, "low", g["state"] == "idle", 20),
        (AlertCode.HARSH_OPERATION, "medium", g["harsh_events"] > 0, 1),
    ]
    for code, sev, mask, min_len in rules:
        for s, e, n in runs(mask.values, g):
            if n >= min_len:
                if code == AlertCode.HARSH_OPERATION and n < 3:
                    continue
                alerts.append(dict(machine_id=mid, operator_id=g.loc[g["timestamp"] == s, "operator_id"].iloc[0],
                                   site_id=g["site_id"].iloc[0], alert_code=code, severity=sev,
                                   start=s, end=e, duration_min=n))
alerts = pd.DataFrame(alerts).sort_values("start").reset_index(drop=True)
alerts.insert(0, "alert_id", [f"AL{i+1:05d}" for i in range(len(alerts))])

# 2-hour summary in the sample's exact format (+ extra columns)
tel["window"] = tel["timestamp"].dt.floor("2h")
al_win = set()
for _, a in alerts.iterrows():
    t = a["start"].floor("2h")
    al_win.add((a["machine_id"], t))
rows = []
for (mid, win), g in tel.groupby(["machine_id", "window"]):
    powered = g[g["is_power_on"] == 1]
    unf = ((g["seatbelt_status"] == SeatbeltStatus.UNFASTENED) & (g["is_power_on"] == 1)).sum()
    diesel = g["fuel_level_pct"].notna().any()
    rows.append({"Timestamp": win, "Machine ID": mid,
                 "Operator ID": g["operator_id"].mode().iloc[0],
                 "Engine Hours": round(g["engine_hours"].iloc[-1], 1),
                 "Fuel Used (L)": round(g["fuel_used_l"].clip(lower=0).sum(), 1) if diesel else np.nan,
                 "Load Cycles": int(g["load_cycles"].sum()),
                 "Idling Time (min)": int((g["state"] == "idle").sum()),
                 "Seatbelt Status": "unfastened" if unf >= 3 else "fastened",
                 "Safety Alert Triggered": "Yes" if (mid, win) in al_win else "No",
                 "Energy Used (kWh)": np.nan if diesel else round(g["energy_used_kwh"].clip(lower=0).sum(), 1),
                 "Working Time (min)": int((g["state"] == "working").sum()),
                 "Powered Time (min)": int(len(powered))})
summary = pd.DataFrame(rows).sort_values(["Timestamp", "Machine ID"])
tel = tel.drop(columns="window").sort_values(["timestamp", "machine_id"])

# static tables
machines_df = pd.DataFrame([dict(machine_id=m, machine_class=c, powertrain=CLASSES[c]["power"],
                                 reference_model=CLASSES[c]["ref_model"], site_id=s, primary_operator_id=o,
                                 engine_hours_at_start=eh,
                                 fuel_tank_l=CLASSES[c].get("tank"), battery_kwh=CLASSES[c].get("battery"),
                                 max_charge_kw=CLASSES[c].get("charge_kw"),
                                 commission_year=int(rng.integers(2016, 2025)) if CLASSES[c]["power"] == "diesel" else 2024)
                            for m, c, s, eh, o in MACHINES])
ops_df = pd.DataFrame([dict(operator_id=o["operator_id"], name=o["name"], experience_years=o["experience_years"],
                            home_site_id=o["home_site"], shift=o["shift"],
                            certifications=";".join(sorted(certs[o["operator_id"]])))
                       for o in operators])
sites_df = pd.DataFrame([dict(site_id=s["site_id"], name=s["name"], city=s["city"], lat=s["lat"], lon=s["lon"],
                              soil_type=s["soil"], speed_limit_kmh=SITE_SPEED_LIMIT) for s in SITES])
points = []
for s in SITES:
    points.append(dict(point_id=f"{s['site_id']}-FB1", site_id=s["site_id"], type="fuel_bowser", power_kw=None,
                       lat=round(s["lat"] + 0.0012, 5), lon=round(s["lon"] - 0.0009, 5)))
    if s["site_id"] in ("S01", "S02"):
        points.append(dict(point_id=f"{s['site_id']}-DC1", site_id=s["site_id"], type="dc_charger",
                           power_kw=150 if s["site_id"] == "S02" else 60,
                           lat=round(s["lat"] - 0.0008, 5), lon=round(s["lon"] + 0.0011, 5)))
points_df = pd.DataFrame(points)

COURSES = [("TRN01", "Seatbelt and ROPS safety", "safety", 36), ("TRN02", "Proximity and blind-spot awareness", "safety", 24),
           ("TRN03", "Fuel-efficient operation", "efficiency", None), ("TRN04", "EV high-voltage safety", "ev", 24),
           ("TRN05", "Pre-shift inspection", "maintenance", None)]
train = []
for o in operators:
    oid = o["operator_id"]
    for cid, cname, cat, valid in COURSES:
        if cid == "TRN04" and "ev_high_voltage" not in certs[oid]:
            continue
        if rng.random() < 0.85 or cid in ("TRN01", "TRN04"):
            done = date(2022, 1, 1) + timedelta(int(rng.integers(0, 1200)))
            if oid == "OP1007" and cid == "TRN01":
                done = date(2021, 11, 15)  # lapsed refresher
            train.append(dict(operator_id=oid, course_id=cid, course=cname, category=cat,
                              completed_on=done, score_pct=int(rng.integers(62, 99)),
                              valid_until=(done + timedelta(days=30 * valid)) if valid else None,
                              format=str(rng.choice(["e-learning", "instructor-led", "simulator"]))))
train_df = pd.DataFrame(train)

# operator-reported incidents (a few, some tied to planted events)
inc = []
crit = gt_events[gt_events["anomaly_type"].isin(["proximity_breach", "fuel_loss", "overheating"])].sample(
    frac=0.5, random_state=args.seed) if len(gt_events) else gt_events
texts = dict(proximity_breach="Ground worker walked into swing radius; stopped machine, spotter reminded",
             fuel_loss="Fuel level lower after lunch than before; possible leak or pilferage, supervisor informed",
             overheating="Coolant warning on dash in afternoon heat; idled down and reported")
for k, (_, r) in enumerate(crit.iterrows()):
    inc.append(dict(incident_id=f"IN{k+1:04d}", reported_at=r["start"] + pd.Timedelta(minutes=int(rng.integers(5, 40))),
                    machine_id=r["machine_id"], operator_id=r["operator_id"], site_id=r["site_id"],
                    category=r["anomaly_type"], severity=r["severity"], description=texts[r["anomaly_type"]],
                    linked_anomaly_id=r["anomaly_id"], status=str(rng.choice(["open", "closed"]))))
for k, (d, s) in enumerate([(days[9], "S02"), (days[20], "S03")]):
    if d.weekday() == 6: d = d + timedelta(1)
    inc.append(dict(incident_id=f"IN{len(inc)+1:04d}", reported_at=datetime(d.year, d.month, d.day, 9, 20),
                    machine_id=None, operator_id=None, site_id=s, category="site_hazard", severity="medium",
                    description="Trench wall softened after overnight rain; area cordoned off before work" if s == "S02"
                    else "Loose rock on haul path near crusher; cleared before shift",
                    linked_anomaly_id=None, status="closed"))
inc_df = pd.DataFrame(inc)

# ------------------------------------------------------------------ write
def write_utc_csv(frame, path, timestamp_columns):
    output = frame.copy()
    for column in timestamp_columns:
        if column in output.columns:
            output[column] = (pd.to_datetime(output[column], utc=True)
                              .dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    output.to_csv(path, index=False)


out = args.out
write_utc_csv(tel, f"{out}/telemetry_1min.csv", ["timestamp"])
summary.to_csv(f"{out}/machine_summary_2h.csv", index=False)
write_utc_csv(pd.DataFrame(tasks_out), f"{out}/tasks.csv", ["planned_start", "actual_start", "actual_end"])
machines_df.to_csv(f"{out}/machines.csv", index=False)
ops_df.to_csv(f"{out}/operators.csv", index=False)
sites_df.to_csv(f"{out}/sites.csv", index=False)
points_df.to_csv(f"{out}/energy_points.csv", index=False)
energy_events_df = pd.DataFrame(energy_events)
write_utc_csv(energy_events_df, f"{out}/energy_events.csv", ["start", "end"])
write_utc_csv(pd.DataFrame(weather_rows), f"{out}/weather_hourly.csv", ["timestamp"])
write_utc_csv(pd.DataFrame(weather_alerts), f"{out}/weather_alerts.csv", ["start", "end"])
write_utc_csv(alerts, f"{out}/safety_alerts.csv", ["start", "end"])
write_utc_csv(gt_events, f"{out}/anomalies_ground_truth.csv", ["start", "end"])
train_df.to_csv(f"{out}/training_records.csv", index=False)
write_utc_csv(inc_df, f"{out}/incidents.csv", ["reported_at"])
print("telemetry rows:", len(tel), "| tasks:", len(tasks_out), "| anomalies:", len(gt_events),
      "| alerts:", len(alerts), "| energy events:", len(energy_events), "| weather alerts:", len(weather_alerts))
