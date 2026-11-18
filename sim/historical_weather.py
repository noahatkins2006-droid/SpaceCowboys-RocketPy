"""Historical HRRR/ERA5 weather profiles for the Bandit RocketPy simulation.

For the Bandit June 17, 2026 flight, the target launch time is 18:55:53 UTC.
The loader uses the 18:00 UTC HRRR analysis (F00), which precedes liftoff.
It does not use the 19:00 UTC analysis, which occurs after liftoff.

Source order:
1. Operational HRRR only if the launch is in its supported live window.
2. Archived HRRR analysis at the floored UTC hour.
3. ERA5 reanalysis at the floored UTC hour.

No weather data or profiles are cached; each run retrieves fresh source data.

There is deliberately no standard-atmosphere fallback.

One issue we had was historical weather download failing (on Windows)

Issue: the CSpire DNS server (10.89.77.111) couldn't resolve the NOAA HRRR archive, so the weather
download failed. Cloudflare DNS resolves it correctly (the archive resolved to Amazon S3 and
returned HTTP 200 OK).

Bypass:
1. Windows Settings → Network & internet → Wi-Fi → your network's Properties.
2. Next to DNS server assignment, click Edit.
3. Change Automatic to Manual and turn IPv4 on.
4. Set Preferred DNS to 1.1.1.1 and Alternate DNS to 1.0.0.1 .
5. Click Save.
"""

# GLOSSARY
# --------
#   HRRR  - High-Resolution Rapid Refresh, NOAA's 3 km hourly weather model
#           covering the continental US. "F00" is the forecast hour 0, i.e. the
#           analysis (the model's best estimate of the atmosphere right now).
#   ERA5  - ECMWF's global reanalysis (about 30 km), a fallback when HRRR
#           data is not available. Needs a free Copernicus CDS account/API key.
#   Herbie - Python package that finds and downloads HRRR GRIB2 files.
#   Pressure level (isobaric) - weather models report data on fixed pressure
#           surfaces (1000 hPa, 975 hPa, ...). Each surface sits at a different
#           height, so we convert to a height-based profile for RocketPy.
#   Surface anchor - a data point at the pad's own elevation, built from the
#           model's surface fields, so the profile starts at the ground.
#
# WHAT THE FINAL PROFILE LOOKS LIKE
# ---------------------------------
# A dictionary of equal-length arrays, sorted from the ground up:
#   height (m ASL), pressure (Pa), temperature (K), u and v wind (m/s)
# where u is the eastward and v the northward wind component.

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import tempfile
import logging
import warnings
from contextlib import redirect_stdout, redirect_stderr
import io

import numpy as np
import xarray as xr
# RocketPy's Environment class, used at the bottom to hold the final weather.
from rocketpy import Environment

# Herbie/cfgrib can emit many informational lines and compatibility warnings.
# Keep routine output concise; actual exceptions still propagate normally.
logging.getLogger("herbie").setLevel(logging.ERROR)
logging.getLogger("cfgrib").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning, module="cfgrib")


def _quiet_xarray_open(herbie_object, search):
    """Open GRIB data without dumping cfgrib's per-hypercube notices."""
    # Temporarily swallow anything printed to stdout/stderr while the file is
    # being opened, then return the opened dataset(s).
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return herbie_object.xarray(search)


# Pressure levels (hPa) requested from ERA5, from near-ground up to about 16 km.
PRESSURE_LEVELS = [
    1000, 975, 950, 925, 900, 875, 850, 825, 800,
    775, 750, 700, 650, 600, 550, 500, 450, 400,
    350, 300, 250, 200, 150, 100,
]

# Rules for deciding whether "live" HRRR (the newest operational forecast) can
# be used instead of the archive:
#   DELAY ............ a model run is only published about 2 hours after its
#                      nominal start time
#   MAX_FORECAST_HOURS  HRRR forecasts run out to 18 hours
#   PAST_TOLERANCE ... how many hours in the past still counts as "live"
LIVE_HRRR_DELAY_HOURS = 2
LIVE_HRRR_MAX_FORECAST_HOURS = 18
LIVE_HRRR_PAST_TOLERANCE_HOURS = 3


def _as_utc(value):
    # Convert many kinds of date/time input into a timezone-aware UTC datetime.
    # numpy datetime64 -> plain datetime first.
    if isinstance(value, np.datetime64):
        value = value.astype("datetime64[us]").astype(datetime)

    # Anything else that is not a datetime (strings, pandas Timestamps, ...)
    # is handed to pandas, which understands most formats.
    if not isinstance(value, datetime):
        try:
            import pandas as pd
            value = pd.Timestamp(value).to_pydatetime()
        except Exception as exc:
            raise TypeError(f"Unsupported datetime value: {value!r}") from exc

    # A "naive" datetime (no timezone) is assumed to already be UTC;
    # an aware one is converted to UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _floor_hour(value):
    # Round down to the top of the hour, e.g. 18:55:53 -> 18:00:00 (UTC).
    # Weather analyses are issued once per hour on the hour.
    return _as_utc(value).replace(minute=0, second=0, microsecond=0)


def _validate(profile, source, valid_time):
    # Final quality gate for a weather profile. Raises ValueError on anything
    # suspicious so a bad dataset can never silently drive the simulation.
    required = ("height", "pressure", "temperature", "u", "v")

    # Each variable must exist, be numeric, have enough points, and be finite
    # (no NaN or infinity).
    for key in required:
        if key not in profile:
            raise ValueError(f"{source}: missing {key}")
        profile[key] = np.asarray(profile[key], dtype=float)
        if len(profile[key]) < 5 or not np.all(np.isfinite(profile[key])):
            raise ValueError(f"{source}: invalid {key} profile")

    # All five arrays must describe the same set of altitudes.
    if len({len(profile[key]) for key in required}) != 1:
        raise ValueError(f"{source}: profile arrays have inconsistent lengths")

    # Physical plausibility checks.
    if np.any(np.diff(profile["height"]) <= 0):
        raise ValueError(f"{source}: heights are not strictly increasing")
    if np.any(profile["pressure"] <= 0):
        raise ValueError(f"{source}: pressure must be positive")
    if np.any((profile["temperature"] < 150) | (profile["temperature"] > 350)):
        raise ValueError(f"{source}: temperature is outside plausible Kelvin range")
    # The rocket flies to roughly 10 km+, so the data must reach at least that high.
    if profile["height"][-1] < 10000:
        raise ValueError(f"{source}: profile top is below 10 km ASL")

    # Tag the profile with where and when it came from.
    profile["source"] = source
    profile["valid_time"] = _as_utc(valid_time).isoformat()
    return profile


def _nearest_grid_point(ds, site):
    # Weather models store data on a grid. Find the grid cell whose center is
    # closest to the launch site and return its (row, column) indices.
    if "latitude" not in ds or "longitude" not in ds:
        raise ValueError("Weather dataset is missing latitude/longitude coordinates.")
    lat = np.asarray(ds["latitude"].values)
    lon = np.asarray(ds["longitude"].values)
    # Wrap the longitude difference into -180..180 so 0-360 and -180..180
    # conventions can be compared directly.
    delta_lon = (lon - site["lon"] + 180) % 360 - 180
    # Approximate squared ground distance; longitude degrees get shorter toward
    # the poles, hence the cos(latitude) scaling.
    distance = (lat - site["lat"]) ** 2 + (
        delta_lon * np.cos(np.deg2rad(site["lat"]))
    ) ** 2
    # Index of the smallest distance, converted back to 2-D grid coordinates.
    return np.unravel_index(np.nanargmin(distance), distance.shape)


def _point_value(da, iy, ix):
    # Pull a single number out of a gridded array at grid cell (iy, ix).
    # HRRR grids use dimensions named y and x...
    if "y" in da.dims and "x" in da.dims:
        da = da.isel(y=iy, x=ix)
    else:
        # ...otherwise treat the last two non-time dimensions as the horizontal grid.
        spatial = [dim for dim in da.dims if dim not in (
            "time", "step", "valid_time", "latitude", "longitude"
        )]
        if len(spatial) >= 2:
            da = da.isel({spatial[-2]: iy, spatial[-1]: ix})
    # Drop any leftover length-1 dimensions and return a plain float.
    return float(np.asarray(da.squeeze(drop=True).values, dtype=float))


def _hrrr_surface_anchor(site, cycle, forecast_hour):
    """Read HRRR surface pressure, 2 m temperature, 10 m winds and terrain."""
    from herbie import Herbie

    # Download into a throwaway folder that is deleted in the `finally` block.
    hrrr_temp_dir = tempfile.mkdtemp(prefix="bandit_hrrr_surface_")
    # "sfc" is HRRR's surface-fields product (as opposed to "prs" for pressure levels).
    h = Herbie(
        _as_utc(cycle).replace(tzinfo=None),
        model="hrrr",
        product="sfc",
        fxx=int(forecast_hour),
        save_dir=hrrr_temp_dir,
        verbose=False,
    )
    # The search string is a regular expression over GRIB message names:
    # PRES = surface pressure, TMP = temperature, UGRD/VGRD = wind components,
    # HGT = terrain height.
    opened = _quiet_xarray_open(h, r":(?:PRES|TMP|UGRD|VGRD|HGT):")
    datasets = opened if isinstance(opened, list) else [opened]

    def find_field(candidates, level_type, level=None):
        # Scan every opened dataset for a variable whose GRIB short name is one
        # of `candidates`, on the right kind of level (and height, if given).
        # Different library versions name the same field differently, which is
        # why each lookup accepts several aliases.
        for ds in datasets:
            for name, da in ds.data_vars.items():
                attrs = da.attrs
                short_name = str(attrs.get("GRIB_shortName", name)).lower()
                type_name = str(attrs.get("GRIB_typeOfLevel", "")).lower()
                grib_level = attrs.get("GRIB_level")
                if short_name not in candidates or type_name != level_type:
                    continue
                if level is not None and grib_level is not None and float(grib_level) != float(level):
                    continue
                return ds, da
        raise ValueError(
            f"HRRR surface data missing {candidates} at {level_type} level {level}."
        )

    try:
        # Locate each needed field: surface pressure, 2 m temperature,
        # 10 m wind components (u east, v north) and the model terrain height.
        pressure_ds, pressure_da = find_field({"sp", "pres"}, "surface")
        temp_ds, temp_da = find_field({"2t", "t", "tmp"}, "heightaboveground", 2)
        u_ds, u_da = find_field({"10u", "u", "ugrd"}, "heightaboveground", 10)
        v_ds, v_da = find_field({"10v", "v", "vgrd"}, "heightaboveground", 10)
        terrain_ds, terrain_da = find_field({"gh", "hgt", "orog"}, "surface")

        # Choose the grid cell nearest the pad and read each value there.
        iy, ix = _nearest_grid_point(pressure_ds, site)
        pressure = _point_value(pressure_da, iy, ix)
        temperature = _point_value(temp_da, iy, ix)
        u = _point_value(u_da, iy, ix)
        v = _point_value(v_da, iy, ix)
        terrain = _point_value(terrain_da, iy, ix)

        # Normalize units to Pa, Kelvin and meters, in case the file reports
        # hPa, Celsius or geopotential (m^2/s^2).
        p_units = str(pressure_da.attrs.get("units", "Pa")).lower()
        if p_units in ("hpa", "mb", "mbar"):
            pressure *= 100.0
        t_units = str(temp_da.attrs.get("units", "K")).lower()
        if t_units in ("c", "degc", "degree_celsius", "degrees_celsius"):
            temperature += 273.15
        z_units = str(terrain_da.attrs.get("units", "m")).lower()
        if "m2" in z_units or "m^2" in z_units or "m**2" in z_units:
            terrain /= 9.80665

        # Reject obviously broken values before using them.
        if not all(np.isfinite(x) for x in (pressure, temperature, u, v, terrain)):
            raise ValueError("HRRR surface anchor contains non-finite values.")
        if pressure <= 0 or not 150 <= temperature <= 350:
            raise ValueError("HRRR surface anchor pressure/temperature is implausible.")
        # If the model's ground height is more than 1 km from the real pad
        # elevation, something is wrong (wrong location or wrong file).
        if abs(site["elevation"] - terrain) > 1000:
            raise ValueError(
                f"HRRR grid terrain ({terrain:.1f} m) differs from pad elevation "
                f"({site['elevation']:.1f} m) by over 1000 m."
            )

        # Hydrostatic adjustment from the HRRR grid terrain to the pad elevation.
        # The model's ground is a smoothed average, so it is slightly above or
        # below the real pad. The barometric formula p2 = p1 * exp(-g*dz/(R*T))
        # corrects the pressure for that height difference
        # (g = 9.80665 m/s^2, R = 287.05 J/(kg*K) for dry air).
        adjusted_pressure = pressure * np.exp(
            -9.80665 * (site["elevation"] - terrain) / (287.05 * temperature)
        )
        return {
            "height": float(site["elevation"]),
            "pressure": float(adjusted_pressure),
            "temperature": float(temperature),
            "u": float(u),
            "v": float(v),
        }
    finally:
        # Always close the files and delete the temporary download folder,
        # even when an error was raised above.
        for ds in datasets:
            try:
                ds.close()
            except Exception:
                pass
        shutil.rmtree(hrrr_temp_dir, ignore_errors=True)


def _era5_surface_anchor(site, target):
    """Retrieve fresh ERA5 surface fields and interpolate them to pad elevation."""
    import cdsapi

    target = _floor_hour(target)
    # Request describing exactly what to download from the Copernicus CDS:
    # surface pressure, 2 m temperature, 10 m winds and geopotential (ground
    # height x gravity) for the single hour, in a small box around the site.
    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "surface_pressure", "2m_temperature",
            "10m_u_component_of_wind", "10m_v_component_of_wind",
            "geopotential",
        ],
        "year": target.strftime("%Y"),
        "month": target.strftime("%m"),
        "day": target.strftime("%d"),
        "time": target.strftime("%H:00"),
        "data_format": "netcdf",
        "download_format": "unarchived",
        # [north, west, south, east] bounding box, +/- 0.25 degrees
        "area": [
            site["lat"] + 0.25, site["lon"] - 0.25,
            site["lat"] - 0.25, site["lon"] + 0.25,
        ],
    }

    # The file lives in a temporary directory that disappears when the block ends.
    with tempfile.TemporaryDirectory(prefix="bandit_era5_surface_") as temp_dir:
        path = Path(temp_dir) / "era5_surface.nc"
        cdsapi.Client().retrieve("reanalysis-era5-single-levels", request, str(path))

        with xr.open_dataset(path) as ds:
            # Variable names differ between CDS file versions (short vs long
            # names), so accept either spelling for each field.
            aliases = {
                "sp": ("sp", "surface_pressure"),
                "t2m": ("t2m", "2m_temperature"),
                "u10": ("u10", "10m_u_component_of_wind"),
                "v10": ("v10", "10m_v_component_of_wind"),
                "z": ("z", "geopotential"),
            }
            names = {}
            for key, choices in aliases.items():
                for choice in choices:
                    if choice in ds.data_vars:
                        names[key] = choice
                        break
                if key not in names:
                    raise ValueError(f"ERA5 single-level data missing {key}: {list(ds.data_vars)}")
            # Pick the grid point nearest the pad. ERA5 longitudes run 0-360,
            # so the negative (western) longitude is wrapped with % 360.
            point = ds.sel(
                latitude=site["lat"], longitude=site["lon"] % 360, method="nearest"
            )

            def scalar(key):
                # Return one float for a variable, collapsing any time dimension
                # (the file only contains a single hour).
                da = point[names[key]]
                for dim in ("time", "valid_time"):
                    if dim in da.dims:
                        da = da.isel({dim: 0})
                return float(np.asarray(da.squeeze().values, dtype=float))

            pressure = scalar("sp")
            temperature = scalar("t2m")
            u = scalar("u10")
            v = scalar("v10")
            # Geopotential divided by standard gravity gives height in meters.
            terrain = scalar("z") / 9.80665
            # Same hydrostatic pressure correction as the HRRR anchor, moving
            # the pressure from the model's terrain height to the pad elevation.
            adjusted_pressure = pressure * np.exp(
                -9.80665 * (site["elevation"] - terrain) / (287.05 * temperature)
            )
            return {
                "height": float(site["elevation"]),
                "pressure": float(adjusted_pressure),
                "temperature": float(temperature),
                "u": float(u),
                "v": float(v),
            }

def _add_surface_anchor(profile, anchor, source, valid_time):
    """Add a pad-elevation boundary condition before validating the profile."""
    # Append the pad-level observation to the end of each profile array...
    arrays = {
        "height": np.append(np.asarray(profile["height"], dtype=float), anchor["height"]),
        "pressure": np.append(np.asarray(profile["pressure"], dtype=float), anchor["pressure"]),
        "temperature": np.append(np.asarray(profile["temperature"], dtype=float), anchor["temperature"]),
        "u": np.append(np.asarray(profile["u"], dtype=float), anchor["u"]),
        "v": np.append(np.asarray(profile["v"], dtype=float), anchor["v"]),
    }
    # ...then sort everything by height so the pad point lands first.
    order = np.argsort(arrays["height"])
    heights = arrays["height"][order]
    # Drop any point within 0.5 m of the one below it. Heights must be strictly
    # increasing for interpolation, and a pressure level that happens to sit
    # right at the pad height would otherwise create a duplicate.
    keep = np.concatenate(([True], np.diff(heights) > 0.5))
    result = {key: values[order][keep] for key, values in arrays.items()}
    return _validate(result, source, valid_time)

def _hrrr_profile(site, cycle, forecast_hour, source_label):
    from herbie import Herbie

    # `cycle` is the model run time; `forecast_hour` is how many hours after
    # that run the data is valid. Valid time = cycle + forecast_hour.
    cycle = _as_utc(cycle)
    hrrr_temp_dir = tempfile.mkdtemp(prefix="bandit_hrrr_pressure_")
    # "prs" is HRRR's pressure-level product: temperature, wind and height
    # on fixed pressure surfaces from the ground up through the stratosphere.
    h = Herbie(
        cycle.replace(tzinfo=None),
        model="hrrr",
        product="prs",
        fxx=int(forecast_hour),
        save_dir=hrrr_temp_dir,
        verbose=False,
    )
    # HGT = geopotential height, TMP = temperature, UGRD/VGRD = wind components.
    opened = _quiet_xarray_open(h, r":(?:HGT|TMP|UGRD|VGRD):")

    # cfgrib may split a GRIB file into several datasets (it groups messages
    # by level type). Keep only the ones that contain pressure levels and
    # merge them into a single dataset.
    if isinstance(opened, list):
        datasets = opened
        pressure_sets = [
            item for item in datasets
            if "isobaricInhPa" in item.dims
            or any("isobaricInhPa" in var.dims for var in item.data_vars.values())
        ]
        if not pressure_sets:
            for item in datasets:
                item.close()
            raise ValueError("HRRR GRIB did not return pressure-level datasets.")
        ds = xr.merge(
            pressure_sets,
            compat="override",
            join="outer",
            combine_attrs="drop_conflicts",
        )
    else:
        datasets = [opened]
        ds = opened

    try:
        # Accept either variable naming style (cfgrib short names or GRIB names).
        aliases = {
            "height": ("gh", "hgt"),
            "temperature": ("t", "tmp"),
            "u": ("u", "ugrd"),
            "v": ("v", "vgrd"),
        }
        names = {}
        for target, choices in aliases.items():
            for candidate in choices:
                if candidate in ds.data_vars:
                    names[target] = candidate
                    break
            if target not in names:
                raise ValueError(
                    f"HRRR missing {target}; variables found: {list(ds.data_vars)}"
                )

        if "latitude" not in ds or "longitude" not in ds:
            raise ValueError("HRRR dataset is missing latitude/longitude.")

        # Find the grid cell nearest the pad (same method as _nearest_grid_point).
        lat = np.asarray(ds["latitude"].values)
        lon = np.asarray(ds["longitude"].values)
        delta_lon = (lon - site["lon"] + 180) % 360 - 180
        distance = (lat - site["lat"]) ** 2 + (
            delta_lon * np.cos(np.deg2rad(site["lat"]))
        ) ** 2
        iy, ix = np.unravel_index(np.nanargmin(distance), distance.shape)

        # Extract a 1-D column (one value per pressure level) above that cell
        # for each variable.
        values = {}
        for target, variable in names.items():
            da = ds[variable]
            if "y" in da.dims and "x" in da.dims:
                da = da.isel(y=iy, x=ix)
            else:
                spatial = [
                    dim for dim in da.dims
                    if dim not in ("isobaricInhPa", "step", "time", "valid_time")
                ]
                if len(spatial) != 2:
                    raise ValueError(f"Unexpected HRRR dimensions for {variable}: {da.dims}")
                da = da.isel({spatial[0]: iy, spatial[1]: ix})
            if "isobaricInhPa" not in da.dims:
                raise ValueError(f"{variable} does not contain isobaricInhPa.")
            values[target] = np.asarray(da.squeeze(drop=True).values, dtype=float)

        # The pressure value of every level, in hPa.
        levels = np.asarray(ds["isobaricInhPa"].values, dtype=float)
        height = values["height"]
        # If heights come as geopotential (m^2/s^2) rather than meters,
        # divide by gravity to convert.
        height_units = str(ds[names["height"]].attrs.get("units", "")).lower()
        if height_units in ("m^2 s^-2", "m**2 s**-2", "m2 s-2"):
            height = height / 9.80665

        # Every array must have exactly one entry per pressure level.
        arrays = [height, values["temperature"], values["u"], values["v"]]
        if any(len(array) != len(levels) for array in arrays):
            raise ValueError("HRRR profile variables do not align with pressure levels.")

        # Keep only levels with good data that sit at or above the pad.
        # (High-pressure levels below ground level are extrapolated by the
        # model and would be meaningless, so they are filtered out.)
        valid = (
            np.isfinite(height)
            & np.isfinite(values["temperature"])
            & np.isfinite(values["u"])
            & np.isfinite(values["v"])
            & np.isfinite(levels)
            & (levels > 0)
            & (height >= site["elevation"])
        )

        # Sort from the ground up and convert hPa to Pa (x100).
        order = np.argsort(height[valid])
        profile = {
            "height": height[valid][order],
            "pressure": levels[valid][order] * 100.0,
            "temperature": values["temperature"][valid][order],
            "u": values["u"][valid][order],
            "v": values["v"][valid][order],
        }
        valid_time = cycle + timedelta(hours=int(forecast_hour))
        # Add a point at the pad's own elevation from the surface fields, then
        # validate the whole profile.
        anchor = _hrrr_surface_anchor(site, cycle, forecast_hour)
        return _add_surface_anchor(profile, anchor, source_label, valid_time)
    finally:
        # Close the files and remove the temporary download folder.
        for item in datasets:
            try:
                item.close()
            except Exception:
                pass
        shutil.rmtree(hrrr_temp_dir, ignore_errors=True)


def _live_hrrr_profile(site, launch_time):
    # Source 1: the newest operational HRRR run. Only applies to launches that
    # are happening now or very soon (see setup_historical_environment).
    target = _floor_hour(launch_time)
    now = datetime.now(timezone.utc)

    if target < now - timedelta(hours=LIVE_HRRR_PAST_TOLERANCE_HOURS):
        raise ValueError("Requested launch time is outside the live HRRR window.")

    # The most recent model run that has actually been published is
    # (current hour - 2 h). Use the run for the target hour if it exists,
    # otherwise the latest available run and a forecast hour that reaches the target.
    latest_cycle = _floor_hour(now) - timedelta(hours=LIVE_HRRR_DELAY_HOURS)
    cycle = min(target, latest_cycle)
    forecast_hour = int((target - cycle).total_seconds() // 3600)

    if forecast_hour < 0 or forecast_hour > LIVE_HRRR_MAX_FORECAST_HOURS:
        raise ValueError(f"Live HRRR forecast hour {forecast_hour} is out of range.")

    return _hrrr_profile(site, cycle, forecast_hour, "HRRR live forecast")


def _historical_hrrr_profile(site, launch_time):
    # Source 2: the archived HRRR analysis (forecast hour 0) for the hour that
    # contains liftoff. For this flight that is the 18:00 UTC run.
    cycle = _floor_hour(launch_time)
    print(f"Requesting archived HRRR analysis: {cycle.isoformat()} UTC F00")
    return _hrrr_profile(site, cycle, 0, "HRRR archived analysis")


def _download_era5_profile(site, launch_time):
    """Download a fresh ERA5 pressure-level profile for this run only."""
    import cdsapi

    # Source 3 (last resort): ERA5 reanalysis for the same hour.
    target = _floor_hour(launch_time)
    # Ask the CDS for geopotential, temperature and wind on all PRESSURE_LEVELS
    # for a +/- 0.5 degree box around the site, as a NetCDF file.
    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "geopotential",
            "temperature",
            "u_component_of_wind",
            "v_component_of_wind",
        ],
        "pressure_level": [str(level) for level in PRESSURE_LEVELS],
        "year": target.strftime("%Y"),
        "month": target.strftime("%m"),
        "day": target.strftime("%d"),
        "time": target.strftime("%H:00"),
        "data_format": "netcdf",
        "download_format": "unarchived",
        # [north, west, south, east]
        "area": [
            site["lat"] + 0.5,
            site["lon"] - 0.5,
            site["lat"] - 0.5,
            site["lon"] + 0.5,
        ],
    }

    with tempfile.TemporaryDirectory(prefix="bandit_era5_pressure_") as temp_dir:
        nc_path = Path(temp_dir) / "era5_pressure.nc"
        cdsapi.Client().retrieve(
            "reanalysis-era5-pressure-levels", request, str(nc_path)
        )

        with xr.open_dataset(nc_path) as ds:
            # Accept both short (z, t, u, v) and long variable names.
            aliases = {
                "z": ("z", "geopotential"),
                "t": ("t", "temperature"),
                "u": ("u", "u_component_of_wind"),
                "v": ("v", "v_component_of_wind"),
            }
            names = {}
            for target_name, choices in aliases.items():
                for candidate in choices:
                    if candidate in ds.data_vars:
                        names[target_name] = candidate
                        break
                if target_name not in names:
                    raise ValueError(f"ERA5 missing {target_name}: {list(ds.data_vars)}")

            # Nearest grid point to the pad (ERA5 longitudes are 0-360).
            point = ds.sel(
                latitude=site["lat"],
                longitude=site["lon"] % 360,
                method="nearest",
            )

            def values(variable):
                # Return the vertical column for one variable as a float array,
                # removing the single-hour time dimension.
                da = point[names[variable]]
                for dim in ("time", "valid_time"):
                    if dim in da.dims:
                        da = da.isel({dim: 0})
                return np.asarray(da.squeeze().values, dtype=float)

            if "pressure_level" not in point.coords:
                raise ValueError("ERA5 file has no pressure_level coordinate.")

            levels = np.asarray(point["pressure_level"].values, dtype=float)
            # ERA5 gives geopotential (m^2/s^2); divide by g for meters.
            z = values("z") / 9.80665
            temperature = values("t")
            u = values("u")
            v = values("v")

            # Keep only finite values at or above the pad elevation.
            valid = (
                np.isfinite(z) & np.isfinite(temperature)
                & np.isfinite(u) & np.isfinite(v)
                & (z >= site["elevation"])
            )
            # Sort from the ground up; convert hPa to Pa.
            order = np.argsort(z[valid])
            profile = {
                "height": z[valid][order],
                "pressure": levels[valid][order] * 100.0,
                "temperature": temperature[valid][order],
                "u": u[valid][order],
                "v": v[valid][order],
            }

    # Add the pad-level anchor (downloaded as a second request) and validate.
    anchor = _era5_surface_anchor(site, target)
    return _add_surface_anchor(profile, anchor, "ERA5 reanalysis", target)


def _print_launch_site_weather(profile, site):
    """Print the atmospheric conditions at the launch pad only."""
    # Unit conversion factors for the printed (imperial) values.
    m_to_ft = 3.280839895
    pa_to_inhg = 0.0002952998307
    mps_to_mph = 2.236936292

    # The surface anchor is inserted at the pad elevation and sorted first.
    pressure = float(profile["pressure"][0]) * pa_to_inhg
    # Kelvin -> Fahrenheit.
    temperature = (float(profile["temperature"][0]) - 273.15) * 9.0 / 5.0 + 32.0
    u = float(profile["u"][0])
    v = float(profile["v"][0])
    wind_speed = (u ** 2 + v ** 2) ** 0.5 * mps_to_mph
    # Meteorological wind direction is where the wind comes FROM, measured
    # clockwise from north. u/v describe where it blows TO, hence the minus signs.
    wind_direction = (np.degrees(np.arctan2(-u, -v)) + 360.0) % 360.0

    print("\n--- Launch site weather ---")
    print(f"Coordinates:    {site['lat']:.6f}, {site['lon']:.6f}")
    print(f"Elevation:      {float(site['elevation']) * m_to_ft:,.1f} ft ASL")
    print(f"Pressure:       {pressure:.3f} inHg")
    print(f"Temperature:    {temperature:.1f} °F")
    print(f"Wind speed:     {wind_speed:.1f} mph")
    print(f"Wind direction: {wind_direction:.0f}°")
    print("----------------------------\n")


def setup_historical_environment(
    site,
    launch_time,
    elevation,
    required_valid_time=None,
):
    """Return a RocketPy Environment built from a validated real weather profile."""
    # This is the only public function in the module; main.py calls it.
    #   site ............... dict with "lat", "lon" (decimal degrees)
    #   launch_time ........ liftoff time (converted to UTC)
    #   elevation .......... pad elevation above sea level (m)
    #   required_valid_time  the exact hour the weather must be valid for;
    #                        defaults to the launch time floored to the hour
    launch_time = _as_utc(launch_time)
    required_valid_time = (
        _as_utc(required_valid_time)
        if required_valid_time is not None
        else _floor_hour(launch_time)
    )
    site = dict(site)  # work on a copy so the caller's dictionary is untouched
    site["elevation"] = float(elevation)

    # Weather from after liftoff would be non-causal, so refuse it.
    if required_valid_time > launch_time:
        raise ValueError("Weather valid time cannot be after the launch time.")

    # "Live" HRRR is only an option if the launch is within a few hours in the
    # past or up to 18 hours in the future of the current clock time.
    now = datetime.now(timezone.utc)
    live_window = (
        launch_time >= now - timedelta(hours=LIVE_HRRR_PAST_TOLERANCE_HOURS)
        and launch_time <= now + timedelta(hours=LIVE_HRRR_MAX_FORECAST_HOURS)
    )

    profile = None
    failures = []

    # Build the ordered list of data sources to try. The lambdas delay each
    # download until it is actually attempted.
    loaders = []
    if live_window:
        loaders.append(("live HRRR", lambda: _live_hrrr_profile(site, launch_time)))
    loaders.extend([
        ("archived HRRR", lambda: _historical_hrrr_profile(site, required_valid_time)),
        ("ERA5", lambda: _download_era5_profile(site, required_valid_time)),
    ])

    # Try each source in order and stop at the first one that works.
    # Every failure is remembered so a total failure can report all reasons.
    for label, loader in loaders:
        try:
            candidate = loader()
            candidate_valid = _as_utc(candidate["valid_time"])
            # The data must be valid for exactly the requested hour.
            if candidate_valid != required_valid_time:
                raise ValueError(
                    f"{label} returned {candidate_valid.isoformat()}, "
                    f"but {required_valid_time.isoformat()} was requested."
                )
            profile = candidate
            break
        except Exception as exc:
            failures.append(f"{label}: {exc}")

    # Every source failed: stop with an explanation instead of silently using
    # an idealized atmosphere.
    if profile is None:
        raise RuntimeError(
            "Could not load a valid real-weather profile. No standard-atmosphere "
            "fallback will be used.\n" + "\n".join(failures)
        )

    # One last validation pass on the chosen profile.
    profile = _validate(profile, profile["source"], profile["valid_time"])

    # Create the RocketPy Environment for the launch site and date, then
    # replace its atmosphere with our custom profile. Each argument is a list
    # of (height, value) pairs that RocketPy interpolates between.
    environment = Environment(
        latitude=site["lat"],
        longitude=site["lon"],
        elevation=elevation,
        date=launch_time.replace(tzinfo=None),
    )
    environment.set_atmospheric_model(
        type="custom_atmosphere",
        pressure=list(zip(profile["height"], profile["pressure"])),
        temperature=list(zip(profile["height"], profile["temperature"])),
        wind_u=list(zip(profile["height"], profile["u"])),
        wind_v=list(zip(profile["height"], profile["v"])),
    )

    # Show the pad-level conditions that were used.
    _print_launch_site_weather(profile, site)

    return environment
