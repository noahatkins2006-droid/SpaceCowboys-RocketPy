## -- Main Research Rocket Script For Simulations -- ##
#####################
## -- Libraries    --##
#####################
from rocketpy import Environment, SolidMotor, Rocket, Flight, MonteCarlo
from rocketpy.stochastic import (
    StochasticEnvironment, StochasticFlight, StochasticModel,
    StochasticNoseCone, StochasticParachute, StochasticRailButtons,
    StochasticRocket, StochasticSolidMotor, StochasticTail, StochasticTrapezoidalFins,
)
import numpy as np
from datetime import datetime
import zoneinfo, sys, os, pandas as pd, datetime as dt
import matplotlib.pyplot as plt
from scipy.optimize import brentq

## --- Home Brewed Scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from conversion.conversion_tool import Conversion
from weather.weather_tool import SpaceWeather
from file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path, get_fin_path
from conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor, get_railbutton
from motors.motor_collection import motorClass
from tools.flight_csv.flight_csv import export_for_visualizer

C     = Conversion()
sw    = SpaceWeather()
motor = motorClass()

##################################
## ---- Configuration        ----##
## ---- Edit values below    ----##
##################################

TARGET_DATE   = "2026-06-17"        # Local date of launch (YYYY-MM-DD)
LAUNCH_HOUR   = "19:00:00"          # Local launch time (HH:MM:SS, 24hr, Central)
HRRR_FXX      = 1                   # Forecast offset: 0=analysis, 1=1hr forecast
LOCATION      = "midland"           # "midland", "tl1", or "sf"
ELEVATION_M   = 880.87              # Pad elevation in meters (2890 ft)

MOTOR_FILE    = "AeroTech_O5500X-PS.eng"
DRAG_FILE     = "Bandit_Rough_Camo_4-30-2026_CD.CSV"
ORK_FILE      = "Bandit TL1(PreAssembly).ork"    # Must have sim data attached
AIRFOIL_FILE  = "Fins_CL_Alpha.csv"
MOTOR_CONFIG  = 0

# Rocket parameters
ROCKET_MASS   = 12.622              # kg (dry mass without motor)
ROCKET_RADIUS = 0.154 / 2          # m
ROCKET_INERTIA = (20.8, 20.8, 0.1) # (I11, I22, I33) kg*m^2
CG_WITHOUT_MOTOR = 1.68            # m from nose

# Known real apogee for CD calibration — disabled, sim calculates apogee freely
REAL_APOGEE_FT = None

##################################
## ---- File Paths           ----##
##################################

motor_file   = get_motor_path(MOTOR_FILE)
drag_path    = get_drag_path(DRAG_FILE)
ork_file     = get_ork_path(ORK_FILE)
airfoil_path = get_fin_path(AIRFOIL_FILE)

on_drag_raw  = pd.read_csv(drag_path, usecols=["Mach", "CD Power-On"]).to_numpy()
off_drag_raw = pd.read_csv(drag_path, usecols=["Mach", "CD Power-Off"]).to_numpy()

set_openrocket_file(ork_file, MOTOR_CONFIG)

##################################
## ---- Location Setup       ----##
##################################

location_map = {
    "midland": (sw.mid_lat, sw.mid_lon),
    "tl1":     (sw.tl_lat,  sw.tl_lon),
    "sf":      (sw.sf_lat,  sw.sf_lon),
}
lat, lon = location_map[LOCATION.lower()]

##################################
## ---- Time Setup           ----##
##################################

local_tz = zoneinfo.ZoneInfo("America/Chicago")
utc_tz   = zoneinfo.ZoneInfo("UTC")

local_dt    = datetime.strptime(f"{TARGET_DATE} {LAUNCH_HOUR}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=local_tz)
utc_dt      = local_dt.astimezone(utc_tz)
hrrr_utc_str = utc_dt.strftime("%Y-%m-%d %H:%M:%S")

print("=" * 50)
print("  Space Cowboys RocketPy System: Research Rocket")
print("=" * 50)
print(f"  Launch Date/Time (Local): {TARGET_DATE} {LAUNCH_HOUR}")
print(f"  Launch Date/Time (UTC):   {hrrr_utc_str}")
print(f"  Location: {LOCATION.upper()} | Elevation: {ELEVATION_M:.1f} m ({ELEVATION_M*3.28084:.0f} ft)")
print("=" * 50)

##################################
## ---- Weather / Environment ----##
##################################

try:
    sw.hrrr_download(launch_time_str=hrrr_utc_str, fxx=HRRR_FXX, save_folder=r"data\weather_data")
except Exception as e:
    print(f"HRRR download failed: {e}")
    sys.exit(1)

env = sw.to_env(
    latitude=lat,
    longitude=lon,
    altitudes_m=np.arange(0, 15000, 1),
    max_height=80000,
    elevation=ELEVATION_M,
)

##################################
## ---- Motor               ----##
##################################

engine = motor.O5500x(motor_file=motor_file)

##################################
## ---- CD Scale Solver      ----##
##################################

def scale_drag(raw, k):
    s = raw.copy(); s[:, 1] *= k; return s

def build_and_fly(cd_scale):
    _on  = scale_drag(on_drag_raw, cd_scale)
    _off = scale_drag(off_drag_raw, cd_scale)
    rkt = Rocket(
        radius=ROCKET_RADIUS, mass=ROCKET_MASS, inertia=ROCKET_INERTIA,
        center_of_mass_without_motor=CG_WITHOUT_MOTOR,
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=_on, power_off_drag=_off,
    )
    rkt.add_motor(motor=engine, position=3.52)
    rkt.add_nose(length=0.865, kind="lvhaack", position=0)
    rkt.add_tail(top_radius=0.154/2, bottom_radius=0.104/2, length=0.127, position=3.3354)
    rkt.add_trapezoidal_fins(n=4, root_chord=.305, tip_chord=.0762, span=0.159,
                              sweep_length=.305, position=2.999, airfoil=(airfoil_path, "degrees"))
    rkt.add_parachute(name="drogue", cd_s=0.437795262, trigger="apogee",
                       sampling_rate=105, lag=3.0, noise=(0, 8.3, 0.5))
    rkt.add_parachute(name="main", cd_s=7.865, trigger=457.2,
                       sampling_rate=105, lag=1.5, noise=(0, 8.3, 0.5))
    flt = Flight(rocket=rkt, environment=env, rail_length=5.1816, inclination=86, heading=0)
    return rkt, flt

if REAL_APOGEE_FT is not None:
    real_apogee_m = REAL_APOGEE_FT / 3.28084
    print(f"\nSolving CD scale to match {REAL_APOGEE_FT} ft apogee...")
    cd_scale = brentq(lambda k: build_and_fly(k)[1].apogee - real_apogee_m, 0.5, 3.0, xtol=1e-3)
    print(f"  CD scale factor: {cd_scale:.4f}")
else:
    cd_scale = 1.0

on_drag  = scale_drag(on_drag_raw,  cd_scale)
off_drag = scale_drag(off_drag_raw, cd_scale)

##################################
## ---- Build Final Rocket   ----##
##################################

Frankenstein = Rocket(
    radius=ROCKET_RADIUS,
    mass=ROCKET_MASS,
    inertia=ROCKET_INERTIA,
    center_of_mass_without_motor=CG_WITHOUT_MOTOR,
    coordinate_system_orientation="nose_to_tail",
    power_on_drag=on_drag,
    power_off_drag=off_drag,
)

Frankenstein.add_motor(motor=engine, position=3.52)

nose_cone = Frankenstein.add_nose(length=0.865, kind="lvhaack", position=0)

boat_tail = Frankenstein.add_tail(
    top_radius=0.154/2, bottom_radius=0.104/2, length=0.127, position=3.3354
)

# rail_buttons = Frankenstein.set_rail_buttons(
#     upper_button_position=1.95, lower_button_position=3.30, angular_position=45,
# )

finset = Frankenstein.add_trapezoidal_fins(
    n=4, root_chord=.305, tip_chord=.0762, span=0.159,
    sweep_length=.305, position=2.999, airfoil=(airfoil_path, "degrees")
)

drogue_parachute = Frankenstein.add_parachute(
    name="drogue", cd_s=0.437795262, trigger="apogee",
    sampling_rate=105, lag=3.0, noise=(0, 8.3, 0.5)
)

main_parachute = Frankenstein.add_parachute(
    name="main", cd_s=7.865, trigger=457.2,
    sampling_rate=105, lag=1.5, noise=(0, 8.3, 0.5)
)

##################################
## ---- Flight              ----##
##################################

test_flight = Flight(
    rocket=Frankenstein,
    environment=env,
    rail_length=5.1816,
    inclination=86,
    heading=0,
)

test_flight.post_process()

##################################
## ---- Results             ----##
##################################

M_TO_FT  = 3.28084
MS_TO_MPH = 2.23694

print(f"\n{'='*50}")
print("  FLIGHT RESULTS")
print(f"{'='*50}")

# Surface conditions
sfc_wind_mph = np.sqrt(sw._sfc_u**2 + sw._sfc_v**2) * MS_TO_MPH
sfc_wind_dir = (270 - np.degrees(np.arctan2(sw._sfc_v, sw._sfc_u))) % 360
sfc_temp_f   = (sw._sfc_temp - 273.15) * 9/5 + 32
sfc_pres_inhg = sw._sfc_pressure / 3386.389

print(f"  Surface Temperature:  {sfc_temp_f:.1f} °F")
print(f"  Surface Pressure:     {sfc_pres_inhg:.2f} inHg (station)")
print(f"  Surface Wind:         {sfc_wind_mph:.1f} mph @ {sfc_wind_dir:.0f}°")

print(f"\n  -- Rail --")
test_flight.prints.launch_rail_conditions()

print(f"\n  -- Burnout --")
test_flight.prints.burn_out_conditions()

print(f"\n  -- Apogee --")
apogee_ft   = test_flight.apogee * M_TO_FT
apogee_time = test_flight.apogee_time
print(f"  Apogee:               {apogee_ft:.1f} ft  ({test_flight.apogee:.1f} m)")
print(f"  Time to Apogee:       {apogee_time:.1f} s")
test_flight.prints.apogee_conditions()

print(f"\n  -- Parachutes --")
test_flight.prints.events_registered()

print(f"\n  -- Impact --")
test_flight.prints.impact_conditions()

print(f"\n  -- Max Values --")
test_flight.prints.maximum_values()

print(f"{'='*50}\n")

# Export flight path for Google Earth / visualizer
kml_out = f"{os.path.abspath(os.path.dirname(__file__))}/googleEarth/bandit_sim_flight_{dt.date.today()}_{LAUNCH_HOUR.split(':')[0]}_animated.kml"
export_for_visualizer(
    test_flight,
    filename=f"{os.path.abspath(os.path.dirname(__file__))}/googleEarth/bandit_sim_flight_{dt.date.today()}_{LAUNCH_HOUR.split(':')[0]}.csv",
    pitch_mode="rocketpy"
)

##################################
## ---- Altitude Graph       ----##
##################################

times = np.array([t for t, _ in test_flight.z.source])
alts_ft = np.array([a * M_TO_FT for _, a in test_flight.z.source])

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(times, alts_ft, color="#0078d4", linewidth=2)
ax.axhline(apogee_ft, color="red", linestyle="--", linewidth=1, label=f"Apogee: {apogee_ft:.0f} ft")
ax.axvline(apogee_time, color="orange", linestyle="--", linewidth=1, label=f"T+{apogee_time:.1f}s")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Altitude (ft)")
ax.set_title(f"Bandit Flight — {TARGET_DATE} {LAUNCH_HOUR}  |  Apogee: {apogee_ft:.0f} ft")
ax.legend()
ax.grid(True, alpha=0.3)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}'))
ax.ticklabel_format(useOffset=False, style='plain')
plt.tight_layout()
plt.show()

##################################
## ---- Google Earth KML path ----##
##################################

ge_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "googleEarth")
kml_files = sorted([f for f in os.listdir(ge_dir) if f.endswith(".kml")], reverse=True)
if kml_files:
    latest_kml = os.path.join(ge_dir, kml_files[0])
    print(f"LATEST_KML={latest_kml}")   # GUI picks this up to enable the button
