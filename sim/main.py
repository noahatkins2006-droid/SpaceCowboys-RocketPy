"""
Space Cowboys RocketPy Simulation System
Main simulation script for the Bandit research rocket.

Uses RocketPy 1.13.0+ built-in HRRR weather via THREDDS and
FlightDataExporter for KML/CSV output.
"""

from rocketpy import Environment, Rocket, Flight, Function
from rocketpy.simulation import FlightDataExporter
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import zoneinfo
import os
import sys

# Local imports
sys.path.insert(0, os.path.dirname(__file__))
from openrocket_parser import (
    set_openrocket_file,
    get_nosecone,
    get_boattail,
    get_finset,
    get_rocket,
    get_motor,
    get_railbutton,
    get_freeform_finset,
    get_parachute,
)
from motors import MotorLibrary
from conversions import Conversion

# ==============================================================================
# Configuration
# ==============================================================================

# Launch site coordinates (elevation in meters)
LAUNCH_SITES = {
    "TL1": {"lat": 33.50, "lon": -101.85, "elevation": 1005},       # Texas (TL1)
    "midland": {"lat": 31.04, "lon": -102.20, "elevation": 875},    # Midland TX
    "south_farm": {"lat": 33.40, "lon": -88.80, "elevation": 116},  # South Farm MS
    "spaceport": {"lat": 32.99, "lon": -106.98, "elevation": 1401}, # Spaceport America NM
    "IREC": {"lat": 31.0498, "lon": -103.5473, "elevation": 894},   # IREC 2026 - Midland Spaceport Launch Area, Saragosa TX (2933 ft)
}

# Select launch site
SITE = "midland"

# Override elevation here if needed (meters), or set to None to use default
ELEVATION_OVERRIDE = None  # e.g. 900 to override

# Target simulation date and time (local Central time) only up to 18 hrs ahead
TARGET_DATE = "2026-08-26"
TARGET_HOUR = "06:00:00"  # Local time (Central) — 11:00 UTC

# Timezone setup
LOCAL_TZ = zoneinfo.ZoneInfo("America/Chicago")
UTC_TZ = zoneinfo.ZoneInfo("UTC")

# ==============================================================================
# File Paths
# ==============================================================================

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
ENGINE_DIR = os.path.join(DATA_DIR, "engine_files")
CD_DIR = os.path.join(DATA_DIR, "cd_data")
ORK_DIR = os.path.join(DATA_DIR, "open_rocket")
FIN_DIR = os.path.join(DATA_DIR, "fin_data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Specific files
MOTOR_FILE = os.path.join(ENGINE_DIR, "AeroTech_O5500X-PS.eng")
DRAG_FILE = os.path.join(CD_DIR, "Bandit_Rough_Camo_4-30-2026_CD.CSV")
ORK_FILE = os.path.join(ORK_DIR, "Bandit_Average_1.ork")
AIRFOIL_FILE = os.path.join(FIN_DIR, "Fins_CL_Alpha.csv")


def setup_environment(site: dict, sim_datetime: datetime) -> Environment:
    """
    Set up the RocketPy Environment using built-in HRRR weather.
    
    RocketPy 1.13.0 natively supports HRRR via THREDDS - no external 
    weather libraries needed.
    """
    elevation = ELEVATION_OVERRIDE if ELEVATION_OVERRIDE is not None else site["elevation"]

    env = Environment(
        latitude=site["lat"],
        longitude=site["lon"],
        elevation=elevation,
        date=sim_datetime,
    )

    # Use RocketPy's built-in HRRR forecast via THREDDS
    try:
        env.set_atmospheric_model(type="forecast", file="HRRR")
        print("✓ HRRR weather data loaded successfully via THREDDS")
    except Exception as e:
        print(f"⚠ HRRR unavailable ({e}), falling back to GFS...")
        try:
            env.set_atmospheric_model(type="forecast", file="GFS")
            print("✓ GFS weather data loaded successfully")
        except Exception as e2:
            print(f"⚠ GFS also unavailable ({e2}), using standard atmosphere")
            env.set_atmospheric_model(type="standard_atmosphere")
            print("✓ Standard atmosphere loaded (no live weather)")

    # Print weather debug info
    print(f"\n--- Weather Debug ---")
    print(f"  Elevation:      {elevation:.0f} m ({elevation * 3.28084:.0f} ft)")
    print(f"  Temperature:    {env.temperature(elevation):.1f} K ({(env.temperature(elevation) - 273.15) * 9/5 + 32:.1f} °F)")
    print(f"  Pressure:       {env.pressure(elevation):.0f} Pa ({env.pressure(elevation) / 6894.76:.2f} psi)")
    print(f"  Air Density:    {env.density(elevation):.4f} kg/m³")
    print(f"  Speed of Sound: {env.speed_of_sound(elevation):.1f} m/s ({env.speed_of_sound(elevation) * 3.28084:.0f} ft/s)")
    print(f"  Wind (surface): {env.wind_speed(elevation):.1f} m/s ({env.wind_speed(elevation) * 2.237:.1f} mph) @ {env.wind_direction(elevation):.0f}°")
    print(f"---------------------\n")

    return env


def setup_motor() -> object:
    """Set up the O5500X-PS motor using the motor library."""
    motors = MotorLibrary()
    engine = motors.O5500X(motor_file=MOTOR_FILE)
    return engine


def setup_rocket(engine) -> Rocket:
    """
    Set up the Bandit rocket with all aerodynamic surfaces and parachutes.
    """
    # Load drag curves as RocketPy Function objects (Mach vs CD)
    drag_df = pd.read_csv(DRAG_FILE)
    on_drag = Function(
        drag_df[["Mach", "CD Power-On"]].to_numpy(),
        inputs="Mach",
        outputs="CD",
        interpolation="linear",
    )
    off_drag = Function(
        drag_df[["Mach", "CD Power-Off"]].to_numpy(),
        inputs="Mach",
        outputs="CD",
        interpolation="linear",
    )

    # Build rocket
    bandit = Rocket(
        radius=0.154 / 2,
        mass=12.622,
        inertia=(20.8, 20.8, 0.1),  # FIXME: Get from SolidWorks model
        center_of_mass_without_motor=1.68,
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
    )

    # Add motor
    bandit.add_motor(motor=engine, position=3.52)

    # Nosecone
    bandit.add_nose(
        length=0.865,
        kind="lvhaack",
        position=0,
    )

    # Boattail
    bandit.add_tail(
        top_radius=0.154 / 2,
        bottom_radius=0.104 / 2,
        length=0.127,
        position=3.3354,
    )

    # Fins
    bandit.add_trapezoidal_fins(
        n=4,
        root_chord=0.305,
        tip_chord=0.0762,
        span=0.159,
        sweep_length=0.305,
        position=2.999,
        airfoil=(AIRFOIL_FILE, "degrees"),
    )

    # Drogue parachute
    bandit.add_parachute(
        name="drogue",
        cd_s=0.437795262,
        trigger="apogee",
        sampling_rate=105,
        lag=3.0,
        noise=(0, 8.3, 0.5),
    )

    # Main parachute
    bandit.add_parachute(
        name="main",
        cd_s=7.865,
        trigger=457.2,
        sampling_rate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    return bandit


def run_simulation(rocket: Rocket, env: Environment) -> Flight:
    """Run the flight simulation."""
    flight = Flight(
        rocket=rocket,
        environment=env,
        rail_length=5.1816,
        inclination=86,
        heading=0,
    )

    return flight


def print_results(flight: Flight):
    """Print key flight results in imperial units."""
    M_TO_FT = 3.28084
    MPS_TO_FPS = 3.28084

    apogee_ft = (flight.apogee - flight.env.elevation) * M_TO_FT
    max_vel_fps = flight.max_speed * MPS_TO_FPS
    max_accel_g = flight.max_acceleration / 9.81
    burnout_alt_ft = (flight.out_of_rail_state[2] if hasattr(flight, 'out_of_rail_state') else 0)

    print("\n" + "=" * 60)
    print("FLIGHT RESULTS (Imperial)")
    print("=" * 60)
    print(f"\n  Apogee:            {apogee_ft:.0f} ft AGL")
    print(f"  Max Speed:         {max_vel_fps:.0f} ft/s ({flight.max_speed:.1f} m/s | Mach {flight.max_mach_number:.2f})")
    print(f"  Max Acceleration:  {max_accel_g:.1f} G")
    print(f"  Apogee Time:       {flight.apogee_time:.2f} s")
    print(f"  Rail Departure V:  {flight.out_of_rail_velocity * MPS_TO_FPS:.1f} ft/s ({flight.out_of_rail_velocity:.1f} m/s)")
    print()
    flight.prints.apogee_conditions()
    flight.prints.events_registered()
    flight.prints.impact_conditions()


def export_results(flight: Flight, sim_datetime: datetime):
    """
    Export flight data to KML and CSV using RocketPy's built-in exporter.
    Replaces the old custom flight_csv tool.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    date_str = sim_datetime.strftime("%Y-%m-%d_%H")
    exporter = FlightDataExporter(flight)

    # Export KML for Google Earth visualization
    kml_file = os.path.join(OUTPUT_DIR, f"bandit_flight_{date_str}.kml")
    exporter.export_kml(file_name=kml_file, extrude=True, altitude_mode="relativetoground")
    print(f"\n✓ KML exported: {kml_file}")

    # Export CSV with key flight data
    csv_file = os.path.join(OUTPUT_DIR, f"bandit_flight_{date_str}.csv")
    exporter.export_data(csv_file)
    print(f"✓ CSV exported: {csv_file}")


# ==============================================================================
# Main Execution
# ==============================================================================

def main():
    print("=" * 60)
    print("Space Cowboys RocketPy Simulation System")
    print("Bandit Research Rocket - RocketPy 1.13.0")
    print("=" * 60)

    # Convert local time to UTC for weather data
    local_time_str = f"{TARGET_DATE} {TARGET_HOUR}"
    local_dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S")
    local_dt = local_dt.replace(tzinfo=LOCAL_TZ)
    utc_dt = local_dt.astimezone(UTC_TZ)

    print(f"\nLaunch Site: {SITE}")
    print(f"Simulated Time (Local): {local_time_str} CT")
    print(f"Simulated Time (UTC):   {utc_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Setup
    site = LAUNCH_SITES[SITE]
    env = setup_environment(site, utc_dt)
    engine = setup_motor()
    bandit = setup_rocket(engine)

    # Run
    flight = run_simulation(bandit, env)

    # Results
    print_results(flight)
    export_results(flight, utc_dt)

    print("\n✓ Simulation complete!")
    return flight


if __name__ == "__main__":
    flight = main()
