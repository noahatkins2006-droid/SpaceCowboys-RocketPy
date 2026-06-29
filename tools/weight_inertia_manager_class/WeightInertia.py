import csv

class WeightInertia:
    def __init__(self, mass=0, inertia=None, cg_pos=0):
        if inertia is None:
            inertia = [0, 0, 0]
        self.massComponents = []
        if mass > 0:
            self.addComplexShape(mass, inertia, cg_pos)
        self.mass = mass
        self.inertia = inertia
        self.cg_pos = cg_pos

    def addComplexShape(self, mass, inertia, cg_pos, radius=0):
        self.massComponents.append(_ComplexShape(mass, inertia, cg_pos, radius))

    def addPointMass(self, mass, cg_pos, radius=0):
        self.massComponents.append(_PointMass(mass, cg_pos, radius))

    def calculate_cg(self):
        massPosSum = 0
        massTotal = 0
        for i in self.massComponents:
            massTotal += i.mass
            massPosSum += (i.mass * i.cg_pos)
        
        # Prevent ZeroDivisionError if rocket is completely empty
        if massTotal == 0:
            return 0
        return massPosSum / massTotal

    def calculate_mass(self):
        massTotal = 0
        for i in self.massComponents:
            massTotal += i.mass
        return massTotal
    
    def calculate_mmoi(self):
        newcg = self.calculate_cg()
        sum_ref_mmoi = 0
        sum_parallel_mmoi = 0
        
        for i in self.massComponents:
            # Using isinstance instead of string comparison for better reliability
            if isinstance(i, _ComplexShape):
                dist_from_orig_cg = abs(self.cg_pos - i.cg_pos)
                mmoi_at_orig_cg = i.inertia[0] + (i.mass)*(dist_from_orig_cg**2)
                component_parallel_mmoi = i.inertia[2]

            if isinstance(i, _PointMass):
                dist_from_orig_cg = abs(self.cg_pos - i.cg_pos)
                mmoi_at_orig_cg = (i.mass)*(dist_from_orig_cg**2)
                # Corrected formula for a point mass at a given radius
                component_parallel_mmoi = (i.mass)*(i.radius**2)
            
            sum_ref_mmoi += mmoi_at_orig_cg
            sum_parallel_mmoi += component_parallel_mmoi
            
        delta_cg = abs(self.cg_pos - newcg)
        mmoi_at_new_cg = sum_ref_mmoi - (self.calculate_mass() * (delta_cg**2))
        return [mmoi_at_new_cg, mmoi_at_new_cg, sum_parallel_mmoi]

    def set_mass(self):
        self.mass = self.calculate_mass()
    
    def set_cg(self):
        self.cg_pos = self.calculate_cg()

    def set_mmoi(self):
        self.inertia = self.calculate_mmoi()


class _ComplexShape:
    def __init__(self, mass, inertia, cg_pos, radius):
        self.mass = mass
        self.inertia = inertia
        self.cg_pos = cg_pos
        self.radius = radius


class _PointMass:
    def __init__(self, mass, cg_pos, radius):
        self.mass = mass
        self.cg_pos = cg_pos
        self.radius = radius


# --- CSV Parsing Logic ---
def process_rocket_csv(filepath):
    # Initialize an empty rocket
    rocket = WeightInertia(mass=0, inertia=[0,0,0], cg_pos=0)
    fixed_radius = 0.07721599999999999
    
    print("Loading components from CSV...")
    print("-" * 50)
    
    with open(filepath, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            component_name = row['Component']
            
            # Skip the 'Total' summary row so we don't double-count mass
            if "Total" in component_name:
                continue
            
            try:
                mass = float(row['Mass Kg'])
                cg = float(row['CG Position'])
            except ValueError:
                # Skips any rows that have empty or invalid text instead of numbers
                continue 
            
            # Add the component to the class
            rocket.addPointMass(mass, cg, fixed_radius)
            print(f"Added: {component_name:<30} | Mass: {mass:>7.4f} | CG: {cg:>7.4f}")

    print("-" * 50)
    print("CALCULATION RESULTS:")
    print(f"Total Mass:    {rocket.calculate_mass():.4f} kg")
    print(f"System CG:     {rocket.calculate_cg():.4f} m from origin")
    
    mmoi = rocket.calculate_mmoi()
    print(f"Transverse I:  {mmoi[0]:.4f} kg·m²")
    print(f"Parallel I:    {mmoi[2]:.4f} kg·m²")

if __name__ == "__main__":
    # Ensure this matches the name of your file exactly
    process_rocket_csv(r'C:\Users\dahle\Documents\Simulations-Repository\tools\weight_inertia_manager_class\BanditComponentMass.csv')