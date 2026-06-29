# OpenRocket File Parser Documentation

## Overview

This module parses OpenRocket (`.ork`) files to extract rocket design parameters and simulation data. OpenRocket files are ZIP archives containing XML data, which this parser reads using BeautifulSoup to provide easy access to component specifications, mass properties, and motor configurations.

## Dependencies

- `BeautifulSoup` (bs4) - XML parsing
- `zipfile` - Reading .ork archive files
- `sys`, `os` - Path management
- Custom module: `file_paths.file_path_func.get_ork_path`

## Global Variables

- `ork_path` - Path to the OpenRocket file
- `bs` - BeautifulSoup object containing parsed XML
- `global_motor_config` - Currently selected motor configuration index
- `data_labels` - List of data field labels from simulation
- `datapoints` - List of simulation data points for current motor config
- `positiondict` - Dictionary mapping component names to axial positions

## Core Functions

### `set_openrocket_file(filepath, motor_config=0)`

Initializes the parser by loading an OpenRocket file.

**Parameters:**
- `filepath` - Path to the .ork file
- `motor_config` - Motor configuration index (default: 0)

**Actions:**
1. Resolves file path using `get_ork_path()`
2. Extracts and parses `rocket.ork` XML from ZIP archive
3. Builds position dictionary for all components
4. Sets the active motor configuration

### `set_motor_config(motor_index)`

Switches to a different motor configuration and loads its simulation data.

**Parameters:**
- `motor_index` - Index of motor configuration to load

**Returns:**
- Motor element from the XML

**Raises:**
- `RuntimeError` if no simulation data is found

### `set_up_position_dictionary()`

Builds a dictionary mapping top level component names to their axial positions along the rocket. Finds top level components by iterating through the children of the nosecone's parent, accumulating lengths.

## Position & Mass Calculation Functions

### `get_position(part)`

Calculates the axial position (in meters) of any rocket component.

**Parameters:**
- `part` - BeautifulSoup element representing a rocket part

**Returns:**
- Float position in meters from nose tip

**Logic:**
- Handles absolute, top, middle, and bottom position types
- Recursively calculates positions for nested components
- Special handling for motors and trapezoidal fin sets

### `get_mass(part)`

Calculates total mass of a component, respecting override settings.
Depreciated and unused because the simulation data provides more accurate values.

**Parameters:**
- `part` - Component element

**Returns:**
- Float mass in kilograms

**Logic:**
- Collects all mass elements
- Excludes masses overridden by subcomponent settings
- Sums remaining masses

### `get_cg(part, midMotor, motorMass)`

Calculates center of gravity for a component.
Depreciated and unused because the simulation data gives more accurate values

**Parameters:**
- `part` - Component element
- `midMotor` - Motor midpoint position
- `motorMass` - Motor mass

**Returns:**
- Float CG position in meters

**Logic:**
- Finds the cumative sum of each components mass times its midpoint
- Adds user input to include the motor mass times position (not needed now with simulation data)
- divides by the total mass to get CG

## Component Getter Functions

### `get_nosecone(value, index=0, name=None)`

Retrieves nosecone properties.

**Parameters:**
- `value` - Property to retrieve: `'length'` or `'position'`
- `index` - Nosecone index if multiple exist (default: 0)
- `name` - Optional exact name to find specific nosecone

**Returns:**
- Float value or None

**Raises:**
- `RuntimeError` if file not loaded
- `ValueError` if no nosecones found or invalid attribute
- `IndexError` if index out of range

### `get_boattail(value, index=0, name="Boattail")`

Retrieves boattail/transition properties.

**Parameters:**
- `value` - Property: `'length'`, `'top_radius'`, `'bottom_radius'`, or `'position'`
- `index` - Transition index (default: 0)
- `name` - Transition name (default: "Boattail")

**Returns:**
- Float value or None

**Note:** This function searches all `<transition>` elements, not just boattails specifically. Index is used to specify a certain `<transition>` element if there is more than one `<transition>` element.

### `get_finset(value, index=0)`

Retrieves fin set properties.

**Parameters:**
- `value` - Property: `'n'`, `'root_chord'`, `'tip_chord'`, `'span'`, `'sweep_length'`, or `'position'`
- `index` - Fin set index (default: 0)

**Returns:**
- Int for `'n'` (number of fins), Float for others, or None

**Special Notes:**
- `'span'` returns height 
- `'position'` returns position of trailing edge of root chord

### `get_railbutton(value, index=0, name=None)`

Retrieves rail button properties.

**Parameters:**
- `value` - Property: `'angular_position'` or `'position'`
- `index` - Rail button index among those with same name (default: 0)
- `name` - Required if multiple rail button types exist

**Returns:**
- Float value or None

### `get_rocket(value)`

Retrieves overall rocket properties.

**Parameters:**
- `value` - Property: `'mass'`, `'radius'`, `'cg'`, or `'cg_without_motor'`

**Returns:**
- Float value or None

**Data Sources:**
- `'mass'` and `'cg'` - Retrieved from simulation datapoints
- `'radius'` - Retrieved from first body tube
- `'cg_without_motor'` - Calculated by removing motor mass contribution

### `get_motor(value)`

Retrieves motor properties.

**Parameters:**
- `value` - Property: `'dry_mass'`, `'full_mass'`, `'propellant_mass'`, `'position'`, `'diameter'`, or `'part'`

**Returns:**
- Float value, motor element, or None

**Logic:**
- Mass values extracted from simulation data across all time points
- `'dry_mass'` - Minimum motor mass (burnout)
- `'full_mass'` - Maximum motor mass (ignition)
- `'propellant_mass'` - Difference between full and dry
- `'part'` - Returns raw motor element

## Usage Example

```python
from openrocket_parser import *

# Load rocket file with first motor configuration
set_openrocket_file("my_rocket.ork", motor_config=0)

# Get various rocket properties
nose_length = get_nosecone('length')
fin_count = get_finset('n')
rocket_mass = get_rocket('mass')
cg_location = get_rocket('cg')
motor_impulse = get_motor('propellant_mass')

# Get rail button positions
rb1_pos = get_railbutton('position', index=0, name='Airfoiled Rail Button')
rb2_pos = get_railbutton('position', index=1, name='Airfoiled Rail Button')
```

## Important Notes

1. **Simulation Data Required:** The file must contain simulation data. Run at least one simulation in OpenRocket and save with data before using this parser.

2. **Motor Configurations:** Many rockets have multiple motor options. Use the `motor_config` parameter to select which configuration to analyze.

3. **Position Reference:** All positions are measured in meters from the nose tip along the rocket's axis.

4. **Mass Units:** All masses are in kilograms.

5. **Naming Conventions:** When retrieving components by name, the name must match exactly as it appears in OpenRocket (case-sensitive, whitespace-sensitive).

## Error Handling

The module raises specific exceptions:
- `RuntimeError` - OpenRocket file not loaded or no simulation data
- `ValueError` - Component not found or invalid attribute requested
- `IndexError` - Component index out of range