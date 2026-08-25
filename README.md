# Space Cowboys RocketPy Simulation

6-DOF trajectory simulation system for the **Bandit** research rocket, built on [RocketPy 1.13.0](https://rocketpy.org/).

## Features

- **Real HRRR Weather**: Uses RocketPy's built-in HRRR forecast via THREDDS (2.5 km resolution, hourly updates)
- **OpenRocket Integration**: Automatically parses .ork files for rocket geometry, mass, CG, and inertia
- **Pre-configured Motors**: O5500X-PS, M1340W, H195NT, J450DM, J800T with validated parameters
- **Google Earth Export**: KML trajectory visualization via built-in FlightDataExporter
- **RASAero Drag Data**: Imports power-on/off drag curves from RASAero II CSV exports

## Project Structure

```
SpaceCowboys-RocketPy/
├── sim/
│   ├── main.py              # Main simulation script
│   ├── openrocket_parser.py # OpenRocket .ork file parser
│   ├── motors.py            # Motor library (pre-configured)
│   └── conversions.py       # Unit conversion utilities
├── data/
│   ├── engine_files/        # Motor thrust curves (.eng)
│   ├── cd_data/             # Drag coefficient CSVs from RASAero
│   ├── fin_data/            # Fin aerodynamic data
│   └── open_rocket/         # Rocket design files (.ork)
├── output/                  # Simulation output (KML, CSV)
├── requirements.txt         # Python dependencies (6 packages)
└── README.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Bandit simulation
cd sim
python main.py
```

## Configuration

Edit `sim/main.py` to change:

- **Launch site**: Set `SITE` to `"TL1"`, `"midland"`, `"south_farm"`, or `"spaceport"`
- **Date/time**: Set `TARGET_DATE` and `TARGET_HOUR`
- **Drag curves**: Change `DRAG_FILE` to use different surface finish data
- **Rocket design**: Change `ORK_FILE` to use a different OpenRocket design

## Weather Models

RocketPy 1.13.0 supports multiple weather sources out of the box:

| Model | Coverage | Resolution | Update Frequency |
|-------|----------|------------|------------------|
| **HRRR** (default) | North America | 2.5 km | Hourly |
| GFS | Global | 0.25° | Every 6 hours |
| NAM | North America | 5 km | Every 6 hours |
| RAP | North America | 13 km | Hourly |
| ECMWF (via Windy) | Global | 9 km | Every 12 hours |

The simulation automatically falls back to GFS → standard atmosphere if HRRR is unavailable.

## Dependencies

Only **6 packages** required:

- `rocketpy` - Core 6-DOF simulation with built-in weather & export
- `numpy` - Numerical computing
- `pandas` - CSV data handling
- `beautifulsoup4` + `lxml` - OpenRocket XML parsing
- `matplotlib` - Plotting (optional)

## Team

Mississippi State University - Space Cowboys Rocketry
