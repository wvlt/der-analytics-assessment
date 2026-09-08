"""
WestGen Energy — DER Assessment Data Generator
Run this in a Databricks notebook cell (or locally with pandas + numpy).
Writes three CSVs to ./westgen_data/ (or /tmp/westgen_data on Databricks).

Deterministic: same data for every candidate (seed=42).
"""

import numpy as np
import pandas as pd
import os

SEED = 42
rng = np.random.default_rng(SEED)

# Create the catalog/schema/volume FIRST (see README setup), then run this.
# Edit this path if you named your catalog/schema/volume differently.
OUT_DIR = "/Volumes/westgen/raw/landing"
if not os.path.isdir(OUT_DIR):
    OUT_DIR = "./westgen_data"
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"NOTE: /Volumes/westgen/raw/landing not found — writing to {os.path.abspath(OUT_DIR)} instead.")
    print("If you're on Databricks, create the Volume first (see README Setup step 2) and re-run,")
    print("or edit OUT_DIR above to match your own catalog/schema/volume names.")

DAYS = 14
START = pd.Timestamp("2026-08-01 00:00:00")  # local time, AWST (UTC+8)
INTERVALS = DAYS * 288  # 5-min intervals

# ----------------------------------------------------------------------
# 1. Asset metadata
# ----------------------------------------------------------------------
assets = [
    # asset_id, name, type, capacity_mw, energy_mwh, region, commissioned
    ("BESS-01", "Kwinana South Battery",  "BESS",  100.0, 200.0, "South Metro", "2024-03-15"),
    ("BESS-02", "Merredin Battery",       "BESS",   50.0, 100.0, "Wheatbelt",   "2025-01-20"),
    ("BESS-03", "Geraldton Battery",      "BESS",   25.0,  50.0, "Mid West",    "2025-09-01"),
    ("SOL-01",  "Northam Solar Farm",     "SOLAR", 120.0,  None, "Wheatbelt",   "2022-06-10"),
    ("SOL-02",  "Karratha Solar Farm",    "SOLAR",  80.0,  None, "Pilbara",     "2023-02-01"),
    ("SOL-03",  "Collie Solar Farm",      "SOLAR",  60.0,  None, "South West",  "2024-11-05"),
    ("SOL-04",  "Byford Solar Farm",      "SOLAR",  30.0,  None, "South Metro", "2021-08-30"),
    ("WND-01",  "Warra Ridge Wind Farm",  "WIND",  180.0,  None, "Mid West",    "2023-07-22"),
    ("WND-02",  "Esperance Wind Farm",    "WIND",   90.0,  None, "Goldfields",  "2020-04-12"),
    ("VPP-01",  "Metro VPP Aggregate",    "VPP",    40.0,  80.0, "Metro",       "2025-05-01"),
]
meta = pd.DataFrame(assets, columns=[
    "asset_id", "asset_name", "asset_type", "capacity_mw",
    "energy_capacity_mwh", "region", "commissioned_date"
])

# --- Deliberate issues in metadata ---
# (a) Duplicate row for SOL-02 with a conflicting capacity value
dup = meta[meta.asset_id == "SOL-02"].copy()
dup["capacity_mw"] = 85.0
meta = pd.concat([meta, dup], ignore_index=True)
# (b) An asset that appears in telemetry but NOT in metadata: "WND-03" (see below)
# (c) Inconsistent casing in region
meta.loc[meta.asset_id == "SOL-04", "region"] = "south metro"

meta.to_csv(f"{OUT_DIR}/asset_metadata.csv", index=False)

# ----------------------------------------------------------------------
# 2. Telemetry (5-min), local AWST timestamps, naive
# ----------------------------------------------------------------------
ts = pd.date_range(START, periods=INTERVALS, freq="5min")
frames = []

def solar_profile(ts_index, cap):
    hour = ts_index.hour + ts_index.minute / 60
    shape = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) ** 1.5
    cloud = rng.uniform(0.55, 1.0, size=(len(ts_index) // 288 + 1))
    daily = np.repeat(cloud, 288)[: len(ts_index)]
    noise = rng.normal(1, 0.04, len(ts_index))
    p = cap * shape * daily * noise
    p = np.where(shape == 0, rng.normal(-0.15, 0.05, len(ts_index)), p)  # night aux load (small negative)
    return p

def wind_profile(ts_index, cap):
    n = len(ts_index)
    w = np.cumsum(rng.normal(0, 0.02, n))
    w = (np.sin(np.linspace(0, 9 * np.pi, n)) * 0.3 + 0.45 + w * 0.05)
    return np.clip(w, 0, 0.95) * cap * rng.normal(1, 0.03, n)

def bess_profile(ts_index, cap, energy, eff=0.87):
    """Charge cheap overnight/midday, discharge evening peak."""
    n = len(ts_index)
    hour = ts_index.hour + ts_index.minute / 60
    p = np.zeros(n)
    p[(hour >= 10) & (hour < 14)] = -cap * 0.6      # charge midday (solar soak)
    p[(hour >= 17) & (hour < 20.5)] = cap * 0.7     # discharge evening
    p *= rng.normal(1, 0.05, n)
    # state of charge
    soc = np.zeros(n)
    e = energy * 0.5
    for i in range(n):
        if p[i] < 0:
            e += -p[i] * (5 / 60) * np.sqrt(eff)
        else:
            e -= p[i] * (5 / 60) / np.sqrt(eff)
        e = min(max(e, 0), energy)
        soc[i] = e / energy * 100
    return p, soc

for _, a in meta.drop_duplicates("asset_id").iterrows():
    if a.asset_type == "SOLAR":
        p = solar_profile(ts, a.capacity_mw)
        soc = np.full(len(ts), np.nan)
    elif a.asset_type == "WIND":
        p = wind_profile(ts, a.capacity_mw)
        soc = np.full(len(ts), np.nan)
    else:  # BESS & VPP
        p, soc = bess_profile(ts, a.capacity_mw, a.energy_capacity_mwh)
    frames.append(pd.DataFrame({
        "timestamp": ts,
        "asset_id": a.asset_id,
        "power_mw": np.round(p, 3),
        "soc_pct": np.round(soc, 2),
        "status": "OK",
    }))

# --- Ghost asset present in telemetry but not metadata ---
ghost = pd.DataFrame({
    "timestamp": ts[:288 * 3],
    "asset_id": "WND-03",
    "power_mw": np.round(wind_profile(ts[:288 * 3], 45.0), 3),
    "soc_pct": np.nan,
    "status": "COMMISSIONING",
})
frames.append(ghost)

tel = pd.concat(frames, ignore_index=True)

# --- Deliberate issues in telemetry ---
# (a) Full-day outage for WND-01 on day 6 (rows removed entirely -> gap)
day6 = (tel.timestamp >= START + pd.Timedelta(days=6)) & (tel.timestamp < START + pd.Timedelta(days=7))
tel = tel[~(day6 & (tel.asset_id == "WND-01"))]

# (b) ~2% exact duplicate rows
dups = tel.sample(frac=0.02, random_state=SEED)
tel = pd.concat([tel, dups], ignore_index=True)

# (c) ~1% null power readings, status flips to COMMS_LOSS
null_idx = tel.sample(frac=0.01, random_state=SEED + 1).index
tel.loc[null_idx, "power_mw"] = np.nan
tel.loc[null_idx, "status"] = "COMMS_LOSS"

# (d) SoC spikes >100% for BESS-02 (sensor fault) on ~40 rows
b2 = tel[(tel.asset_id == "BESS-02") & tel.soc_pct.notna()].sample(40, random_state=SEED)
tel.loc[b2.index, "soc_pct"] = np.round(rng.uniform(101, 140, 40), 2)

# (e) BESS-03 reports power in kW, not MW (unit inconsistency)
tel.loc[tel.asset_id == "BESS-03", "power_mw"] = np.round(
    tel.loc[tel.asset_id == "BESS-03", "power_mw"] * 1000, 1)

# (f) Mixed timestamp formats: SOL-04's vendor exports timestamps as strings in UTC with 'Z'
tel["timestamp"] = tel["timestamp"].astype(str)
mask = tel.asset_id == "SOL-04"
utc = (pd.to_datetime(tel.loc[mask, "timestamp"]) - pd.Timedelta(hours=8))
tel.loc[mask, "timestamp"] = utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")

tel = tel.sample(frac=1, random_state=SEED).reset_index(drop=True)  # shuffle
tel.to_csv(f"{OUT_DIR}/telemetry.csv", index=False)

# ----------------------------------------------------------------------
# 3. Market prices (30-min, AWST)
# ----------------------------------------------------------------------
pts = pd.date_range(START, periods=DAYS * 48, freq="30min")
hour = np.asarray(pts.hour + pts.minute / 60, dtype=float)
base = 60 + 45 * np.exp(-((hour - 18.5) ** 2) / 4) - 25 * np.exp(-((hour - 12) ** 2) / 6)
price = base * rng.normal(1, 0.15, len(pts))
# occasional negative midday prices and evening spikes
price[(hour > 11) & (hour < 14) & (rng.random(len(pts)) < 0.25)] *= -0.4
spike_mask = (rng.random(len(pts)) < 0.01) & (hour > 17) & (hour < 21)
price[spike_mask] = rng.uniform(300, 950, spike_mask.sum())
prices = pd.DataFrame({
    "interval_start": pts,
    "price_aud_per_mwh": np.round(price, 2),
})
prices.to_csv(f"{OUT_DIR}/market_prices.csv", index=False)

print(f"Done. Files written to {OUT_DIR}:")
for f in os.listdir(OUT_DIR):
    print(" -", f, f"({os.path.getsize(os.path.join(OUT_DIR, f)):,} bytes)")
