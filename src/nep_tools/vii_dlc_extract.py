import errno
import os
from os import walk
from typing import List

from nep_tools import binary_file_utils

import bpy

DEFAULT_VII_DLC_PATH = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Megadimension Neptunia VII\\DLC\\"


class DLC_Description:
    def __init__(self, title: str, comment: str, folder: str) -> None:
        super().__init__()
        self.title, self.comment, self.folder = title, comment, folder

    def __str__(self) -> str:
        com = "    " + self.comment.replace("\n", "\n    ")
        return "%s\n%s\n%s" % (self.folder[self.folder.rindex(os.sep) + 1:], self.title, com)


def get_dlc_description(path: str) -> DLC_Description:
    (_, _, files) = walk(path).__next__()
    for file in files:
        if file.startswith("main"):
            R = open(path + "\\" + file, 'rt', encoding='utf8')
            title: str = ""
            comment: str = ""
            line: str = R.readline()
            if not line.startswith("<title:"):  # Wrong file format
                # Returns path only so we know what path the error is caused in
                return DLC_Description("NONE", "NONE", path)
            title = R.readline()[:-1]
            line = R.readline()
            while line != "":
                if line.startswith("<comment:"):
                    line = R.readline()
                    while line != "" and line != ">\n":
                        comment = comment + line
                        line = R.readline()
                    break
                line = R.readline()
            return DLC_Description(title, comment, path)


def list_dlc_as_text(folder: str):
    (_, dirs, _) = walk(folder).__next__()
    for dir in dirs:
        print(get_dlc_description(folder + dir))


###################
### EXTRACT ARC ###
###################

# CREDIT: Quick BMS Script found here:  https://zenhax.com/viewtopic.php?t=2732

class ArcFileDescriptior:
    def __init__(self, path_type: int, entry_number: int, name: str, offset: int, size: int) -> None:
        super().__init__()
        if path_type == 0x02000000:
            self.path_type_root: bool = False
            self.path_type_folder: bool = True
            self.path_type_file: bool = False
        elif path_type == 0x03000000:
            self.path_type_root: bool = True
            self.path_type_folder: bool = True
            self.path_type_file: bool = False
        elif path_type == 0x04000000:
            self.path_type_root: bool = False
            self.path_type_folder: bool = False
            self.path_type_file: bool = True
        else:
            self.path_type_root: bool = False
            self.path_type_folder: bool = False
            self.path_type_file: bool = False
        self.name: str = name
        self.path: str = ""
        self.entry_number: int = entry_number
        self.offset: int = offset
        self.size: int = size
        self.parent: ArcFileDescriptior = None

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


def extract_arc_file(path: str):
    f = open(path, 'rb')
    R = binary_file_utils.LD_BinaryReader(f, False)
    if not f.read(4) == b'ARC\x02':
        print("INCORRECT FILE FORMAT  %s" % path)

    file_count = R.read_long_unsigned()  # File Count
    description_table_size = R.read_long_unsigned()  # Length of all the File Descriptions
    description_table_entry_size = int(description_table_size / file_count)  # Length of all the File Descriptions
    file_name_list_size = R.read_long_unsigned()  # Full length
    offset_file_descriptions = f.tell()  # Location that File Descriptions begin
    offset_file_names = offset_file_descriptions + description_table_size  # Location that File Names begin
    offset_files = offset_file_names + file_name_list_size  # Location that File Data begins

    # Get file descriptors
    file_descriptors: List[ArcFileDescriptior] = []
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
        d = ArcFileDescriptior(a_path_type, a_entry_number, a_name, a_offset, a_size)
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
            f.close()
            out.close()


if __name__ == "__main__":
    list_dlc_as_text(DEFAULT_VII_DLC_PATH)
