import sys 
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.rocketBuilder.buildRocket import buildRocket, buildMotor
import gradio as gr
import matplotlib
matplotlib.use('Agg')  # MUST be before pyplot import. Forces silent background plotting.
import matplotlib.pyplot as plt
import math

# ==========================================
# Gradio Wrapper Functions
# ==========================================

def ui_build_motor(name, dry_mass, dry_inertia_long, dry_inertia_rot, nozzle_radius, 
                   grain_number, grain_density, grain_outer_radius, grain_initial_inner_radius, 
                   grain_initial_height, grain_separation, grains_center_of_mass_position, 
                   center_of_dry_mass_position, nozzle_position, throat_radius):
    
    # 1. Call your existing buildMotor function
    motor_obj = buildMotor(
        name, dry_mass, dry_inertia_long, dry_inertia_rot, nozzle_radius, 
        grain_number, grain_density, grain_outer_radius, grain_initial_inner_radius, 
        grain_initial_height, grain_separation, grains_center_of_mass_position, 
        center_of_dry_mass_position, nozzle_position, throat_radius
    )
    
    # 2. Let RocketPy draw normally, then catch the figure
    plt.close('all') 
    motor_obj.draw()       # No ax argument!
    fig = plt.gcf()        # "Get Current Figure" from matplotlib's memory
    
    return motor_obj, fig

def ui_build_rocket(ork_filepath, cd_filepath, motor_obj):
    if motor_obj is None:
        raise gr.Error("⚠️ You must build the motor in Step 1 before building the rocket!")
    if ork_filepath is None or cd_filepath is None:
        raise gr.Error("⚠️ Please upload both the OpenRocket (.ork) and Drag (.csv) files.")
        
    # 1. Call your existing buildRocket function
    rocket_obj = buildRocket(ork_filepath, cd_filepath, motor_obj)
    
    # 2. Let RocketPy draw normally, then catch the figure
    plt.close('all')
    rocket_obj.draw()      # No ax argument!
    fig = plt.gcf()        # Catch the figure
    
    return fig

def calculate_propellant_mass(grain_num, density, r_out, r_in, height):
    # Protect against invalid geometry where inner core is larger than the motor!
    if r_in >= r_out:
        return 0.0, "⚠️ Error: Inner radius must be smaller than outer radius."
    
    # Volume of a hollow cylinder: pi * (R_out^2 - R_in^2) * h
    vol = math.pi * (r_out**2 - r_in**2) * height
    
    total_mass = grain_num * density * vol
    
    return total_mass, f"✅ Propellant geometry valid."

# ==========================================
# Gradio Interface Layout
# ==========================================

with gr.Blocks(title="Space Cowboys: Rocket Builder") as demo:
    gr.Markdown("#Rocket Builder")
    
    # This State variable acts as our backend memory. It holds the SolidMotor object.
    stored_motor = gr.State(value=None)
    
    with gr.Row():
        
        # ------------------------------------
        # STEP 1: MOTOR BUILDER
        # ------------------------------------
        with gr.Column(scale=1):
            gr.Markdown("### Step 1: Configure & Build Motor")
            
            # Using an accordion to hide the massive list of parameters and keep UI clean
            with gr.Accordion("Motor Parameters", open=True):
                m_name = gr.Textbox(value="O5500X-PS", label="Motor Name (ThrustCurve)")
                
                with gr.Row():
                    m_dry_mass = gr.Number(value=1.5, label="Dry Mass (g)")
                
                with gr.Row():
                    m_inertia_long = gr.Number(value=0.1, label="Dry Inertia Long")
                    m_inertia_rot = gr.Number(value=0.01, label="Dry Inertia Rot")
                    
                with gr.Row():
                    m_nozzle_rad = gr.Number(value=0.02, label="Nozzle Radius (m)")
                    m_throat_rad = gr.Number(value=0.01, label="Throat Radius (m)")
                    
                with gr.Row():
                    m_grain_num = gr.Number(value=5, label="Grain Number", precision=0)
                    m_grain_density = gr.Number(value=1815, label="Grain Density (kg/m³)")
                    
                with gr.Row():
                    m_grain_out_rad = gr.Number(value=0.04, label="Grain Outer Radius (m)")
                    m_grain_in_rad = gr.Number(value=0.015, label="Grain Inner Radius (m)")
                    
                with gr.Row():
                    m_grain_height = gr.Number(value=0.12, label="Grain Initial Height (m)")
                    m_grain_sep = gr.Number(value=0.005, label="Grain Separation (m)")

                with gr.Row():
                    # Set interactive=False so users can't type in it; it's read-only
                    calc_prop_mass = gr.Number(label="Calculated Propellant Mass (kg)", interactive=False)
                    calc_status = gr.Textbox(label="Geometry Status", interactive=False)
                    
                with gr.Row():
                    m_grain_cm = gr.Number(value=0.3, label="Grains CM Position (m)")
                    m_dry_cm = gr.Number(value=0.25, label="Dry Mass CM Position (m)")
                    m_nozzle_pos = gr.Number(value=0.0, label="Nozzle Position (m)")
            
            grain_inputs = [m_grain_num, m_grain_density, m_grain_out_rad, m_grain_in_rad, m_grain_height]
    
            # Loop through them, and bind the change event to the function
            for input_component in grain_inputs:
                input_component.change(
                    fn=calculate_propellant_mass,
                    inputs=grain_inputs,
                    outputs=[calc_prop_mass, calc_status]
                )

            btn_build_motor = gr.Button("1. Build Motor", variant="primary")
            plot_motor = gr.Plot(label="Motor Schematic")

        # ------------------------------------
        # STEP 2: ROCKET BUILDER
        # ------------------------------------
        with gr.Column(scale=1):
            gr.Markdown("### Step 2: Upload Files & Build Rocket")
            
            ork_upload = gr.File(label="Upload OpenRocket (.ork)", file_types=[".ork"], type="filepath")
            cd_upload = gr.File(label="Upload Drag Curve (.csv)", file_types=[".csv"], type="filepath")
            
            btn_build_rocket = gr.Button("2. Build Rocket", variant="secondary")
            plot_rocket = gr.Plot(label="Rocket Schematic")

    # ==========================================
    # Event Wiring
    # ==========================================
    
    # Wiring the Motor Button
    btn_build_motor.click(
        fn=ui_build_motor,
        inputs=[
            m_name, m_dry_mass, m_inertia_long, m_inertia_rot, m_nozzle_rad, 
            m_grain_num, m_grain_density, m_grain_out_rad, m_grain_in_rad, 
            m_grain_height, m_grain_sep, m_grain_cm, m_dry_cm, m_nozzle_pos, 
            m_throat_rad
        ],
        outputs=[stored_motor, plot_motor] # Outputs to BOTH the invisible State and the Plot
    )
    
    # Wiring the Rocket Button
    btn_build_rocket.click(
        fn=ui_build_rocket,
        inputs=[ork_upload, cd_upload, stored_motor], # Pulls the motor out of the State
        outputs=[plot_rocket]
    )

if __name__ == "__main__":
    # Launching the interface locally
    demo.launch(inbrowser=True)