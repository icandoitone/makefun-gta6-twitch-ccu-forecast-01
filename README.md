# makefun-gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/icandoitone/makefun-gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/icandoitone/makefun-gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A launch-day Twitch forecaster for Grand Theft Auto VI: a single standard-library Python program that reads a case's hour-1 viewer print and its comparable past launches, then forecasts hours 2–24 as five quantiles each. For every comparable launch it takes the release-day hourly viewers as log-ratios to that launch's hour-1 print, and per hour fits log-ratio against log10(hour-1 / 100k) — big launches whose hour 1 is already huge stay flat, small hour-1 launches climb steeply as the US wakes up and unlocks — reading the line off at the case's own hour-1 print, with the fit's residual spread as the forecast bands; early-access-contaminated launches are excluded, the shape is smoothed across hours, and the output is fully deterministic.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=1xb9yrrs&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
