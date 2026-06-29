import cfgrib, numpy as np, urllib.request, json

lat_target, lon_target = 31.0436111, -103.5283333 + 360

# ── 1. HRRR Analysis (fxx=0) from the 00z Jun 18 run (= 7pm CDT Jun 17) ──
from herbie import Herbie
import warnings; warnings.filterwarnings("ignore")

H_sfc = Herbie("2026-06-18 00:00", model="hrrr", product="sfc", fxx=0)
H_sfc.download(save_dir=r"data\weather_data")
sfc_file = str(H_sfc.get_localFilePath())

results = {}
for ds in cfgrib.open_datasets(sfc_file):
    lat_g = ds['latitude'].values.flatten()
    lon_g = ds['longitude'].values.flatten()
    idx = np.argmin((lat_g - lat_target)**2 + (lon_g - lon_target)**2)
    yi, xi = np.unravel_index(idx, ds['latitude'].values.shape)
    for var in ['t2m', 'sp', 'u10', 'v10']:
        if var in ds.variables and var not in results:
            results[var] = float(ds[var].isel(y=yi, x=xi).values)

t_f    = (results['t2m'] - 273.15) * 9/5 + 32
p_inhg_station  = results['sp'] / 3386.389
u, v   = results.get('u10', 0), results.get('v10', 0)
spd_mph = (u**2 + v**2)**0.5 * 2.23694
direction = (270 - np.degrees(np.arctan2(v, u))) % 360

print("── HRRR Analysis (fxx=0) ──")
print(f"  Temperature:       {t_f:.1f} F")
print(f"  Station Pressure:  {p_inhg_station:.2f} inHg")
print(f"  Wind Speed:        {spd_mph:.1f} mph")
print(f"  Wind Direction:    {direction:.0f} deg (from)")

# ── 2. IEM ASOS actual observation from KMAF (Midland Intl) ──
print("\n── KMAF ASOS Observation (actual) ──")
url = "https://mesonet.agron.iastate.edu/json/current.json?station=KMAF&network=TX_ASOS"
# IEM historical: pull the 00:00 UTC Jun 18 obs
url_hist = "https://mesonet.agron.iastate.edu/json/obhistory.json?station=KMAF&network=TX_ASOS&date=2026-06-18"
try:
    with urllib.request.urlopen(url_hist, timeout=10) as r:
        data = json.loads(r.read())
    # Find obs closest to 00:00 UTC
    obs_list = data.get("data", [])
    target_obs = None
    for obs in obs_list:
        if "00:00" in obs.get("utc_valid", ""):
            target_obs = obs
            break
    if target_obs is None and obs_list:
        target_obs = obs_list[0]
    if target_obs:
        tmpf = target_obs.get("tmpf", "N/A")
        alti = target_obs.get("alti", "N/A")   # altimeter inHg
        sknt = target_obs.get("sknt", "N/A")   # wind knots
        drct = target_obs.get("drct", "N/A")   # wind direction
        wspd_mph = float(sknt) * 1.15078 if sknt != "N/A" else "N/A"
        print(f"  Temperature:       {tmpf} F")
        print(f"  Altimeter:         {alti} inHg")
        print(f"  Wind Speed:        {wspd_mph:.1f} mph" if wspd_mph != "N/A" else "  Wind Speed: N/A")
        print(f"  Wind Direction:    {drct} deg")
except Exception as e:
    print(f"  IEM fetch failed: {e}")
