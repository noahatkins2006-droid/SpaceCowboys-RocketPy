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
import sys
import os

## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory
from conversion.openrocket_to_rocketpy import set_openrocket_file, get_nosecone, get_boattail, get_finset, get_rocket, get_motor
from file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path

    ##----------------------------------------##
    ## ---- rocketpy rocket class set up ---- ##
    ##----------------------------------------##
def rocket(rocket:str, on_drag:str, off_drag:str, nose_cone_type:str, inertia:tuple, engine, motor_config = 0, nosecone = True, boattail = True, finset = True):


    on_drag = get_drag_path(on_drag)
    print(os.path.exists(on_drag))

    off_drag = get_drag_path(off_drag)
    print(os.path.exists(off_drag))

    ork_file = get_ork_path(rocket)   # HAS TO HAVE SIM ATTACHED
    print(os.path.exists(ork_file))

    set_openrocket_file(ork_file, motor_config)

    r = Rocket(
        radius=get_rocket(value='radius'),
        mass=get_rocket(value='mass'), 
        inertia=inertia,  #FIXME: This is temporary and will need solved in solidworks
        center_of_mass_without_motor=get_rocket(value='cg_without_motor'), # This will be a user input in the software
        coordinate_system_orientation="nose_to_tail",
        power_on_drag=on_drag,
        power_off_drag=off_drag,
    )

    ##---------------------------------##
    ## ---- rocketpy add features ---- ##
    ##---------------------------------##
    if nosecone:
        nose_cone = r.add_nose(
                    length=get_nosecone(value='length'), 
                    kind=nose_cone_type,
                    position=get_nosecone(value='position')
                    )
    if boattail:
        boat_tail = r.add_tail(  
            top_radius=get_boattail(value='top_radius'), 
            bottom_radius=get_boattail(value='bottom_radius'), 
            length=get_boattail(value='length'), 
            position=(get_boattail(value='position'))
        )
    if finset:
        finset = r.add_trapezoidal_fins(
            n=get_finset(value='n'),
            root_chord=get_finset(value='root_chord'),
            tip_chord=get_finset(value='tip_chord'),
            span=(get_finset(value='span')),
            sweep_length=(get_finset(value='sweep_length')),
            position=(get_finset(value='position')-get_finset(value='root_chord'))
            )
    
    
    r.add_motor(motor=engine, position=(get_motor("position"))) 
    
    r.all_info
    return r
