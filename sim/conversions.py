"""
Unit Conversion Utilities

Simple imperial-to-metric conversions used throughout the simulation code.
"""


class Conversion:
    """Unit conversion helper for imperial to metric."""

    @staticmethod
    def FT_to_Meters(variable: float) -> float:
        return variable / 3.281

    @staticmethod
    def FT_to_Centimeters(variable: float) -> float:
        return variable * 30.48

    @staticmethod
    def FT_to_Inches(variable: float) -> float:
        return variable * 12

    @staticmethod
    def LBs_to_Kilo(variable: float) -> float:
        return variable / 2.205

    @staticmethod
    def In_to_M(variable: float) -> float:
        return variable / 39.37

    @staticmethod
    def Gram_to_Kilo(variable: float) -> float:
        return variable / 1000

    @staticmethod
    def LB_cubic_in_to_Kilo_cubic_M(variable: float) -> float:
        return variable * 27680

    @staticmethod
    def mm_to_m(variable: float) -> float:
        return variable / 1000

    @staticmethod
    def cm_to_m(variable: float) -> float:
        return variable / 100
