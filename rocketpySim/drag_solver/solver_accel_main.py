## -- Main Drag Solver Script For Simulations -- ##
#####################
## -- Libraries -- ##
#####################
from rocketpy import Environment, SolidMotor, Rocket, Flight, MonteCarlo
from rocketpy.stochastic import (StochasticEnvironment,
    StochasticFlight,
    StochasticModel,
    StochasticNoseCone,
    StochasticParachute,
    StochasticRailButtons,
    StochasticRocket,
    StochasticSolidMotor,
    StochasticTail,
    StochasticTrapezoidalFins,
)
from scipy import optimize, interpolate
from scipy.optimize import brentq, minimize_scalar
import numpy as np
from datetime import datetime
import sys
import os
import pandas as pd
import datetime as dt
from solver import TimeBasedAcceleration
from pathlib import Path

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Opening whole directory


from conversion.conversion_tool import Conversion
from weather.weather_tool import SpaceWeather 
from file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path
from conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket
from drag_solver.solver_functions import rocketSim

C = Conversion()
sw = SpaceWeather()



##################################
##------------------------------##
## ---- Dynamic File Paths ---- ##
##------------------------------##
##################################

motor_file = get_motor_path("AeroTech_O5500X-PS.eng")
# print(os.path.exists(motor_file))

on_drag = get_drag_path("CD_Power_On_Frank.CSV")
# print(os.path.exists(on_drag))

off_drag = get_drag_path("CD_Power_Off_Frank.CSV")
# print(os.path.exists(off_drag))

ork_file = get_ork_path("helios_jun7_irec.ork")
# print(os.path.exists(ork_file))

weather_file = sw.hrrr_download(
        
        launch_time_str=f"2025-06-09 14:00:00",
        fxx=0,
        save_folder=r"data\weather_data",
        )

env = sw.to_env(
        latitude=sw.mid_lat, # latitude calling the sw class
        longitude=sw.mid_lon, # longitude calling the sw class
        altitudes_m=None,
        max_height=C.FT_to_Meters(variable=38000),   # max simulated height in feet
        )

# --- Measured data ---
real_apogee = 2808.485  # meters


base_df_off = pd.read_csv(off_drag)
base_df_on = pd.read_csv(on_drag)


def f(x,startTime,endTime,lowerdrag,upperdrag):
    df_off_drag = base_df_off.copy()
    df_on_drag = base_df_on.copy()
    mask = (df_off_drag['Mach'] >= lowerdrag) & (df_off_drag['Mach'] <= upperdrag)
    df_off_drag.loc[mask, 'CD Power-Off'] = df_off_drag.loc[mask, 'CD Power-Off'] + x
    apogee, accel_df, alt_df, vel_df, powerOnMax_time, powerOffMax_time, apogee_time = rocketSim(
        motor_file, 
        df_on_drag[['Mach', 'CD Power-On']].to_numpy(), 
        df_off_drag[['Mach', 'CD Power-Off']].to_numpy(), 
        ork_file, 
        env)
    accel_data = TimeBasedAcceleration(open((Path(__file__).resolve().parent/"helios_solver_data"/"helios_time_x_acceleration.csv").resolve(),"r"), accel_df)
    total_deviation = accel_data.get_total_deviation(startTime,endTime)
    abs_deviation = accel_data.get_absolute_deviation(startTime,endTime)
    print("total deviation:", total_deviation)
    print("abs deviation:", abs_deviation)
    print("scale", x)
    return(abs_deviation)

# Solve for drag scale
def solve_off_drag(startTime,endTime,lowerdrag,upperdrag,lowerBound=-0.5, upperBound=0.15):
    scale_solution = minimize_scalar(f, bounds=(lowerBound, upperBound),args=(startTime,endTime,lowerdrag,upperdrag),tol=1e-1, method="bounded")  # search range for Cd multiplier
    print(f"Best-fit drag scale = {scale_solution.x:.3f}")
    return(scale_solution.x)

# def editdrag(starttime,endtime,on_drag_path,off_drag_path):
#     dragsolution = solve_drag(starttime,endtime)
#     apogee, accel_df, alt_df, vel_df, powerOnMax_time, powerOffMax_time, apogee_time = rocketSim(motor_file, on_drag, off_drag, ork_file, "06:00:00", dragsolution)
#     accel_data = TimeBasedAcceleration(open((Path(__file__).resolve().parent/"helios_solver_data"/"helios_time_x_acceleration.csv").resolve(),"r"), accel_df)
#     data_mask = accel_data.get_mask(starttime,endtime)
#     drag_on = pd.read_csv(on_drag_path)
#     drag_off = pd.read_csv(off_drag_path)
#     for index, row in data_mask.iterrows():
#         machnumber = row['Mach Number']
#         time = row['Time (s)']
#         on_mach_index = drag_on.index.asof(machnumber)
#         off_mach_index = drag_off.index.asof(machnumber)
#         drag_on.at[on_mach_index, 'CD Power-On'] = drag_on.at[on_mach_index, 'CD Power-On'] * dragsolution
#         drag_off.at[off_mach_index, 'CD Power-Off'] = drag_off.at[off_mach_index, 'CD Power-Off'] * dragsolution
#     with pd.option_context('display.max_rows', None):
#         print(drag_on)
#         print(drag_off)

# Added 'current_accel_df' as the last argument
def editoffdrag(starttime, endtime, lowerdrag, upperdrag, off_drag_df, current_accel_df):
    
    # 1. Get the multiplier from your solver
    if starttime == -1:
        # Use the passed-in dataframe!
        lowtime, hightime = get_mach_time_bounds(current_accel_df, lowerdrag, upperdrag)
        if hightime >= 40:
            hightime = 40
        if lowtime <= 4:
            lowtime = 4
    else:
        lowtime = starttime
        hightime = endtime
        
    dragsolution = solve_off_drag(lowtime, hightime, lowerdrag, upperdrag)
    
    # 3. Create boolean masks for your target Mach range
    mask_off = (off_drag_df['Mach'] >= lowerdrag) & (off_drag_df['Mach'] <= upperdrag)

    # -1. Apply the multiplier ONLY to the rows inside that Mach range
    off_drag_df.loc[mask_off, 'CD Power-Off'] = off_drag_df.loc[mask_off, 'CD Power-Off'] + dragsolution

    # Run the simulation and save the NEW flight data to a differently named variable
    _, new_accel_df, _, _, _, _, _ = rocketSim(
        motor_file, 
        base_df_on[['Mach', 'CD Power-On']].to_numpy(), 
        off_drag_df[['Mach', 'CD Power-Off']].to_numpy(), 
        ork_file, 
        env)

    print(f"Modified drag between Mach {lowerdrag} and {upperdrag} by {dragsolution:.3f}")
    
    # RETURN BOTH the edited drag curve AND the new flight data
    return off_drag_df, new_accel_df

def get_mach_time_bounds(accel_df, min_mach, max_mach):
    # Filter for only the rows where the rocket is inside the target Mach range
    in_range = accel_df[(accel_df['Mach Number'] >= min_mach) & (accel_df['Mach Number'] <= max_mach)]
    
    # Safety fallback in case the rocket never reaches a certain speed (e.g., Mach 1.5)
    if in_range.empty:
        return 4.0, 40.0 
        
    # Get the exact time the rocket entered and exited this Mach regime
    t_start = in_range['Time (s)'].min()
    t_end = in_range['Time (s)'].max()
    
    return t_start, t_end

dnuapogee, init_accel_df, dnualt_df, dnuvel_df, dnupowerOnMax_time, dnupowerOffMax_time, dnuapogee_time = rocketSim(
        motor_file, 
        base_df_on[['Mach', 'CD Power-On']].to_numpy(), 
        base_df_off[['Mach', 'CD Power-Off']].to_numpy(), 
        ork_file, 
        env)


# 1. Global Baseline Shift (Gets overall apogee roughly correct)
base_df_off, current_accel_df = editoffdrag(4, 40, 0.0, 2.0, base_df_off, init_accel_df)
print("Global pass done")

# 2. Targeted Regime Fine-Tuning (Subsonic, Transonic, Supersonic)
base_df_off, current_accel_df = editoffdrag(-1, 40, 0.00, 0.80, base_df_off, current_accel_df)
base_df_off, current_accel_df = editoffdrag(-1, 40, 0.81, 1.20, base_df_off, current_accel_df)
base_df_off, current_accel_df = editoffdrag(-1, 40, 1.21, 2.00, base_df_off, current_accel_df)
print("Regime tuning done")

# 3. SMOOTH THE CURVE (This is the magic step that removes the cliffs!)
# This applies a rolling average to blend the boundaries together naturally
window_size = 7 
base_df_off['CD Power-Off'] = base_df_off['CD Power-Off'].rolling(window=window_size, center=True, min_periods=1).mean()

with pd.option_context('display.max_rows', None):
    print("Final Smoothed Drag DF:\n", base_df_off)

