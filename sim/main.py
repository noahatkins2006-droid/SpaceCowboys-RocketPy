"""
Bandit RocketPy flight reconstruction (for testing and validations purposes)
Target flight: 2026-06-17 18:55:53.485 UTC (13:55:53.485 CDT).

Weather source priority is handled by historical_weather.py. There is no
standard-atmosphere fallback this time.
"""

# HOW THIS SCRIPT WORKS (big picture)
# -----------------------------------
#   1. Describe the launch site and the exact liftoff time.
#   2. Download a real weather profile for that moment (historical_weather.py).
#   3. Build the motor (motors.py) and the Bandit rocket (geometry, mass, drag,
#      fins, parachutes) from the constants defined below.
#   4. Run RocketPy's 6-DOF flight simulation off a launch rail.
#   5. Print a summary in imperial units and export a KML + CSV of the flight.
#
# All constants below are in SI units (meters, kilograms, seconds, degrees)
# because that is what RocketPy expects. Only the printed results are converted
# to feet / mph for readability.

from datetime import datetime
from pathlib import Path
import zoneinfo
import warnings

import pandas as pd
# Rocket   - the vehicle definition (mass, geometry, drag, parachutes)
# Flight   - runs the trajectory simulation
# Function - RocketPy's interpolating 1-D/2-D function wrapper (used for drag)
from rocketpy import Rocket, Flight, Function
# Writes the finished flight to KML (Google Earth) and CSV files
from rocketpy.simulation import FlightDataExporter

# Local project modules (same folder as this file)
from motors import MotorLibrary
from historical_weather import setup_historical_environment

# Keep third-party compatibility warnings out of the normal run output.
warnings.filterwarnings("ignore", category=FutureWarning, module="cfgrib")


# ---------------------------------------------------------------------------
# Launch and flight-computer reference configuration
# ---------------------------------------------------------------------------

# Launch pad location.
SITE = {
    "name": "Midland Spaceport IREC Rocket Launch Area",
    "latitude": 31.0498056,
    "longitude": -103.5473056,
    "elevation_m": 880.87,  # pad elevation above sea level (m)
}

# Time zones: the flight computer logged local (Central) time, but weather
# archives and RocketPy work in UTC, so both are kept.
LOCAL_TZ = zoneinfo.ZoneInfo("America/Chicago")
UTC_TZ = zoneinfo.ZoneInfo("UTC")

# Exact liftoff time from the flight-computer summary.
# datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])
LAUNCH_LOCAL = datetime(2026, 6, 17, 13, 55, 53, 485000, tzinfo=LOCAL_TZ)
LAUNCH_UTC = LAUNCH_LOCAL.astimezone(UTC_TZ)

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

# Paths are built relative to this file, so the script works no matter which
# directory it is launched from.
#   <project>/sim/main.py      <- this file  (SIM_DIR)
#   <project>/data/...         <- input data (motor curves, drag, fin polars)
#   <project>/output/...       <- results written by export_results()
SIM_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SIM_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
ENGINE_DIR = DATA_DIR / "engine_files"
CD_DIR = DATA_DIR / "cd_data"
FIN_DIR = DATA_DIR / "fin_data"
OUTPUT_DIR = PROJECT_DIR / "output"

# Individual input files:
#   MOTOR_FILE   - AeroTech O5500X-PS thrust curve (.eng format)
#   DRAG_FILE    - drag coefficient vs. Mach exported from RAS
#   AIRFOIL_FILE - fin lift coefficient vs. angle of attack (degrees)
MOTOR_FILE = ENGINE_DIR / "AeroTech_O5500X-PS.eng"
DRAG_FILE = CD_DIR / "Bandit_OpenRocket_aero_vs_mach.csv"
AIRFOIL_FILE = FIN_DIR / "Fins_CL_Alpha.csv"

# ---------------------------------------------------------------------------
# Bandit physical configuration from the supplied OpenRocket/SolidWorks data
# ---------------------------------------------------------------------------

# Rocket body properties WITHOUT the motor (RocketPy adds the motor's own mass
# and inertia on top of these). Positions are measured from the nose tip,
# pointing toward the tail ("nose_to_tail" coordinate system).
ROCKET = {
    "radius_m": 0.15443 / 2,          # body-tube outer radius (diameter / 2)
    "dry_mass_kg": 14.668,            # mass with no motor installed
    "center_of_mass_m": 1.6568,       # CG of the dry rocket, from nose tip
    "inertia_11_kg_m2": 12.807,       # moment of inertia about a transverse axis
    "inertia_22_kg_m2": 12.807,       # same as above (rocket is axisymmetric)
    "inertia_33_kg_m2": 0.0700,       # moment of inertia about the roll (long) axis
    "length_m": 3.4814,               # overall length (documentation only)
}

# Where the motor's nozzle exit sits, measured from the nose tip. This equals
# the rocket's overall length because the nozzle is flush with the aft end.
MOTOR_POSITION_M = 3.4814

# Nose cone: a von Karman profile
NOSE = {
    "length_m": 0.8652,
    "kind": "von karman",
    "position_m": 0.0,                # the nose starts at the origin
}

# Boattail (tapered tail section that narrows toward the nozzle).
# It goes from the body radius down to a smaller aft radius over 0.127 m.
TAIL = {
    "top_radius_m": 0.15443 / 2,
    "bottom_radius_m": 0.10414 / 2,
    "length_m": 0.127,
    "position_m": 3.3544,             # start of the boattail, from nose tip
}

# Trapezoidal fin set. (fin mass is already inside the rocket's dry mass).
FINS = {
    "count": 4,
    "root_chord_m": 0.3048,           # fin length where it meets the body
    "tip_chord_m": 0.0762,            # fin length at the outer edge
    "span_m": 0.15875,                # how far the fin sticks out from the body
    "sweep_length_m": 0.3048,         # how far the tip is shifted aft of the root's leading edge
    "position_m": 2.9988,             # start of the fin root, from nose tip
}

# Launch rail setup.
RAIL = {
    "length_m": 5.1816,               # 17 ft rail
    "inclination_deg": 84.0,          # angle above horizontal (90 = straight up)
    "heading_deg": 90.0,              # compass direction of tilt (90 = east)
}

# Parachute properties. "cd_s" is drag coefficient x reference area (m^2),
# the single number that sets how much drag a parachute produces.
PARACHUTES = {
    "drogue_cd_s": 0.4378,
    "drogue_lag_s": 0.0,              # delay between the trigger and full deployment
    "main_cd_s": 2.860,
    "main_trigger_altitude_m_agl": 457.2,  # main deploys at 1,500 ft above ground
}


def require_file(path: Path, label: str) -> None:
    # when an input file is missing or misnamed.
    if not path.is_file():
        raise FileNotFoundError(
            f"Required {label} file was not found:\n{path}\n"
            "Check the project data folder and filenames."
        )


def setup_motor():
    # Confirm the thrust curve exists, then build the motor from the library.
    require_file(MOTOR_FILE, "AeroTech O5500X-PS motor")
    motor_library = MotorLibrary()
    return motor_library.O5500X(motor_file=str(MOTOR_FILE))


def load_drag_curves():
    frame = pd.read_csv(DRAG_FILE)

    # Make sure the three columns this script depends on are present.
    required = ["Mach", "CD_power_on", "CD_power_off"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(
            f"OpenRocket aerodynamic CSV is missing columns {missing}. "
            f"Available columns: {list(frame.columns)}"
        )

    # Build one drag-vs-Mach curve for powered flight and one for coasting.
    curves = {}
    for label, column in (("power_on", "CD_power_on"), ("power_off", "CD_power_off")):
        # Keep just Mach and this CD column, convert to numbers, and drop rows
        # with blanks (the first power-off row in the table is empty, for example).
        points = frame[["Mach", column]].copy()
        points = points.apply(pd.to_numeric, errors="coerce").dropna()
        # Interpolation needs strictly increasing Mach values with no duplicates. <-- Big important
        points = points.sort_values("Mach").drop_duplicates("Mach")
        # Sanity checks: enough points, and physically sensible (non-negative) values.
        if len(points) < 2:
            raise ValueError(f"Insufficient valid Mach data for {label} drag.")
        if (points["Mach"] < 0).any() or (points[column] < 0).any():
            raise ValueError(f"Negative Mach or drag coefficient in {label} data.")
        # Linear interpolation between table points. Outside the table's Mach
        # range (below 0.05 or above 1.95) the nearest end value is held
        # constant instead of extrapolating a trend.
        curves[label] = Function(
            points.to_numpy(),
            inputs="Mach",
            outputs="CD",
            interpolation="linear",
            extrapolation="constant",
        )

    return curves["power_on"], curves["power_off"]


def setup_rocket(engine) -> Rocket:
    # The fin lift polar must exist before RocketPy tries to read it.
    require_file(AIRFOIL_FILE, "fin airfoil polar")

    power_on_drag, power_off_drag = load_drag_curves()

    # Create the bare rocket (no motor, nose, tail, fins or parachutes yet).
    bandit = Rocket(
        radius=ROCKET["radius_m"],
        mass=ROCKET["dry_mass_kg"],
        inertia=(
            ROCKET["inertia_11_kg_m2"],
            ROCKET["inertia_22_kg_m2"],
            ROCKET["inertia_33_kg_m2"],
        ),
        center_of_mass_without_motor=ROCKET["center_of_mass_m"],
        # Positions are measured from the nose tip, increasing toward the tail.
        coordinate_system_orientation="nose_to_tail",
        power_off_drag=power_off_drag,
        power_on_drag=power_on_drag,
    )

    # Nozzle exit/aft end is at the rocket aft station, 3.4814 m from nose tip.
    bandit.add_motor(motor=engine, position=MOTOR_POSITION_M)

    # Nose cone
    bandit.add_nose(
        length=NOSE["length_m"],
        kind=NOSE["kind"],
        position=NOSE["position_m"],
    )

    # Boattail
    bandit.add_tail(
        top_radius=TAIL["top_radius_m"],
        bottom_radius=TAIL["bottom_radius_m"],
        length=TAIL["length_m"],
        position=TAIL["position_m"],
    )

    # Fins. The airfoil tuple is (CSV path, angle unit); the CSV gives lift
    # coefficient versus angle of attack for the fin cross-section.
    bandit.add_trapezoidal_fins(
        n=FINS["count"],
        root_chord=FINS["root_chord_m"],
        tip_chord=FINS["tip_chord_m"],
        span=FINS["span_m"],
        sweep_length=FINS["sweep_length_m"],
        position=FINS["position_m"],
        airfoil=(str(AIRFOIL_FILE), "degrees"),
    )

    # Drogue (small stabilizing chute): fires at apogee.
    # sampling_rate is how often (Hz) the simulated flight computer checks the
    # trigger. noise=(mean, standard deviation, time correlation) adds
    # realistic sensor noise to the pressure reading that the trigger sees.
    bandit.add_parachute(
        name="drogue",
        cd_s=PARACHUTES["drogue_cd_s"],
        trigger="apogee",
        sampling_rate=105,
        lag=PARACHUTES["drogue_lag_s"],
        noise=(0, 8.3, 0.5),
    )

    # Main (large landing chute): fires when the rocket descends through the
    # trigger altitude (a number means "meters above ground level").
    bandit.add_parachute(
        name="main",
        cd_s=PARACHUTES["main_cd_s"],
        trigger=PARACHUTES["main_trigger_altitude_m_agl"],
        sampling_rate=105,
        lag=0.0,
        noise=(0, 8.3, 0.5),
    )

    return bandit


def run_simulation(rocket: Rocket, environment) -> Flight:
    # Running the simulation happens inside the Flight constructor: it
    # integrates the 6-DOF equations of motion from the pad to impact.
    # Inclination is measured up from the horizontal; heading is the compass
    # bearing of the rail tilt.
    return Flight(
        rocket=rocket,
        environment=environment,
        rail_length=RAIL["length_m"],
        inclination=RAIL["inclination_deg"],
        heading=RAIL["heading_deg"],
    )


def print_results(flight: Flight) -> None:
    # Conversion factors from RocketPy's SI units to imperial units.
    m_to_ft = 3.280839895
    mps_to_fps = 3.280839895
    mps_to_mph = 2.236936292
    # RocketPy reports altitude above sea level; subtracting the pad elevation
    # gives altitude above ground level (AGL).
    environment_elevation_m = float(flight.env.elevation)

    # State vectors are laid out as [time, x, y, z, vx, vy, vz, ...], where x/y
    # are east/north displacement from the pad and z is altitude above sea level.
    apogee_state = flight.apogee_state
    impact_state = flight.impact_state

    # --- Apogee quantities ---
    apogee_agl_ft = (float(flight.apogee) - environment_elevation_m) * m_to_ft
    apogee_time_s = float(flight.apogee_time)
    apogee_velocity = apogee_state[4:7]  # (vx, vy, vz) at apogee
    # Horizontal speed uses the Pythagorean combination of vx and vy.
    apogee_horizontal_speed_fps = (
        (float(apogee_velocity[0]) ** 2 + float(apogee_velocity[1]) ** 2) ** 0.5
        * mps_to_fps
    )
    apogee_vertical_speed_fps = float(apogee_velocity[2]) * mps_to_fps
    # Straight-line ground distance from the pad to the point under apogee.
    apogee_drift_ft = (
        float(flight.apogee_x) ** 2 + float(flight.apogee_y) ** 2
    ) ** 0.5 * m_to_ft
    apogee_freestream_fps = float(flight.apogee_freestream_speed) * mps_to_fps
    apogee_mach = float(flight.mach_number(apogee_time_s))

    # --- Impact quantities ---
    impact_time_s = float(impact_state[0])
    impact_altitude_agl_ft = (float(impact_state[3]) - environment_elevation_m) * m_to_ft
    impact_velocity_fps = float(flight.impact_velocity) * mps_to_fps
    impact_vertical_speed_fps = float(impact_state[6]) * mps_to_fps
    impact_drift_ft = (
        float(flight.x_impact) ** 2 + float(flight.y_impact) ** 2
    ) ** 0.5 * m_to_ft

    # --- Whole-flight maxima ---
    max_speed_fps = float(flight.max_speed) * mps_to_fps
    # Acceleration is converted to "g" by dividing by standard gravity.
    max_accel_g = float(flight.max_acceleration) / 9.80665

    # --- Formatted report ---
    # In the format specs, ",.0f" means thousands separators and 0 decimals.
    print("\n" + "=" * 68)
    print("BANDIT SIMULATION RESULTS")
    print("=" * 68)
    print(f"Apogee:             {apogee_agl_ft:,.0f} ft AGL")
    print(f"Apogee time:        {apogee_time_s:.2f} s after liftoff")
    print(f"Maximum speed:      {max_speed_fps:,.1f} ft/s ({max_speed_fps*mps_to_mph:,.1f} mph)")
    print(f"Maximum Mach:       {float(flight.max_mach_number):.3f}")
    print(f"Maximum accel.:     {max_accel_g:.1f} g")
    print(f"Rail departure:     {float(flight.out_of_rail_velocity)*mps_to_fps:.1f} ft/s")

    print("\n--- Apogee details ---")
    print(f"Time to apogee:     {apogee_time_s:.2f} s")
    print(f"Altitude:           {apogee_agl_ft:,.0f} ft AGL")
    print(f"Freestream speed:   {apogee_freestream_fps:,.1f} ft/s ({apogee_freestream_fps*mps_to_mph:,.1f} mph)")
    print(f"Mach at apogee:     {apogee_mach:.3f}")
    print(f"Horizontal speed:   {apogee_horizontal_speed_fps:,.1f} ft/s")
    print(f"Vertical speed:     {apogee_vertical_speed_fps:,.1f} ft/s")
    print(f"Drift from pad:     {apogee_drift_ft:,.0f} ft")

    print("\n--- Landing / impact ---")
    print(f"Time of impact:     {impact_time_s:.2f} s after liftoff")
    print(f"Time after apogee:  {impact_time_s-apogee_time_s:.2f} s")
    print(f"Impact altitude:    {impact_altitude_agl_ft:,.1f} ft AGL")
    print(f"Impact speed:       {impact_velocity_fps:,.1f} ft/s ({impact_velocity_fps*mps_to_mph:,.1f} mph)")
    print(f"Vertical speed:     {impact_vertical_speed_fps:,.1f} ft/s")
    print(f"Landing drift:      {impact_drift_ft:,.0f} ft from pad")

    # Each recorded event is (time, parachute object); the parachute's name
    # ("drogue" / "main") is read defensively in case the object lacks one.
    print("\n--- Parachute events ---")
    if flight.parachute_events:
        for event in flight.parachute_events:
            event_time = float(event[0])
            parachute = event[1]
            parachute_name = getattr(parachute, "name", str(parachute))
            print(f"{parachute_name}: {event_time:.2f} s after liftoff")
    else:
        print("No parachute events were recorded.")
    print("=" * 68)


def export_results(flight: Flight) -> None:
    # Create the output folder on first run.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # File names carry the liftoff timestamp in UTC, e.g. 2026-06-17_185553_UTC.
    stamp = LAUNCH_UTC.strftime("%Y-%m-%d_%H%M%S_UTC")
    exporter = FlightDataExporter(flight)

    kml_path = OUTPUT_DIR / f"bandit_flight_{stamp}.kml"
    csv_path = OUTPUT_DIR / f"bandit_flight_{stamp}.csv"

    # KML opens in Google Earth. "extrude" draws a curtain from the path down to
    # the ground; "relativetoground" makes altitudes AGL instead of sea level.
    exporter.export_kml(
        file_name=str(kml_path),
        extrude=True,
        altitude_mode="relativetoground",
    )
    # CSV with the full time series of the simulated flight.
    exporter.export_data(str(csv_path))

    print(f"\nKML saved: {kml_path}")
    print(f"CSV saved: {csv_path}")


def main():
    # Banner and a summary of what is about to be simulated.
    print("=" * 68)
    print("SPACE COWBOYS - BANDIT HISTORICAL FLIGHT RECONSTRUCTION")
    print("=" * 68)
    print(f"Launch site: {SITE['name']}")
    print(f"Coordinates: {SITE['latitude']:.7f}, {SITE['longitude']:.7f}")
    print(f"Launch local: {LAUNCH_LOCAL.isoformat()}")
    print(f"Launch UTC:   {LAUNCH_UTC.isoformat()}")
    print(f"Pad elevation: {SITE['elevation_m'] * 3.280839895:,.1f} ft ASL")
    print()

    # Step 1: get the real atmosphere for this launch. The weather must be
    # valid at the top of the launch hour (18:00 UTC), i.e. at or before
    # liftoff, never from an hour after it.
    environment = setup_historical_environment(
        site={
            "lat": SITE["latitude"],
            "lon": SITE["longitude"],
            "elevation": SITE["elevation_m"],
        },
        launch_time=LAUNCH_UTC,
        elevation=SITE["elevation_m"],
        required_valid_time=LAUNCH_UTC.replace(minute=0, second=0, microsecond=0),
    )

    # Step 2: build the hardware, then fly it.
    motor = setup_motor()
    rocket = setup_rocket(motor)
    flight = run_simulation(rocket, environment)
    rocket.draw()

    # Step 3: report and save.
    print_results(flight)
    export_results(flight)

    print("\nSimulation finished.")
    return flight


# Only run when executed as a script (python main.py), not when imported.
if __name__ == "__main__":
    main()
