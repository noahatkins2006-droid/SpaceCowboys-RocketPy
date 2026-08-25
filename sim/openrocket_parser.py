"""
OpenRocket to RocketPy Parser

Parses .ork files (ZIP archives containing XML) and extracts rocket geometry,
mass properties, motor data, and parachute configurations for use with RocketPy.

Ported from the original rocketpySim/conversion/openrocket_to_rocketpy.py
with cleanup and removal of unused file_path dependencies.
"""

from bs4 import BeautifulSoup
import zipfile
import re
import os


# Module-level state
bs = None
ork_path = None
positiondict = {}
data_labels = None
datapoints = None
global_motor_config = 0


def set_openrocket_file(filepath: str, motor_config: int = 0):
    """
    Load an OpenRocket .ork file and parse its contents.
    
    Args:
        filepath: Full path to the .ork file
        motor_config: Index of the motor configuration to use (default 0)
    """
    global ork_path, bs, global_motor_config

    ork_path = filepath
    if not os.path.exists(ork_path):
        raise FileNotFoundError(f"OpenRocket file not found: {ork_path}")

    with zipfile.ZipFile(ork_path, 'r') as zf:
        rocket_content = zf.read('rocket.ork')
    
    bs = BeautifulSoup(rocket_content, features="xml")
    _set_up_position_dictionary()
    global_motor_config = motor_config
    _set_motor_config(motor_config)


def _set_motor_config(motor_index: int):
    """Configure which motor/simulation to use from the .ork file."""
    global data_labels, datapoints

    if bs.find_all('datapoint')[0] is None:
        raise RuntimeError(
            "No simulation data points found. "
            "Run a simulation in OpenRocket and save with all simulation data."
        )

    data_labels = bs.find("databranch").attrs["types"].split(",")
    try:
        datapoints = bs.find_all("simulation")[motor_index].find_all("datapoint")
    except IndexError:
        raise FileExistsError(
            "Please save your rocket with simulation data or pick a valid motor config."
        )
    return bs.find_all('motor')[motor_index]


def _set_up_position_dictionary():
    """Build position lookup dictionary from rocket body components."""
    global positiondict
    positiondict = {}
    position = 0
    for i in bs.nosecone.parent.children:
        if i.name is not None:
            positiondict[i.find('name').string] = position
            position += float(i.length.string)


def _advanced_part_search(search_string: str):
    """
    Search for parts in the rocket XML using dot-notation path syntax.
    Supports indexed searches (part:index) and list retrieval (part.getlist).
    """
    if len(bs.find_all(search_string.split('.')[-1].split(':')[0])) != 0:
        try:
            for i in search_string.split('.'):
                j = i.split(':')
                if i == search_string.split('.')[0]:
                    if len(j) != 1:
                        if j[1] == "regex":
                            tagSearch = bs.find_all(re.compile(j[0]))[int(j[2])]
                        else:
                            tagSearch = bs.find_all(j[0])[int(j[1])]
                    else:
                        tagSearch = bs.find_all(j[0])[0]
                else:
                    if len(j) != 1:
                        if j[1] == "regex":
                            tagSearch = tagSearch.find_all(re.compile(j[0]))[int(j[2])]
                        else:
                            tagSearch = tagSearch.find_all(j[0])[int(j[1])]
                    else:
                        tagSearch = tagSearch.find_all(j[0])[0]
            return tagSearch
        except Exception:
            return -1
    elif ((len(bs.find_all(search_string.split('.')[-2].split(':')[0])) != 0) and
          (search_string.split('.')[-1].split(':')[0] == "getlist")):
        try:
            index = 0
            for i in search_string.split('.'):
                j = i.split(':')
                if i == search_string.split('.')[0]:
                    if search_string.split('.')[index + 1] != "getlist":
                        if len(j) != 1:
                            if j[1] == "regex":
                                tagSearch = bs.find_all(re.compile(j[0]))[int(j[2])]
                            else:
                                tagSearch = bs.find_all(j[0])[int(j[1])]
                        else:
                            tagSearch = bs.find_all(j[0])[0]
                    else:
                        if len(j) != 1:
                            if j[1] == "regex":
                                tagSearch = bs.find_all(re.compile(j[0]))
                        else:
                            tagSearch = bs.find_all(j[0])
                        return tagSearch
                else:
                    if search_string.split('.')[index + 1] != "getlist":
                        if len(j) != 1:
                            if j[1] == "regex":
                                tagSearch = tagSearch.find_all(re.compile(j[0]))[int(j[2])]
                            else:
                                tagSearch = tagSearch.find_all(j[0])[int(j[1])]
                        else:
                            tagSearch = tagSearch.find_all(j[0])[0]
                    else:
                        if len(j) != 1:
                            if j[1] == "regex":
                                tagSearch = tagSearch.find_all(re.compile(j[0]))
                        else:
                            tagSearch = tagSearch.find_all(j[0])
                        return tagSearch
                index += 1
            return tagSearch
        except Exception:
            return -1
    else:
        return -1


def _get_position(part):
    """
    Calculate the absolute position (meters from nose tip) of a rocket part.
    Handles absolute, top, middle, and bottom position types.
    """
    if part.name != "motor":
        if part.position['type'] == 'absolute':
            return float(part.position.string)

    # Find the parent body component
    for i in bs.nosecone.parent.children:
        if i.name is not None and part in i.descendants:
            partParent = i
            break

    if part.parent.parent.find('name').string in positiondict:
        if part.name == 'trapezoidfinset':
            length = float(part.rootchord.string)
        elif part.name == 'freeformfinset':
            length = float(part.finpoints.find_all('point')[-1]['x'])
        else:
            try:
                length = float(part.length.string)
            except (AttributeError, TypeError):
                length = 0

        result = float(positiondict[partParent.find('name').string])

        if part.name == "motor":
            parentPos = float(positiondict[partParent.find('name').string])
            result = parentPos + float(part.parent.parent.length.string) + float(part.parent.overhang.string)
            return result
        else:
            if part.position['type'] == 'bottom':
                try:
                    result = float(positiondict[partParent.next_sibling.next_sibling.find('name').string]) - length + float(part.position.string)
                except (AttributeError, TypeError):
                    result = float(positiondict[partParent.find('name').string]) + float(partParent.length.string) - length + float(part.position.string)
            if part.position['type'] == 'middle':
                try:
                    result = (float(positiondict[partParent.next_sibling.next_sibling.find('name').string]) + float(positiondict[partParent.find('name').string])) / 2 - length
                except (AttributeError, TypeError):
                    result = (float(positiondict[partParent.next_sibling.next_sibling.find('name').string]) + float(partParent.length.string)) / 2 - length
            if part.position['type'] == 'top':
                result = float(positiondict[partParent.find('name').string]) + length
            return result
    else:
        if part.name == "motor":
            parentPos = _get_position(part.parent.parent)
            result = parentPos + float(part.parent.parent.length.string) + float(part.parent.overhang.string)
            return result
        else:
            parentPos = _get_position(part.parent.parent)
            result = parentPos
            if part.name == 'trapezoidfinset':
                length = float(part.rootchord.string)
            elif part.name == 'freeformfinset':
                length = float(part.finpoints.find_all('point')[-1]['x'])
            else:
                try:
                    length = float(part.length.string)
                except (AttributeError, TypeError):
                    length = float(part.find_all(re.compile("length"))[0].string)

            if part.position['type'] == 'bottom':
                result += float(part.parent.parent.length.string) - length + float(part.position.string)
            if part.position['type'] == 'middle':
                result += float(part.parent.parent.length.string) * 0.5 - float(part.position.string)
            if part.position['type'] == 'top':
                result += float(part.position.string)
            return result


# ==============================================================================
# Public API - Getters
# ==============================================================================

def get_nosecone(value: str, index: int = 0, name: str = None):
    """Get nosecone properties: 'length', 'position'."""
    nosecones = bs.find_all('nosecone')
    if not nosecones:
        raise ValueError('No <nosecone> elements found')

    nc = None
    if name is not None:
        for n in nosecones:
            nm = n.find('name')
            if nm and nm.string and nm.string.strip() == name:
                nc = n
                break
        if nc is None:
            raise ValueError(f'No nosecone with name "{name}" found')
    else:
        nc = nosecones[index]

    match value:
        case 'length':
            return float(nc.length.string) if nc.find('length') and nc.length.string else None
        case 'position':
            return float(positiondict[nc.find('name').string])
        case _:
            raise ValueError(f'Invalid nosecone attribute: {value}')


def get_boattail(value: str, index: int = 0, name: str = "Boattail"):
    """Get boattail/transition properties: 'length', 'top_radius', 'bottom_radius', 'position'."""
    boattails = bs.find_all('transition')
    if not boattails:
        raise ValueError('No <transition> (boattail) elements found')

    bt = None
    if name is not None:
        for n in boattails:
            nm = n.find('name')
            if nm and nm.string and nm.string.strip() == name:
                bt = n
                break
    if bt is None:
        bt = boattails[index]

    match value:
        case "length":
            return float(bt.length.string) if bt.find('length') and bt.length.string else None
        case "top_radius":
            return float((bt.foreradius.string).split()[-1]) if bt.find('foreradius') and bt.foreradius.string else None
        case "bottom_radius":
            return float(bt.aftradius.string) if bt.find('aftradius') and bt.aftradius.string else None
        case "position":
            return float(positiondict[bt.find('name').string])
        case _:
            raise ValueError(f'Invalid boattail attribute: {value}')


def get_finset(value: str, index: int = 0):
    """Get trapezoidal finset properties: 'n', 'root_chord', 'tip_chord', 'span', 'sweep_length', 'position'."""
    finset = bs.find_all('trapezoidfinset')
    if not finset:
        raise ValueError('No finset elements found')
    fs = finset[index]

    match value:
        case "n":
            return int(fs.instancecount.string) if fs.find('instancecount') and fs.instancecount.string else None
        case "root_chord":
            return float(fs.rootchord.string) if fs.find('rootchord') and fs.rootchord.string else None
        case "tip_chord":
            return float(fs.tipchord.string) if fs.find('tipchord') and fs.tipchord.string else None
        case "span":
            return float(fs.height.string) if fs.find('height') and fs.height.string else None
        case "sweep_length":
            return float(fs.sweeplength.string) if fs.find('sweeplength') and fs.sweeplength.string else None
        case "position":
            return _get_position(fs)
        case _:
            raise ValueError(f'Invalid finset attribute: {value}')


def get_freeform_finset(value: str, index: int = 0):
    """Get freeform finset properties: 'n', 'shape_points', 'position'."""
    fffs = _advanced_part_search("freeformfinset.getlist")[index]

    match value:
        case "n":
            return int(fffs.instancecount.string) if fffs.find('instancecount') and fffs.instancecount.string else None
        case "shape_points":
            if fffs.finpoints:
                return [(float(p['x']), float(p['y'])) for p in fffs.finpoints.find_all('point')]
            return None
        case "position":
            return _get_position(fffs) + float(fffs.finpoints.find_all('point')[-1]['x'])
        case _:
            raise ValueError(f'Invalid freeform finset attribute: {value}')


def get_railbutton(value: str, index: int = 0):
    """Get rail button properties: 'angular_position', 'position'."""
    railbuttons = _advanced_part_search("railbuttons.getlist")
    if not railbuttons:
        raise ValueError('No <railbutton> elements found')
    rb = railbuttons[index]

    match value:
        case 'angular_position':
            return float(rb.angleoffset.string) if rb.find('angleoffset') and rb.angleoffset.string else None
        case 'position':
            return _get_position(rb)
        case _:
            raise ValueError(f'Invalid railbutton attribute: {value}')


def get_rocket(value: str):
    """Get rocket properties: 'mass', 'radius', 'cg', 'cg_without_motor', 'inertia'."""
    match value:
        case "radius":
            bt = bs.find('bodytube')
            if bt and bt.find('radius') and bt.find('radius').string:
                return float(bt.find('radius').string.split(" ")[-1])
            return None
        case "mass":
            return float(datapoints[0].string.split(",")[data_labels.index("Mass")])
        case "cg":
            return float(datapoints[0].string.split(",")[data_labels.index("CG location")])
        case "cg_without_motor":
            total_mass = get_rocket('mass')
            total_cg = get_rocket('cg')
            motor_mass = get_motor("full_mass")
            motor_pos = get_motor("position") - float(get_motor("part").length.string) * 0.5
            return (total_cg * total_mass - motor_pos * motor_mass) / (total_mass - motor_mass)
        case "inertia":
            I_total = float(datapoints[0].string.split(",")[data_labels.index("Longitudinal moment of inertia")])
            m_total = get_rocket('mass')
            cg_total = get_rocket('cg')
            m_motor = get_motor('full_mass')
            L_motor = get_motor('length')
            cg_motor = _get_position(get_motor('part')) - (L_motor / 2)
            m_dry = m_total - m_motor
            cg_dry = get_rocket('cg_without_motor')
            I_motor_cm = (1 / 12) * m_motor * (L_motor ** 2)
            d_motor = cg_motor - cg_total
            d_dry = cg_dry - cg_total
            long_inertia_dry = I_total - (I_motor_cm + m_motor * (d_motor ** 2)) - (m_dry * (d_dry ** 2))
            rot_inertia = float(datapoints[0].string.split(",")[data_labels.index("Rotational moment of inertia")])
            return (long_inertia_dry, long_inertia_dry, rot_inertia)
        case _:
            raise ValueError(f'Invalid rocket attribute: {value}')


def get_motor(value: str):
    """Get motor properties: 'dry_mass', 'full_mass', 'propellant_mass', 'position', 'diameter', 'length', 'part'."""
    mt = _set_motor_config(global_motor_config)
    motor_mass = [
        float(dp.string.split(",")[data_labels.index("Motor mass")])
        for dp in datapoints
    ]

    match value:
        case "diameter":
            return float(mt.find('diameter').string) if mt.find('diameter') and mt.find('diameter').string else None
        case "length":
            return float(mt.find('length').string) if mt.find('length') and mt.find('length').string else None
        case "dry_mass":
            return min(motor_mass)
        case "full_mass":
            return max(motor_mass)
        case "propellant_mass":
            return max(motor_mass) - min(motor_mass)
        case "position":
            return _get_position(mt)
        case "part":
            return mt
        case _:
            raise ValueError(f'Invalid motor attribute: {value}')


def get_parachute(value: str, index: int = 0):
    """Get parachute properties: 'name', 'cd', 'diameter', 'deployment', 'delay'."""
    pc = _advanced_part_search("parachute.getlist")[index]

    match value:
        case 'name':
            return pc.find('name').string if pc.find('name') else None
        case 'cd':
            return 0.8 if pc.cd.string == 'auto' else float(pc.cd.string)
        case 'diameter':
            return float(pc.diameter.string) if pc.diameter else None
        case "deployment":
            if pc.deployevent.string == 'apogee':
                return 'apogee'
            if pc.deployevent.string == 'altitude':
                return float(pc.deployaltitude.string)
            if pc.deployevent.string == 'ejection':
                return 'apogee'
        case "delay":
            return float(pc.deploydelay.string) if pc.deploydelay else None
        case _:
            raise ValueError(f'Invalid parachute attribute: {value}')
