## -- Main Drag Solver Script For Simulations -- ##
#####################
## -- Libraries -- ##
#####################
from rocketpy import Environment, SolidMotor, Rocket, Flight, MonteCarlo
from motors.motor_collection import motorClass
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

C = Conversion()
sw = SpaceWeather()
motor = motorClass()



def rocketSim( motor_file:str, on_drag:np.ndarray, off_drag:np.ndarray, ork_file:str, weather):

        motor_file = get_motor_path(motor_file)
        print(os.path.exists(motor_file))

        ork_file = get_ork_path(ork_file)
        print(os.path.exists(ork_file))

        set_openrocket_file(ork_file,0)

        ##########################################
        ##--------------------------------------##
        ## ---- rocketpy environment setup ---- ##
        ##--------------------------------------##
        ##########################################


        env = weather

        #env.all_info()
        # print("\n")




        ##--------------------------------##
        ## ---- rocketpy motor setup ---- ##
        ##--------------------------------##

        engine = motor.O5500x(motor_file=motor_file)

        # burn_time = engine.burn_time
        # print(burn_time)
        #M1340w.all_info()
        #M1340w.draw()




        ##----------------------------------------##
        ## ---- rocketpy rocket class set up ---- ##
        ##----------------------------------------##

        Frankenstein = Rocket(
        radius=get_rocket(value='radius'),
        mass=get_rocket(value='mass'), 
        inertia=(20.44,20.44,0.16807),  #FIXME: This is temporary and will need solved in solidworks
        center_of_mass_without_motor=get_rocket(value="cg_without_motor"), # This will be a user input in the software
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
        )





        ##---------------------------------##
        ## ---- rocketpy add features ---- ##
        ##---------------------------------##

        Frankenstein.add_motor(engine, position=(get_boattail(value='position')+get_boattail(value='length')))    #TODO

        nose_cone = Frankenstein.add_nose(
                length=get_nosecone(value='length'), 
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
        sweep_length=C.In_to_M(variable=12),
        position=(get_finset(value='position')-get_finset(value='root_chord')),
        #airfoil=("../data/airfoils/NACA0012-radians.txt","radians"),   # TODO: Figure out how to get airfoil data
        )

        #Frankenstein.plots.stability_margin()
        #Frankenstein.draw()

            # Apply drag scale factor

        ##--------------------------------------##
        ## ----- flight class integration ----- ##
        ##--------------------------------------##

        test_flight = Flight(
        rocket=Frankenstein,    # Input Rocket
        environment=env,    # Input Environment
        rail_length= C.FT_to_Meters(variable=10),   # Rail Length
        inclination=84,     # Rail Inclination
        heading=0,      # Rail Heading
        )
        

        apo = test_flight.apogee
        max_accel = test_flight.max_acceleration
        time_array = time_array = test_flight.time
        accel_array = test_flight.acceleration(time_array)
        mach_array = test_flight.mach_number(time_array)
        accel_df = pd.DataFrame({
            "Time (s)": time_array,
            "Acceleration (m/s^2)": accel_array,
            "Mach Number": mach_array
        })
        alt_array = test_flight.altitude(time_array)
        alt_df = pd.DataFrame({
            "Time (s)": time_array,
            "Altitude (m)": alt_array,
            "Mach Number": mach_array
        })
        vel_array = test_flight.speed(time_array)
        vel_df = pd.DataFrame({
            "Time (s)": time_array,
            "Velocity (m/s)": vel_array,
            "Mach Number": mach_array
        })
        
        





        return apo, accel_df, alt_df, vel_df, test_flight.max_acceleration_power_on_time, test_flight.max_acceleration_power_off_time, test_flight.apogee_time

# --- Root-finding function ---
# def f(x, real_apogee):
#     return rocketSim(x) - real_apogee

# Solve for drag scale
# scale_solution = brentq(f, 0.5, 1.5, args=(1385,))  # search range for Cd multiplier
# print(f"Best-fit drag scale = {scale_solution:.3f}")
