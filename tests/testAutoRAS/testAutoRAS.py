import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.automated_RASAero import autoRASAero

rocketPath = (Path(__file__).resolve() / ".." / "Research_Vehicle_09182025_4.CDX1").resolve()

outputDirectory = (Path(__file__).resolve() / "..").resolve()

editDict = {
    "Fin.Count" : 5,
    "Fin.Chord" : 13,
    "Fin.Span" : 6,
    "Fin.Rizz" : "unbelievable"
}

modifiedRocketPath, modifiedRocketName = autoRASAero.createModifiedRocket(rocketPath, editDict)

outputName = "AutomatedOutput-" + modifiedRocketName

data_file_path = autoRASAero.getData(modifiedRocketPath, outputDirectory, outputName)

cd_on_file_path, cd_off_file_path = autoRASAero.getCDFiles(data_file_path)