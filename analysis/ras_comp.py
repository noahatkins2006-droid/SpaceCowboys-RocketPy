## RasAero Comparison
# By: Hunter Latimer

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np



## ----- file paths ----- ##

## --- Rough Surface Finish ---##
# Rough Camoflage Paint

HRF = pd.read_csv(r"data\ras_aero_data\HRF.CSV")  # Heavy Rough Surface Finish

ARF = pd.read_csv(r"data\ras_aero_data\ARF.CSV")

LRF = pd.read_csv(r"data\ras_aero_data\LRF.CSV")    # Light Rough Surface Finish


## --- Smooth Surface Finish --- ##
# Sheet Metal Surface Finish


HSF = pd.read_csv(r"data\ras_aero_data\HSF.CSV")

ASF = pd.read_csv(r"data\ras_aero_data\ASF.CSV")

LSF = pd.read_csv(r"data\ras_aero_data\LSF.CSV")    # Light Smooth Surface Finish

# Get highest altitude in each dataset
rough_max = [HRF["Altitude (ft)"].max(), ARF["Altitude (ft)"].max(), LRF["Altitude (ft)"].max()]
smooth_max = [HSF["Altitude (ft)"].max(), ASF["Altitude (ft)"].max(), LSF["Altitude (ft)"].max()]

# Labels for bars
rough_labels = ["Heavy (78.4 lbs)", "Average (72.2 lbs)", "Light (67 lbs)"]
smooth_labels = ["Heavy (78.4 lbs)", "Average (72.2 lbs)", "Light (67 lbs)"]

# Create side-by-side panels
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

# Rough
ax1.bar(rough_labels, rough_max, color="steelblue", alpha=0.8)
ax1.set_title("Rough Surface Finishes")
ax1.set_ylabel("Highest Altitude")

# Smooth
ax2.bar(smooth_labels, smooth_max, color="salmon", alpha=0.8)
ax2.set_title("Smooth Surface Finishes")
ax2.set_ylabel("Highest Altitude")

plt.suptitle("Highest Altitude Comparison: Rough vs Smooth Finishes")
plt.tight_layout()
plt.show()
