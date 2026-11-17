"""Forecast launch-day Twitch viewers, hours 2..24, from hour 1's print.

Method: learn the shape of a big console launch day from the case's own
comparables.  For every past launch we take its release-day hourly viewers,
divide each hour by that launch's hour-1 print, and work in log space.
A launch whose hour 1 is already huge (the whole world is watching at
midnight) stays flat; a launch whose hour 1 is small (only the first
timezones are in) climbs steeply as the US wakes up and unlocks.  So for
each hour we fit a one-variable line -- log ratio against log10(hour-1 /
100k) -- over the comparable launches, and read off the line at this case's
hour-1 print.  The line's residual spread gives the width of the forecast
bands.  Early-access-contaminated launches (their peak happened days
before release day) are left out of the fit, because their release-day
shape is not a launch-day shape at all.

Standard library only.  No network, no randomness, no clock: the same
case always produces the same bytes.
"""

import json
import math
import os
import re
import sys

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
# Standard-normal quantiles for the five levels.
Z = (-1.6448536269514722, -0.6744897501960817, 0.0,
     0.6744897501960817, 1.6448536269514722)
HOURS = list(range(2, 25))
REFERENCE = 100000.0          # hour-1 print the regression is centred on
MIN_POOL_HOUR1 = 5000         # ignore launches whose hour 1 is near zero:
                              # their ratios are unlock artefacts, not shapes
SIGMA_SCALE = 0.85            # shrink the residual spread a little: the
                              # leave-one-out coverage at this scale is ~0.9
SIGMA_FLOOR = 0.15
SIGMA_CAP = 0.90
SLOPE_LOW, SLOPE_HIGH = -1.3, 0.3
SCALE_LOW, SCALE_HIGH = -0.7, 1.3   # log10(h1 / 100k) clamps


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _pstdev(values, mean):
    if len(values) < 2:
        return 0.6
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _tier(unlock_text):
    """The 'Tier: ...' note the kit attaches to each comparable's unlock."""
    match = re.search(r"Tier:\s*([^.]+)", unlock_text or "")
    return match.group(1).strip().lower() if match else ""


def _release_day_viewers(comp):
    """The 24 hourly viewer counts of a comparable's release day, or None."""
    day = (comp.get("day_start") or "")[:10]
    if not day:
        return None
    hours = [row for row in comp.get("hourly") or []
             if str(row.get("from", ""))[:10] == day]
    if len(hours) != 24:
        return None
    out = []
    for row in hours:
        try:
            out.append(max(float(row.get("viewers") or 0), 0.0))
        except (TypeError, ValueError):
            return None
    return out


def _pool(case):
    """(hour-1 print, release-day viewers) for every usable comparable."""
    pool = []
    for comp in case.get("comparables") or []:
        if "contaminated" in _tier(comp.get("unlock")):
            continue
        day = _release_day_viewers(comp)
        if day is None:
            continue
        hour1 = day[0]
        if hour1 < MIN_POOL_HOUR1:
            continue
        pool.append((hour1, day))
    return pool


def _smooth(values):
    """Three-hour moving average; launch-day curves are smooth, noise is not."""
    out = []
    for i in range(len(values)):
        lo = max(0, i - 1)
        hi = min(len(values), i + 2)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def _fit_shape(pool, hour1):
    """Per-hour (median log ratio, log spread) at this case's hour-1 print.

    Returns two lists of 23 numbers, for hours 2..24.  The fitted log
    ratios are clipped to a sane band (0.3x to 7.4x the hour-1 print):
    the regression is only ever fitted inside the comparables' range,
    and a final hour-1 print far outside it must not extrapolate the
    line into an absurd forecast.
    """
    scale = math.log10(max(hour1, 1.0) / REFERENCE)
    scale = max(SCALE_LOW, min(SCALE_HIGH, scale))
    medians = []
    spreads = []
    for hour in HOURS:
        idx = hour - 1
        xs = []
        ys = []
        for h1, day in pool:
            xs.append(math.log10(max(h1, 1.0) / REFERENCE))
            ys.append(math.log(max(day[idx], 1.0) / max(h1, 1.0)))
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        if denom > 0:
            slope = sum((x - mean_x) * (y - mean_y)
                        for x, y in zip(xs, ys)) / denom
        else:
            slope = 0.0
        slope = max(SLOPE_LOW, min(SLOPE_HIGH, slope))
        intercept = mean_y - slope * mean_x
        fitted = intercept + slope * scale
        medians.append(max(-1.2, min(1.9, fitted)))
        resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
        spreads.append(_pstdev(resid, sum(resid) / n) * SIGMA_SCALE)
    return _smooth(medians), spreads


def _fallback_shape(pool):
    """Pooled median log ratio per hour, used when the fit has too few points."""
    medians = []
    spreads = []
    for hour in HOURS:
        idx = hour - 1
        ratios = [math.log(max(day[idx], 1.0) / max(h1, 1.0))
                  for h1, day in pool]
        med = _median(ratios)
        medians.append(med)
        spreads.append(_pstdev(ratios, med) * SIGMA_SCALE)
    return _smooth(medians), spreads


def _baseline_rows(print1):
    """Persistence forecast: every hour stays at hour 1, spread widening."""
    rows = []
    for hour in HOURS:
        spread = 0.15 * math.sqrt(hour - 1)
        rows.append({
            "hour": hour,
            "q": [round(print1 * math.exp(z * spread), 2) for z in Z],
        })
    return rows


def _hour1_print(case):
    """The case's hour-1 print: the known row for hour 1, else the first."""
    known = case.get("known") or []
    row = None
    for candidate in known:
        if candidate.get("hour") == 1:
            row = candidate
            break
    if row is None and known:
        row = known[0]
    if row is None:
        return 1.0
    try:
        return max(float(row.get("viewers") or 0), 1.0)
    except (TypeError, ValueError):
        return 1.0


def forecast(case):
    print1 = _hour1_print(case)
    pool = _pool(case)
    if len(pool) >= 8:
        medians, spreads = _fit_shape(pool, print1)
    elif pool:
        medians, spreads = _fallback_shape(pool)
    else:
        return _baseline_rows(print1)
    rows = []
    for i, hour in enumerate(HOURS):
        spread = max(SIGMA_FLOOR, min(SIGMA_CAP, spreads[i]))
        quantiles = []
        for z in Z:
            value = print1 * math.exp(medians[i] + z * spread)
            value = max(1.0, min(1e9, value))
            quantiles.append(round(value, 2))
        # Rounding can only tie neighbours, never invert them, but be safe.
        for j in range(1, len(quantiles)):
            if quantiles[j] < quantiles[j - 1]:
                quantiles[j] = quantiles[j - 1]
        rows.append({"hour": hour, "q": quantiles})
    return rows


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    names = sorted(name for name in os.listdir(in_dir)
                   if name.endswith(".in"))
    for name in names:
        case_id = name[:-3]
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        try:
            rows = forecast(case)
        except Exception:
            # Never leave a case without an output: fall back to persistence.
            rows = _baseline_rows(_hour1_print(case))
        payload = json.dumps({"hours": rows}, separators=(",", ":"))
        with open(os.path.join(out_dir, case_id + ".out"),
                  "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
