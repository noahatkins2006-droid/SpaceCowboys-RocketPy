## -- Space Cowboys RocketPy GUI Launcher -- ##
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess, sys, os, threading, re, glob

SCRIPT = os.path.join(os.path.dirname(__file__), "rocketpySim", "rocketpy_main", "main_rocket", "rocketpy_main.py")
GE_DIR = os.path.join(os.path.dirname(__file__), "rocketpySim", "rocketpy_main", "main_rocket", "googleEarth")

LOCATIONS = ["midland", "tl1", "sf"]
MOTORS    = ["AeroTech_O5500X-PS.eng", "AeroTech_M1340W.eng", "AeroTech_J450DM.eng",
             "AeroTech_J800T.eng", "AeroTech_HP-H195NT.eng"]
DRAG_FILES = [
    "Bandit_Rough_Camo_4-30-2026_CD.CSV", "Bandit_TL1_Camo_CD_Power_On.csv",
    "Bandit_TL1_Smooth_CD_Power_On.csv", "Bandit10_CD_On.CSV", "Bandit7_CD_On.CSV",
    "CD_Power_On_Frank.CSV",
]

# ── Theme Colors ──
DARK = {
    "bg": "#1a1a2e", "fg": "#e0e0e0", "entry_bg": "#16213e", "entry_fg": "#e0e0e0",
    "frame_bg": "#0f3460", "accent": "#e94560", "accent_hover": "#c23152",
    "output_bg": "#0d1117", "output_fg": "#c9d1d9", "select_bg": "#e94560",
}
LIGHT = {
    "bg": "#f5f5f5", "fg": "#1a1a1a", "entry_bg": "#ffffff", "entry_fg": "#1a1a1a",
    "frame_bg": "#ffffff", "accent": "#0078d4", "accent_hover": "#005a9e",
    "output_bg": "#ffffff", "output_fg": "#1a1a1a", "select_bg": "#0078d4",
}

is_dark = [True]
latest_kml = [None]

def find_latest_kml():
    """Find the most recent KML in the googleEarth folder."""
    if not os.path.isdir(GE_DIR):
        return None
    kmls = glob.glob(os.path.join(GE_DIR, "*.kml"))
    if not kmls:
        return None
    return max(kmls, key=os.path.getmtime)

def open_google_earth():
    """Open the latest KML file in Google Earth."""
    kml = latest_kml[0] or find_latest_kml()
    if kml and os.path.exists(kml):
        os.startfile(kml)
    else:
        messagebox.showwarning("No KML Found", "Run a simulation first to generate a flight path.")

def apply_theme(colors):
    root.configure(bg=colors["bg"])
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabelframe", background=colors["frame_bg"])
    style.configure("TLabelframe.Label", background=colors["frame_bg"], foreground=colors["fg"],
                    font=("Segoe UI", 10, "bold"))
    style.configure("TLabel", background=colors["frame_bg"], foreground=colors["fg"],
                    font=("Segoe UI", 9))
    style.configure("TButton", background=colors["accent"], foreground="#ffffff",
                    font=("Segoe UI", 9, "bold"), padding=6)
    style.map("TButton", background=[("active", colors["accent_hover"]),
                                      ("disabled", "#555555")])
    # Entry
    style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"],
                    insertcolor=colors["fg"])
    style.map("TEntry", fieldbackground=[("readonly", colors["entry_bg"])],
              foreground=[("readonly", colors["entry_fg"])])
    # Combobox — this fixes the dropdown text visibility
    style.configure("TCombobox", fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"],
                    selectbackground=colors["select_bg"], selectforeground="#ffffff",
                    background=colors["entry_bg"])
    style.map("TCombobox",
              fieldbackground=[("readonly", colors["entry_bg"]), ("disabled", "#333333")],
              foreground=[("readonly", colors["entry_fg"]), ("disabled", "#888888")],
              selectbackground=[("readonly", colors["select_bg"])],
              selectforeground=[("readonly", "#ffffff")])
    # Fix the dropdown popdown listbox colors
    root.option_add("*TCombobox*Listbox.background", colors["entry_bg"])
    root.option_add("*TCombobox*Listbox.foreground", colors["entry_fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", colors["select_bg"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    # Progressbar
    style.configure("TProgressbar", background=colors["accent"], troughcolor=colors["entry_bg"])
    # Output box
    output_box.configure(bg=colors["output_bg"], fg=colors["output_fg"],
                         insertbackground=colors["fg"], selectbackground=colors["select_bg"],
                         selectforeground="#ffffff")

def toggle_theme():
    is_dark[0] = not is_dark[0]
    apply_theme(DARK if is_dark[0] else LIGHT)
    btn_theme.config(text="☀️  Light Mode" if is_dark[0] else "🌙  Dark Mode")

def patch_and_run():
    """Patch the config block in rocketpy_main.py and run it, streaming output."""
    btn_run.config(state="disabled", text="Running...")
    output_box.config(state="normal")
    output_box.delete(1.0, tk.END)

    with open(SCRIPT, "r") as f:
        src = f.read()

    def sub(pattern, value):
        return re.sub(pattern, value, src, flags=re.MULTILINE)

    src = sub(r'^TARGET_DATE\s*=.*$',     f'TARGET_DATE   = "{date_var.get()}"')
    src = sub(r'^LAUNCH_HOUR\s*=.*$',     f'LAUNCH_HOUR   = "{hour_var.get()}"')
    src = sub(r'^HRRR_FXX\s*=.*$',        f'HRRR_FXX      = {fxx_var.get()}')
    src = sub(r'^LOCATION\s*=.*$',         f'LOCATION      = "{loc_var.get()}"')
    src = sub(r'^ELEVATION_M\s*=.*$',      f'ELEVATION_M   = {elev_var.get()}')
    src = sub(r'^MOTOR_FILE\s*=.*$',       f'MOTOR_FILE    = "{motor_var.get()}"')
    src = sub(r'^DRAG_FILE\s*=.*$',        f'DRAG_FILE     = "{drag_var.get()}"')
    src = sub(r'^ROCKET_MASS\s*=.*$',      f'ROCKET_MASS   = {mass_var.get()}')
    src = sub(r'^CG_WITHOUT_MOTOR\s*=.*$', f'CG_WITHOUT_MOTOR = {cg_var.get()}')

    real_apo = real_apo_var.get().strip()
    if real_apo:
        src = sub(r'^REAL_APOGEE_FT\s*=.*$', f'REAL_APOGEE_FT = {real_apo}')
    else:
        src = sub(r'^REAL_APOGEE_FT\s*=.*$', f'REAL_APOGEE_FT = None')

    run_file = os.path.join(os.path.dirname(SCRIPT), "_gui_run.py")
    with open(run_file, "w") as f:
        f.write(src)

    # ── Progress popup ──
    colors = DARK if is_dark[0] else LIGHT
    popup = tk.Toplevel(root)
    popup.title("Running Simulation...")
    popup.geometry("440x170")
    popup.resizable(False, False)
    popup.configure(bg=colors["bg"])
    popup.grab_set()

    tk.Label(popup, text="Space Cowboys RocketPy", font=("Segoe UI", 12, "bold"),
             bg=colors["bg"], fg=colors["fg"]).pack(pady=(14,2))
    stage_var = tk.StringVar(value="Initializing...")
    tk.Label(popup, textvariable=stage_var, font=("Segoe UI", 10),
             bg=colors["bg"], fg=colors["accent"]).pack(pady=2)

    progress = ttk.Progressbar(popup, mode="determinate", length=380, maximum=100)
    progress.pack(pady=8)
    pct_var = tk.StringVar(value="0%")
    tk.Label(popup, textvariable=pct_var, font=("Consolas", 9),
             bg=colors["bg"], fg=colors["fg"]).pack()

    STAGES = [
        ("Downloading HRRR Pressure",    5,  "📡 Downloading pressure-level weather..."),
        ("Downloading HRRR Surface",     10, "📡 Downloading surface weather..."),
        ("Pad Elevation",                18, "🌡️  Processing weather at launch site..."),
        ("Solving CD scale",             25, "🔢 Calibrating drag curves..."),
        ("CD scale factor",              45, "✅ Drag calibration complete"),
        ("Setting up flight",            50, "🚀 Building rocket model..."),
        ("post_process",                 55, "⚙️  Running flight simulation..."),
        ("Surface wind",                 70, "📊 Processing surface conditions..."),
        ("Rail conditions",              78, "📋 Computing rail conditions..."),
        ("Apogee",                       85, "🏔️  Computing apogee..."),
        ("Parachute",                    90, "🪂 Computing parachute events..."),
        ("Impact",                       94, "🎯 Computing landing..."),
        ("export",                       98, "💾 Exporting flight path..."),
        ("Opening Google Earth",         99, "🌍 Launching Google Earth..."),
    ]
    current_pct = [0]

    def update_progress(line):
        for keyword, pct, msg in STAGES:
            if keyword.lower() in line.lower() and pct > current_pct[0]:
                current_pct[0] = pct
                progress["value"] = pct
                pct_var.set(f"{pct}%")
                stage_var.set(msg)
                popup.update_idletasks()
                break

    def stream():
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            [sys.executable, run_file],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            cwd=os.path.dirname(run_file),
            env=env,
        )
        for line in proc.stdout:
            output_box.insert(tk.END, line)
            output_box.see(tk.END)
            update_progress(line)
            if line.startswith("LATEST_KML="):
                latest_kml[0] = line.strip().split("=", 1)[1]
            root.update_idletasks()
        proc.wait()
        progress["value"] = 100
        pct_var.set("100%")
        if proc.returncode == 0:
            stage_var.set("✅ Simulation complete!")
            output_box.insert(tk.END, "\n✅ Simulation complete.\n")
            btn_ge.config(state="normal")
        else:
            stage_var.set("❌ Simulation failed")
            output_box.insert(tk.END, f"\n❌ Exited with code {proc.returncode}\n")
        popup.after(1500, popup.destroy)
        btn_run.config(state="normal", text="▶  Run Simulation")

    threading.Thread(target=stream, daemon=True).start()

# ── Window ──
root = tk.Tk()
root.title("Space Cowboys — RocketPy Launcher")
root.resizable(True, True)

style = ttk.Style()
style.theme_use("clam")

pad = {"padx": 8, "pady": 5}

# ── Left panel: inputs ──
left = ttk.LabelFrame(root, text="  Simulation Config  ", padding=12)
left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

def row(parent, label, widget_type, variable, options=None, r=0):
    ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", **pad)
    if widget_type == "entry":
        w = ttk.Entry(parent, textvariable=variable, width=28)
    elif widget_type == "combo":
        w = ttk.Combobox(parent, textvariable=variable, values=options, width=26, state="readonly")
    w.grid(row=r, column=1, sticky="ew", **pad)
    return r + 1

date_var     = tk.StringVar(value="2026-06-17")
hour_var     = tk.StringVar(value="19:00:00")
fxx_var      = tk.StringVar(value="1")
loc_var      = tk.StringVar(value="midland")
elev_var     = tk.StringVar(value="880.87")
motor_var    = tk.StringVar(value=MOTORS[0])
drag_var     = tk.StringVar(value=DRAG_FILES[0])
mass_var     = tk.StringVar(value="12.622")
cg_var       = tk.StringVar(value="1.68")
real_apo_var = tk.StringVar(value="")

r = 0
r = row(left, "Launch Date (YYYY-MM-DD):", "entry", date_var,    r=r)
r = row(left, "Launch Hour (HH:MM:SS):",   "entry", hour_var,    r=r)
r = row(left, "HRRR fxx (0=analysis):",    "entry", fxx_var,     r=r)
r = row(left, "Location:",                 "combo", loc_var,  LOCATIONS, r=r)
r = row(left, "Elevation (m):",            "entry", elev_var,    r=r)
r = row(left, "Motor File:",               "combo", motor_var, MOTORS,   r=r)
r = row(left, "Drag File:",                "combo", drag_var,  DRAG_FILES, r=r)
r = row(left, "Rocket Mass (kg):",         "entry", mass_var,    r=r)
r = row(left, "CG without motor (m):",     "entry", cg_var,      r=r)

# Separator
ttk.Separator(left, orient="horizontal").grid(row=r, column=0, columnspan=2, sticky="ew", pady=8)
r += 1

btn_run = ttk.Button(left, text="▶  Run Simulation", command=patch_and_run)
btn_run.grid(row=r, column=0, columnspan=2, pady=6, ipadx=12, ipady=8, sticky="ew")
r += 1

btn_ge = ttk.Button(left, text="🌍  Open in Google Earth", command=open_google_earth)
btn_ge.grid(row=r, column=0, columnspan=2, pady=4, ipadx=12, ipady=6, sticky="ew")
r += 1

btn_theme = ttk.Button(left, text="☀️  Light Mode", command=toggle_theme)
btn_theme.grid(row=r, column=0, columnspan=2, pady=4, ipadx=12, ipady=6, sticky="ew")

# ── Right panel: output ──
right = ttk.LabelFrame(root, text="  Output  ", padding=12)
right.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

output_box = scrolledtext.ScrolledText(right, width=72, height=38, font=("Cascadia Code", 9),
                                        relief="flat", borderwidth=0)
output_box.pack(fill="both", expand=True)

root.columnconfigure(1, weight=1)
root.rowconfigure(0, weight=1)

# Enable Google Earth button if a KML already exists
if find_latest_kml():
    btn_ge.config(state="normal")

apply_theme(DARK)
root.mainloop()
