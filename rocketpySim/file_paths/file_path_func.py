import os
from pathlib import Path

def get_motor_path(filename : str):
    # Go up two levels, then into data/engine_files/
    path = (Path(__file__).resolve().parent.parent.parent / "data" / "engine_files" / filename).resolve()

    print(f"Found Path: {path} (exists={path.exists()})")

    return str(path)

def get_drag_path(filename : str):

    path = (Path(__file__).resolve().parent.parent.parent / "data" / "cd_data" / filename).resolve()

    print(f"Found Path: {path} (exists={path.exists()})")
    
    return str(path)

def get_ork_path(filename : str):

    path = (Path(__file__).resolve().parent.parent.parent / "data" / "open_rocket" / filename).resolve()

    print(f"Found Path: {path} (exists={path.exists()})")
    
    return str(path)

def get_fin_path(filename : str):
    # Go up two levels, then into data/engine_files/
    path = (Path(__file__).resolve().parent.parent.parent / "data" / "fin_data" / filename).resolve()

    print(f"Found Path: {path} (exists={path.exists()})")

    return str(path)