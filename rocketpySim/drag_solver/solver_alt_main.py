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
from solver import TimeBasedAltitude
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

motor_file = get_motor_path("AeroTech_M1340W.eng")
print(os.path.exists(motor_file))

on_drag = get_drag_path("CD_Power_On_Frank.CSV")
print(os.path.exists(on_drag))

off_drag = get_drag_path("CD_Power_Off_Frank.CSV")
print(os.path.exists(off_drag))

ork_file = get_ork_path("Design_1_2_revision.ork")
print(os.path.exists(ork_file))

# --- Measured data ---
real_apogee = 2808.485  # meters


def f(x,startTime,endTime):
    
    apogee, accel_df, alt_df, vel_df, powerOnMax_time, powerOffMax_time, apogee_time = rocketSim(motor_file, on_drag, off_drag, ork_file, "06:00:00", x)
    alt_data = TimeBasedAltitude(open((Path(__file__).resolve().parent/"helios_solver_data"/"helios_time_x_altitude.csv").resolve(),"r"), alt_df)
    total_deviation = alt_data.get_total_deviation(startTime,endTime)
    abs_deviation = alt_data.get_absolute_deviation(startTime,endTime)
    print("total deviation:", total_deviation)
    print("abs deviation:", abs_deviation)
    return(abs_deviation)

# Solve for drag scale
def solve_drag(startTime,endTime,lowerBound=0, upperBound=50):
    scale_solution = minimize_scalar(f, bounds=(lowerBound, upperBound),args=(startTime,endTime),tol=1e-1, method="bounded")  # search range for Cd multiplier
    print(f"Best-fit drag scale = {scale_solution.x:.3f}")
    return(scale_solution)

solve_drag(0,1000)
