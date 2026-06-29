# Usage guide for the advanced tag search

## advanced_part_search function
The function advanced_part_search() takes a single string as an argument
if it succeeds it returns the tag
if it fails to find the pert it returns -1

A rocket part is a xml tag so this search function also functions as a tag search algorithm.
this is useful if you dont just want to get a part but a specific attribute (length, position, mass, etc..) of a part as it is also a tag

# simple part search

The syntax for a string argument for a simple advanced_part_search():
1. For a part
- "PartType"
 returns the entire tag and its children of a part
 example: "nosecone"

2. For an attribute
- "PartAttribute"
 returns a attribute (and children if applicable)
 example: "length"

# multiple parts

Now some attributes/subparts may exist in multiple parts. for example, nosecone and bodytube both have a length attribute
To specify which part to search for an attribute use this syntax:
1. For a subpart
- "PartType.SubPartType"
 returns the entire tag and its children of a subpart 
 example: "bodytube.railbutton"

2. For an attribute
- "PartType.AttributeName"
 returns the attribute tag (and children if applicable)
 example: "nosecone.name"

Some parts have multiple of the same type within the rocket. for example, there are multiple bodytubes.
Usually the duplicate parts are indexed in order of increasing distance from the nosecone tip
To specify between two different parts of the same rocket append :(index) after the part name to pick a specific index of the part.
NOTE: the index for duplicate parts starts at 0 so the first part would be acessed by adding :0
If :(index) is not added then the tag search defaults to searching the first instance of that part type
1. For a subpart
- "PartType:(index).subcomponents.SubPartType"
 returns the entire tag and its children of a subpart 
 example: "bodytube:0.railbutton" 

2. For an attribute
- "PartType:(index).AttributeName"
 returns the attribute tag (and children if applicable)
 example: "bodytube:1.length"

# getting a list
Sometime you might want to get a list of all the child components, or components with the same name or type.
you can get the funtion to return a list of the names by adding ".getlist" to the end.
for example to get all the bodytubes on a rocket as a list you can pass in:

- "bodytube.getlist"

or if you want to get a all the masscomponents from body the second body tube:

- "bodytube:1.masscomponents.getlist"

if you want all masscomponents even if they are in different body tubes then simply:

- "masscomponents.getlist"
# tag based files and examples
If you are familiar with how tag based files work (xml, html, etc) then the syntax can be simplified to the following:
-"ParentTag:(index).ChildTag"
Child tags can also have indexes and children of child tags can be accessed:
- "ParentTag:(index).ChildTag:(index).ChildTag"

Although most of the time unnessecary, a tag can be very specifically referenced by starting at the top of the xml tree and working down to the tag you want to find
to find the materical of a parachute on the first body tube you can input the following:

- "openrocket.rocket.subcomponents.stage.subcomponents.bodytube:0.subcomponents.parachute.material"

but this shorter string will achieve the same result:

- "bodytube:0parachute.material"

and so will this string if the parachutes are only on the first body tube:

- "parachute:0.material"

its best to use the shorter inputs as it is less likely to fail in its search if a parent tag is misspelled or doesnt exist.

# regex support
If you wish to use regex to search for parts you can format your input like:
- "(expression):regex:(index)"
Or:
- "(expression):regex.getlist"

NOTE: if using regex YOU MUST EITHER SPECIFY AN INDEX OR USE .getlist
examples:

- "length:regex:0"
 returns the first instance of length found by a regex

- "length:regex.getlist"
 returns all attributes/tags that have "length" in their name (length, packedlength, etc)

- "bodytube:2.length:regex.getlist"
 returns all attributes/tags that have "length" in their name in the 3rd body tube

- "^b:length.getlist"
 returns all attributes/tags whose names start with the leter 'b'

# beautiful soup 

these functions return instances of beautiful soups tag class/object. Look at beautiful soup's documentation for what operations you can do with these tags.

## Opening up a rocket file to see the xml tree
open rockets .ork file is just a .zip file in disguise
1. rename the rocket file to change the extention to .zip
2. unzip the file
3. a folder should appear with a file called "rocket.ork"
4. open the file in a text editor to see the xml tree.
