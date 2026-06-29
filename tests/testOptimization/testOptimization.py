import os
import sys
from pathlib import Path

# Ensure the project root is in the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the optimization function
from tools.optimization.optimization import maximize_alt

def main():
    # 1. Path to your baseline RASAero II file
    # Make sure this points to a valid, working .CDX1 file in your directory
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    base_rocket_file = os.path.join(script_dir, "files", "Bandit_TL1.CDX1")
    
    # 2. Define the fin parameters you want to optimize.
    # We are assuming the fins are attached to the 3rd Body Tube (Index 2).
    # Adjust "BodyTube:2" if your fins are on a different tube.
    tags_to_adjust = [
        "BodyTube:3.Fin.Span",
        "BodyTube:3.Fin.Chord",          # Root Chord
        "BodyTube:3.Fin.TipChord",
        "BodyTube:3.Fin.SweepDistance"
    ]
    
    # 3. Define the physical constraints (bounds) for each parameter in INCHES.
    # Format: (Min, Max). Make sure these represent a buildable fin!
    bounds = [
        (10.0, 16.0),   # Span: between 4 and 10 inches
        (8.0, 16.0),   # Root Chord: between 8 and 16 inches
        (2.0, 8.0),    # Tip Chord: between 2 and 8 inches
        (2.0, 15.0)    # Sweep Distance: between 2 and 12 inches
    ]
    
    print(f"Starting Fin Optimization for: {base_rocket_file}")
    print(f"Adjusting {len(tags_to_adjust)} parameters...")
    
    # 4. Run the maximization routine
    # Note: Scipy will automatically start testing at the exact midpoint of your bounds.
    result = maximize_alt(base_rocket_file, tags_to_adjust, bounds, 13, 3)
    # 5. Final output summary
    if result:
        print("\n=========================================")
        print("          OPTIMIZATION COMPLETE          ")
        print("=========================================")
        print(f"Best Apogee Achieved: {-result.fun:.2f} meters")
        print("Optimal Fin Geometry (Inches):")
        for tag, val in zip(tags_to_adjust, result.x):
            print(f" -> {tag.split('.')[-1]}: {val:.4f}")
    else:
        print("\nOptimization terminated early or failed.")

if __name__ == "__main__":
    main()