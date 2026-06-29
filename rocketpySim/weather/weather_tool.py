## -- Libraries -- ##
import numpy as np      
import xarray as xr
import cfgrib
from datetime import datetime
from herbie import Herbie
from herbie.toolbox import pc
import metpy.calc as mpcalc
from metpy.units import units
from rocketpy import Environment
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

class SpaceWeather:

    # Midland coords
    mid_lat = 31.0436111
    mid_lon = -103.5283333

    # TL1 coords
    tl_lat = 33.4990039
    tl_lon = -99.3325714

    # South Farm coords
    sf_lat = 33.395075
    sf_lon = -88.752587

    def __init__(self, model='hrrr'):
        self.model = model
        self.init_time_str = None   # Model Initalize Time
        self.launch_time_str = None # Hour that we want to launch
        self.fxx = None
        self.prs_file = None        # Store pressure file path
        self.sfc_file = None        # Store surface file path

    def hrrr_download(self, launch_time_str, fxx, save_folder):
        """ Download HRRR data.
        launch_time_str: the MODEL RUN time in UTC (e.g. "2026-06-17 23:00:00" for a 6pm CDT run)
        fxx: forecast hour offset from that model run (1 = forecast valid 1hr later)
        """

        self.launch_time_str = launch_time_str
        self.fxx = fxx

        print("Downloading HRRR Pressure levels (prs)...")
        H_prs = Herbie(
            launch_time_str,
            model=self.model,
            product='prs',
            fxx=self.fxx
        )
        H_prs.download(save_dir=save_folder)
        self.prs_file = str(H_prs.get_localFilePath())

        print("Downloading HRRR Surface levels (sfc)...")
        H_sfc = Herbie(
            launch_time_str,
            model=self.model,
            product='sfc',
            fxx=self.fxx
        )
        H_sfc.download(save_dir=save_folder)
        self.sfc_file = str(H_sfc.get_localFilePath())

        return self.prs_file, self.sfc_file
    

## -- Convert Hrrr data into rocketpy environment -- ##

    def to_env(self, longitude, latitude, max_height, altitudes_m = None, elevation = None):
        """ This is to convert the hrrr downloads into an executable rocketpy atmosphere """

        if self.prs_file is None or self.sfc_file is None:
            raise ValueError("HRRR files not downloaded yet!")

        if altitudes_m is None:
            altitudes_m = np.arange(0, 15000, 500)  # default: 0-15 km

        # Open HRRR GRIB via xarray, selecting isobaric levels from the PRS file
        ds = xr.open_dataset(       
            self.prs_file,
            engine='cfgrib',
            decode_timedelta=False,        
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}}     
        )

        # Extract latitude and longitude grids (2D)
        lat_grid = ds['latitude'].values
        lon_grid = ds['longitude'].values

        # Flatten grids to find nearest point
        lat_flat = lat_grid.flatten()
        lon_flat = lon_grid.flatten()

        target_lon = longitude + 360 if longitude < 0 else longitude

        dist = (lat_flat - latitude)**2 + (lon_flat - target_lon)**2
        idx = np.argmin(dist)
        y_idx, x_idx = np.unravel_index(idx, lat_grid.shape)

        # Extract variables at nearest grid point from the PRS file
        try:
            temperature = ds['t'].isel(y=y_idx, x=x_idx).values
            wind_u = ds['u'].isel(y=y_idx, x=x_idx).values
            wind_v = ds['v'].isel(y=y_idx, x=x_idx).values
            gh = ds['gh'].isel(y=y_idx, x=x_idx).values # Pull actual altitudes in meters
        except KeyError:
            raise ValueError("HRRR dataset is missing standard variables (t, u, v, gh).")

        # Pressure levels (convert hPa to Pascals)
        if 'isobaricInhPa' in ds.coords:
            pressure = ds['isobaricInhPa'].values * 100 
        else:
            raise ValueError("HRRR dataset is missing isobaric levels.")
        
        # --- Extract Surface Data from the SFC file ---
        try:
            # This magical function reads the entire GRIB file and splits it into a list 
            # of valid Datasets, completely bypassing the filter_by_keys bugs!
            sfc_datasets = cfgrib.open_datasets(self.sfc_file)
            
            # Initialize variables in case they aren't found
            sfc_elev = None
            sfc_pressure = None
            sfc_temp = None
            sfc_u = None
            sfc_v = None

            # Loop through the separated datasets and grab our variables wherever they landed
            for ds_chunk in sfc_datasets:
                if 'orog' in ds_chunk.variables:
                    sfc_elev = ds_chunk['orog'].isel(y=y_idx, x=x_idx).values
                if 'sp' in ds_chunk.variables:
                    sfc_pressure = ds_chunk['sp'].isel(y=y_idx, x=x_idx).values
                    self._sfc_pressure = float(sfc_pressure)
                if 't2m' in ds_chunk.variables:
                    sfc_temp = ds_chunk['t2m'].isel(y=y_idx, x=x_idx).values
                    self._sfc_temp = float(sfc_temp)
                if 'u10' in ds_chunk.variables:
                    sfc_u = ds_chunk['u10'].isel(y=y_idx, x=x_idx).values
                if 'v10' in ds_chunk.variables:
                    sfc_v = ds_chunk['v10'].isel(y=y_idx, x=x_idx).values

            # Ensure we actually found everything
            if None in [sfc_elev, sfc_pressure, sfc_temp, sfc_u, sfc_v]:
                raise ValueError("One or more surface variables were missing from the parsed file.")

            # Append the surface values to the isobaric arrays
            gh = np.append(gh, float(sfc_elev))
            pressure = np.append(pressure, float(sfc_pressure))
            temperature = np.append(temperature, float(sfc_temp))
            wind_u = np.append(wind_u, float(sfc_u))
            wind_v = np.append(wind_v, float(sfc_v))

            # Store surface wind for external reporting
            self._sfc_u = float(sfc_u)
            self._sfc_v = float(sfc_v)
            sfc_wind_speed_mph = np.sqrt(float(sfc_u)**2 + float(sfc_v)**2) * 2.23694
            print(f" Pad Elevation: {float(sfc_elev):.1f} m ASL | Pad Temp: {(float(sfc_temp) - 273.15) * 9/5 + 32:.1f} F | Surface Wind: {sfc_wind_speed_mph:.1f} mph")

        except Exception as e:
            print(f"Warning: Could not extract surface data. Proceeding with isobaric levels only. Error: {e}")
        # ----------------------------------------------

        # Sort the data by altitude (gh) to ensure RocketPy reads it correctly (bottom to top)
        sort_idx = np.argsort(gh)
        altitudes_actual = gh[sort_idx]
        pressure_actual = pressure[sort_idx]
        temperature_actual = temperature[sort_idx]
        wind_u_actual = wind_u[sort_idx]
        wind_v_actual = wind_v[sort_idx]

        # Convert altitudes from ASL to AGL (RocketPy custom_atmosphere expects AGL)
        pad_elevation = float(sfc_elev) if sfc_elev is not None else (elevation if elevation else 0)
        altitudes_agl = altitudes_actual - pad_elevation
        # Clamp negatives (isobaric levels below pad) to 0
        altitudes_agl = np.maximum(altitudes_agl, 0)

        # Stack directly without linear interpolation
        pressure_src    = np.column_stack((altitudes_agl, pressure_actual))
        temperature_src = np.column_stack((altitudes_agl, temperature_actual))
        wind_u_src      = np.column_stack((altitudes_agl, wind_u_actual))
        wind_v_src      = np.column_stack((altitudes_agl, wind_v_actual))


        # Create RocketPy Environment
        env = Environment(latitude=latitude, longitude=longitude)
        env.max_expected_height = max_height   
        
        # If no elevation is passed in manually, use the 'orog' elevation we just pulled from the HRRR sfc file!
        if elevation == None:
            try:
                env.set_elevation(float(sfc_elev))
            except NameError:
                env.set_elevation() # Fallback if sfc_elev failed to extract
        else:
            env.set_elevation(elevation) 
            
        env.set_atmospheric_model(
            type="custom_atmosphere",
            pressure=pressure_src,
            temperature=temperature_src,
            wind_u=wind_u_src,
            wind_v=wind_v_src,
        )

        return env
    
if __name__ == "__main__":
    sw = SpaceWeather()
    sw.hrrr_download(
        launch_time_str=f"2026-04-30 18:00:00",
        fxx=00,
        save_folder=r"data\weather_data",
    )
    env = sw.to_env(
        latitude=sw.mid_lat, 
        longitude=sw.mid_lon, 
        altitudes_m=None,
        max_height=32000, 
        elevation=None # Or set to None to let HRRR define the pad elevation
    )
    print(env.all_info())