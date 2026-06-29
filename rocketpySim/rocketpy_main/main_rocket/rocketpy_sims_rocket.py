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
import zoneinfo
import sys
import os
import pandas as pd
import datetime as dt

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory

from conversion.conversion_tool import Conversion
from weather.weather_tool import SpaceWeather 
from file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path, get_fin_path
from conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor, get_railbutton
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

drag = get_drag_path("new_sims_rocket_rough_camo.CSV")

on_drag = pd.read_csv(drag, usecols=["Mach","CD Power-On"]).to_numpy()
off_drag = pd.read_csv(drag, usecols=["Mach","CD Power-Off"]).to_numpy()


ork_file = get_ork_path("Sims_Rocket_H195_Acurate_Mass.ork")   # HAS TO HAVE SIM ATTACHED
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

target_date = "2026-04-30"

local_tz = zoneinfo.ZoneInfo("America/Chicago")
utc_tz = zoneinfo.ZoneInfo("UTC")
###############################
##---------------------------##
## ---- Code Begins Here ----##
##---------------------------##
###############################

for x in hours:     # loop through the hours list
    run_amt +=1 # Iterates every time it runs the for loop
    # 1. Create a full string combining the date and your local hour
    local_time_str = f"{target_date} {x}"

    # 2. Parse the string into a Python datetime object
    local_dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S")

    # 3. Tell Python this datetime is in the Central timezone
    local_dt = local_dt.replace(tzinfo=local_tz)

    # 4. Convert it to UTC
    utc_dt = local_dt.astimezone(utc_tz)

    # 5. Format it back to a string for the Herbie/HRRR download
    hrrr_utc_str = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
    # ----------------------------------

    print(f"Space Cowboys Rocketpy System: Sims Rocket")
    print(f"Simulated Time (Local): {local_time_str}")
    print(f"Simulated Time (UTC):   {hrrr_utc_str}")
    print(f"Simulations Ran: {run_amt}")

    ##########################################
    ##--------------------------------------##
    ## ---- rocketpy environment setup ---- ##
    ##--------------------------------------##
    ##########################################

    sw.hrrr_download(
        launch_time_str=hrrr_utc_str, 
        fxx=0, #SHOULD STAY 0
        save_folder=r"data\weather_data",
        )


    env = sw.to_env(
        latitude=sw.sf_lat, # latitude calling the sw class
        longitude=sw.sf_lon, # longitude calling the sw class
        altitudes_m=np.arange(0, 15000, 1),
        max_height=80000,   # max simulated height in feet
    )

    # env.all_info()
    print("\n")

    ##--------------------------------##
    ## ---- rocketpy motor setup ---- ##
    ##--------------------------------##

    engine = motor.J800t(motor_file=motor_file)
    engine.dry_I_11 = 0
    engine.dry_I_12 = 0
    engine.dry_I_13 = 0
    engine.dry_I_22 = 0
    engine.dry_I_23 = 0
    engine.dry_I_33 = 0


    # engine.all_info()
    #engine.draw()

    ##----------------------------------------##
    ## ---- rocketpy rocket class set up ---- ##
    ##----------------------------------------##

    SimsRocket = Rocket(
        radius=0.062/2,
        mass=1.612, 
        inertia=(0.43,0.43,0.0022),  
        center_of_mass_without_motor=0.75, 
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
    )
    
    ##---------------------------------##
    ## ---- rocketpy add features ---- ##
    ##---------------------------------##

    SimsRocket.add_motor(motor=engine, position=1.328)

    nose_cone = SimsRocket.add_nose(
                length= 0.305, 
                kind="ogive",
                position=0
                )

    # boat_tail = SimsRocket.add_tail(  
    #     top_radius=get_boattail(value='top_radius'), 
    #     bottom_radius=get_boattail(value='bottom_radius'), 
    #     length=get_boattail(value='length'), 
    #     position=(get_boattail(value='position'))
    # )

    rail_buttons = SimsRocket.set_rail_buttons(
         upper_button_position=0.8125,
         lower_button_position=0.8125+.478,
         angular_position=180,
    )
    

    finset = SimsRocket.add_trapezoidal_fins(
        n=3,
        root_chord=0.178,
        tip_chord=0.127,
        span=0.064,
        sweep_length=0.064,
        position=1.144,
        # airfoil = (airfoil_path,"degrees")
    )

    

    main_parachute = SimsRocket.add_parachute(
        name="main",
        cd_s=0.3644,
        trigger="apogee",         
        sampling_rate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5)
    )


    #SimsRocket.plots.stability_margin()
    # SimsRocket.draw()

    ##--------------------------------------##
    ## ----- flight class integration ----- ##
    ##--------------------------------------##

    test_flight = Flight(
        rocket=SimsRocket,    # Input Rocket
        environment=env,    # Input Environment
        rail_length= 3.05,   # Rail Length
        inclination=87,     # Rail Inclination
        heading=45,      # Rail Heading
    )

    ##----------------------------##
    ## ---- run flight class ---- ##
    ##----------------------------##

    test_flight.post_process()  # This will run the simulation

    # This is to check the surface and wind conditions at launch site and at the rail
    test_flight.prints.surface_wind_conditions()
    test_flight.prints.launch_rail_conditions()

    # This is the out of rail conditions
    test_flight.prints.out_of_rail_conditions()

    # This is to check the burn out time
    test_flight.prints.burn_out_conditions()

    # This is to check the apogee conditions
    test_flight.prints.apogee_conditions()

    # This is to check for the ejection of parachutes
    test_flight.prints.events_registered()

    # This is to check for the impact conditions
    test_flight.prints.impact_conditions()

    # This provides a summary of the maximum values recorded during the flight
    test_flight.prints.maximum_values()

    # This is is to plot the results of the flight and show the trajectory
    # test_flight.plots.trajectory_3d()

    export_for_visualizer(test_flight, filename=f"{os.path.abspath(os.path.dirname(__file__))}/googleEarth/sims_rocket_sim_flight_{dt.date.today()}_{x.split(":")[0]}.csv")

    


    