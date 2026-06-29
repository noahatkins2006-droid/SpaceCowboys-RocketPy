# Exhaustive Guide to Modifiable Tags in RASAero II (.CDX1)

This document outlines every tag available in a generic RASAero II XML file. When using the automation script, use the **`Parent.Child`** syntax to target tags, and the **`Tag:Index`** syntax when multiple parts share the same name (like body tubes or simulations). Indexes always start at `0`.

---

## 1. Global Rocket Settings (`<RocketDesign>`)

These tags apply to the entire rocket's aerodynamic profile and staging setup. Since they are direct children of `<RocketDesign>`, no indexing is needed unless specified.

* **`Surface`**: The surface finish affecting skin friction drag (e.g., `Smooth Paint`, `Camouflage Paint`).
* **`ModifiedBarrowman`**: Toggle for the aerodynamic calculation method (`True` or `False`).
* **`Turbulence`**: Toggle for turbulent boundary layer calculations (`True` or `False`).
* **`SustainerNozzle`**: Base diameter of the sustainer's motor nozzle.
* **`Booster1Nozzle`**: Base diameter of the first stage's motor nozzle.
* **`Booster2Nozzle`**: Base diameter of the second stage's motor nozzle.
* **`UseBooster1`**: Toggle for a 2-stage configuration (`True` or `False`).
* **`UseBooster2`**: Toggle for a 3-stage configuration (`True` or `False`).

---

## 2. Nose Cone (`<NoseCone>`)

There is generally only one nose cone at the top of the rocket.

* **`NoseCone.Length`**: Overall length of the nose cone.
* **`NoseCone.Diameter`**: Base outer diameter.
* **`NoseCone.Shape`**: Aerodynamic profile (e.g., `LV-Haack`, `Von Karman`, `Ogive`, `Conical`).
* **`NoseCone.BluntRadius`**: Radius of the spherical blunting at the tip (0 for sharp).
* **`NoseCone.Location`**: Distance from the top (always `0` for the primary nose cone).

---

## 3. Body Tubes (`<BodyTube>`)

Because rockets are built with multiple tube sections, **you must use the index syntax (`:0`, `:1`, `:2`, etc.)** to specify which tube you are modifying. 

* **`BodyTube:X.Length`**: Length of the specific tube section.
* **`BodyTube:X.Diameter`**: Outer diameter of the tube.
* **`BodyTube:X.Location`**: Distance from the nose cone tip to the top of this tube.
* **`BodyTube:X.LaunchLugDiameter`**: Outer diameter of an attached launch lug (0 if none).
* **`BodyTube:X.LaunchLugLength`**: Length of the attached launch lug.
* **`BodyTube:X.RailGuideDiameter`**: Diameter of an attached rail button/guide.
* **`BodyTube:X.RailGuideHeight`**: Height/standoff of the rail guide.
* **`BodyTube:X.LaunchShoeArea`**: Frontal area of a conformal launch shoe.
* **`BodyTube:X.BoattailLength`**: Length of an integrated boattail at the end of this tube.
* **`BodyTube:X.BoattailRearDiameter`**: Aft diameter of the integrated boattail.
* **`BodyTube:X.BoattailOffset`**: Vertical offset of the boattail.
* **`BodyTube:X.Overhang`**: Length the tube extends past the motor block.

---

## 4. Fins (`<Fin>`)

Fins are attached to a specific body tube. To modify them, you must route your dictionary key through the specific body tube they are attached to.

* **`BodyTube:X.Fin.Count`**: Number of fins in the set (e.g., `3` or `4`).
* **`BodyTube:X.Fin.Chord`**: Root chord length (where it attaches to the tube).
* **`BodyTube:X.Fin.Span`**: Distance from the root to the tip of the fin.
* **`BodyTube:X.Fin.SweepDistance`**: Longitudinal distance from the root leading edge to the tip leading edge.
* **`BodyTube:X.Fin.TipChord`**: Length of the fin tip.
* **`BodyTube:X.Fin.Thickness`**: Physical thickness of the fin material.
* **`BodyTube:X.Fin.LERadius`**: Leading Edge radius.
* **`BodyTube:X.Fin.Location`**: Distance from the top of the *body tube* down to the fin root leading edge.
* **`BodyTube:X.Fin.AirfoilSection`**: Cross-sectional shape (e.g., `Double Wedge`, `Hexagonal`, `Rounded`).
* **`BodyTube:X.Fin.FX1`**: Custom airfoil parameter 1 (shape dependent).
* **`BodyTube:X.Fin.FX3`**: Custom airfoil parameter 3 (shape dependent).

---

## 5. Boat Tails and Transitions (`<BoatTail>` / `<Transition>`)

These connect tubes of different diameters or taper the rear of the rocket. Usually requires indexing if there are multiple.

* **`BoatTail:X.Length`**: Longitudinal length of the transition section.
* **`BoatTail:X.Diameter`**: Forward (starting) diameter.
* **`BoatTail:X.RearDiameter`**: Aft (ending) diameter.
* **`BoatTail:X.Location`**: Distance from the nose cone tip to the start of the boattail.

---

## 6. Launch Environment (`<LaunchSite>`)

The atmospheric and physical conditions at the launch pad. No indexing required.

* **`LaunchSite.Altitude`**: Pad elevation above sea level (feet/meters based on your RASAero settings).
* **`LaunchSite.Pressure`**: Atmospheric pressure.
* **`LaunchSite.RodAngle`**: Launch angle off-vertical (degrees).
* **`LaunchSite.RodLength`**: Length of the launch rail/rod.
* **`LaunchSite.Temperature`**: Ambient air temperature.
* **`LaunchSite.WindSpeed`**: Average wind speed at the pad.

---

## 7. Recovery Systems (`<Recovery>`)

Parameters for parachutes and deployment events. No indexing required.

* **`Recovery.Altitude1`**: Deployment altitude for event 1 (typically drogue).
* **`Recovery.DeviceType1`**: Type of device (e.g., `Parachute`, `Streamer`, `None`).
* **`Recovery.Size1`**: Physical dimension of the recovery device.
* **`Recovery.CD1`**: Drag coefficient of the first recovery device.
* **`Recovery.Event1`**: Boolean toggling if the event happens (`True`/`False`).
* **`Recovery.Altitude2`**: Deployment altitude for event 2 (typically main).
* **`Recovery.DeviceType2`**: Type of device for event 2.
* **`Recovery.Size2`**: Physical dimension of the second recovery device.
* **`Recovery.CD2`**: Drag coefficient of the second recovery device.
* **`Recovery.Event2`**: Boolean toggling if the event happens.

---

## 8. Saved Simulations (`<Simulation>`)

These are the stored motor setups inside `<SimulationList>`. A `.CDX1` file can hold multiple saved setups, so **you must index them (`Simulation:0`, `Simulation:1`, etc.)**.

* **`Simulation:X.SustainerEngine`**: Exact string name of the loaded motor (e.g., `M1340W  (AT)`).
* **`Simulation:X.SustainerLaunchWt`**: Liftoff mass of the rocket.
* **`Simulation:X.SustainerNozzleDiameter`**: Nozzle diameter for this specific flight profile.
* **`Simulation:X.SustainerCG`**: Center of Gravity location from the nose tip.
* **`Simulation:X.SustainerIgnitionDelay`**: Delay before motor ignition.

*(Note: Staged rockets will also have identical tags for `Booster1LaunchWt`, `Booster1CG`, `Booster2LaunchWt`, etc., within the simulation profile. Output tags like `MaxAltitude`, `FlightTime`, and `MaxVelocity` are also located here, but they should not be modified via script, as the simulation executable recalculates them.)*

---

## 💡 Code Implementation Example

Here is a Python dictionary showing how to target a wide variety of these parameters at once using your script:

```python
modifications = {
    "ModifiedBarrowman": "True",
    "NoseCone.Shape": "Von Karman",
    "BodyTube:1.Length": 24.5,
    "BodyTube:2.Fin.Span": 6.25,
    "BodyTube:2.Fin.SweepDistance": 10.5,
    "BoatTail.RearDiameter": 3.5,
    "LaunchSite.RodLength": 12,
    "LaunchSite.WindSpeed": 5,
    "Recovery.CD1": 1.5,
    "Simulation:0.SustainerEngine": "N2000W  (AT)",
    "Simulation:0.SustainerLaunchWt": 65.0,
    "Simulation:0.SustainerCG": 110.5
}