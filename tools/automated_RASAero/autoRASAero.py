import subprocess
import sys
import os
from pathlib import Path
from bs4 import BeautifulSoup 
import pandas as pd

def getData(CDX1Path, outPutDirectory, fileName, roughness = ""):
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    # 1. Define the paths
    # Use 'r' before the string (raw string) so Windows backslashes don't cause errors
    exe_path = (Path(__file__).resolve() / ".." / "RASAeroII_CLI.exe").resolve()
    input_rocket_file = Path(CDX1Path).resolve()
    output_csv_file = (Path(outPutDirectory).resolve() / (fileName + ".CSV")).resolve()

    # 2. Build the command as a list
    # The first item is always the executable, followed by the arguments in order
    if roughness == "":
        command = [exe_path, input_rocket_file, output_csv_file]
    else:
        command = [exe_path, input_rocket_file, output_csv_file, str(roughness)]

    try:
        # 3. Run the executable
        # capture_output=True hides the console spam and lets you read it if needed
        # text=True returns the output as a normal string
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
        return output_csv_file
        
        

        
    except subprocess.CalledProcessError as e:
        # This triggers if the exe crashes or returns an error code instead of 0
        print("An error occurred while running the simulation.")
        print("Exit Code:", e.returncode)
        print("Error Output:", e.stderr)

def createModifiedRocket(rocket_file, editDictionary):
    try:
        # Validate that the source file exists
        if not os.path.isfile(rocket_file):
            raise FileNotFoundError(f"Rocket file '{rocket_file}' does not exist.")
        
        source_dir = os.path.dirname(rocket_file)
        filename = os.path.basename(rocket_file)
        name_without_ext, ext = os.path.splitext(filename)
        modified_dir = os.path.join(source_dir, f"{name_without_ext}_Modified")
        os.makedirs(modified_dir, exist_ok=True)

        dict_string = str(sorted(editDictionary.items()))
        short_hash = str(abs(hash(dict_string)))[:8]
        newfilename = f"{name_without_ext}_opt_{short_hash}"
            

        with open(rocket_file,'r') as fp:
            mr = BeautifulSoup(fp, features="xml")
        
        for key, value in sorted(editDictionary.items()):
            if len(mr.find_all(key.split('.')[-1].split(':')[0])) != 0:
                for i in key.split('.'):
                    j = i.split(':')
                    if i == key.split('.')[0]:
                        if len(j) != 1:
                            tagSearch = mr.find_all(j[0])[int(j[1])]
                        else:
                            tagSearch = mr.find_all(j[0])[0]
                    else:
                        if len(j) != 1:
                            tagSearch = tagSearch.find_all(j[0])[int(j[1])]
                        else:
                            tagSearch = tagSearch.find_all(j[0])[0]
                tagSearch.string = str(value)
            else:
                print(f"Rocket attribute '{key}' not found")

        destination_path = os.path.join(modified_dir, newfilename + f"{ext}")
        print(destination_path)
            
        with open(destination_path, "w", encoding="utf-8") as file:
            file.write(str(mr))
            file.close()
    
    except FileNotFoundError as fnf_err:
        print(f"Error: {fnf_err}")
    except PermissionError:
        print("Error: Permission denied. Check file permissions.")
    except IsADirectoryError:
        print("Error: One of the paths is a directory, not a file.")
    except UnicodeDecodeError:
        print("Note: The file is not a text file, so it can't be displayed as text.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return destination_path , newfilename

def getRocketAttribute(rocket_file, attribute):
    with open(rocket_file,'r') as fp:
            mr = BeautifulSoup(fp, features="xml")

    if len(mr.find_all(attribute.split('.')[-1].split(':')[0])) != 0:
                
        for i in attribute.split('.'):
            j = i.split(':')
            if i == attribute.split('.')[0]:
                if len(j) != 1:
                    tagSearch = mr.find_all(j[0])[int(j[1])]
                else:
                    tagSearch = mr.find_all(j[0])[0]
            else:
                if len(j) != 1:
                    tagSearch = tagSearch.find_all(j[0])[int(j[1])]
                else:
                    tagSearch = tagSearch.find_all(j[0])[0]
        return tagSearch.string
    else:
                print(f"Rocket attribute '{attribute}' not found")


def getCDFiles(dataCSV_filePath):
        
    source_dir = os.path.dirname(dataCSV_filePath)
    filename = os.path.basename(dataCSV_filePath)
    name_without_ext, ext = os.path.splitext(filename)
    modified_dir = os.path.join(source_dir, f"{name_without_ext}_DragCurves")
    os.makedirs(modified_dir, exist_ok=True)

    on_path = (Path(modified_dir).resolve() /  (name_without_ext + "_CD_On" + ext)).resolve()
    off_path = (Path(modified_dir).resolve() / (name_without_ext + "_CD_Off" + ext)).resolve()

    df_CD_On = pd.read_csv(dataCSV_filePath, usecols=["Mach","CD Power-On"])
    df_CD_On.to_csv(on_path, index=False)
    df_CD_Off = pd.read_csv(dataCSV_filePath, usecols=["Mach","CD Power-Off"])
    df_CD_Off.to_csv(off_path, index=False)

    return on_path, off_path








