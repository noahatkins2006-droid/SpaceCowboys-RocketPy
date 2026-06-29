## -- Main Rocketpy Script for Simulations -- ##

## -- Libraries -- ##
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
import pandas as pd
import sys
import os
import pandas as pd

## -- Home Brewed scripts -- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Opening whole directory

from conversion.conversion_tool import Conversion
from weather.weather_tool import SpaceWeather 
from calculations.calc import calc 
from file_paths.file_path_func import get_motor_path, get_drag_path

C = Conversion()
sw = SpaceWeather()
cal = calc()

motor_file = get_motor_path("AeroTech_M1340W.eng")
print(os.path.exists(motor_file))

on_drag = get_drag_path("CD_Power_On_Frank.CSV")
print(os.path.exists(on_drag))

off_drag = get_drag_path("CD_Power_Off_Frank.CSV")
print(os.path.exists(off_drag))


hours = ['06:00:00','07:00:00','08:00:00','09:00:00','10:00:00','11:00:00', '12:00:00',
          '13:00:00', '14:00:00', '15:00:00', '16:00:00', '17:00:00', '18:00:00']   # Assumed Morning Hours 6 A.M. to 6 P.M. 

run_amt = 0     # How many times the simulation has run

## -- rocketpy environment setup -- ##
for x in hours:     # loop through the hours list

    run_amt +=1 # Iterates every time it runs the for loop

    print(f"Space Cowboys Rocketpy System: Research Rocket")
    print(f"Simulated Time: {x}")
    print(f"Simulations Ran: {run_amt}")

    sw.hrrr_download(
        init_time_str="2025-10-14 06:00:00",
        launch_time_str=f"2025-10-14 {x}",
        fxx=x,
        save_folder=r"data\weather_data",
        )

    env = sw.to_env(
        latitude=sw.sf_lat, # latitude calling the sw class
        longitude=sw.sf_lon, # longitude calling the sw class
        altitudes_m=None,
        max_height=C.FT_to_Meters(variable=38000),   # max simulated height in feet
    )

#     # env.all_info()
#     # print("\n")

## -- Rocketpy Stochastic Environment -- ##
    # stochastic_env = StochasticEnvironment(
    #     environment=env,
    #     wind_velocity_x_factor=(0.8, 1.2),
    #     wind_velocity_y_factor=(0.8, 1.2)
    # )


#     stochastic_env.visualize_attributes()

    M1340w = SolidMotor(
        thrust_source=motor_file,    
        dry_mass=C.Gram_to_Kilo(variable=2949.00),
        dry_inertia=(1.16485,1.16485,0.0596609693875),  #TODO : This is an estimation 10/7/2025, create solidworks model and get tuple from there
        nozzle_radius=C.In_to_M(variable=1.75),
        grain_number=5,
        grain_density=C.LB_cubic_in_to_Kilo_cubic_M(variable=0.0656),
        grain_outer_radius=C.In_to_M(variable=3.365/2),
        grain_initial_inner_radius=C.In_to_M(variable=3.27/2),
        grain_initial_height=C.In_to_M(variable=6.00),
        grain_separation=C.In_to_M(variable=0.07),
        grains_center_of_mass_position=C.In_to_M(variable=20),
        center_of_dry_mass_position=C.In_to_M(variable=20),
        nozzle_position=0,
        burn_time=5.5,
        throat_radius=C.In_to_M(variable=0.734),
        coordinate_system_orientation='nozzle_to_combustion_chamber'
    )

    # M1340w.all_info()
    # M1340w.draw()

    # stochastic_motor = StochasticSolidMotor(
    #     solid_motor=M1340w,
    #     burn_out_time=(0, 0.5, 'binomial'),
    #     grains_center_of_mass_position=0.001,
    #     grain_density=C.LB_cubic_in_to_Kilo_cubic_M(variable=0.0656),
    #     grain_separation=(1/1000),
    #     grain_initial_height=(1/1000),
    #     grain_initial_inner_radius=(0.375/1000),
    #     grain_outer_radius=(0.375/1000),
    #     total_impulse=(7369, 1000),
    #     throat_radius=(0.05/1000),
    #     nozzle_radius=(0.5/1000),
    #     nozzle_position=0.001,
    # )

    # stochastic_motor.visualize_attributes()

    Frankenstein = Rocket(
        radius=C.In_to_M(variable=(6/2)),
        mass=C.LBs_to_Kilo(variable=41.2), 
        inertia=(20.44,20.44,0.16807),  #FIXME: This is temporary and will need solved in solidworks
        center_of_mass_without_motor=0,
        coordinate_system_orientation="tail_to_nose",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
    )
    # Frankenstein.all_info()

    Frankenstein.add_motor(M1340w, position=C.In_to_M(variable=-145))    #FIXME: Reposition this once rocket class is complete


    nose_cone = Frankenstein.add_nose(
                C.In_to_M(variable=36), 
                kind="lvhaack",
                position=0)


    boat_tail = Frankenstein.add_tail(  
        top_radius=C.cm_to_m(variable=(7.75)), 
        bottom_radius=C.cm_to_m(variable=(5.2)), 
        length=C.cm_to_m(variable=12.7), 
        position=C.In_to_M(variable=-140)
    )

    rail_buttons = Frankenstein.set_rail_buttons(
        upper_button_position=-2,
        lower_button_position=-3,
        angular_position=45,
    )

    finset = Frankenstein.add_fins(
        n=4,
        root_chord=C.In_to_M(variable=12),
        tip_chord=C.In_to_M(variable=3),
        span=C.In_to_M(variable=7),
        position=C.In_to_M(variable=-127),
        #airfoil=("../data/airfoils/NACA0012-radians.txt","radians"),   # TODO: Figure out how to get airfoil data
    )

    Frankenstein.draw()

    test_flight = Flight(
        rocket=Frankenstein,
        environment=env,
        rail_length= C.FT_to_Meters(variable=10),
        inclination=85,
        heading=0,
    )

    test_flight.post_process()

    #This is to check the internal state of the rocket at the time of ignition:
    test_flight.prints.initial_conditions()

    #This is to check the surface and wind conditions at launch site and at the rail
    test_flight.prints.surface_wind_conditions()
    test_flight.prints.launch_rail_conditions()

    #This is the out of rail conditions
    test_flight.prints.out_of_rail_conditions()

    #This is to check the burn out time
    test_flight.prints.burn_out_conditions()

    #This is to check the apogee conditions
    test_flight.prints.apogee_conditions()

    #This is to check for the ejection of parachutes
    test_flight.prints.events_registered()

    #This is to check for the impact conditions
    test_flight.prints.impact_conditions()

    #This provides a summary of the maximum values recorded during the flight
    test_flight.prints.maximum_values()

    #This is is to plot the results of the flight and show the trajectory
    test_flight.plots.trajectory_3d()

    # stochastic_flight = StochasticFlight(
        
    # )

    # flight.all_info()

    # test_disp = MonteCarlo(
    #     filename=x, #TODO: Finish the file system for the ML algorithm
    #     environment=stochastic_env,
    #     rocket=stochastic_rocket,
    #     flight=stochastic_flight
    # )


