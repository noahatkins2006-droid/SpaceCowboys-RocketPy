"""
Motor Library for Space Cowboys Rocketry

Pre-configured SolidMotor definitions for the team's rocket fleet.
Motor parameters sourced from manufacturer data and real-world experimentation.
"""

from rocketpy import SolidMotor
from conversions import Conversion

C = Conversion()


class MotorLibrary:
    """Collection of pre-configured rocket motors."""

    def O5500X(self, motor_file: str = "") -> SolidMotor:
        """
        AeroTech O5500X-PS - Primary research motor for Bandit.
        Inertia values gathered from real-world experimentation.
        """
        return SolidMotor(
            thrust_source=motor_file,
            dry_mass=6.71316708,
            dry_inertia=(1.241235258, 1.241235258, 0.014265125),
            nozzle_radius=0.0762 / 2,
            grain_number=7,
            grain_density=1638,
            grain_outer_radius=0.085725 / 2,
            grain_initial_inner_radius=0.0381 / 2,
            grain_initial_height=0.18415,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.7525385,
            center_of_dry_mass_position=0.771525,
            nozzle_position=0,
            throat_radius=0.03302 / 2,
            coordinate_system_orientation="nozzle_to_combustion_chamber",
        )

    def M1340W(self, motor_file: str = "") -> SolidMotor:
        """AeroTech M1340W - Medium-power motor."""
        return SolidMotor(
            thrust_source=motor_file,
            dry_mass=C.Gram_to_Kilo(2949.00),
            dry_inertia=(1.16485, 1.16485, 0.0596609693875),
            nozzle_radius=C.In_to_M(1.75),
            grain_number=5,
            grain_density=C.LB_cubic_in_to_Kilo_cubic_M(0.0656),
            grain_outer_radius=C.In_to_M(3.365 / 2),
            grain_initial_inner_radius=C.In_to_M(3.27 / 2),
            grain_initial_height=C.In_to_M(6.00),
            grain_separation=C.In_to_M(0.07),
            grains_center_of_mass_position=C.In_to_M(20),
            center_of_dry_mass_position=C.In_to_M(20),
            nozzle_position=0,
            burn_time=5.5,
            throat_radius=C.In_to_M(0.734),
            coordinate_system_orientation="nozzle_to_combustion_chamber",
        )

    def H195NT(self, motor_file: str = "") -> SolidMotor:
        """AeroTech HP-H195NT - Small test motor for Sims Rocket."""
        return SolidMotor(
            thrust_source=motor_file,
            dry_mass=C.Gram_to_Kilo(82),
            dry_inertia=(0.000301, 0.000301, 0.0000163),
            nozzle_radius=0.00889,
            grain_number=3,
            grain_density=1750,
            grain_outer_radius=0.0254 / 2,
            grain_initial_inner_radius=0.009525 / 2,
            grain_initial_height=0.0508,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.1016,
            center_of_dry_mass_position=0.11176,
            nozzle_position=0,
            burn_time=1.15,
            throat_radius=0.004064,
            coordinate_system_orientation="nozzle_to_combustion_chamber",
        )

    def J450DM(self, motor_file: str = "") -> SolidMotor:
        """AeroTech J450DM - Mid-power motor."""
        return SolidMotor(
            thrust_source=motor_file,
            dry_mass=C.Gram_to_Kilo(468),
            dry_inertia=(0.00594, 0.00594, 0.00020),
            nozzle_radius=0.009144,
            grain_number=3,
            grain_density=1750,
            grain_outer_radius=0.047498 / 2,
            grain_initial_inner_radius=0.015875 / 2,
            grain_initial_height=0.0910082,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.1670558,
            center_of_dry_mass_position=0.186055,
            nozzle_position=0,
            burn_time=2.4,
            throat_radius=0.004572,
            coordinate_system_orientation="nozzle_to_combustion_chamber",
        )

    def J800T(self, motor_file: str = "") -> SolidMotor:
        """AeroTech J800T - Mid-power motor."""
        return SolidMotor(
            thrust_source=motor_file,
            dry_mass=C.Gram_to_Kilo(541),
            dry_inertia=(0.00594, 0.00594, 0.00020),
            nozzle_radius=0.009144,
            grain_number=3,
            grain_density=4309,
            grain_outer_radius=0.047498 / 2,
            grain_initial_inner_radius=0.015875 / 2,
            grain_initial_height=0.0910082,
            grain_separation=0.0015875,
            grains_center_of_mass_position=0.1670558,
            center_of_dry_mass_position=0.186055,
            nozzle_position=0,
            throat_radius=0.004572,
            coordinate_system_orientation="nozzle_to_combustion_chamber",
        )
