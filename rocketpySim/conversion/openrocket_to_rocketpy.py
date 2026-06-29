import sys
import os
from bs4 import BeautifulSoup
import zipfile
import re


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from file_paths.file_path_func import get_ork_path

def set_openrocket_file(filepath,motor_config=0, fullpath = False):
    global ork_path
    if fullpath:
        ork_path = filepath
    else:
        ork_path = get_ork_path(filepath)
    print(os.path.exists(ork_path))

    with zipfile.ZipFile(ork_path, 'r') as zf:
        rocket_content = zf.read('rocket.ork')
    global bs
    bs = BeautifulSoup(rocket_content, features="xml")
    set_up_position_dictionary()
    global global_motor_config
    global_motor_config = motor_config
    set_motor_config(motor_config)

def set_motor_config(motor_index):
    if bs.find_all('datapoint')[0] == None:
        raise RuntimeError("no simulation data points found. Try running a simulation in open rocket and saving the file with all simulation data.")

    global data_labels
    data_labels = bs.find("databranch").attrs["types"].split(",")
    global datapoints
    try:
        datapoints = bs.find_all("simulation")[motor_index].find_all("datapoint")
    except IndexError:
        raise FileExistsError("PLEASE SAVE YOUR ROCKET WITH SIMULATION DATA OR PICK A VALID MOTOR CONFIG")
    motor = bs.find_all('motor')[motor_index]
    return(motor)

def advanced_part_search(search_string):
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
            except:
                print(f"Rocket attribute '{search_string}' not found.\nCheck if the index of the part exists\nif applicable check if the subpart youre searching for exists on the parent part")
                return -1
        elif ((len(bs.find_all(search_string.split('.')[-2].split(':')[0])) != 0) and (search_string.split('.')[-1].split(':')[0] == "getlist")):
            try:
                index = 0
                for i in search_string.split('.'):
                    
                    j = i.split(':')
                    if i == search_string.split('.')[0]:
                        if search_string.split('.')[index+1] != "getlist" :
                            if len(j) != 1:
                                if j[1] == "regex":
                                    tagSearch = bs.find_all(re.compile(j[0]))[int(j[2])]
                                else:
                                    tagSearch = bs.find_all(j[0])[int(j[1])]
                            else:
                                tagSearch = bs.find_all(j[0])[0]
                        else:
                            if (len(j) != 1):
                                if j[1] == "regex":
                                    tagSearch = bs.find_all(re.compile(j[0]))
                            else:
                                tagSearch = bs.find_all(j[0])
                            return tagSearch
                    else:
                        if search_string.split('.')[index+1] != "getlist" :
                            if len(j) != 1:
                                if j[1] == "regex":
                                    tagSearch = tagSearch.find_all(re.compile(j[0]))[int(j[2])]
                                else:
                                    tagSearch = tagSearch.find_all(j[0])[int(j[1])]
                            else:
                                tagSearch = tagSearch.find_all(j[0])[0]
                        else:
                            if (len(j) != 1):
                                if j[1] == "regex":
                                    tagSearch = tagSearch.find_all(re.compile(j[0]))
                            else:
                                tagSearch = tagSearch.find_all(j[0])
                            return tagSearch

                    index +=1

                return tagSearch
            except:
                print(f"Rocket attribute '{search_string}' not found.\nCheck if the index of the part exists\nif applicable check if the subpart youre searching for exists on the parent part")
                return -1
        else:
            print(f"Rocket attribute '{search_string}' not found")
            return -1

positiondict = {}

def set_up_position_dictionary():
    position = 0
    for i in bs.nosecone.parent.children:
        if i.name != None:
            positiondict[i.find('name').string] = position
            position+=float(i.length.string)

def get_mass(part):
    massList = part.find_all('overridemass')
    massList = massList + part.find_all('mass')
    overrideComponentsList = part.find_all('overridesubcomponentsmass')
    for j in overrideComponentsList:
        for k in j.descendants:
            try:
                massList.remove(k)
            except:
                pass
    massSum = 0
    for i in massList:
        massSum += float(i.string)
    return(massSum)


def get_position(part):
    
    """Get a position in meters for a part. Its incredibly inefficient but it works.

    Args:
        part: the part that the position needs to be found
        index: integer index when multiple of the same part exist (default 0 for the first instance)


    Returns:
        The requested value (float for position) or None if not found.
    """
    if part.name != "motor":
        if part.position['type'] =='absolute':
            return(float(part.position.string))
    for i in bs.nosecone.parent.children:
        if i.name != None and part in i.descendants:
            partParent = i
            break
    
    if part.parent.parent.find('name').string in positiondict:
        if part.name == 'trapezoidfinset':
            length = float(part.rootchord.string)
        else:
            try:
                length = float(part.length.string)
            except:
                length = 0
        if part.name == 'freeformfinset':
            length = float(part.finpoints.find_all('point')[-1]['x'])
        else:
            try:
                length = float(part.length.string)
            except:
                length = 0
        result = float(positiondict[partParent.find('name').string])
        if part.name == "motor":
            parentPos = float(positiondict[partParent.find('name').string])
            result = parentPos+float(part.parent.parent.length.string)+float(part.parent.overhang.string)
            return result
        else:
            if part.position['type'] =='bottom':
                try:
                    result = float(positiondict[partParent.next_sibling.next_sibling.find('name').string]) - length + float(part.position.string)
                except:
                    result = float(positiondict[partParent.find('name').string]) + float(partParent.length.string) - length + float(part.position.string)
            if part.position['type'] =='middle':
                try:
                    result = (float(positiondict[partParent.next_sibling.next_sibling.find('name').string]) +float(positiondict[partParent.find('name').string]))/2 - length
                except:
                    result = (float(positiondict[partParent.next_sibling.next_sibling.find('name').string]) +float(partParent.length.string))/2 - length
            if part.position['type'] =='top':
                result = float(positiondict[partParent.find('name').string]) + length
            return result
    else:
        if part.name == "motor":
            parentPos = get_position(part.parent.parent)
            result = parentPos+float(part.parent.parent.length.string)+float(part.parent.overhang.string)
            return result

        else:
            parentPos = get_position(part.parent.parent)
            result = parentPos
            if part.name == 'trapezoidfinset':
                length = float(part.rootchord.string)
            else:
                try:
                    length = float(part.length.string)
                except:
                    print("regex used for", part.name,float(part.find_all(re.compile("length"))[0].string) )
                    length = float(part.find_all(re.compile("length"))[0].string)
            if part.position['type'] =='bottom':
                result += float(part.parent.parent.length.string) - length + float(part.position.string)
            if part.position['type'] =='middle':
                result += float(part.parent.parent.length.string)*0.5 - float(part.position.string)
            if part.position['type'] =='top':
                result += float(part.position.string)
            return result
            

def get_cg(part,midMotor,motorMass):
    massList = part.find_all('overridemass')
    overrideComponentsList = part.find_all('overridesubcomponentsmass')
    for j in overrideComponentsList:
        for k in j.descendants:
            try:
                massList.remove(k)
            except:
                pass
    massSum = 0
    for i in massList:
        if i.parent.find('length') and i.parent.length.string:
            massSum += (float(i.string)*(get_position(part) + float(i.parent.length.string)*0.5))
        elif i.parent.find('packedlength') and i.parent.packedlength.string:
            massSum += (float(i.string)*(get_position(part) + float(i.parent.packedlength.string)*0.5))
        elif i.parent.find('rootchord') and i.parent.rootchord.string:
            massSum += (float(i.string)*(get_position(part) + float(i.parent.rootchord.string)*0.5))
        else:
            massSum += (float(i.string)*(get_position(part)))
            print(f"{i.parent.find('name').string} has mass but no length")
    return((massSum + midMotor*motorMass)/(get_mass(part)+motorMass))

def get_nosecone(value, index=0, name=None):
    """Get a value from a nosecone.

    Args:
        value: one of 'length', 'position'
        index: integer index when multiple nosecones exist (default 0)
        name: optional exact <name> text to search for a specific nosecone

    Returns:
        The requested value (float for length) or None if not found.
    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

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
        try:
            nc = nosecones[index]
        except IndexError:
            raise IndexError(f'No nosecone at index {index}')

    match value:
        case 'length':
            if nc.find('length') and nc.length.string:
                return float(nc.length.string)
            return None
        case 'position':
            return float(positiondict[nc.find('name').string])
        case _:
            raise ValueError('improper attribute')

def get_boattail(value,index=0,name="Boattail"):
    """Get a value from a boattail or transition element.
    
    Args:
        value: one of 'length', 'top_radius', 'bottom_radius', or 'position'
        index: integer index if multiple boatails/transition elements (default 0)
        name: string containing the name of the transition in open rocket. (default "Boattail")
        ###NOTE name input is only needed if the boat tail has a different name than "Boattail" 
        # or if you are trying to find values from a transition element that is not a boat tail. 
        # If the name doesnt match with the name of the boattail 
        # then it may read values from a different transition element
    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

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
            try:
                bt = boattails[index]
            except IndexError:
                raise IndexError(f'No boattail/transition found at index {index}')
    else:
        try:
            bt = boattails[index]
        except IndexError:
            raise IndexError(f'No boattail/transition found at index {index}')

    match value:
        case "length":
            if bt.find('length') and bt.length.string:
                return float(bt.length.string)
            return None
        case "top_radius":
            if bt.find('foreradius') and bt.foreradius.string:
                return float((bt.foreradius.string).split()[-1])
            return None
        case "bottom_radius":
            if bt.find('aftradius') and bt.aftradius.string:
                return float(bt.aftradius.string)
            return None
        case "position":
            return float(positiondict[bt.find('name').string])
        case _:
            raise ValueError('improper attribute')

def get_finset(value, index=0):
    """Get a value from the fin set.
    
    Args:
        value: one of 'n', 'root_chord', 'tip_chord', 'span' ,'position'
    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

    finset = bs.find_all('trapezoidfinset')
    if not finset:
        raise ValueError('No finset elements found')

    try:
        fs = finset[index]
    except IndexError:
        raise IndexError(f'No fins found at index {index}')

    match value:
        case "n":
            if fs.find('instancecount') and fs.instancecount.string:
                return int(fs.instancecount.string)
            return None
        case "root_chord":
            if fs.find('rootchord') and fs.rootchord.string:
                return float(fs.rootchord.string)
            return None
        case "tip_chord":
            if fs.find('tipchord') and fs.tipchord.string:
                return float(fs.tipchord.string)
            return None
        case "span":
            if fs.find('height') and fs.height.string:
                return (float(fs.height.string))
            return None
        case "sweep_length":
            if fs.find('sweeplength') and fs.sweeplength.string:
                return float(fs.sweeplength.string)
            return None
        case "position":
            return get_position(fs)
        case _:
            raise ValueError('improper attribute')

def get_railbutton(value, index=0, name=None):
    """Get values from rail buttons.

    Args:
        value: one of 'angular_position', 'position'
        index: integer index when multiple railbuttons with the same name exist (default 0)
        name: required for position if multiple air buttons with different names exist (e.g. 'Airfoiled Rail Button')

    Returns:
        The requested value (float for position) or None if not found.
    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

    railbuttons = advanced_part_search("railbuttons.getlist")
    if not railbuttons:
        raise ValueError('No <railbutton> elements found')
    
    # rbWithName = []

    # rb = None
    # if name is not None:
    #     for n in railbuttons:
    #         nm = n.find('name')
    #         if nm and nm.string and nm.string.strip() == name:
    #             rb = n
    #             rbWithName.append(n)
            
    #     if rb is None:
    #         raise ValueError(f'No railbutton with name "{name}" found')
    # else:
    #     try:
    #         rb = railbuttons[index]
    #         nm = rb.find('name').string
    #     except IndexError:
    #         raise IndexError(f'No railbutton at index {index}')
    
    rb = railbuttons[index]

    match value:
        case 'angular_position':
            if rb.find('angleoffset') and rb.angleoffset.string:
                return float(rb.angleoffset.string)
            return None
        case 'position':
            return get_position(rb)
        case _:
            raise ValueError('improper attribute')

def get_rocket(value):
    """Get a value from the rocket.
    
    Args:
        value: one of 'mass', 'radius', 'cg', "cg_without_motor", "inertia"


    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

    rk = bs.find('rocket')

    


    match value:
        case "radius":
            if bs.find('bodytube').find('radius') and bs.find('bodytube').find('radius').string:
                return float(bs.find('bodytube').find('radius').string.split(" ")[-1])
            return None
        case "mass":
                if datapoints[0] != None:
                    return(float(datapoints[0].string.split(",")[data_labels.index("Mass")]))
                #return get_mass(rk)
        case "cg":
                if datapoints[0] != None:
                    return(float(datapoints[0].string.split(",")[data_labels.index("CG location")]))
                #return get_cg(rk,midMotor,motorMass)
        case "cg_without_motor":
                if datapoints[0] != None:
                    return(((float(datapoints[0].string.split(",")[data_labels.index("CG location")])*get_rocket('mass'))-(get_motor("position") - float(get_motor("part").length.string)*0.5)*(get_motor("full_mass")))/(get_rocket('mass')-get_motor("full_mass")))
                #return get_cg(rk,midMotor,motorMass)
        case "inertia":
                if datapoints[0] != None:
                    I_total = float(datapoints[0].string.split(",")[data_labels.index("Longitudinal moment of inertia")])
                    m_total = get_rocket('mass')
                    cg_total = get_rocket('cg')

                    m_motor = get_motor('full_mass')
                    L_motor = get_motor('length')

                    # NOTE: OpenRocket usually defines 'position' as the forward-most tip of the component.
                    # Assuming this, the motor's CG is half its length down from its position.
                    cg_motor = get_position(get_motor('part')) - (L_motor / 2) 

                    m_dry = m_total - m_motor
                    cg_dry = get_rocket('cg_without_motor')

                    # 2. Calculate the Motor's inertia about its own Center of Mass
                    I_motor_cm = (1/12) * m_motor * (L_motor ** 2)

                    # 3. Calculate distances from the fully loaded rocket CG
                    d_motor = cg_motor - cg_total
                    d_dry = cg_dry - cg_total

                    # 4. Apply the Parallel Axis Theorem
                    long_inertia_dry = I_total - (I_motor_cm + m_motor * (d_motor ** 2)) - (m_dry * (d_dry ** 2))
                    return((long_inertia_dry,long_inertia_dry,float(datapoints[0].string.split(",")[data_labels.index("Rotational moment of inertia")])))
                return(None)
        case _:
            raise ValueError('improper attribute')

def get_motor(value):
    """Get a value from the motor.
    
    Args:
        value: one of 'dry_mass', 'full_mass', 'propellant_mass' 'position', 'diameter', 'length' 
        motor_config: the index of each motor the rocket has (0 for O5500X-PS, 1 for M1340W)



    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

    mt = set_motor_config(global_motor_config)

    motor_mass = [float(datapoint.string.split(",")[data_labels.index("Motor mass")]) for datapoint in datapoints]


    match value:
        case "diameter":
            if bs.find('motor').find('diameter') and bs.find('motor').find('diameter').string:
                return float(mt.find('diameter').string)
            return None
        case "length":
            if bs.find('motor').find('length') and bs.find('motor').find('length').string:
                return float(mt.find('length').string)
            return None
        case "dry_mass":
                return min(motor_mass)
        case "full_mass":
                return max(motor_mass)
        case "propellant_mass":
                return (max(motor_mass)-min(motor_mass))
        case "position":
                return get_position(mt)
        case "part":
                return mt
        case _:
            raise ValueError('improper attribute')
        
def get_parachute(value, index = 0):
    """Get a value from the parachutes.
    
    Args:
        value: one of 'name', 'cd', 'diameter', 'deployment', 'delay',


    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

    pc = advanced_part_search("parachute.getlist")[index]

    


    match value:
        case 'name':
            if pc.find('name'):
                return pc.find('name').string
            return None
        case 'cd':
                if pc.cd.string == 'auto':
                    return(0.8)
                else:
                    return(float(pc.cd.string))
        case 'diameter':
                if pc.diameter:
                    return(float(pc.diameter.string))
                return None
        case "deployment":
                if pc.deployevent.string == 'apogee':
                    return('apogee')
                if pc.deployevent.string == 'altitude':
                    return(float(pc.deployaltitude.string))
                if pc.deployevent.string == 'ejection':
                    return('apogee') #TODO figure ts out.
        case "delay":
                if pc.deploydelay:
                    return(float(pc.deploydelay.string))
        case _:
            raise ValueError('improper attribute')
        
def get_freeform_finset(value, index=0):
    """Get a value from the freeform fin set.
    
    Args:
        value: one of 'n', 'shape_points','position'
    """
    if not bs:
        raise RuntimeError('OpenRocket file not loaded; call set_openrocket_file() first')

    fffs = advanced_part_search("freeformfinset.getlist")[index]

    match value:
        case "n":
            if fffs.find('instancecount') and fffs.instancecount.string:
                return int(fffs.instancecount.string)
            return None
        case "shape_points":
            if fffs.finpoints:
                shape_points = []
                for point in fffs.finpoints.find_all('point'):
                    shape_points.append((float(point['x']),float(point['y'])))
                return shape_points
            return None
        case "position":
            return get_position(fffs)+ float(fffs.finpoints.find_all('point')[-1]['x'])
        case _:
            raise ValueError('improper attribute')
        

    
if __name__ == "__main__":
    set_openrocket_file("KevinL2.ork",0)
    # print(get_railbutton('position',index=0))
    # print(get_railbutton('angular_position',index=0))
    # print(get_railbutton('position',index=1))
    # print(get_railbutton('angular_position',index=1)) #TODO handle the case of 1 railbutton with multiple instances
    # print(get_finset('n'))
    # print(get_finset('root_chord'))
    # print(get_finset('tip_chord'))
    # print(get_finset('span'))
    # print(get_finset('position'))
    # print(get_finset('sweep_length'))
    print(get_nosecone('length'))
    print(get_nosecone('position'))
    # print(get_boattail('length'))
    # print(get_boattail('top_radius'))
    # print(get_boattail('bottom_radius'))
    # print(get_boattail('position'))
    print(get_rocket('radius'))
    print(get_rocket('mass'))
    print(get_rocket('cg'))
    print(get_rocket("cg_without_motor"))
    print(get_rocket("mass"))
    print(get_motor('dry_mass'))
    print(get_motor('full_mass'))
    print(get_motor('propellant_mass'))
    print(get_motor('position'))
    print(get_parachute('name'))
    print(get_freeform_finset('shape_points'))
    print(get_freeform_finset('position'))
    
    
    
    


