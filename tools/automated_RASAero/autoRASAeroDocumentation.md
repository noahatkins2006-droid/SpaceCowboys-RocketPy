# RASAero II Automation Script

This module provides utilities for automating RASAero II workflow. It includes functions to programmatically modify XML-based rocket design files and run aerodynamic simulations via the RASAero II Command Line Interface (CLI), exporting the results to a CSV file.

## Dependencies

To run this script, ensure you have the following installed:
* **Python Standard Library:** `os`, `sys`, `subprocess`, `pathlib` (No installation required)
* **External Packages:** `beautifulsoup4`, `lxml` (Required for BeautifulSoup's XML parsing)
    * Install via pip: `pip install beautifulsoup4 lxml`

> **Note:** The script expects the executable `RASAeroII_CLI.exe` to be located exactly two directories above the directory where this script resides.

---

## Functions

### `getData(CDX1Path, outPutDirectory, fileName)`

Executes the RASAero II CLI to run a simulation on a specified rocket design file and exports the flight data to a CSV.

**Parameters:**
* `CDX1Path` (str): The absolute or relative path to the input RASAero II rocket file (e.g., `.CDX1`).
* `outPutDirectory` (str): The directory where the resulting CSV data should be saved.
* `fileName` (str): The desired name for the output CSV file (without the `.CSV` extension).

**Behavior:**
1. Resolves the path to `RASAeroII_CLI.exe` relative to the script's current location.
2. Constructs absolute paths for the input and output files to prevent pathing errors.
3. Executes the simulation silently using `subprocess.run()`.
4. Prints success or captures and displays exact error codes and standard error outputs if the executable crashes.

---

### `createModifiedRocket(rocket_file, editDictionary)`

Parses an XML-based rocket design file, updates specific tag values based on a provided dictionary, and saves a new modified copy of the file into a dedicated subdirectory.

**Parameters:**
* `rocket_file` (str): The file path to the source XML rocket file.
* `editDictionary` (dict): A dictionary mapping target XML tags to their new values. The keys use a specific dot-and-colon syntax to traverse the XML tree (see **Tag Targeting Syntax** below).

**Returns:**
* `tuple (str, str)`: A tuple containing:
    1. `destination_path`: The full file path to the newly created, modified rocket file.
    2. `newfilename`: The newly generated base filename (without the file extension).

**Behavior:**
1. Verifies the source file exists.
2. Creates a new directory named `{OriginalFileName}_Modified` next to the source file.
3. Parses the XML using `BeautifulSoup`.
4. Iterates through `editDictionary` to locate specific XML nodes and overwrite their string values.
5. Constructs a unique filename by appending the applied modifications in brackets (e.g., `RocketName[Stage_Motor=O3400].CDX1`).
6. Saves the modified XML tree to the new destination.

---

## Tag Targeting Syntax for `editDictionary`

The `createModifiedRocket` function uses a custom syntax in the `editDictionary` keys to navigate the nested XML structure of the rocket file. 

* **Dot (`.`)** indicates a child relationship.
* **Colon (`:`)** indicates an index (0-based) for when there are multiple tags of the same name. If no colon is provided, it defaults to the first occurrence (index 0).

**Examples:**
* `"Motor"`: Finds the first `<Motor>` tag.
* `"Stage.Motor"`: Finds the first `<Motor>` tag inside the first `<Stage>` tag.
* `"Stage:1.Motor:0"`: Finds the first `<Motor>` tag inside the **second** `<Stage>` tag.