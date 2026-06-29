import os
import sys
from pathlib import Path
from datetime import datetime
import zoneinfo
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.optimize import minimize_scalar
from rocketpy import Environment, SolidMotor, Rocket, Flight
import tempfile

# Ensure the project root is in the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.automated_RASAero.autoRASAero import getData
from rocketpySim.weather.weather_tool import SpaceWeather
from rocketpySim.motors.motor_collection import motorClass
from rocketpySim.file_paths.file_path_func import get_fin_path

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    base_rocket_file = os.path.join(script_dir, "files", "Bandit TL1 (PreAssembly).CDX1")
    
    target_altitude = 697.5348
    
    print("\n=========================================")
    print("      STARTING ROUGHNESS OPTIMIZATION     ")
    print("=========================================")
    
    # Run optimization with an initial roughness guess of 1.0
    result, best_alt = optimize_roughness(base_rocket_file, target_altitude, initial_guess=1.0)
    
    if result and result.success:
        print("\n=========================================")
        print("          OPTIMIZATION COMPLETE          ")
        print("=========================================")
        print(f"Target Altitude:   {target_altitude:.2f} m")
        print(f"Best Alt Achieved: {best_alt:.2f} m")
        print(f"Difference:        {result.fun:.2f} m")
        print(f"Optimal Roughness: {result.x:.8f}")
    else:
        print("\nOptimization terminated early or failed.")
        if result:
            print(result.message)

def optimize_roughness(rocket_file_path, target_altitude, initial_guess):
    # 1. SETUP ENVIRONMENT ONCE (Do not do this in the loop)
    sw = SpaceWeather()
    motor = motorClass()
    
    target_date = "2025-06-11"
    time_str = '18:00:00'
    
    local_tz = zoneinfo.ZoneInfo("America/Chicago")
    utc_tz = zoneinfo.ZoneInfo("UTC")
    
    local_dt = datetime.strptime(f"{target_date} {time_str}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=local_tz)
    utc_dt = local_dt.astimezone(utc_tz)
    hrrr_utc_str = utc_dt.strftime("%Y-%m-%d %H:%M:%S")

    print("Downloading weather data...")
    sw.hrrr_download(
        launch_time_str=hrrr_utc_str, 
        fxx=0, 
        save_folder=r"data\weather_data",
    )
    
    env = sw.to_env(
        latitude=sw.tl_lat, 
        longitude=sw.tl_lon, 
        altitudes_m=np.arange(0, 15000, 1), 
        max_height=80000,
    )
    
    # Pre-load static assets
    engine = motor.O5500x()
    airfoil_path = get_fin_path("Fins_CL_Alpha.csv")
    
    # Prepare directories
    base_dir = os.path.dirname(rocket_file_path)
    output_dir = os.path.join(base_dir, "Cd_curves")
    os.makedirs(output_dir, exist_ok=True)

    # We need to store the actual altitude achieved to print it later
    best_sim_alt = [0.0] 

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Temporary workspace created at: {temp_dir}")

        # 2. DEFINE OBJECTIVE FUNCTION
        def objective(roughness): # <-- Changed from roughness_array
            # roughness is already a float now, no need to extract from an array
            print(f"Testing Roughness: {roughness:.8f}...", end=" ")
            
            str_rough = f"{roughness:.8f}"
            
            # Point all file generation to the temporary directory
            file_prefix = os.path.join(temp_dir, f"run_{str_rough}")
            
            # Step B: Run RASAero and save to temp_dir
            csv_path = getData(r"C:\Users\dahle\Documents\Simulations-Repository\tests\testAutoRAS\Bandit TL1 (PreAssembly).CDX1", temp_dir, file_prefix, str_rough)
            
            # Step C: Parse Drag (Reading from the temp file)
            on_drag = pd.read_csv(csv_path, usecols=["Mach","CD Power-On"]).to_numpy()
            off_drag = pd.read_csv(csv_path, usecols=["Mach","CD Power-Off"]).to_numpy()

            # Step D: Build Rocket Instance (Updates with new drag curves)
            Helios = Rocket(
                # radius=.155/2,
                # mass=16.830, 
                # inertia=(20.44, 20.44, 0.16807), 
                # center_of_mass_without_motor=1.74, 
                # coordinate_system_orientation="nose_to_tail",
                # power_on_drag=on_drag,
                # power_off_drag=off_drag,
                radius=0.154/2,
                mass=12.622, 
                inertia=(20.8,20.8,0.1),  #FIXME: This is temporary and will need solved in solidworks
                center_of_mass_without_motor=1.68, # This will be a user input in the software
                coordinate_system_orientation="nose_to_tail",
                power_on_drag=on_drag,
                power_off_drag=off_drag,
            )

            Helios.add_motor(motor=engine, position=3.52)
            Helios.add_nose(
                # length=.787, 
                # kind="lvhaack", 
                # position=0
                length= 0.865, 
                kind="lvhaack",
                position=0
                )
            Helios.add_tail(
                # top_radius=0.155/2, 
                # bottom_radius=.102/2, 
                # length=0.127, 
                # position=3.4195
                top_radius=0.154/2, 
                bottom_radius=0.104/2, 
                length=0.127, 
                position=3.3354
                )
            Helios.add_trapezoidal_fins(
            #     n=4, root_chord=0.305, tip_chord=0.0762, span=0.152, 
            #     sweep_length=0.305, position=3.07, airfoil=(airfoil_path,"degrees")
                n=4,
                root_chord=.305,
                tip_chord=.0762,
                span=0.159,
                sweep_length=.305,
                position=2.999,
                airfoil = (airfoil_path,"degrees")
            )

            # Step E: Fly
            test_flight = Flight(
                rocket=Helios,
                environment=env,
                rail_length=5.1816,
                inclination=84,
                heading=0,
                terminate_on_apogee=True # Optimization speeds up if we stop simulating after apogee
            )
            
            sim_alt = test_flight.altitude(2.62)
            best_sim_alt[0] = sim_alt # Keep track of the altitude calculated
            score = abs(target_altitude - sim_alt)
            
            print(f"Apogee: {sim_alt:.2f} m (Diff: {score:.2f} m)")
            return score
                
        print("Starting optimization loop... This may take a while.")
        
        # 3. RUN OPTIMIZATION
        result = minimize_scalar(
            objective, 
            bounds=(0.0000001, 1.0), # Forces it to hunt between near-perfectly smooth and 1.0
            method='bounded',     # The correct method for 1D bounded optimization
            options={'xatol': 1e-8} # Tells it to stop when it finds the roughness within 8 decimal places
        )
        
        return result, best_sim_alt[0]

if __name__ == "__main__":
    main()