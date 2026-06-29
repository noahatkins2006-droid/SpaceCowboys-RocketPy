import pandas as pd
import time
import os
import sys, logging, csv, operator, datetime, time, glob, os
from pathlib import Path
import math
import numpy as np

# Assuming you have already run your RocketPy simulation
# and your Flight object is named 'test_flight'


def export_for_visualizer(flight, filename="rocketpy_flight.csv", pitch_mode="auto"):
    max_time = flight.z[-1, 0] 
    fps = 30 
    times = np.arange(0, max_time, 1.0 / fps)
    
    launch_unix_time = time.time()
    
    # Extract RocketPy 6-DOF Attitude
    if pitch_mode in ["rocketpy", "hybrid"]:
        yaw_raw = np.array([flight.psi(t) for t in times])
        pitch_raw = np.array([flight.theta(t) for t in times])
        roll_raw = np.array([flight.phi(t) for t in times])
        
        yaw_deg = np.degrees(np.unwrap(np.radians(yaw_raw)))
        pitch_deg = np.degrees(np.unwrap(np.radians(pitch_raw)))
        roll_deg = np.degrees(np.unwrap(np.radians(roll_raw)))
    
    trigger_time = flight.apogee_time 
    data = []
    playback_multiplier = 1.0 
    
    for i, t in enumerate(times):
        current_unixtime = launch_unix_time + (t * playback_multiplier)
        
        lat = flight.latitude(t)
        lon = flight.longitude(t)
        alt_feet = flight.z(t) / 0.3048 
        
        # ----------------------------------------------------
        # ATTITUDE LOGIC SWITCHER
        # ----------------------------------------------------
        if pitch_mode == "rocketpy":
            kml_heading, kml_tilt, kml_roll = yaw_deg[i], -90 - pitch_deg[i], roll_deg[i]
            has_angles = 1
            
        elif pitch_mode == "auto":
            kml_heading, kml_tilt, kml_roll = 0, 0, 0 # Ignored by KML
            has_angles = 0
            
        elif pitch_mode == "hybrid":
            if t <= trigger_time:
                kml_heading, kml_tilt, kml_roll = yaw_deg[i], -90 - pitch_deg[i], roll_deg[i]
                has_angles = 1
            else:
                kml_heading, kml_tilt, kml_roll = 0, 0, 0 # Ignored by KML
                has_angles = 0
        else:
            kml_heading, kml_tilt, kml_roll = 0, 0, 0
            has_angles = 0
        # ----------------------------------------------------

        readable_time = datetime.datetime.fromtimestamp(current_unixtime).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        data.append({
            "UNIXTIME": current_unixtime,
            "LAT": lat,
            "LON": lon,
            "ALT": alt_feet,
            "DUMMY_COL": 0,
            "VALID_FLAG": 1,
            "FLIGHT_TIME_S": t,
            "READABLE_TIME": readable_time,
            "HEADING": kml_heading,
            "TILT": kml_tilt,
            "ROLL": kml_roll,
            "HAS_ANGLES": has_angles # NEW FLAG
        })
        
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Successfully exported {len(df)} data points at {fps} FPS to {filename} using '{pitch_mode}' mode.")
    
    convert_file_to_kml(filename)
    return filename

def convert_file_to_kml(filename):
    totalflights = 1 
    try:
        droppedFile = filename
        print(f"[File Found]: {droppedFile}")

        rows = []
        with open(droppedFile, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            fields = next(csvreader)
            for row in csvreader:
                rows.append(row)

        latindex = fields.index("LAT")
        lonindex = fields.index("LON")
        altindex = fields.index("ALT")
        unixtimeindex = fields.index("UNIXTIME")
        headingindex = fields.index("HEADING")
        tiltindex = fields.index("TILT")
        rollindex = fields.index("ROLL")
        hasanglesindex = fields.index("HAS_ANGLES") # New flag

        rows = sorted(rows, key=lambda x: float(x[unixtimeindex]))

        outfile_name = str(droppedFile).replace('.csv', '_animated.kml')
        
        whens = []
        coords = []
        angles = [] 
        flight_data = [] 
        
        lasttimeUNIX = float(rows[0][unixtimeindex])
        last_has_angles = int(rows[0][hasanglesindex])
        
        for row in rows:
            if float(row[5]) <= 0:
                continue
                
            current_time = float(row[unixtimeindex])
            current_has_angles = int(row[hasanglesindex])
            
            # Start a new track segment if 60s passes OR if the pitch mode swaps
            if (current_time - lasttimeUNIX > 60 or current_has_angles != last_has_angles) and len(whens) > 0:
                flight_data.append({'whens': whens, 'coords': coords, 'angles': angles, 'has_angles': last_has_angles})
                whens = []
                coords = []
                angles = []
                totalflights += 1
                
            dt_utc = datetime.datetime.fromtimestamp(current_time, datetime.timezone.utc)
            when_str = dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            whens.append(when_str)
            
            alt_meters = float(row[altindex]) * 0.3048
            coord_str = f"{row[lonindex]} {row[latindex]} {alt_meters}"
            coords.append(coord_str)
            
            angle_str = f"{row[headingindex]} {row[tiltindex]} {row[rollindex]}"
            angles.append(angle_str)
            
            lasttimeUNIX = current_time
            last_has_angles = current_has_angles

        if len(whens) > 0:
            flight_data.append({'whens': whens, 'coords': coords, 'angles': angles, 'has_angles': last_has_angles})

        with open(outfile_name, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n')
            f.write('\t<Document>\n')
            f.write('\t\t<name>RocketPy 6-DOF Flight</name>\n')
            
            f.write('\t\t<Style id="track_style">\n')
            f.write('\t\t\t<LineStyle>\n')
            f.write('\t\t\t\t<color>ff0000ff</color>\n')
            f.write('\t\t\t\t<width>4</width>\n')
            f.write('\t\t\t</LineStyle>\n')
            f.write('\t\t</Style>\n')

            # Auto-play tour that follows the rocket
            f.write('\t\t<gx:Tour>\n')
            f.write('\t\t\t<name>Follow Rocket</name>\n')
            f.write('\t\t\t<gx:Playlist>\n')
            # FlyTo the launch point first
            first_coord = flight_data[0]['coords'][0].split()
            f.write('\t\t\t\t<gx:FlyTo>\n')
            f.write('\t\t\t\t\t<gx:duration>2</gx:duration>\n')
            f.write('\t\t\t\t\t<gx:flyToMode>bounce</gx:flyToMode>\n')
            f.write('\t\t\t\t\t<LookAt>\n')
            f.write(f'\t\t\t\t\t\t<longitude>{first_coord[0]}</longitude>\n')
            f.write(f'\t\t\t\t\t\t<latitude>{first_coord[1]}</latitude>\n')
            f.write(f'\t\t\t\t\t\t<altitude>{first_coord[2]}</altitude>\n')
            f.write('\t\t\t\t\t\t<range>500</range>\n')
            f.write('\t\t\t\t\t\t<tilt>60</tilt>\n')
            f.write('\t\t\t\t\t\t<heading>0</heading>\n')
            f.write('\t\t\t\t\t\t<altitudeMode>absolute</altitudeMode>\n')
            f.write('\t\t\t\t\t</LookAt>\n')
            f.write('\t\t\t\t</gx:FlyTo>\n')
            # Animate along the track with FlyTo at key points
            all_coords = []
            for seg in flight_data:
                all_coords.extend(seg['coords'])
            step = max(1, len(all_coords) // 60)
            for idx in range(0, len(all_coords), step):
                c = all_coords[idx].split()
                alt_f = float(c[2])
                rng = max(200, alt_f * 0.3)
                f.write('\t\t\t\t<gx:FlyTo>\n')
                f.write(f'\t\t\t\t\t<gx:duration>{1.0 / (60 / step):.2f}</gx:duration>\n')
                f.write('\t\t\t\t\t<gx:flyToMode>smooth</gx:flyToMode>\n')
                f.write('\t\t\t\t\t<LookAt>\n')
                f.write(f'\t\t\t\t\t\t<longitude>{c[0]}</longitude>\n')
                f.write(f'\t\t\t\t\t\t<latitude>{c[1]}</latitude>\n')
                f.write(f'\t\t\t\t\t\t<altitude>{c[2]}</altitude>\n')
                f.write(f'\t\t\t\t\t\t<range>{rng:.0f}</range>\n')
                f.write('\t\t\t\t\t\t<tilt>60</tilt>\n')
                f.write('\t\t\t\t\t\t<heading>0</heading>\n')
                f.write('\t\t\t\t\t\t<altitudeMode>absolute</altitudeMode>\n')
                f.write('\t\t\t\t\t</LookAt>\n')
                f.write('\t\t\t\t</gx:FlyTo>\n')
            f.write('\t\t\t</gx:Playlist>\n')
            f.write('\t\t</gx:Tour>\n')

            for i, flight in enumerate(flight_data):
                f.write('\t\t<Placemark>\n')
                f.write(f'\t\t\t<name>Flight Segment {i+1}</name>\n')
                f.write('\t\t\t<styleUrl>#track_style</styleUrl>\n')
                f.write('\t\t\t<gx:Track>\n')
                f.write('\t\t\t\t<altitudeMode>absolute</altitudeMode>\n')
                
                for w in flight['whens']:
                    f.write(f'\t\t\t\t<when>{w}</when>\n')
                
                for c in flight['coords']:
                    f.write(f'\t\t\t\t<gx:coord>{c}</gx:coord>\n')
                    
                # ONLY write angles if the flag is 1
                if flight['has_angles'] == 1:
                    for a in flight['angles']:
                        f.write(f'\t\t\t\t<gx:angles>{a}</gx:angles>\n')
                    
                f.write('\t\t\t\t<Model>\n')
                f.write('\t\t\t\t\t<altitudeMode>absolute</altitudeMode>\n')
                f.write('\t\t\t\t\t<Scale>\n')
                f.write('\t\t\t\t\t\t<x>0.001</x>\n')
                f.write('\t\t\t\t\t\t<y>0.001</y>\n')
                f.write('\t\t\t\t\t\t<z>0.001</z>\n')
                f.write('\t\t\t\t\t</Scale>\n')
                f.write('\t\t\t\t\t<Link>\n')
                f.write('\t\t\t\t\t\t<href>rocket_model.dae</href>\n')
                f.write('\t\t\t\t\t</Link>\n')
                f.write('\t\t\t\t</Model>\n')

                f.write('\t\t\t</gx:Track>\n')
                f.write('\t\t</Placemark>\n')

            f.write('\t</Document>\n')
            f.write('</kml>\n')

        print(f"[Animated KML Created]: {outfile_name}")
        os.remove(droppedFile)
        return outfile_name

    except Exception as e:
        print(f"Conversion failed: {e}")




if __name__ == "__main__":
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

    from rocketpySim.conversion.conversion_tool import Conversion
    from rocketpySim.weather.weather_tool import SpaceWeather 
    from rocketpySim.file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path, get_fin_path
    from rocketpySim.conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor
    from rocketpySim.motors.motor_collection import motorClass


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

    on_drag = get_drag_path("SimsRocket_Camo_CD_On.CSV")
    print(os.path.exists(on_drag))

    off_drag = get_drag_path("SimsRocket_Camo_CD_Off.CSV")
    print(os.path.exists(off_drag))

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

    ###############################
    ##---------------------------##
    ## ---- Code Begins Here ----##
    ##---------------------------##
    ###############################

    for x in hours[8:]:     # loop through the hours list

        run_amt +=1 # Iterates every time it runs the for loop

        print(f"Space Cowboys Rocketpy System: Sims Rocket")
        print(f"Simulated Time: {x}")
        print(f"Simulations Ran: {run_amt}")

        ##########################################
        ##--------------------------------------##
        ## ---- rocketpy environment setup ---- ##
        ##--------------------------------------##
        ##########################################

        sw.hrrr_download(
            launch_time_str=f"2026-04-09 {x}",
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

        engine = motor.H195nt(motor_file=motor_file)


        # engine.all_info()
        #engine.draw()

        ##----------------------------------------##
        ## ---- rocketpy rocket class set up ---- ##
        ##----------------------------------------##

        SimsRocket = Rocket(
            radius=get_rocket(value='radius'),
            mass=get_rocket(value='mass') - get_motor(value="full_mass"), 
            inertia=(0.002558,0.002558,0.0000257),  #FIXME: This is temporary and will need solved in solidworks
            center_of_mass_without_motor=get_rocket("cg_without_motor"), # This will be a user input in the software
            coordinate_system_orientation="nose_to_tail",
            power_on_drag=on_drag,
            power_off_drag=off_drag,
        )
        
        ##---------------------------------##
        ## ---- rocketpy add features ---- ##
        ##---------------------------------##

        SimsRocket.add_motor(motor=engine, position=0.69)    #TODO

        nose_cone = SimsRocket.add_nose(
                    length= get_nosecone(value='length'), 
                    kind="lvhaack",
                    position=get_nosecone(value='position')
                    )

        # boat_tail = SimsRocket.add_tail(  
        #     top_radius=get_boattail(value='top_radius'), 
        #     bottom_radius=get_boattail(value='bottom_radius'), 
        #     length=get_boattail(value='length'), 
        #     position=(get_boattail(value='position'))
        # )

        rail_buttons = SimsRocket.set_rail_buttons(
            upper_button_position=0.41,
            lower_button_position=0.41+0.254,
            angular_position=180,
        )
        

        finset = SimsRocket.add_trapezoidal_fins(
            n=get_finset(value='n'),
            root_chord=get_finset(value='root_chord'),
            tip_chord=get_finset(value='tip_chord'),
            span=(get_finset(value='span')),
            sweep_length=(get_finset(value='sweep_length')),
            position=(get_finset(value='position')-get_finset(value='root_chord')),
            # airfoil = (airfoil_path,"degrees")
        )

        

        main_parachute = SimsRocket.add_parachute(
            name="main",
            cd_s=0.1312236968,
            trigger=350,         
            sampling_rate=105,
            lag=1.5,
            noise=(0, 8.3, 0.5)
        )


        #SimsRocket.plots.stability_margin()
        SimsRocket.draw()

        ##--------------------------------------##
        ## ----- flight class integration ----- ##
        ##--------------------------------------##

        test_flight = Flight(
            rocket=SimsRocket,    # Input Rocket
            environment=env,    # Input Environment
            rail_length= 2.8702,   # Rail Length
            inclination=89.5,     # Rail Inclination
            heading=0,      # Rail Heading
        )


        ##----------------------------##
        ## ---- run flight class ---- ##
        ##----------------------------##

        test_flight.post_process()  # This will run the simulation

        # This is to check the surface and wind conditions at launch site and at the rail
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

        # This is is to plot the results of the flight and show the trajectory
        test_flight.plots.trajectory_3d()

        export_for_visualizer(test_flight, filename="sim_rocket_sim_flight.csv")
