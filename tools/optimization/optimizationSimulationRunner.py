## -- Main Research Rocket Script For Simulations -- ##
#####################
## -- Libraries -- ##
#####################

from rocketpy import Environment, SolidMotor, Rocket, Flight
import numpy as np
import sys
import os
import pandas as pd
import datetime as dt

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory

from rocketpySim.conversion.conversion_tool import Conversion
from rocketpySim.file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path
from rocketpySim.conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket
from rocketpySim.motors.motor_collection import motorClass
from tools.automated_RASAero.autoRASAero import getRocketAttribute

C = Conversion()
motor = motorClass()

# Load OpenRocket file ONCE outside the loop to save memory
ork_file = get_ork_path("Bandit_Average_10_1.ork")
set_openrocket_file(ork_file, 0)

##################################
##------------------------------##
## ---- Dynamic File Paths ---- ##
##------------------------------##
##################################
import multiprocessing
import time

# 1. The Wrapper Function
# This runs in the background and puts the result into a queue
def simulation_worker(siminputs, queue):
    try:
        on_drag_path, off_drag_path, cdx1_file_path = siminputs
        motor_file = get_motor_path("AeroTech_O5500X-PS.eng")

        ##########################################
        ##--------------------------------------##
        ## ---- rocketpy environment setup ---- ##
        ##--------------------------------------##
        ##########################################
        
        env = Environment(
            latitude=32.990254,  # Spaceport America lat
            longitude=-106.974991, # Spaceport America lon
            elevation=1400  # Elevation in meters
        )
        env.set_atmospheric_model(type="standard_atmosphere")

        ##--------------------------------##
        ## ---- rocketpy motor setup ---- ##
        ##--------------------------------##
        
        engine = motor.O5500x(motor_file=motor_file)

        ##----------------------------------------##
        ## ---- rocketpy rocket class set up ---- ##
        ##----------------------------------------##
        
        
        # Pull base rocket geometry strictly from OpenRocket
        Frankenstein = Rocket(
            radius=get_rocket(value='radius'),
            mass=get_rocket(value='mass'), 
            inertia=(20.44, 20.44, 0.16807), 
            center_of_mass_without_motor=2.17, 
            coordinate_system_orientation="nose_to_tail",
            power_on_drag=on_drag_path,
            power_off_drag=off_drag_path,
        )

        ##---------------------------------##
        ## ---- rocketpy add features ---- ##
        ##---------------------------------##

        # Add Motor
        Frankenstein.add_motor(
            motor=engine, 
            position=(get_boattail(value='position') + get_boattail(value='length'))
        )

        # Add Nose Cone
        Frankenstein.add_nose(
            length=get_nosecone(value='length'), 
            kind="lvhaack", 
            position=get_nosecone(value='position')
        )

        # Add Boat Tail
        Frankenstein.add_tail(  
            top_radius=get_boattail(value='top_radius'), 
            bottom_radius=get_boattail(value='bottom_radius'), 
            length=get_boattail(value='length'), 
            position=get_boattail(value='position')
        )

    
    
    # --- THIS IS THE ONLY PART THAT USES RASAERO (.CDX1) NOW ---
    # We fetch the exact 4 tags being optimized and convert them from inches to meters.
        try:
            fin_root_m = float(getRocketAttribute(cdx1_file_path, 'BodyTube:3.Fin.Chord')) * 0.0254
            fin_tip_m = float(getRocketAttribute(cdx1_file_path, 'BodyTube:3.Fin.TipChord')) * 0.0254
            fin_span_m = float(getRocketAttribute(cdx1_file_path, 'BodyTube:3.Fin.Span')) * 0.0254 * 0.5
            fin_sweep_m = float(getRocketAttribute(cdx1_file_path, 'BodyTube:3.Fin.SweepDistance')) * 0.0254
            total_span_m = float(getRocketAttribute(cdx1_file_path, 'BodyTube:3.Fin.Span')) * 0.0254
            body_radius_m = get_rocket(value='radius') # Assuming this is in meters

            print(fin_root_m,fin_tip_m,fin_span_m,fin_sweep_m)

            
            
        except Exception as e:
            print(f" Error extracting Fin attributes from CDX1: {e}")
            return None

        Frankenstein.add_trapezoidal_fins(
            n=get_finset(value='n'), # Kept from ORK
            root_chord=fin_root_m,
            tip_chord=fin_tip_m,
            span=fin_span_m,
            sweep_length=fin_sweep_m,
            position=(get_finset(value='position') - fin_root_m), # Math maintained
        )

        
        
        
        ##--------------------------------------##
        ## ----- flight class integration ----- ##
        ##--------------------------------------##
        try:
            test_flight = Flight(
                rocket=Frankenstein,
                environment=env,
                rail_length=C.FT_to_Meters(variable=10),
                inclination=85,
                heading=0,
                terminate_on_apogee=True, 
                max_time_step=0.1        
            )
            
            calibers = test_flight.out_of_rail_stability_margin
            print(f"Caliber: {calibers}")
            body_diameter_m = 2 * get_rocket(value='radius')
            margin_meters = calibers * body_diameter_m
            rocket_length = 3.52
            
            stability = (margin_meters / rocket_length) * 100
            
            # CRITICAL: Force everything into standard Python floats 
            # so it safely crosses the queue without a silent crash!
            safe_apogee = float(test_flight.apogee)
            safe_stability = float(stability)
            
            result_tuple = (safe_apogee, safe_stability)
            queue.put(result_tuple)

        except Exception as e:
            print(f"\n[!] RocketPy Physics Crash! Error: {e}")
            # Put None in the queue, DO NOT put the exception object!
            queue.put(None) 
            
    except Exception as e:
        # THE SILENT KILLER REVEALED:
        # If it crashes while building the rocket (before the flight), it goes here.
        import traceback
        print(f"\n[FATAL WORKER ERROR] Something broke before the simulation started!")
        print(f"Error Details: {e}")
        traceback.print_exc() # This will force the terminal to print the exact line that broke
        queue.put(None)

# 2. The Timeout Controller
def run_with_timeout(sim_inputs, timeout_sec=20, default_return=(0,0)):
    """
    Spawns the simulation in a new process. Kills it if it takes too long.
    """
    queue = multiprocessing.Queue()
    
    # Create the background process
    p = multiprocessing.Process(target=simulation_worker, args=(sim_inputs, queue))
    
    # Start the clock
    p.start()
    
    # Wait for the process to finish, BUT ONLY up to timeout_sec
    p.join(timeout_sec)
    
    # Check if the process is still running after the timer expires
    if p.is_alive():
        print(f"\n[!] Simulation exceeded {timeout_sec} seconds. Terminating...")
        p.terminate()  # Forcefully kill the hung process
        p.join()       # Clean up the leftover process memory
        return default_return
    
    # If the process finished in time, grab the result
    if not queue.empty():
        result = queue.get()
        
        # Optional: Raise the error if the simulation crashed
        if isinstance(result, Exception):
            print(f"Simulation failed with error: {result}")
            return default_return
            
        return result
        
    return default_return

# --- Example Usage ---
# CRITICAL FOR WINDOWS: You MUST have this 'if __name__ == "__main__":' block
# Otherwise, multiprocessing will infinitely open new terminal windows and crash.
    
if __name__ == "__main__":
    # Test execution block
    runSimulation(
        r"C:\Users\dahle\Documents\Simulations-Repository\tests\testOptimization\files\Optimization_Results\Bandit_Average_7_opt_64698278_DragCurves\Bandit_Average_7_opt_64698278_CD_On.CSV",
        r"C:\Users\dahle\Documents\Simulations-Repository\tests\testOptimization\files\Optimization_Results\Bandit_Average_7_opt_64698278_DragCurves\Bandit_Average_7_opt_64698278_CD_Off.CSV",
        r"C:\Users\dahle\Documents\Simulations-Repository\tests\testOptimization\files\Bandit_Average_7.CDX1"
    )