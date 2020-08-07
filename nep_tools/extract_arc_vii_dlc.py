"""
Author: LilacDogoo

Currently only tested against 'Megadimention Neptunia VII' arc files. May work with other arc files.

This Script has 2 functions:
    1. 'list_dlc_as_text()' function will iterate through all of your installed
        DLCs from 'Megadimention Neptunia VII' and print detailes to Blender's 'System Console'
        This just makes it really easy to find a specific DLC with out having to manually open each descriptor file yourself.
    2. Extracts arc files.

How to use:
    1. Blender Menus -> 'NepTools > Generate VII DLC Descriptions'.
    2. Use the Text Editor within blender to open the 'DLC_descriptions.txt'.
    3. (eg) Search for 'swim' to find all the swimsuit models.
    4. In this case we can see that 'Uzume Swimsuit Set' is listed under 'DLC000000000009500000'
    5. Blender Menus -> 'NepTools > Extract Arc File' (locate 'DLC000000000009500000').
        A folder was created with the same name and location of the arc file.
    6. Blender Menus -> 'File > Import > ISM2 Importer (Neptunia)' (locate the ISM2 file within the extracted files).

REMEMBER: I did not automate this completely as of yet. You must convert 'tid's to 'png's yourself.
    After that Blender will find them and apply them to your model for you.
"""
import errno
import os
from os import walk
from typing import List

import bpy

import nep_tools
from nep_tools import file_ism2
from nep_tools.utils import binary_file

DEFAULT_VII_DLC_PATH = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megadimension Neptunia VII\\DLC\\"
DLC_DESCRIPTION_FILE_NAME = "DLC_descriptions.txt"


class BlenderOperator_ARC_Descriptor(bpy.types.Operator):
    bl_idname = "descriptor.arc"
    bl_label = "Generate VII DLC Descriptions"
    bl_description = "List off all the DLCs for VII"
    bl_options = {'UNDO'}

    # Properties used by the file browser
    directory: bpy.props.StringProperty(maxlen=1024, default=DEFAULT_VII_DLC_PATH, subtype='FILE_PATH', options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(name="Filter Folders", description="", default=True, options={'HIDDEN'})
    filter_glob: bpy.props.StringProperty(default="*.arc", options={'HIDDEN'})

    def invoke(self, context, event):
        self.directory = DEFAULT_VII_DLC_PATH
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        text = list_dlcs_as_text(self.directory)
        if text is not None:
            text_block: bpy.types.Text
            text_block = bpy.data.texts.get(DLC_DESCRIPTION_FILE_NAME)
            if text_block is None:
                text_block = bpy.data.texts.new(DLC_DESCRIPTION_FILE_NAME)
            text_block.from_string(text)
        return {'FINISHED'}


class BlenderOperator_ARC_Extractor(bpy.types.Operator):
    bl_idname = "extract.arc"
    bl_label = "Extract VII DLCs"
    bl_description = "Extracts arc files."
    bl_options = {'UNDO'}

    # Properties used by the file browser
    filepath: bpy.props.StringProperty(name="File Path", description="The 'arc' file to extract",
                                       maxlen=1024, default="", options={'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN'})
    directory: bpy.props.StringProperty(maxlen=1024, default=DEFAULT_VII_DLC_PATH, subtype='FILE_PATH', options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(name="Filter Folders", description="", default=True, options={'HIDDEN'})
    filter_glob: bpy.props.StringProperty(default="*.arc", options={'HIDDEN'})

    def invoke(self, context, event):
        self.directory = DEFAULT_VII_DLC_PATH
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        extract_arc_file(self.filepath)
        return {'FINISHED'}


class DLC_Description:
    def __init__(self, title: str, comment: str, folder: str) -> None:
        super().__init__()
        self.title, self.comment, self.folder = title, comment, folder

    def __str__(self) -> str:
        com = "    " + self.comment.replace("\n", "\n    ")
        return "%s\n%s\n%s" % (self.folder[self.folder.rindex(os.sep) + 1:], self.title, com)


def get_dlc_description(path: str) -> str:
    (_, _, files) = walk(path).__next__()
    for file in files:
        if file.startswith("main"):
            R = open(path + "\\" + file, 'rt', encoding='utf8')
            title: str
            comment: str = ""
            line: str = R.readline()
            if not line.startswith("<title:"):  # Wrong file format
                # Returns path only so we know what path the error is caused in
                return "%s   < ERROR >" % (path[path.rindex(os.sep) + 1:])
            title = R.readline()[:-1]
            line = R.readline()
            while line != "":
                if line.startswith("<comment:"):
                    line = R.readline()
                    while line != "" and line != ">\n":
                        comment = comment + "    " + line
                        line = R.readline()
                    break
                line = R.readline()
            return "%s\n%s\n%s" % (path[path.rindex(os.sep) + 1:], title, comment)


def list_dlcs_as_text(folder: str = DEFAULT_VII_DLC_PATH) -> str:
    (_, dirs, _) = walk(folder).__next__()
    descriptions = []
    for _dir in dirs:
        descriptions.append(get_dlc_description(folder + _dir))
    text = "\n".join(descriptions)
    if nep_tools.debug:
        print(text)
    return text


class ArcFileDescriptor:
    def __init__(self, path_type: int, entry_number: int, name: str, offset: int, size: int) -> None:
        super().__init__()
        self.path_type_root: bool = False
        self.path_type_folder: bool = False
        self.path_type_file: bool = False
        if path_type == 0x02000000:
            self.path_type_folder: bool = True
        elif path_type == 0x03000000:
            self.path_type_root: bool = True
            self.path_type_folder: bool = True
        elif path_type == 0x04000000:
            self.path_type_file: bool = True
        self.name: str = name
        self.path: str = ""
        self.entry_number: int = entry_number
        self.offset: int = offset
        self.size: int = size
        self.parent: ArcFileDescriptor = None

    def get_path_type_name(self) -> str:
        if self.path_type_folder:
            if self.path_type_root:
                return "root"
            return "Folder"
        if self.path_type_file:
            return "File"
        return "<Unknown>"

    def get_path_toroot(self) -> str:
        return self.name if self.parent is None else self.parent.get_path_toroot() + os.sep + self.name

    def __str__(self) -> str:
        return "%s %s -> %s" % (hex(self.offset).rjust(10), self.get_path_type_name().ljust(6), self.get_path_toroot())


"""
CREDIT: This section of code is based on a Quick BMS Script found here:  https://zenhax.com/viewtopic.php?t=2732
"""


def extract_arc_file(path: str):
    f = open(path, 'rb')
    R = binary_file.LD_BinaryReader(f, True)
    if not f.read(4) == b'ARC\x02':
        print("INCORRECT FILE FORMAT  %s" % path)
        return

    file_count = R.read_long_unsigned()  # File Count
    description_table_size = R.read_long_unsigned()  # Length of all the File Descriptions
    description_table_entry_size = int(description_table_size / file_count)  # Length of the File Descriptions
    file_name_list_size = R.read_long_unsigned()  # Full length
    offset_file_descriptions = f.tell()  # Location that File Descriptions begin
    offset_file_names = offset_file_descriptions + description_table_size  # Location that File Names begin
    offset_files = offset_file_names + file_name_list_size  # Location that File Data begins

    # Get file descriptors
    file_descriptors: List[ArcFileDescriptor] = []
    for i in range(file_count):
        R.goto(offset_file_descriptions + description_table_entry_size * i)
        a_path_type = R.read_long_unsigned()
        a_entry_number = R.read_long_unsigned()
        a_name_offset = R.read_long_unsigned() + offset_file_names
        a_size = R.read_long_unsigned()
        R.seek(4)
        a_offset = R.read_long_unsigned()
        R.goto(a_name_offset)
        a_name = R.read_string()
        d = ArcFileDescriptor(a_path_type, a_entry_number, a_name, a_offset, a_size)
        file_descriptors.append(d)

    # Set Parents to create a folder heirachy
    for i, af in enumerate(file_descriptors):
        if af.path_type_folder:
            for j in range(i + af.offset, i + af.offset + af.size):
                file_descriptors[j].parent = file_descriptors[i]

    # Dump Files
    dump_location = path[0:path.rindex('\\')]
    for af in file_descriptors:
        if af.path_type_file:
            out_path = dump_location + af.get_path_toroot()
            out_dir = os.path.dirname(out_path)
            if not os.path.exists(out_dir):
                try:
                    os.makedirs(out_dir)
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            R.goto(offset_files + af.offset)
            out = open(out_path, 'wb')  # Starts from a fresh empty file
            out.write(f.read(af.size))
            # out.flush()  # Closing probably ensures that it is flushed anyway
            out.close()
    f.close()


if __name__ == "__main__":
    nep_tools.debug = True
    extract_arc_file("C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megadimension Neptunia VII\\DLC\\DLC000000000006900000\\contents.arc")
    # list_dlcs_as_text()
