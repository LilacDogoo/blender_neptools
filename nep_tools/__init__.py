"""
Author: LilacDogoo
"""

import datetime

lastUpdated = datetime.datetime(2021, 6, 20)
bl_info = {
    "name": "NepTools",
    "author": "LilacDogoo",
    "version": (1, 2, 0),
    "blender": (2, 93, 0),
    "category": "Import-Export",
    "location": "File > Import",
    "description": "Importer for ISM2 files from the Neptunia games."
}

# DEBUG MODE
debug = False
serious_error_notify = False

if "bpy" in locals():
    import importlib
    import nep_tools

    importlib.reload(nep_tools.utils.binary_file)
    importlib.reload(nep_tools.utils.matrix4f)
    importlib.reload(nep_tools.import_to_blender)
    importlib.reload(nep_tools.file_ism2)
    importlib.reload(nep_tools.extract_arc_vii_dlc)
else:
    from nep_tools.utils import matrix4f
    from nep_tools import import_to_blender
    from nep_tools import file_ism2
    from nep_tools import extract_arc_vii_dlc

import bpy


def menu_func_import(self, context):
    self.layout.operator(file_ism2.BlenderOperator_ISM2_import.bl_idname, text="Neptunia Models (.ism2)")


class TOPBAR_MT_NepTools(bpy.types.Menu):
    bl_idname = "TOPBAR_MT_NepTools"
    bl_label = "NepTools"

    def menu_draw(self, context):
        self.layout.menu("TOPBAR_MT_NepTools")

    def draw(self, context):
        self.layout.operator(file_ism2.BlenderOperator_ISM2_import.bl_idname)
        self.layout.separator()
        self.layout.operator(extract_arc_vii_dlc.BlenderOperator_ARC_Descriptor.bl_idname)
        self.layout.operator(extract_arc_vii_dlc.BlenderOperator_ARC_Extractor.bl_idname)


_classes = (
    file_ism2.BlenderOperator_ISM2_import,
    extract_arc_vii_dlc.BlenderOperator_ARC_Descriptor,
    extract_arc_vii_dlc.BlenderOperator_ARC_Extractor,
    TOPBAR_MT_NepTools,
)


def register():
    # Register all classes contained in this package so that Blender has access to them
    for cls in _classes:
        bpy.utils.register_class(cls)

    # Add menu items
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_NepTools.menu_draw)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    # Remove menu items
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_NepTools)

    # Unregister classes
    for cls in _classes:
        if hasattr(bpy.types, cls.bl_idname):
            bpy.utils.unregister_class(cls)
