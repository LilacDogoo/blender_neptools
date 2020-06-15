# <pep8 compliant>
import datetime


disclaimer = "This script was written by LilacDogoo based on a 3ds Max script written by Random Talking Bush.\n" \
             "The 3ds Max script written by Random Talking Bush is based on the LightWave importer by howfie.\n" \
             "If you use it, consider giving thanks to Idea Factory, Compile Heart, howfie, " \
             "Random Talking Bush, and myself."
lastUpdated = datetime.datetime(2020, 4, 10)
bl_info = {
    "name": "Neptunia ISM2 Import",
    "author": "LilacDogoo",
    "version": (1, 0, 0),
    "blender": (2, 82, 0),
    "category": "Import-Export",
    "location": "File > Import",
    "description": "Importer for ISM2 files from the Neptunia games."
}

# DEBUG MODE
debug = False

if "bpy" in locals():
    print("in locals")
    import importlib
    import blender_neptools
    importlib.reload(blender_neptools.binary_file_utils)
    importlib.reload(blender_neptools.matrix4f)
    importlib.reload(blender_neptools.import_to_blender)
    importlib.reload(blender_neptools.file_ism2)
    importlib.reload(blender_neptools.vii_dlc_extract)
else:
    print("out of locals")
    from blender_neptools import matrix4f
    from blender_neptools import binary_file_utils
    from blender_neptools import import_to_blender
    from blender_neptools import file_ism2
    from blender_neptools import vii_dlc_extract

import bpy


def menu_func_import(self, context):
    self.layout.operator(file_ism2.ISM2_importOperator.bl_idname, text="Neptunia Models (.ism2)")


_classes = (
    file_ism2.ISM2_importOperator,
)


def register():
    # Register all classes contained in this package so that Blender has access to them
    from bpy.utils import register_class
    for cls in _classes:
        register_class(cls)

    # Add menu items
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    # Remove menu items
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    # Unregister classes
    for cls in _classes:
        bpy.utils.unregister_class(cls)

