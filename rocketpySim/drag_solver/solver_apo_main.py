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
from scipy.optimize import brentq
import numpy as np
from datetime import datetime
import sys
import os
import pandas as pd
import datetime as dt

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


def f(x, real_apogee):
    return (rocketSim(motor_file, on_drag, off_drag, ork_file, "06:00:00", x)[0] - real_apogee)

# Solve for drag scale
scale_solution = brentq(f, 0, 50, args=(real_apogee,),xtol=1e-3)  # search range for Cd multiplier
print(f"Best-fit drag scale = {scale_solution:.3f}")
