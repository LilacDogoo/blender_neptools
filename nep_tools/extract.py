"""
Auto detects what type of file and chooses the correct extractor
"""

import bpy

DEFAULT_STEAM_GAME_PATH = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\"


class BlenderOperator_Extract_NepFile(bpy.types.Operator):
    bl_idname = "extract_any"
    bl_label = "Extract NepFile"
    bl_description = "Extracts any Type of Nep File Container"
    bl_options = {'UNDO'}

    # Properties used by the file browser
    filepath: bpy.props.StringProperty(name="File Path", description="The 'arc' file to extract",
                                       maxlen=1024, default="", options={'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN'})
    directory: bpy.props.StringProperty(maxlen=1024, default=DEFAULT_STEAM_GAME_PATH, subtype='FILE_PATH', options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(name="Filter Folders", description="", default=True, options={'HIDDEN'})
    filter_glob: bpy.props.StringProperty(default="*.arc;*.cl3;*.cpk;*.pac", options={'HIDDEN'})

    def invoke(self, context, event):
        self.directory = DEFAULT_STEAM_GAME_PATH
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        extract_nep_file(self.filepath, self.files, self.directory)
        return {'FINISHED'}


def extract_nep_file(filepath: str, files: str, directory: str):
   pass