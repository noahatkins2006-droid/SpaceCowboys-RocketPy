## Conversion Class
## Goal: Convert units from emperical to metric

# Class Set-up with conversions being different functions
class Conversion:

    def __init__(self):
        pass
    #@ staticmethod

    def FT_to_Meters(self, variable):
        return variable / 3.281

    def FT_to_Centimeters(self, variable):
        return variable * 30.48

    def FT_to_Inches(self, variable):
        return variable * 12
    
    def LBs_to_Kilo(self, variable):
        return variable / 2.205
    
    def In_to_M(self, variable):
        return variable / 39.37
    
    def Gram_to_Kilo(self, variable):
        return variable / 1000
    
    def LB_cubic_in_to_Kilo_cubic_M(self, variable):
        return variable *  27680
    
    def mm_to_m(self, variable):
        return variable / 1000
    
    def cm_to_m(self, variable):
        return variable / 100