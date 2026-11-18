# Space Cowboys RocketPy Simulation

6-DOF trajectory simulation for the **Bandit** research rocket, built on [RocketPy 1.13.0](https://docs.rocketpy.org/).

The current `main.py` reconstructs Bandit's **June 17, 2026 flight** at the Midland Spaceport IREC launch area (liftoff 13:55:53.485 CDT / 18:55:53.485 UTC), driving the simulation with real weather from the moment of launch so the results can be validated against the flight-computer data.

## Features

- **Real historical weather**: HRRR analysis (3 km) with automatic fallback to ERA5. There is deliberately **no standard-atmosphere fallback**, so a simulation never runs on made-up weather.
- **Validated inputs**: every weather profile is checked for completeness, units and physical plausibility before it is used.
- **Measured Bandit configuration**: mass, CG, inertia, geometry and parachutes come from the OpenRocket / SolidWorks data.
- **OpenRocket drag data**: power-on and power-off drag curves versus Mach number, with a built-in copy of the table if the CSV is missing.
- **Motor library**: AeroTech O5500X-PS (Bandit's motor), M1340W, HP-H195NT, J450DM and J800T.
- **Clear results**: apogee, speeds, Mach, acceleration, drift, impact conditions and parachute events printed in imperial units.
- **Google Earth export**: KML trajectory plus a full CSV of the simulated flight.
- **OpenRocket parser**: standalone utility that reads `.ork` design files (see below).

## Project Structure

```
SpaceCowboys-RocketPy/
├── sim/
│   ├── main.py                # Bandit configuration, simulation and reporting
│   ├── historical_weather.py  # HRRR / ERA5 weather download and validation
│   ├── motors.py              # Pre-configured motor library
│   ├── conversions.py         # Imperial -> metric unit helpers
│   ├── openrocket_parser.py   # .ork file parser (standalone utility)
│   └── __init__.py
├── data/
│   ├── engine_files/          # Motor thrust curves (.eng)
│   ├── cd_data/               # Drag coefficient tables
│   ├── fin_data/              # Fin lift coefficient vs. angle of attack
│   └── open_rocket/           # OpenRocket design files (.ork)
├── output/                    # Created on first run (KML + CSV results)
├── requirements.txt
├── README.md
└── CHANGELOG.md
```

## Quick Start

```bash
# 1. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the Bandit reconstruction
cd sim
python main.py
```

**Requirements**

- Python 3.10 or newer
- An internet connection (weather data is downloaded on every run and is not cached)
- For the ERA5 fallback only: a free [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/) account and API key saved in `~/.cdsapirc`. Most runs succeed with HRRR and never touch this.

## What You Get

A run prints the launch-site weather and a results summary, then writes two files to `output/`:

| File | Contents |
|------|----------|
| `bandit_flight_<UTC timestamp>.kml` | 3-D flight path for Google Earth |
| `bandit_flight_<UTC timestamp>.csv` | Full time series of the simulated flight |

The summary reports apogee (ft AGL), max speed and Mach, max acceleration, rail departure speed, apogee and landing drift, impact speed, and the time of each parachute event.

## Configuration

Everything is set by the constants at the top of `sim/main.py`:

| Constant | What it controls |
|----------|------------------|
| `SITE` | Launch pad name, latitude, longitude and elevation |
| `LAUNCH_LOCAL` | Exact liftoff time (timezone-aware); UTC is derived automatically |
| `ROCKET`, `NOSE`, `TAIL`, `FINS` | Mass, inertia, CG and geometry |
| `MOTOR_POSITION_M`, `MOTOR_FILE` | Where the motor sits and which thrust curve it uses |
| `RAIL` | Rail length, inclination and heading |
| `PARACHUTES` | Drogue / main CdS, lag and main deployment altitude |
| `DRAG_FILE`, `AIRFOIL_FILE` | Drag table and fin lift polar |

All values are in SI units (meters, kilograms, degrees). To use a different motor, call another method of `MotorLibrary` in `setup_motor()`.

## Weather Pipeline

`historical_weather.py` tries these sources in order and uses the first one that returns a valid profile:

1. **Live HRRR**: only if the launch time is within the live window (up to 3 hours ago, or up to 18 hours ahead).
2. **Archived HRRR analysis (F00)** for the hour containing liftoff. This is the normal path for past flights.
3. **ERA5 reanalysis** for the same hour.

The weather used is always valid at the **top of the launch hour (18:00 UTC for the Bandit flight)**, never from after liftoff. Each profile gets a ground-level data point at the pad's own elevation (pressure is corrected hydrostatically from the model terrain height) and must pass checks for finite values, increasing altitude, plausible temperatures and a top above 10 km. If every source fails, the run stops with a message listing why each one failed.

## OpenRocket Parser

`sim/openrocket_parser.py` reads `.ork` files (ZIP archives containing XML) and returns geometry, mass properties, motor data and parachute settings in SI units:

```python
import openrocket_parser as ork

ork.set_openrocket_file("../data/open_rocket/Bandit_Average_1.ork")
ork.get_rocket("mass")           # kg
ork.get_finset("span")           # m
ork.get_parachute("deployment")  # 'apogee' or an altitude in m
```

The Bandit reconstruction in `main.py` uses fixed, measured values instead of the parser. The `.ork` file must have been saved with simulation data for mass, CG and inertia to be available.

## Troubleshooting

| Problem | Likely fix |
|---------|-----------|
| `Required ... file was not found` | Check that the `data/` folder is next to `sim/` and the filenames match |
| `Could not load a valid real-weather profile` | Read the listed reasons. Usually no internet, or HRRR/ERA5 unavailable for that hour. For ERA5, confirm `~/.cdsapirc` exists |
| cfgrib / eccodes errors on install | Reinstall in a clean virtual environment; on some systems `conda install -c conda-forge eccodes` is easiest |
| `zoneinfo` cannot find `America/Chicago` (Windows) | `pip install tzdata` (already in `requirements.txt`) |

## Team

Mississippi State University - Space Cowboys Rocketry