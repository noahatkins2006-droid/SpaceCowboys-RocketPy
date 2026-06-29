import sys
import os
import numpy as np
from scipy.optimize import minimize
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import your automated RASAero tools
from tools.automated_RASAero.autoRASAero import createModifiedRocket, getData, getCDFiles

# Import the RocketPy simulation runner 
from tools.optimization.optimizationSimulationRunner import run_with_timeout

def maximize_alt(rocket_file_path, arrayValuesToAdjust, arrayValueBounds, targetStability, acceptableStabilityDeviation):
    """
    Maximizes rocket altitude by iterating through RASAero and RocketPy simulations.
    
    :param rocket_file_path: Path to the base .CDX1 file.
    :param arrayValuesToAdjust: List of strings (tags) to modify (e.g., ["BodyTube:2.Fin.Span"]).
    :param arrayValueBounds: List of tuples defining (min, max) for each tag.
    :return: The Scipy optimization result object.
    """
    
    # 1. Generate an initial guess (x0) using the midpoint of each provided bound
    x0 = np.array([11.999999987759999,13,6.299999993574,11.999999987759999])
    
    # Define an output directory to store all the generated files so things stay clean
    base_dir = os.path.dirname(rocket_file_path)
    output_dir = os.path.join(base_dir, "Optimization_Results")
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Define the objective function for Scipy to evaluate
    def objective(x):
        print(x)
        # Map the current Scipy variables (x) to their corresponding XML tags
        editDictionary = {tag: round(val, 4) for tag, val in zip(arrayValuesToAdjust, x)}
        
        # --- REMOVED THE TRY BLOCK ---
        
        # Step A: Create the modified .CDX1 file
        modified_cdx1_path, new_filename = createModifiedRocket(rocket_file_path, editDictionary)
        
        # Step B: Run RASAero CLI to get the raw flight data CSV
        csv_path = getData(modified_cdx1_path, output_dir, new_filename)
        
        # Step C: Split the CSV into Power-On and Power-Off drag files
        on_drag_path, off_drag_path = getCDFiles(csv_path)
        
        # Step D: Run RocketPy using the new drag curves and modified .CDX1
        sim_result = run_with_timeout((on_drag_path, off_drag_path, modified_cdx1_path))

        if sim_result == (0, 0) or sim_result is None:
            print("Simulation failed or timed out. Assigning massive penalty to optimizer.")
            return 999999.0
        
        altitude, stability = sim_result

        
        

        
        print(f"Tested: {editDictionary} | Apogee: {altitude:.2f} m | Stability: {stability:.2f}")

        std_dev = acceptableStabilityDeviation/2
        mean = targetStability

        coefficient = 1.0 / (std_dev * np.sqrt(2 * np.pi))
        exponent = np.exp(-0.5 * (( stability - mean) / std_dev) ** 2)

        scalar = coefficient**exponent

        print(f"Stabillity punishment: {scalar}")

        print(f"Score: {altitude*scalar}")
        
        return -(altitude*scalar)
            
    print("Starting optimization loop... This may take a while.")
    
    # 3. Run the optimization
    result = minimize(
        objective, 
        x0, 
        bounds=arrayValueBounds, 
        method='L-BFGS-B',
        options={'eps': 0.1, 'disp': False} # eps is the step size for gradient calculation
    )
    
    # 4. Output the final results
    if result.success:
        print("\n=== Optimization Successful ===")
        print(f"Max Altitude Found: {-result.fun:.2f} m")
        print("Optimal Parameters:")
        for tag, val in zip(arrayValuesToAdjust, result.x):
            print(f"  {tag}: {val:.4f}")
    else:
        print("\n=== Optimization Failed ===")
        print(result.message)
        
    return result