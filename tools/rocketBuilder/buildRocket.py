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
import math

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory

from rocketpySim.conversion.conversion_tool import Conversion
from rocketpySim.weather.weather_tool import SpaceWeather 
from rocketpySim.file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path, get_fin_path
from rocketpySim.conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor,get_freeform_finset, get_parachute, advanced_part_search
from rocketpySim.motors.motor_collection import motorClass
from tools.flight_csv.flight_csv import export_for_visualizer
from tools.automated_RASAero.autoRASAero import getCDFiles


C = Conversion()
sw = SpaceWeather()

import requests
import tempfile

import requests

def fetch_motor_eng(motor_name):
    """
    Searches ThrustCurve.org for a motor, requests the pre-parsed JSON data samples 
    (bypassing raw RASP files), cleans the math, and returns a 2D array for RocketPy.
    """
    search_url = "https://www.thrustcurve.org/api/v1/search.json"
    download_url = "https://www.thrustcurve.org/api/v1/download.json"

    # 1. Search for the motor ID
    search_payload = {"commonName": motor_name, "maxResults": 1}
    response = requests.post(search_url, json=search_payload)
    if response.status_code != 200:
        raise ConnectionError(f"ThrustCurve Search API Error {response.status_code}")
        
    data = response.json()
    if not data.get("results"):
        raise ValueError(f"Motor '{motor_name}' not found on ThrustCurve.org.")

    motor_id = data["results"][0]["motorId"]
    brand = data["results"][0].get("manufacturerAbbrev", "Unknown")
    designation = data["results"][0].get("designation", motor_name)
    print(f"Found: {brand} {designation} (ID: {motor_id})")

    # -----------------------------------------
    # 2. Request Pre-Parsed Samples (The Magic Trick)
    # -----------------------------------------
    download_payload = {
        "motorId": motor_id,
        "data": "samples" # Tells the API to give us pure numbers, no text files!
    }
    dl_response = requests.post(download_url, json=download_payload)
    if dl_response.status_code != 200:
        raise ConnectionError(f"ThrustCurve Download API Error {dl_response.status_code}")
        
    dl_data = dl_response.json()
    if not dl_data.get("results"):
        raise ValueError(f"No simulation files available for '{brand} {designation}'.")

    # 3. Extract the array of pure math samples
    samples = None
    for file_data in dl_data["results"]:
        if "samples" in file_data and len(file_data["samples"]) > 0:
            samples = file_data["samples"]
            break

    if not samples:
        raise ValueError(f"No parsed thrust samples found for '{brand} {designation}'.")

    # 4. Construct the strict 2D array for RocketPy
    thrust_curve_data = []
    last_time = -0.001 

    for s in samples:
        t = float(s["time"])
        thrust_val = float(s["thrust"])

        # Force strict mathematical progression to prevent RocketPy's ZeroDivisionError
        if t <= last_time:
            t = last_time + 0.0001

        thrust_curve_data.append([t, thrust_val])
        last_time = t

    # Return the perfect 2D list straight into SolidMotor!
    return thrust_curve_data

def buildRocket(orkpath:str, cdpath:str, motor):
    
    set_openrocket_file(orkpath,0,True)
    
    on_drag = pd.read_csv(cdpath, usecols=["Mach","CD Power-On"]).to_numpy()
    off_drag = pd.read_csv(cdpath, usecols=["Mach","CD Power-Off"]).to_numpy()

    rocket = Rocket(
        radius=get_rocket(value='radius'),
        mass=get_rocket(value='mass') - get_motor(value="full_mass"), 
        inertia=get_rocket('inertia'),  
        center_of_mass_without_motor=get_rocket("cg_without_motor"), # This will be a user input in the software
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
    )

    nose_cone = rocket.add_nose(
                length= get_nosecone(value='length'), 
                kind="lvhaack", #TODO add ability to get nosecone types from openrocket
                position=get_nosecone(value='position')
                )
    try:
        get_boattail('bottom_radius')
        boat_tail = rocket.add_tail(  
            top_radius=get_boattail(value='top_radius'), 
            bottom_radius=get_boattail(value='bottom_radius'), 
            length=get_boattail(value='length'), 
            position=(get_boattail(value='position'))
        )
    except:
        pass

    try:
        get_finset('root_chord')
        finset = rocket.add_trapezoidal_fins(
        n=get_finset(value='n'),
        root_chord=get_finset(value='root_chord'),
        tip_chord=get_finset(value='tip_chord'),
        span=(get_finset(value='span')),
        sweep_length=(get_finset(value='sweep_length')),
        position=(get_finset(value='position')-get_finset(value='root_chord')*2),
        )
    except:
        pass

    try:
        freefinset = rocket.add_free_form_fins(
        n=get_freeform_finset('n'),
        shape_points= get_freeform_finset('shape_points'),
        position= get_freeform_finset('position'),
        radius = get_rocket('radius')
        )
    except:
        pass

    try:
        paralist = []
        for i in range(len(advanced_part_search("parachute.getlist"))):
            paralist[i] = rocket.add_parachute(
            name=get_parachute('name',i),
            cd_s=((((get_parachute('diameter')/2)**2)*math.pi)*get_parachute('cd')),
            trigger=get_parachute('deployment'),      
            sampling_rate=105,     
            lag=get_parachute('delay'),               
            noise=(0, 8.3, 0.5)    
            )
    except:
        pass

    try:
        rocket.add_motor(motor=motor,
                          position=get_motor('position')
                          )
    except:
        pass

    return(rocket)

def buildMotor(name,dry_mass,dry_inertia_long, dry_inertia_rot,nozzle_radius,grain_number,grain_density, grain_outer_radius,grain_initial_inner_radius,grain_initial_height,grain_separation,grains_center_of_mass_position,center_of_dry_mass_position,nozzle_position,throat_radius):

    motor = SolidMotor(
        thrust_source=fetch_motor_eng(name),    
        dry_mass=C.Gram_to_Kilo(dry_mass),
        dry_inertia=(dry_inertia_long,dry_inertia_long,dry_inertia_rot),  #TODO : This is an estimation 10/7/2025, create solidworks model and get tuple from there
        nozzle_radius=nozzle_radius,
        grain_number=grain_number,
        grain_density=grain_density,
        grain_outer_radius=grain_outer_radius,
        grain_initial_inner_radius=grain_initial_inner_radius,
        grain_initial_height=grain_initial_height,
        grain_separation=grain_separation,
        grains_center_of_mass_position=grains_center_of_mass_position,
        center_of_dry_mass_position=center_of_dry_mass_position,
        nozzle_position=nozzle_position,
        throat_radius=throat_radius,
        coordinate_system_orientation='nozzle_to_combustion_chamber')
    
    return(motor)

if __name__ == "__main__":
    try:
        user_input = "O5500X-PS" 
        eng_file_path = fetch_motor_eng(user_input)
        print(f"Temporary .eng file successfully saved at: {eng_file_path}")
    except Exception as e:
        print(f"Error: {e}")

