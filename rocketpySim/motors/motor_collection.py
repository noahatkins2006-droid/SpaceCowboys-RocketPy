from rocketpy import Environment, SolidMotor, Rocket, Flight, MonteCarlo
import sys
import os
## --- Home Brewed scripts --- ##
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Opening whole directory
from rocketpySim.conversion.conversion_tool import Conversion
from rocketpySim.file_paths.file_path_func import get_motor_path, get_drag_path, get_ork_path

C = Conversion()

class motorClass:

    def O5500x(self, motor_file:str = ''):
        mf = get_motor_path("AeroTech_O5500X-PS.eng")

        O5500x = SolidMotor(
        # thrust_source=mf,    
        # dry_mass=C.Gram_to_Kilo(variable=7158.00),
        # #dry intertia
        # dry_inertia=(1.6892,1.6892,0.0150),
        # nozzle_radius=C.In_to_M(variable=2.737),
        # grain_number=7,
        # grain_density=C.LB_cubic_in_to_Kilo_cubic_M(variable=0.06333),
        # grain_outer_radius=C.In_to_M(variable=3.37/2),
        # grain_initial_inner_radius=C.In_to_M(variable=1.50/2),
        # grain_initial_height=C.In_to_M(variable=7.25),
        # grain_separation=C.In_to_M(variable=0.07),
        #grains center of mass position
        grains_center_of_mass_position = 0.7525385,
        #center of dry mass position
        center_of_dry_mass_position=0.771525,
        # #nozzle position
        nozzle_position = 0,
        # burn_time=3.997,
        throat_radius= 0.03302/2,
        coordinate_system_orientation='nozzle_to_combustion_chamber',
        
        thrust_source=mf,      #This is aquired on the ThrustCurve Website, look up the motor and download an eng file, then link it by copying a path
        dry_mass=6.71316708,       #Kilograms
        # dry_inertia=(1.16485,1.16485,0.0596609693875),       #Tuple or list containing the motor’s dry mass inertia tensor components, in kg*m^2. This inertia is defined with respect to the the center_of_dry_mass_position position. Assuming e_3 is the rocket’s axis of symmetry, e_1 and e_2 are orthogonal and form a plane perpendicular to e_3, the dry mass inertia tensor components must be given in the following order: (I_11, I_22, I_33, I_12, I_13, I_23), where I_ij is the component of the inertia tensor in the direction of e_i x e_j. Alternatively, the inertia tensor can be given as (I_11, I_22, I_33), where I_12 = I_13 = I_23 = 0.
        dry_inertia=(1.241235258,1.241235258,0.014265125), #gathered from irl experimentation. Parallel moment estimated from motor drawings and irl weight.
        nozzle_radius=0.0762/2,    #diameter to radius 
        grain_number=7,      #Number of grains in the motor
        grain_density=1638,     #kilogram/meters cubed
        grain_outer_radius= 0.085725/2,        #Measured in meters
        grain_initial_inner_radius=0.0381/2,        #Measured in meters
        grain_initial_height=0.18415,      #Measured in meters
        grain_separation=0.0015875,      #Distance between two grains in meters
        
        
        
        )
        return O5500x
    
    def M1340w(self, motor_file = ''):
        mf = get_motor_path("AeroTech_M1340W.eng")

        M1340w = SolidMotor(
        thrust_source=mf,    
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
        return M1340w
    
    def H195nt(self, motor_file:str = ''):
        mf = get_motor_path("AeroTech_HP-H195NT.eng")

        H195 = SolidMotor(
            thrust_source=mf,
            dry_mass=C.Gram_to_Kilo(variable=82),
            dry_inertia=(0.000301,0.000301,0.0000163),
            nozzle_radius=0.00889,
            grain_number=3,
            grain_density=1750,
            grain_outer_radius=0.0254/2,
            grain_initial_inner_radius=0.009525/2,
            grain_initial_height=0.0508,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.1016,
            center_of_dry_mass_position=0.11176,
            nozzle_position=0,
            burn_time=1.15,
            throat_radius=0.004064,
            coordinate_system_orientation='nozzle_to_combustion_chamber'
        )

        return H195
    
    def J450dm(self, motor_file:str = ''):
        mf = get_motor_path("AeroTech_J450DM.eng")

        J450 = SolidMotor(
            thrust_source=mf,
            dry_mass=C.Gram_to_Kilo(variable=468),
            dry_inertia=(0.00594, 0.00594, 0.00020),
            nozzle_radius=0.009144,
            grain_number=3,
            grain_density=1750,
            grain_outer_radius=0.047498/2,
            grain_initial_inner_radius=0.015875/2,
            grain_initial_height=0.0910082,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.1670558,
            center_of_dry_mass_position=0.186055,
            nozzle_position=0,
            burn_time=2.4,
            throat_radius=0.004572,
            coordinate_system_orientation='nozzle_to_combustion_chamber'
        )

        return J450
    
    def J800t(self, motor_file:str = ''):
        mf = get_motor_path("AeroTech_J800T.eng")

        J800 = SolidMotor(
            thrust_source=mf,
            dry_mass=C.Gram_to_Kilo(variable=541),
            dry_inertia=(0.00594, 0.00594, 0.00020),
            nozzle_radius=0.009144,
            grain_number=3,
            grain_density=4309,
            grain_outer_radius=0.047498/2,
            grain_initial_inner_radius=0.015875/2,
            grain_initial_height=0.0910082,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.1670558,
            center_of_dry_mass_position=0.186055,
            nozzle_position=0,
            throat_radius=0.004572,
            coordinate_system_orientation='nozzle_to_combustion_chamber'
        )

        return J800
    
    def broomstick(self,motorfile:str =''):
        
        broomstick = HybridMotor
    

if __name__ == "__main__":
    mymotor = motorClass()
    thismotor = mymotor.J800t()
    thismotor.info()
    thismotor.draw()
    