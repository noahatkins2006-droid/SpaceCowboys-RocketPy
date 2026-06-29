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
from tools.weight_inertia_manager_class import WeightInertia

C = Conversion()
sw = SpaceWeather()
motor = motorClass()





##################################
##------------------------------##
## ---- Dynamic File Paths ---- ##
##------------------------------##
##################################

motor_file = get_motor_path("AeroTech_O5500X-PS.eng")
print(os.path.exists(motor_file))

on_drag = get_drag_path("Bandit7_CD_On.CSV")
print(os.path.exists(on_drag))

off_drag = get_drag_path("Bandit7_CD_Off.CSV")
print(os.path.exists(off_drag))

ork_file = get_ork_path("Bandit_Average_7.ork")   # HAS TO HAVE SIM ATTACHED
print(os.path.exists(ork_file))

airfoil_path = get_fin_path("Fins_CL_Alpha.csv")
print(os.path.exists(airfoil_path))

set_openrocket_file(ork_file, 0)

# Frankenstein = Rocket(
#         radius=get_rocket(value='radius'),
#         mass=get_rocket(value='mass') - get_motor(value="full_mass"), 
#         inertia=(12.2046,12.2046,0.0783),  #FIXME: This is temporary and will need solved in solidworks
#         center_of_mass_without_motor=get_rocket("cg_without_motor"), # This will be a user input in the software
#         coordinate_system_orientation="nose_to_tail",
#         power_on_drag=on_drag,
#         power_off_drag=off_drag,
#     )


weightConfiguration = WeightInertia(mass = get_rocket(value='mass') - get_motor(value="full_mass"), inertia = (12.2046,12.2046,0.0783), cg_pos = get_rocket("cg_without_motor"))

targetApogee = 7467.6
maxweightplates = 10

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



run_amt +=1 # Iterates every time it runs the for loop

print(f"Space Cowboys Rocketpy System: Research Rocket")
print(f"Simulated Time: 12:00:00")
print(f"Simulations Ran: {run_amt}")

##########################################
##--------------------------------------##
## ---- rocketpy environment setup ---- ##
##--------------------------------------##
##########################################

sw.hrrr_download(
    launch_time_str=f"{dt.date.today()} 12:00:00",
    #launch_time_str=f"2026-03-18 12:00:00",
    fxx=12,
    save_folder=r"data\weather_data",
    )

env = sw.to_env(
    latitude=sw.mid_lat, # latitude calling the sw class
    longitude=sw.mid_lon, # longitude calling the sw class
    altitudes_m=None,
    max_height=32000,   # max simulated height in feet
)

#env.all_info()
print("\n")

##--------------------------------##
## ---- rocketpy motor setup ---- ##
##--------------------------------##

engine = motor.O5500x(motor_file=motor_file)


# engine.all_info()
#engine.draw()

##----------------------------------------##
## ---- rocketpy rocket class set up ---- ##
##----------------------------------------##

Frankenstein = Rocket(
    radius=get_rocket(value='radius'),
    mass=get_rocket(value='mass') - get_motor(value="full_mass"), 
    inertia=(12.2046,12.2046,0.0783),  #FIXME: This is temporary and will need solved in solidworks
    center_of_mass_without_motor=get_rocket("cg_without_motor"), # This will be a user input in the software
    coordinate_system_orientation="nose_to_tail",
    power_on_drag=on_drag,
    power_off_drag=off_drag,
)

##---------------------------------##
## ---- rocketpy add features ---- ##
##---------------------------------##

Frankenstein.add_motor(motor=engine, position=(get_boattail(value='position')+get_boattail(value='length')))    #TODO

nose_cone = Frankenstein.add_nose(
            length= get_nosecone(value='length'), 
            kind="lvhaack",
            position=get_nosecone(value='position')
            )

boat_tail = Frankenstein.add_tail(  
    top_radius=get_boattail(value='top_radius'), 
    bottom_radius=get_boattail(value='bottom_radius'), 
    length=get_boattail(value='length'), 
    position=(get_boattail(value='position'))
)

# rail_buttons = Frankenstein.set_rail_buttons(
#     upper_button_position=-2,
#     lower_button_position=-3,
#     angular_position=45,
# )

finset = Frankenstein.add_trapezoidal_fins(
    n=get_finset(value='n'),
    root_chord=get_finset(value='root_chord'),
    tip_chord=get_finset(value='tip_chord'),
    span=(get_finset(value='span')),
    sweep_length=(get_finset(value='sweep_length')),
    position=(get_finset(value='position')-get_finset(value='root_chord')),
    airfoil = (airfoil_path,"degrees")
)

drogue_parachute = Frankenstein.add_parachute(
    name="drogue",
    cd_s=0.452,
    trigger="apogee",      
    sampling_rate=105,     
    lag=1.5,               
    noise=(0, 8.3, 0.5)    
)

main_parachute = Frankenstein.add_parachute(
    name="main",
    cd_s=7.865,
    trigger=457.2,         
    sampling_rate=105,
    lag=1.5,
    noise=(0, 8.3, 0.5)
)


#Frankenstein.plots.stability_margin()
#Frankenstein.draw()

##--------------------------------------##
## ----- flight class integration ----- ##
##--------------------------------------##

test_flight = Flight(
    rocket=Frankenstein,    # Input Rocket
    environment=env,    # Input Environment
    rail_length= 5.1816,   # Rail Length
    inclination=84,     # Rail Inclination
    heading=0,      # Rail Heading
)

##----------------------------##
## ---- run flight class ---- ##
##----------------------------##

test_flight.post_process()  # This will run the simulation


# This provides a summary of the maximum values recorded during the flight
test_flight.prints.maximum_values()