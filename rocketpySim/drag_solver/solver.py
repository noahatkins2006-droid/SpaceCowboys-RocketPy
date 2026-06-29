import pandas as pd
from scipy.interpolate import interp1d




class TimeBasedHybridDrag:
    def __init__(self, on_drag_csv, off_drag_csv, motor_burn_time):
        # Load CSVs
        self.on_data = pd.read_csv(on_drag_csv)
        self.off_data = pd.read_csv(off_drag_csv)

        # Interpolators
        self.cd_on_interp = interp1d(
            self.on_data["Mach"], self.on_data["Cd"],
            kind="cubic", fill_value="extrapolate"
        )
        self.cd_off_interp = interp1d(
            self.off_data["Mach"], self.off_data["Cd"],
            kind="cubic", fill_value="extrapolate"
        )

        self.k_on = 1.0
        self.k_off = 1.0
        self.burn_time = motor_burn_time

    def drag(self, mach, time=None, altitude=None):
        """
        Returns drag coefficient.
        Uses power-on drag during burn, power-off drag after burnout.
        """
        if time is None:
            # fallback to off drag
            return self.k_off * float(self.cd_off_interp(mach))

        if time <= self.burn_time:
            return self.k_on * float(self.cd_on_interp(mach))
        else:
            return self.k_off * float(self.cd_off_interp(mach))

class TimeBasedAcceleration:
    def __init__(self, real_data_csv, sim_dataframe):
        self.real_df = pd.read_csv(real_data_csv)
        self.sim_df = sim_dataframe.rename(columns={"Acceleration (m/s^2)": "Sim_Accel"})
        self.real_df = self.real_df.rename(columns={self.real_df.columns[1]: "Real_Accel"})
        
        self.left_key = "Time (s)"
        self.right_key = self.real_df.columns[0]
        self.accSimThreshold = 10.0

        # --- Get the first threshold-crossing times (as scalars) ---
        self.realThresholdTime = self.real_df.loc[
            self.real_df["Real_Accel"] > self.accSimThreshold, self.real_df.columns[0]
        ].iloc[0]

        self.simThresholdTime = self.sim_df.loc[
            self.sim_df["Sim_Accel"] > self.accSimThreshold, "Time (s)"
        ].iloc[0]



        # --- Compute offset (align so threshold crossings match) ---
        self.startOffSet = self.realThresholdTime - self.simThresholdTime

        # --- Shift the real data’s time axis ---
        self.real_df[self.right_key] = self.real_df[self.right_key] - self.startOffSet

        # --- Sort both DataFrames by time ---
        self.real_df = self.real_df.sort_values(self.right_key)
        self.sim_df = self.sim_df.sort_values(self.left_key)

        # --- Merge (using merge_asof requires sorted keys & no NaNs) ---
        self.merged_df = pd.merge_asof(
            self.sim_df,
            self.real_df,
            left_on=self.left_key,
            right_on=self.right_key,
            direction="backward"
        )

        # --- Compute acceleration differences ---
        self.merged_df["dt"] = self.merged_df[self.left_key].diff().fillna(0)
        self.merged_df["Accel_Diff"] = self.merged_df["Real_Accel"] - self.merged_df["Sim_Accel"]
        self.merged_df["Normalized_Diff"] = self.merged_df["Accel_Diff"] * self.merged_df["dt"]
        self.merged_df["Absolute_Normalized_Diff"] = (self.merged_df["Normalized_Diff"].abs())**2

        # with pd.option_context('display.max_rows', None):
        #     print(self.merged_df)
    
    def get_total_deviation(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        sum_norm_diff = subset["Normalized_Diff"].sum()
        return(sum_norm_diff)
    
    def get_absolute_deviation(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        sum_abs_diff = subset["Absolute_Normalized_Diff"].sum()
        return(sum_abs_diff)
    
    def get_mask(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        return(subset)


class TimeBasedAltitude:
    def __init__(self, real_data_csv, sim_dataframe):
        self.real_df = pd.read_csv(real_data_csv)
        self.sim_df = sim_dataframe.rename(columns={"Altitude (m)": "Sim_Alt"})
        self.real_df = self.real_df.rename(columns={self.real_df.columns[1]: "Real_Alt"})
        
        self.left_key = "Time (s)"
        self.right_key = self.real_df.columns[0]
        self.accSimThreshold = 10.0

        # --- Get the first threshold-crossing times (as scalars) ---
        self.realThresholdTime = self.real_df.loc[
            self.real_df["Real_Alt"] > self.accSimThreshold, self.real_df.columns[0]
        ].iloc[0]

        self.simThresholdTime = self.sim_df.loc[
            self.sim_df["Sim_Alt"] > self.accSimThreshold, "Time (s)"
        ].iloc[0]



        # --- Compute offset (align so threshold crossings match) ---
        self.startOffSet = self.realThresholdTime - self.simThresholdTime

        # --- Shift the real data’s time axis ---
        self.real_df[self.right_key] = self.real_df[self.right_key] - self.startOffSet

        # --- Sort both DataFrames by time ---
        self.real_df = self.real_df.sort_values(self.right_key)
        self.sim_df = self.sim_df.sort_values(self.left_key)

        # --- Merge (using merge_asof requires sorted keys & no NaNs) ---
        self.merged_df = pd.merge_asof(
            self.sim_df,
            self.real_df,
            left_on=self.left_key,
            right_on=self.right_key,
            direction="backward"
        )

        # --- Compute acceleration differences ---
        self.merged_df["dt"] = self.merged_df[self.left_key].diff().fillna(0)
        self.merged_df["Alt_Diff"] = self.merged_df["Real_Alt"] - self.merged_df["Sim_Alt"]
        self.merged_df["Normalized_Diff"] = self.merged_df["Alt_Diff"] * self.merged_df["dt"]
        self.merged_df["Absolute_Normalized_Diff"] = self.merged_df["Normalized_Diff"].abs()

        # with pd.option_context('display.max_rows', None):
        #     print(self.merged_df)
    
    def get_total_deviation(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        sum_norm_diff = subset["Normalized_Diff"].sum()
        return(sum_norm_diff)
    
    def get_absolute_deviation(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        sum_abs_diff = subset["Absolute_Normalized_Diff"].sum()
        return(sum_abs_diff)
    
    def get_mask(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        return(subset)


class TimeBasedVelocity:
    def __init__(self, real_data_csv, sim_dataframe):
        self.real_df = pd.read_csv(real_data_csv)
        self.sim_df = sim_dataframe.rename(columns={"Velocity (m/s)": "Sim_Vel"})
        self.real_df = self.real_df.rename(columns={self.real_df.columns[1]: "Real_Vel"})
        
        self.left_key = "Time (s)"
        self.right_key = self.real_df.columns[0]
        self.accSimThreshold = 5.0

        # --- Get the first threshold-crossing times (as scalars) ---
        self.realThresholdTime = self.real_df.loc[
            self.real_df["Real_Vel"] > self.accSimThreshold, self.real_df.columns[0]
        ].iloc[0]

        self.simThresholdTime = self.sim_df.loc[
            self.sim_df["Sim_Vel"] > self.accSimThreshold, "Time (s)"
        ].iloc[0]



        # --- Compute offset (align so threshold crossings match) ---
        self.startOffSet = self.realThresholdTime - self.simThresholdTime

        # --- Shift the real data’s time axis ---
        self.real_df[self.right_key] = self.real_df[self.right_key] - self.startOffSet

        # --- Sort both DataFrames by time ---
        self.real_df = self.real_df.sort_values(self.right_key)
        self.sim_df = self.sim_df.sort_values(self.left_key)

        # --- Merge (using merge_asof requires sorted keys & no NaNs) ---
        self.merged_df = pd.merge_asof(
            self.sim_df,
            self.real_df,
            left_on=self.left_key,
            right_on=self.right_key,
            direction="backward"
        )

        # --- Compute acceleration differences ---
        self.merged_df["dt"] = self.merged_df[self.left_key].diff().fillna(0)
        self.merged_df["Vel_Diff"] = self.merged_df["Real_Vel"] - self.merged_df["Sim_Vel"]
        self.merged_df["Normalized_Diff"] = self.merged_df["Vel_Diff"] * self.merged_df["dt"]
        self.merged_df["Absolute_Normalized_Diff"] = self.merged_df["Normalized_Diff"].abs()

        # with pd.option_context('display.max_rows', None):
        #     print(self.merged_df)
    
    def get_total_deviation(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        sum_norm_diff = subset["Normalized_Diff"].sum()
        return(sum_norm_diff)
    
    def get_absolute_deviation(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        sum_abs_diff = subset["Absolute_Normalized_Diff"].sum()
        return(sum_abs_diff)
    
    def get_mask(self,start_time,end_time):
        mask = (self.merged_df["Time (s)"] >= start_time) & (self.merged_df["Time (s)"] <= end_time)
        subset = self.merged_df.loc[mask]
        return(subset)

    


