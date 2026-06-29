## -- Main Research Rocket Script For Simulations -- ##
#####################
## -- Libraries -- ##
#####################
from rocketpy import Environment, SolidMotor, Rocket, Flight
import numpy as np
import datetime as dt
import pandas as pd
import sys
import os
import pandas as pd
import scipy

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory

from conversion.conversion_tool import Conversion
from weather.weather_tool import SpaceWeather 
from set_rocket.set_rocket import rocket
from motors.motor_collection import motorClass

C = Conversion()
sw = SpaceWeather()
motor = motorClass()

###############################
##---------------------------##
## ---- Code Begins Here ----##
##---------------------------##
###############################


print(f"Space Cowboys Rocketpy System")

##########################################
##--------------------------------------##
## ---- rocketpy environment setup ---- ##
##--------------------------------------##
##########################################


sw.hrrr_download(
    launch_time_str=f"{dt.date.today()} 06:00:00", 
    fxx=6,  # This is the hour of launch as a whole number
    save_folder=r"data\weather_data",
    )

env = sw.to_env(
    latitude=sw.sf_lat, # latitude calling the sw class
    longitude=sw.sf_lon, # longitude calling the sw class
    altitudes_m=None,
    max_height=C.FT_to_Meters(variable=38000),   # max simulated height in feet
)

engine = motor.H195nt(motor_file="AeroTech_HP-H195NT.eng")

r = rocket(rocket='Sims_Rocket_2.ork', 
        on_drag='power_on_sims.CSV', 
        off_drag='power_off_sims.csv', 
        nose_cone_type='lvhaack',
        inertia=(2e-2, 2e-2, 1e-4),
        engine=engine,
        boattail= False
        )
##--------------------------------------##
## ----- flight class integration ----- ##
##--------------------------------------##

launch = Flight(
    rocket=r,    # Input Rocket
    environment=env,    # Input Environment
    rail_length= C.FT_to_Meters(variable=8),   # Rail Length
    inclination=85,     # Rail Inclination
    heading=0,      # Rail Heading
    ode_solver=("LSODA")
)

##----------------------------##
## ---- run flight class ---- ##
##----------------------------##

launch.post_process()  # This will run the simulation

# This is to check the surface and wind conditions at launch site and at the rail
launch.prints.surface_wind_conditions()
launch.prints.launch_rail_conditions()

# This is the out of rail conditions
launch.prints.out_of_rail_conditions()

# This is to check the burn out time
launch.prints.burn_out_conditions()

# This is to check the apogee conditions
launch.prints.apogee_conditions()

# This is to check for the ejection of parachutes
launch.prints.events_registered()

# This is to check for the impact conditions
launch.prints.impact_conditions()

# This provides a summary of the maximum values recorded during the flight
launch.prints.maximum_values()

# This is is to plot the results of the flight and show the trajectory
r.draw()
launch.plots.trajectory_3d()