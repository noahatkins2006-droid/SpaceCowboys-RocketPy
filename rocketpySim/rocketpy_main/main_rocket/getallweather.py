## -- Main Research Rocket Script For Simulations -- ##
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
import numpy as np
from datetime import datetime
import sys
import os
import pandas as pd
import datetime as dt

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory

from conversion.conversion_tool import Conversion
from weather.weather_tool import SpaceWeather 
from file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path, get_fin_path
from conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor
from motors.motor_collection import motorClass

C = Conversion()
sw = SpaceWeather()
motor = motorClass()





################################
##----------------------------##
## ---- Simulation hours ---- ##
##----------------------------##
################################

hours = ['06:00:00','07:00:00','08:00:00','09:00:00','10:00:00','11:00:00', '12:00:00',
          '13:00:00', '14:00:00', '15:00:00', '16:00:00', '17:00:00', '18:00:00']   # Assumed Morning Hours 6 A.M. to 6 P.M.
 
run_amt = 0     # How many times the simulation has run

###############################
##---------------------------##
## ---- Code Begins Here ----##
##---------------------------##
###############################

for x in hours:     # loop through the hours list

    run_amt +=1 # Iterates every time it runs the for loop

    print(f"Space Cowboys Rocketpy System: Research Rocket")
    print(f"Simulated Time: {x}")
    print(f"Simulations Ran: {run_amt}")

    ##########################################
    ##--------------------------------------##
    ## ---- rocketpy environment setup ---- ##
    ##--------------------------------------##
    ##########################################

    sw.hrrr_download(
        launch_time_str=f"{dt.date.today()} {x}",
        #launch_time_str=f"2026-03-25 14:00:00",
        fxx=x,
        save_folder=r"data\weather_data",
        )