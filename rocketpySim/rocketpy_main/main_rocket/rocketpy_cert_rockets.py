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
from conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor, get_railbutton, get_freeform_finset
from motors.motor_collection import motorClass
from tools.flight_csv.flight_csv import export_for_visualizer


C = Conversion()
sw = SpaceWeather()
motor = motorClass()




##################################
##------------------------------##
## ---- Dynamic File Paths ---- ##
##------------------------------##
##################################

motor_file = get_motor_path("AeroTech_HP-H195NT.eng")
print(os.path.exists(motor_file))

on_drag = get_drag_path("KevinL2_Rough_Camo_CD_On.CSV")
print(os.path.exists(on_drag))

off_drag = get_drag_path("KevinL2_Rough_Camo_CD_Off.CSV")
print(os.path.exists(off_drag))

ork_file = get_ork_path("KevinL2.ork")   # HAS TO HAVE SIM ATTACHED
print(os.path.exists(ork_file))

# airfoil_path = get_fin_path("Fins_CL_Alpha.csv")
# print(os.path.exists(airfoil_path))

set_openrocket_file(ork_file, 0)

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

for x in hours[8:]:     # loop through the hours list

    run_amt +=1 # Iterates every time it runs the for loop

    print(f"Space Cowboys Rocketpy System: Kevins L2 Cert Rocket")
    print(f"Simulated Time: {x}")
    print(f"Simulations Ran: {run_amt}")

    ##########################################
    ##--------------------------------------##
    ## ---- rocketpy environment setup ---- ##
    ##--------------------------------------##
    ##########################################

    sw.hrrr_download(
        launch_time_str=f"2026-04-10 12:00:00",
        #launch_time_str=f"2026-03-25 14:00:00",
        fxx=0,
        save_folder=r"data\weather_data",
        )

    env = sw.to_env(
        latitude=sw.sf_lat, # latitude calling the sw class
        longitude=sw.sf_lon, # longitude calling the sw class
        altitudes_m=None,
        max_height=32000,   # max simulated height in feet
    )

    #env.all_info()
    print("\n")

    ##--------------------------------##
    ## ---- rocketpy motor setup ---- ##
    ##--------------------------------##

    engine = motor.J800t(motor_file=motor_file)


    # engine.all_info()
    #engine.draw()

    ##----------------------------------------##
    ## ---- rocketpy rocket class set up ---- ##
    ##----------------------------------------##

    CertRocket = Rocket(
        radius=get_rocket(value='radius'),
        mass=get_rocket(value='mass') - get_motor(value="full_mass"), 
        inertia=(1.371,1.371,0.0116),  #FIXME: This is temporary and will need solved in solidworks
        center_of_mass_without_motor=get_rocket("cg_without_motor"), # This will be a user input in the software
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
    )
    
    ##---------------------------------##
    ## ---- rocketpy add features ---- ##
    ##---------------------------------##

    CertRocket.add_motor(motor=engine, position=2.01)    #TODO

    nose_cone = CertRocket.add_nose(
                length= get_nosecone(value='length'), 
                kind="ogive",
                position=get_nosecone(value='position')
                )

    # boat_tail = CertRocket.add_tail(  
    #     top_radius=get_boattail(value='top_radius'), 
    #     bottom_radius=get_boattail(value='bottom_radius'), 
    #     length=get_boattail(value='length'), 
    #     position=(get_boattail(value='position'))
    # )

    rail_buttons = CertRocket.set_rail_buttons(
         upper_button_position=1.32,
         lower_button_position=1.98,
         angular_position=180,
    )
    

    finset = CertRocket.add_free_form_fins(
        n=3,
        shape_points= get_freeform_finset('shape_points'),
        position=get_freeform_finset('position'),
        radius = 0.051054

        # airfoil = (airfoil_path,"degrees")
    )

    

    drogue_parachute = CertRocket.add_parachute(
        name="drogue",
        cd_s=0.0192,
        trigger="apogee",      
        sampling_rate=105,     
        lag=3.0,               
        noise=(0, 8.3, 0.5)    
    )

    main_parachute = CertRocket.add_parachute(
        name="main",
        cd_s=1.47411381288,
        trigger=229,         
        sampling_rate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5)
    )


    #CertRocket.plots.stability_margin()
    CertRocket.draw()

    ##--------------------------------------##
    ## ----- flight class integration ----- ##
    ##--------------------------------------##

    test_flight = Flight(
        rocket=CertRocket,    # Input Rocket
        environment=env,    # Input Environment
        rail_length= 3.05,   # Rail Length
        inclination=87,     # Rail Inclination
        heading=180,      # Rail Heading
    )

    # ##----------------------------##
    # ## ---- run flight class ---- ##
    # ##----------------------------##

    # test_flight.post_process()  # This will run the simulation

    # # This is to check the surface and wind conditions at launch site and at the rail
    # test_flight.prints.surface_wind_conditions()
    # test_flight.prints.launch_rail_conditions()

    # # This is the out of rail conditions
    # test_flight.prints.out_of_rail_conditions()

    # # This is to check the burn out time
    # test_flight.prints.burn_out_conditions()

    # # This is to check the apogee conditions
    # test_flight.prints.apogee_conditions()

    # # This is to check for the ejection of parachutes
    # test_flight.prints.events_registered()

    # # This is to check for the impact conditions
    # test_flight.prints.impact_conditions()

    # # This provides a summary of the maximum values recorded during the flight
    # test_flight.prints.maximum_values()

    # # This is is to plot the results of the flight and show the trajectory
    # test_flight.plots.trajectory_3d()

    # export_for_visualizer(test_flight, filename="cert_rocket_sim_flight.csv")

    


    