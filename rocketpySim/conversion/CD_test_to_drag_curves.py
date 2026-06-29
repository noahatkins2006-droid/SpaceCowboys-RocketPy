import os
from pathlib import Path
import pandas as pd
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from file_paths.file_path_func import get_drag_path



def getCDFiles(dataCSV_filePath):
        
    source_dir = os.path.dirname(dataCSV_filePath)
    filename = os.path.basename(dataCSV_filePath)
    name_without_ext, ext = os.path.splitext(filename)

    on_path = (Path(source_dir).resolve() /  (name_without_ext + "_CD_On" + ext)).resolve()
    off_path = (Path(source_dir).resolve() / (name_without_ext + "_CD_Off" + ext)).resolve()

    df_CD_On = pd.read_csv(dataCSV_filePath, usecols=["Mach","CD Power-On"])
    df_CD_On.to_csv(on_path, index=False)
    df_CD_Off = pd.read_csv(dataCSV_filePath, usecols=["Mach","CD Power-Off"])
    df_CD_Off.to_csv(off_path, index=False)

    return on_path, off_path

if __name__ == "__main__":
    CD_test_path = get_drag_path("KevinL2_Rough_Camo.CSV")
    getCDFiles(CD_test_path)