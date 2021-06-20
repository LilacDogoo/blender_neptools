"""
Author: LilacDogoo

This adds an 'Import from ISM2 menu item' in the 'import' menu in Blender.
This also hold all the capabilities of reading ISM2 files into a 'PreBlender_Model' object.

CREDIT: Random Talking Brush, howie
This script was written by me (LilacDogoo) based on a 3ds Max script written by Random Talking Bush.
The 3ds Max script written by Random Talking Bush is based on the LightWave importer by howfie.
If you use it, consider giving thanks to Idea Factory, Compile Heart, howfie, Random Talking Bush, and myself.


REMEMBER: I did not automate this completely, as of yet.
    You must do this yourself:
      • extract 'pac' file collections
      • extract 'cl3' file collections
      • convert 'tid' files to 'png' files
    Blender should do the rest from there. (aside from some face problems)
    Some links to help you:
      • Hyperdimension Neptunia Re;Birth 1 & 2  >  https://steamcommunity.com/sharedfiles/filedetails/?id=453717187
      • Megadimension Neptunia Victory II  >  https://github.com/MysteryDash/Dash.FileFormats

About the face problem:
    The UV's are there. So; assigning the face texture and transforming the UV's to fit should be easy to do manually.
"""

import os
import traceback
import math
import time
from typing import List, BinaryIO

import bpy

import nep_tools
from nep_tools import import_to_blender
from nep_tools.utils import binary_file
from nep_tools.utils.matrix4f import Matrix4f


class BlenderOperator_ISM2_import(bpy.types.Operator):
    bl_idname = "import_scene.ism2"
    bl_label = "ISM2 Importer (Neptunia)"
    bl_description = "Import Models from Neptunia ISM2 files."
    bl_options = {'UNDO'}

    # Properties used by the file browser
    filepath: bpy.props.StringProperty(name="File Path", description="The file path used for importing the ISM2 files",
                                       maxlen=1024, default="", options={'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN'})
    directory: bpy.props.StringProperty(maxlen=1024, default="", subtype='FILE_PATH', options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(name="Filter Folders", description="", default=True, options={'HIDDEN'})
    filter_glob: bpy.props.StringProperty(default="*.ism2", options={'HIDDEN'})

    # Custom Properties used by the file browser
    p_cull_back_facing: bpy.props.BoolProperty(name="Cull Backfaces",
                                               description="Generally enabled for video games models. Keep in mind, Models from these games are intended to 'back-face cull. Faces will exist in the exact same positions but have opposite normals.",
                                               default=True)
    # p_merge_vertices: bpy.props.BoolProperty(name="Merge Vertices",
    #                                          description="The original model is all individual triangles. This will attempt to create a continuous 'connected' mesh. Slow.",
    #                                          default=False)
    p_parse_bounding_boxes: bpy.props.BoolProperty(name="Parse Bounding Boxes",
                                                   description="They existed in the ISM2 file so I figured I could include them.",
                                                   default=False)
    # p_parse_motion: bpy.props.BoolProperty(name="Parse Armature Animation",
    #                                        description="For models that have animation data, an attempt will be made to parse it.\nCurrently not working",
    #                                        default=False)
    p_parse_face_anm: bpy.props.BoolProperty(name="Parse \"face.anm\" File",
                                             description="For models that have face anm file, an attempt will be made to parse that file.\nNot too useful yet, but will provide a dump of information in a Blender text file.",
                                             default=False)

    def invoke(self, context, event):
        self.directory = "C:\\Program Files (x86)\\Steam\\steamapps\\common"
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        nep_tools.serious_error_notify = False
        time_start = time.time()  # Operation Timer
        # Create Pre-Models from each selected file
        models: List[import_to_blender.PreBlender_Model] = []
        for file in self.files:
            # Extract ISM2 file into Model Object
            model: import_to_blender.PreBlender_Model = None
            try:
                model = read_ism2(filedirectory=self.directory, filename=file.name,
                                  option_parse_bounding_boxes=self.p_parse_bounding_boxes,
                                  option_parse_face_anm=self.p_parse_face_anm,
                                  option_parse_motion=False)  # self.p_parse_motion,  # TODO
            except:
                print("ERROR: Failed to read ► %s" % file.name)
                traceback.print_exc()

            if model is not None:  # IF model succeeded THEN add to model list
                models.append(model)

        # Use Pre-Models to import to blender
        if len(models):
            import_to_blender.to_blender(models,
                                         option_cull_back_facing=self.p_cull_back_facing,
                                         option_merge_vertices=False,  # self.p_merge_vertices,  # TODO
                                         option_import_location=bpy.context.scene.cursor.location)

        time_end = time.time()  # Operation Timer
        print("    Completed %s in %.4f seconds" % (models[0].getName() if len(models) > 0 else "%i models" % len(models), time_end - time_start))

        if nep_tools.serious_error_notify:
            def draw(self, context):
                self.layout.label(text="Check Console for details.\n \'Window > Toggle System Console\'")

            bpy.context.window_manager.popup_menu(draw, title="Serious Error(s)", icon='ERROR')

        return {'FINISHED'}


def read_ism2(filedirectory: str, filename: str,
              option_parse_bounding_boxes: bool = False,
              option_parse_face_anm: bool = False,
              option_parse_motion: bool = False,
              transform_to_blender_space: Matrix4f = Matrix4f.create_rotation_x(math.pi * .5)) -> nep_tools.import_to_blender.PreBlender_Model:
    # Blender adds a '\' to the end of the filepath. This is annoying since upon the first use of 'os.path.dirname()' does not work as intended. Only the last '\' gets removed.
    # To counter this effect I will ensure that there is no '\' at the end of the file
    while filedirectory[-1] == '\\':
        filedirectory = filedirectory[0:-1]

    # Begin Parsing File
    f: BinaryIO = open(os.path.join(filedirectory, filename), 'rb')

    # Reads the first 4 bytes of the files and checks for the signature
    if f.read(4).decode() != "ISM2":
        print("ERROR: File signature did not match \"ISM2\"" + filedirectory)
        f.close()
        return None

    # Check Endian -- This is the section count, which will obviously always have a low positive integer
    # Stream Reader Functions :: Some reader functions are based on endian
    f.seek(0x14)
    R: binary_file.LD_BinaryReader = binary_file.LD_BinaryReader(f, not (0 < binary_file.struct_ULongL.unpack_from(f.read(4))[0] < 0x10000))

    model = nep_tools.import_to_blender.PreBlender_Model(filename)  # default name in case the real name was not found. (Usually found in one of the Armature Bones)

    # Map all material Locations - This is NOT part of the ISM2 file
    texture_directory_characters: str = os.path.join(filedirectory, "texture")
    texture_directory_maps_RB3: str = os.path.join(os.path.dirname(filedirectory), "texture")
    texture_directory_maps_VII: str = os.path.join(os.path.dirname(os.path.dirname(filedirectory)), "texture")

    if os.path.exists(texture_directory_characters):  # This should be true for Characters & Accessories
        subpaths: List[str] = next(os.walk(texture_directory_characters), (None, [], None))[1]
        if len(subpaths) == 0: print("Character textures have not been extracted at this location:\n    %s" % texture_directory_characters)
        for sp in subpaths:  # Characters always have variation textures in subdirectories
            model.texture_directories.append(import_to_blender.TextureDirectory(sp, os.path.join(texture_directory_characters, sp)))
    elif os.path.exists(texture_directory_maps_VII):  # This should be true for Maps in VII
        model.texture_directories.append(import_to_blender.TextureDirectory(None, texture_directory_maps_VII))
    elif os.path.exists(texture_directory_maps_RB3):  # This should be true for Maps in ReBirth 3
        model.texture_directories.append(import_to_blender.TextureDirectory(None, texture_directory_maps_RB3))

    # Helper Variables
    bboxCount = 0
    degTOrad = math.pi / 180

    # Begin Decoding
    R.goto(0x04)
    versionA = R.read_byte_unsigned()
    versionB = R.read_byte_unsigned()
    versionC = R.read_byte_unsigned()
    versionD = R.read_byte_unsigned()
    R.goto(0x10)  # Skip over unused variables listed above
    file_length = R.read_long_unsigned()
    file_section_count = R.read_long_unsigned()

    print("ISM2 v%s.%s.%s.%s  Size: %s  < %s >" % (versionA, versionB, versionC, versionD, str(file_length).rjust(8), os.path.join(filedirectory, filename)))

    R.goto(0x20)  # Where the File Section pointers are
    # Read File Section Pointers
    file_section_codes = []
    file_section_offsets = []
    for _ in range(file_section_count):
        file_section_codes.append(R.read_long_unsigned())
        file_section_offsets.append(R.read_long_unsigned())
    for file_section_index in range(file_section_count):
        file_section_code = file_section_codes[file_section_index]
        file_section_offset = file_section_offsets[file_section_index]

        # File Section Types
        # ------------------
        # ( ) = Not Implemented  - No work has been done
        # (T) = Text output only - Data is exported to a human-readable file
        # (E) = Error Prone      - Functions but buggy
        # (G) = Good             - Functions without guarantee
        # (C) = Complete         - Fully Functional and believed to be bug free
        # ------------------
        # 0x03 003 (G) Armature Data Block (Surfaces are in here for some reason)
        # 0x0B 011 (G) Object-Mesh
        # 0x21 033 (C) Strings
        # 0x2E 046 (C) Textures
        # 0x32 050 ( ) <unknown>
        # 0x34 052 ( ) Armature Animations
        # 0x61 097 (G) Materials
        # 0x62 098 (G) FX Shader Nodes
        # 0x82 130 ( ) <unknown>

        R.goto(file_section_offset)
        if file_section_code == 0x21:  # Strings
            R.seek(0x08)
            string_count = R.read_long_unsigned()
            offset_array = []
            for _ in range(string_count):
                offset_array.append(R.read_long_unsigned())
            for offset in offset_array:
                R.goto(offset)
                model.strings.append(R.read_string())

        elif file_section_code == 0x2E:  # 46 # Textures
            R.seek(8)  # Skip over Section Type & Header Length
            textures_count = R.read_long_unsigned()  # Textures Header 2: Number of Textures in list

            if nep_tools.debug:
                print("\n  File Section Type %s == %s  Texture List @ %s" % (hex(file_section_code), file_section_code, hex(file_section_offset)))

            texture_offsets = []
            for ___ in range(textures_count):
                texture_offsets.append(R.read_long_unsigned())
            for texture_offset in texture_offsets:
                R.goto(texture_offset)
                R.seek(0x04)
                texture_name = model.strings[R.read_long_unsigned()]
                R.seek(0x08)
                texture_filename = model.strings[R.read_long_unsigned()]
                i = texture_filename.rfind('.')  # Trim file extension if it exists
                if i > 0: texture_filename = texture_filename[0:i]
                model.textures[texture_name] = texture_filename

        elif file_section_code == 0x62:  # 98 # FX Shader Nodes
            pass  # Not Implemented - No usefull information in this section

        elif file_section_code == 0x61:  # 97 # Materials
            R.seek(0x08)  # Skip over unused header variables
            materials_count = R.read_long_unsigned()  # Materials Header 2: Number of Materials in list
            if nep_tools.debug:
                print("\n  File Section Type %s == %s  Material List @ %s" % (hex(file_section_code), file_section_code, hex(file_section_offset)))

            material_offsets = []
            for ___ in range(materials_count):
                material_offsets.append(R.read_long_unsigned())
            for material_index, material_offset in enumerate(material_offsets):
                R.goto(material_offset)

                # Type 0x0D - # 13 # Material
                R.seek(0x0C)
                material = import_to_blender.Material(model.strings[R.read_long_unsigned()])  # Read the material_name_ID
                model.materials.append(material)
                R.seek(0x0C)
                R.goto(R.read_long_unsigned())

                # Type 0x6C = 108 - This is where the split to multiple textures happen (diffuse, normal, ect...)
                R.seek(0x08)
                texture_count = R.read_long_unsigned()

                if nep_tools.debug:
                    print("    Material %s: @ %s   [[ %s ]]" % (
                        material_index, hex(material_offset), material))

                texture_offsets = []
                for ____ in range(texture_count):
                    texture_offsets.append(R.read_long_unsigned())
                for texture_offset in texture_offsets:
                    R.goto(texture_offset)

                    # Type 0x6A = 106
                    R.seek(0x14)
                    R.goto(R.read_long_unsigned())

                    # ** 0X6B ** Description
                    # 0x6B Header
                    # Offset      Length      Description
                    # 0x00        0x04        BlockID  = 0x6A
                    # 0x04        0x04        BlockLen = 0x18
                    # 0x08        0x04        EntryCount (Always a list of pointers)
                    # 0x0C        0x02        EntryType ** View Types Below
                    # 0x0E        0x02         <Unknown>  (I've only seen values 0x00 and 0x19 so far)
                    # 0x10        0x04        EntryLength (Examples: {IF entries are integers THEN 1 , IF entries are vectors THEN 3})
                    # 0x14        0x04        Pointer to 0x6A Block. Only EntryType[0x0E] contains these.
                    # 0x6B BODY
                    # The body is always a list of pointers.
                    # The '1st 0x6B' usually has an entry type of '0x02' OR '0x06'. These contain pointers that point to more '0x6B's.
                    #
                    # 0x6B > EntryType Values (The pointers will point to these)
                    # 0x06    Pointers to more '0x6B' blocks as listed below - This is a 'Texture(Surface)'. *** TARGET ***
                    #   0x15    'file_name' - 99% of the time. Sometimes it says things like 'rock_c1' when it should say 'rock_c'. *** TARGET ***
                    #   0x18    'pixel_format' - of DDS file. (I already have to converted to PNG)
                    # 0x02    Pointers to more '0x6B' blocks as listed below - This is a 'Texture(Surface) Sampler'.
                    #   0x0E    The name of the '0x6A' block that contains the texture(surface) for this sampler. (This also contains a pointer to the same '0x6A' block in it's header.)
                    #   0x0F    The name of referenced 'Texture(Surface) Sampler' ???
                    #   0x10    The name of referenced 'Texture(Surface) Sampler' ???
                    #   0x12    The file_name of an 'ism2' file ???
                    #   0x13    The file_name of an 'ism2' file ???
                    #   0x14    The file_name of an 'ism2' file ???

                    # Type 0x6B = 107 - We can determin here if this will be a texture(0x06) or surface(0x02)
                    R.seek(0x0C)
                    # IF the read value is not 0x06 THEN this is not a texture
                    if 0x06 != R.read_short_unsigned():
                        continue
                    R.seek(0x0A)  # From the '1st 0x6B'; the first pointer always points to the '2nd 0x6B' which has the 'file_name'.
                    R.goto(R.read_long_unsigned())  # read the pointer to the second 0x6B block and goes to it

                    # Type 0x6B = 107 - This '2nd 0x6B' always contains 1 pointer that points to the 'string_index' which contains the 'file_name'.
                    R.seek(0x18)
                    R.goto(R.read_long_unsigned())  # read the '2nd 0x6B's pointer and go to it.

                    # TODO Define in Blender how to handle missing textures.
                    #    • Create a texture node with the corrext filepath even tho it doesn't exist so that when the user does create the PNG Blender will find it.
                    # TODO  Auto-Extract DDS and TID >> convert to PNG

                    texture_filename: str = model.strings[R.read_long_unsigned()]
                    texture_filename_mapped: str = model.textures[texture_filename] if texture_filename in model.textures else None

                    if len(model.texture_directories) > 0:  # Test against first directory
                        texture_directory = model.texture_directories[0]
                        # The preffered texture is the one we use the Texture dict where key-value pairs are (name, filename).
                        # IF preffered texture failed THEN try non-mapped texture
                        if texture_filename_mapped is not None and os.path.exists(os.path.join(texture_directory.path, "%s.png" % texture_filename_mapped)):
                            texture_filename = texture_filename_mapped  # Preffered texture found
                        else:
                            if not os.path.exists(os.path.join(texture_directory.path, "%s.png" % texture_filename)):
                                # Neither PNG was found
                                if os.path.exists(os.path.join(texture_directory.path, "%s.tid" % texture_filename)) \
                                        or os.path.exists(os.path.join(texture_directory.path, "%s.tid" % texture_filename_mapped)):
                                    print("  Texture['%s']: User did not extract PNG from TID file in directory < %s >" % (texture_filename, texture_directory.path))
                                else:
                                    print("  Texture['%s']: Neither PNG or TID file was found in directory < %s >" % (texture_filename, texture_directory.path))

                    # Assign the texture_filename to the correct texture map
                    _index = texture_filename.rfind("_", -4)
                    texture_code: str = texture_filename[_index + 1].lower() if _index != -1 else "_"
                    if texture_code == "c":
                        material.texture_diffuse_filename = texture_filename
                    elif texture_code == "s":
                        material.texture_specular_filename = texture_filename
                    elif texture_code == "i":
                        material.texture_emission_filename = texture_filename
                    elif texture_code == "n":
                        material.texture_normal_filename = texture_filename
                    elif texture_code == "m":
                        material.texture_cyangreen_filename = texture_filename
                    else:
                        print("  ERROR: Texture type unknown: < %s >" % texture_filename)

        elif file_section_code == 0x03:  # Armature
            R.seek(4)  # Skip over unused variables listed above
            # Armature Header 1: Armature Header Length
            armature_header_length = R.read_long_unsigned()
            # Armature Header 2: Bone Count
            model.bones = import_to_blender.Bones(R.read_long_unsigned())

            if nep_tools.debug:
                print("\n  File Section Type %s == %s: Armature  @ %s" %
                      (hex(file_section_code), file_section_code, hex(file_section_offset)))

            R.goto(file_section_offset + armature_header_length)

            # Read each Bone
            bone_header_offset_array = []
            for ___ in range(len(model.bones)):
                bone_header_offset_array.append(R.read_long_unsigned())
            for current_bone_offset in bone_header_offset_array:  # BONE DATA BLOCK
                R.goto(current_bone_offset)

                # Bone Header 0: Type
                #   I've only seen values 4 & 5 at this location so far - I don't know what they mean though
                #   Possibly, Type 0x04 == non-deforming && Type 0x05 == deforming
                #   Possibly, Type 0x04 never has a parent bone
                bone_type = R.read_long_unsigned()

                # Bone Header 1: The length of this header block (Always 0x40 == 64)
                bone_header_length = R.read_long_unsigned()

                # Bone Header 2: How many attributes this bone has
                bone_attribute_count = R.read_long_unsigned()

                # Bone Header 3: String ID
                bone_name1_string_id = R.read_long_unsigned()
                # Bone Header 4: String ID
                # bone_name2_string_id = R.read_long_unsigned()

                # Bone Header 5: Unknown
                # Bone Header 6: Unknown

                R.goto(current_bone_offset + 0x1C)  # Skip over unused variables listed above
                # Bone Header 7: Points to the position-in-file of the parent bone
                bone_parent_offset = R.read_long_signed()

                # Bone Header 8: Unknown - Possibly, how many child bones
                # Bone Header 9: Unknown
                # Bone Header 10: Unknown - The last bone had value 2
                R.goto(current_bone_offset + 0x2C)  # Skip over unused variables listed above
                # Bone Header 11: Bone ID (-1 means ???  root OR attachment part)
                bone_id = R.read_long_signed()
                # Bone Header 12 = Never Used
                R.seek(4)
                bone_number = R.read_long_unsigned()  # First Bone in file is assigned 0. Each next bone is assigned ++1
                # Bone Header 14 = Unknown
                # Bone Header 15 = Unknown

                current_bone: import_to_blender.Bone = import_to_blender.Bone(model.strings[bone_name1_string_id], bone_id, bone_number)
                # Assign Parent Bone
                if bone_parent_offset != 0x0:
                    R.goto(bone_parent_offset + 0x34)
                    current_bone.parentid = R.read_long_unsigned()
                R.goto(current_bone_offset + bone_header_length)

                if nep_tools.debug:
                    _parent = model.bones[current_bone.parentid].name if current_bone.parentid >= 0 else "NONE"
                    print("    BONE @ %s: ID=%s  Type: %s  @ %s   ParentBone: %s   name= %s" % (
                        hex(current_bone_offset), str(current_bone.bone_id).rjust(3), bone_type, hex(current_bone_offset),
                        str(_parent).ljust(15), current_bone.name))

                # Read Bone Attributes
                bone_attribute_offset_array = []
                for ____ in range(bone_attribute_count):
                    bone_attribute_offset_array.append(R.read_long_unsigned())
                for current_bone_attribute_offset in bone_attribute_offset_array:
                    R.goto(current_bone_attribute_offset)

                    bone_attribute_type = R.read_long_unsigned()
                    if bone_attribute_type == 0x5B:  # Type 91 # Bone Attibute: Transforms (Transforms are relative to parent)
                        bone_transform_length = R.read_long_unsigned()
                        bone_transform_count = R.read_long_unsigned()

                        if nep_tools.debug: print("      Bone Attribute Type 0x5B == 91 <Transforms>: @ %s" % hex(current_bone_attribute_offset).rjust(6))

                        # TODO Figure out the Matrix stuff so that is can be used with animations
                        m_trans = (0, 0, 0)
                        m_scale = (1, 1, 1)
                        m_rot_euler_a = [0, 0, 0]
                        m_rot_euler_b = [0, 0, 0]

                        bone_transform_offset_array = []
                        for ______ in range(bone_transform_count):
                            bone_transform_offset_array.append(R.read_long_unsigned())
                        for current_transform_index, current_transform_offset in enumerate(bone_transform_offset_array):
                            R.goto(current_transform_offset)
                            bone_transform_type = R.read_long_unsigned()
                            # bone_transform_header1 = R.read_long_unsigned()  # I don't know what this is but it is always zero
                            R.seek(4)  # skip bone_transform_header1

                            if bone_transform_type == 0x14:  # 20 # Matrix Translation
                                m41, m42, m43 = R.read_float(), R.read_float(), R.read_float()
                                m_trans = (m41, m42, m43)
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Translate(%.4f, %.4f, %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m41, m42, m43))
                            # I have not needed the scale section yet. So until I need it, I'm not going to bother processing it
                            # elif bone_transform_type == 0x15:  # 21 # Scale
                            #     scalex, scaley, scalez = R.read_float(), R.read_float(), R.read_float()
                            #     m_scale = (scalex, scaley, scalez)
                            #     if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Scale(%.4f, %.4f, %.4f)" % (
                            #         current_transform, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, scalex, scaley, scalez))
                            elif bone_transform_type == 0x5D:  # 93 # Matrix X
                                m15, m16, m17, m18 = R.read_float(), R.read_float(), R.read_float(), R.read_float()
                                # f.seek(12, 1)  # Skips the Vector
                                m_rot_euler_b[0] = degTOrad * m18  # R.read_float()
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Matrix.X(%.4f, %.4f, %.4f, %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m15, m16, m17, m18))
                            elif bone_transform_type == 0x5E:  # 94 # Matrix Y
                                m25, m26, m27, m28 = R.read_float(), R.read_float(), R.read_float(), R.read_float()
                                # f.seek(12, 1)  # Skips the Vector
                                m_rot_euler_b[1] = degTOrad * m28  # R.read_float()
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Matrix.Y(%.4f, %.4f, %.4f, %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m25, m26, m27, m28))
                            elif bone_transform_type == 0x5F:  # 95 # Matrix Z
                                m35, m36, m37, m38 = R.read_float(), R.read_float(), R.read_float(), R.read_float()
                                # f.seek(12, 1)  # Skips the Vector
                                m_rot_euler_b[2] = degTOrad * m38  # R.read_float()
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Matrix.Z(%.4f, %.4f, %.4f,  %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m35, m36, m37, m38))

                            # These "Joint Orient" blocks contains 4 floats.
                            # The first three represent a Vector
                            # The last float is the rotation in degrees around that Vector
                            # The Vector part seems to be redundant since we already know it base on "bone_transform_type"
                            elif bone_transform_type == 0x67:  # 103 # Joint Orient X
                                m11, m12, m13, m14 = R.read_float(), R.read_float(), R.read_float(), R.read_float()
                                # f.seek(12, 1)  # Skips the Vector
                                m_rot_euler_a[0] = degTOrad * m14  # R.read_float()
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Joint.X(%.4f, %.4f, %.4f,  %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m11, m12, m13, m14))
                            elif bone_transform_type == 0x68:  # 104 # Joint Orient Y
                                m21, m22, m23, m24 = R.read_float(), R.read_float(), R.read_float(), R.read_float()
                                # f.seek(12, 1)  # Skips the Vector
                                m_rot_euler_a[1] = degTOrad * m24  # R.read_float()
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Joint.Y(%.4f, %.4f, %.4f,  %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m21, m22, m23, m24))
                            elif bone_transform_type == 0x69:  # 105 # Joint Orient Z
                                m31, m32, m33, m34 = R.read_float(), R.read_float(), R.read_float(), R.read_float()
                                # f.seek(12, 1)  # Skips the Vector
                                m_rot_euler_a[2] = degTOrad * m34  # R.read_float()
                                if nep_tools.debug: print("        Bone Tansform %s: @ %s == %s  Type=%s == %s          Joint.Z(%.4f, %.4f, %.4f,  %.4f)" % (
                                    current_transform_index, hex(current_transform_offset).rjust(6), str(current_transform_offset).ljust(6), hex(bone_transform_type), bone_transform_type, m31, m32, m33, m34))

                            #
                            # This is commented since no assigned variables ever get used after
                            # Although, I am keeping this, since it was part of the previous script
                            # Maybe one day someone will decypher the rest of the ISM2 file
                            #
                            # elif bone_transform_type == 0x70:  # 112 # Collision Flag
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x71:  # 113 # Collision Radius
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x72:  # 114 # Physics Flag
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_long_signed()
                            # elif bone_transform_type == 0x73:  # 115 # Physics Radius
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x74:  # 116 # Physics Cost
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x75:  # 117 # Physics Mass
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x76:  # 118 # Physics Expand
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x77:  # 119 # Physics Shape Memory
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x7A:  # 122 # Unknown
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x7B:  # 123 # Unknown
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x7C:  # 124 # Unknown
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x7D:  # 125 # Unknown
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x7E:  # 126 # Unknown
                            #     v1, v2, v3 = R.read_long_signed(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x82:  # 130 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x84:  # 132 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x85:  # 133 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x86:  # 134 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x8C:  # 140 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x8D:  # 141 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x8E:  # 142 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x8F:  # 143 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x90:  # 144 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x91:  # 145 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x96:  # 150 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0x97:  # 151 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0xA0:  # 160 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_long_signed()
                            # elif bone_transform_type == 0xA1:  # 161 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0xA2:  # 162 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0xA3:  # 163 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()
                            # elif bone_transform_type == 0xA4:  # 164 # Unknown
                            #     v1, v2, v3, v4 = sr_short(), sr_short(), R.read_long_signed(), R.read_float()

                        # Only do as much proccessing as neccisary
                        # TODO insure 'scale' works
                        t = Matrix4f()
                        # I have not needed the scale section yet. So until I need it, I'm not going to bother processing it
                        # s = None if m_scale[0] == 0 and m_scale[1] == 0 and m_scale[2] == 0 else Matrix4f.create_scale(m_scale)
                        if m_rot_euler_b[2] != 0:
                            t = t.multiply_right(Matrix4f.create_rotation_z(m_rot_euler_b[2]))
                        if m_rot_euler_b[1] != 0:
                            t = t.multiply_right(Matrix4f.create_rotation_y(m_rot_euler_b[1]))
                        if m_rot_euler_b[0] != 0:
                            t = t.multiply_right(Matrix4f.create_rotation_x(m_rot_euler_b[0]))
                        # if s is not None:
                        #     t = t.multiply_right(s)
                        if m_rot_euler_a[2] != 0:
                            t = t.multiply_right(Matrix4f.create_rotation_z(m_rot_euler_a[2]))
                        if m_rot_euler_a[1] != 0:
                            t = t.multiply_right(Matrix4f.create_rotation_y(m_rot_euler_a[1]))
                        if m_rot_euler_a[0] != 0:
                            t = t.multiply_right(Matrix4f.create_rotation_x(m_rot_euler_a[0]))
                        # if s is not None:
                        #     t = t.multiply_right(s)
                        t.m03, t.m13, t.m23 = m_trans
                        # IF parent exists THEN multiply against parent matrix
                        current_bone.transform = model.bones[current_bone.parentid].transform.multiply_right(t) if current_bone.parentid >= 0 else transform_to_blender_space.multiply_right(t)

                    elif bone_attribute_type == 0x4C or bone_attribute_type == 0x4D:  # Type 76 or 77 # Bone Attribute: Surfaces  ( WHY are surfaces here? It makes no sense to me )
                        # This is the only bone that contains surfaces, it also has the name of the model
                        model.name = current_bone.name
                        R.seek(4)
                        bone_attribute_surfaces_count = R.read_long_unsigned()
                        R.seek(12) if bone_attribute_type == 0x4C else R.seek(8)
                        if nep_tools.debug: print("      Bone Attribute Type 0x4C == 76 <Surfaces>: @ %s" % hex(current_bone_attribute_offset).rjust(6))

                        # Read each Surface
                        bone_attribute_surface_offset_array = []
                        for ______ in range(bone_attribute_surfaces_count):
                            bone_attribute_surface_offset_array.append(R.read_long_unsigned())
                        for current_surface_index, current_surface_offset in enumerate(bone_attribute_surface_offset_array):
                            R.goto(current_surface_offset)
                            R.seek(12)
                            # The next 2 values from 'R.read_long_unsigned()' are 'Surface_Name_StringID' and 'Material_Name_StringID'
                            S: import_to_blender.Surface = import_to_blender.Surface(model.strings[R.read_long_unsigned()], model.getMaterialByName(model.strings[R.read_long_unsigned()]))
                            model.surfaces.append(S)
                            if nep_tools.debug: print("        Surface %s: @ %s  mat=\"%s\"  tex=\"%s\"" % (current_surface_index, hex(current_surface_offset),
                                                                                                            S.name, model.materials[S.material_index].name))
                    elif bone_attribute_type == 0x4D:  # Type 77 # Bone Attribute: Shape Keys
                        if nep_tools.debug: print("      Bone Attribute Type 0x4D == 77  Shape Keys  @ %s" % hex(current_bone_attribute_offset).rjust(6))

                    elif bone_attribute_type == 0x5C:  # Type 92 # Bone Attribute: Child Bone List
                        if nep_tools.debug: print("      Bone Attribute Type 0x5C == 92  Child Bone List  @ %s" % hex(current_bone_attribute_offset).rjust(6))
                    else:
                        if nep_tools.debug: print("      Bone Attribute Type %s == %s  <not-implemented>  @ %s" % (hex(bone_attribute_type), bone_attribute_type, hex(current_bone_attribute_offset).rjust(6)))
                model.bones.append(current_bone)
                if nep_tools.debug: print(current_bone)
            model.bones.trim()  # After all bones are added, trim this list to cut down on a bit of proccessing

        elif file_section_code == 0x32:  # 50 #
            R.seek(8)
            something_count = R.read_long_unsigned()
            if nep_tools.debug:
                print("\n  File Section Type %s == %s   @ %s Something[Count:%s]  <not-implemented>" %
                      (hex(file_section_codes[file_section_index]), file_section_codes[file_section_index],
                       hex(file_section_offset), something_count))

        elif file_section_code == 0x0B:  # 11 # Object-Mesh
            # Object-Mesh Header 0: File Section Type
            #   Unused because it always equals file_section_type. It is duplicate data.
            # object_mesh_file_section_type = Never Used
            # mesh_header_length = R.read_long_unsigned()

            R.seek(8)  # Skip over unused variables listed above
            object_mesh_attribute_count = R.read_long_unsigned()

            if nep_tools.debug:
                print("\n  File Section Type %s == %s: Object[Mesh] @ %s  Attributes %s" % (hex(file_section_code), file_section_code, hex(file_section_offset), object_mesh_attribute_count))

            object_mesh_attribute_offset_array = []
            for current_object_mesh_attribute in range(object_mesh_attribute_count):
                object_mesh_attribute_offset_array.append(R.read_long_unsigned())

            for current_object_mesh_attribute in range(object_mesh_attribute_count):
                current_object_mesh_attribute_offset = object_mesh_attribute_offset_array[current_object_mesh_attribute]
                R.goto(current_object_mesh_attribute_offset)
                object_mesh_attribute_type = R.read_long_unsigned()

                if object_mesh_attribute_type == 0x0A:  # 10 # Mesh
                    R.seek(4)
                    mesh_section_count = R.read_long_unsigned()
                    R.seek(20)

                    if nep_tools.debug:
                        print("    Mesh Surfaces @ %s   Count %i" % (hex(current_object_mesh_attribute_offset), mesh_section_count))

                    mesh_section_offset_array = []
                    for current_mesh_section_index in range(mesh_section_count):
                        mesh_section_offset_array.append(R.read_long_unsigned())

                    for current_mesh_section_index in range(mesh_section_count):
                        current_mesh_section_offset = mesh_section_offset_array[current_mesh_section_index]
                        R.goto(current_mesh_section_offset)
                        mesh_section_type = R.read_long_unsigned()

                        if mesh_section_type == 0x59:  # 89 # Mesh Surface Vertices
                            # vertex_blocks_header_length = R.read_long_unsigned()
                            R.seek(4)  # skip header length - it is always the same
                            vertex_blocks_count = R.read_long_unsigned()
                            vertex_type = R.read_short_unsigned()
                            R.seek(2)  # vertex_blocks_header4 = R.read_short_unsigned()   <unknown>
                            vertex_count = R.read_long_unsigned()
                            vertex_size = R.read_long_unsigned()
                            R.seek(4)  # vertex_blocks_header7 = R.read_long_unsigned()    <unknown>

                            if nep_tools.debug:
                                print("      Mesh Surface: Vertices: Count %s  @ %s" % (vertex_blocks_count, hex(current_mesh_section_offset)))

                            # All of these blocks have the same pointer, so it does not matter which one we use.
                            R.goto(R.read_long_unsigned() + 20)  # goto last value of first vertex block
                            vertex_block_offset = R.read_long_unsigned()
                            R.goto(vertex_block_offset)

                            if vertex_type == 0x1:  # Position, Normal 1 & 2, UV Mapping, Vertex Color
                                if nep_tools.debug:
                                    print("        Data @ %s" % hex(vertex_block_offset))
                                for current_vertex_index in range(vertex_count):
                                    x, y, z = transform_to_blender_space.transform(R.read_float(), R.read_float(), R.read_float())
                                    nx, ny, nz = transform_to_blender_space.transform(R.read_half_float(), R.read_half_float(), R.read_half_float())
                                    u = R.read_half_float()
                                    # I don't currently use this or even know what this is used for so to increase performance I will skip it.
                                    # n2x, n2y, n2z = transform_to_blender_space.transform(R.read_half_float(), R.read_half_float(), R.read_half_float())
                                    R.seek(6)
                                    v = R.read_half_float() * -1 + 1
                                    r, g, b, a = R.read_byte_as_float(), R.read_byte_as_float(), R.read_byte_as_float(), R.read_byte_as_float()
                                    model.vertices.append(import_to_blender.Vertex(x, y, z, u, v, r, g, b, a, nx, ny, nz))
                            elif vertex_type == 0x3:  # Bone Weights
                                def create_bone_weight_list(ids, weights):
                                    w = []
                                    for i in range(len(ids)):
                                        if weights[i] <= 0:
                                            # If a zero weight is found then the rest will also be zero, I don't care about zero weights so we can leave this function.
                                            break
                                        w.append(import_to_blender.BoneWeight(ids[i], weights[i]))
                                    return w

                                if nep_tools.debug:
                                    print("        Bone Weights @ %s" % hex(vertex_block_offset))
                                if versionA == 2:
                                    if vertex_size == 0x20:
                                        for current_vertex_index in range(vertex_count):
                                            model.vertices[current_vertex_index].boneWeights = create_bone_weight_list(
                                                (R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned()),
                                                (R.read_float(), R.read_float(), R.read_float(), R.read_float())
                                            )
                                            R.seek(8)

                                    elif vertex_size == 0x30:
                                        for current_vertex_index in range(vertex_count):
                                            model.vertices[current_vertex_index].boneWeights = create_bone_weight_list(
                                                (R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned()),
                                                (R.read_float(), R.read_float(), R.read_float(), R.read_float(), R.read_float(), R.read_float(), R.read_float(), R.read_float())
                                            )
                                    else:
                                        if nep_tools.debug:
                                            print("      Vertex Type %s  File Version %s  Vertex Size %s  <not-implemented>" % (vertex_type, versionA, vertex_size))
                                elif versionA == 1:
                                    if vertex_size == 0x20:
                                        for current_vertex_index in range(vertex_count):
                                            model.vertices[current_vertex_index].boneWeights = create_bone_weight_list(
                                                (R.read_byte_signed(), R.read_byte_signed(), R.read_byte_signed(), R.read_byte_signed()),
                                                (R.read_float(), R.read_float(), R.read_float(), R.read_float())
                                            )
                                            R.seek(12)
                                    elif vertex_size == 0x10:
                                        for current_vertex_index in range(vertex_count):
                                            model.vertices[current_vertex_index].boneWeights = create_bone_weight_list(
                                                (R.read_byte_signed(), R.read_byte_signed(), R.read_byte_signed(), R.read_byte_signed()),
                                                (R.read_half_float(), R.read_half_float(), R.read_half_float(), R.read_half_float())
                                            )
                                            R.seek(4)
                                    else:
                                        if nep_tools.debug:
                                            print("      Vertex Type %s  File Version %s  Vertex Size %s  <not-implemented>" % (vertex_type, versionA, vertex_size))
                                else:
                                    if nep_tools.debug:
                                        print("      Vertex Type %s  File VersionA %s  <not-implemented>" % (vertex_type, versionA))

                            else:
                                if nep_tools.debug:
                                    print("      Vertex Type %s <not-implemented>" % vertex_type)

                        elif mesh_section_type == 0x46:  # 70 # Mesh Surface Indices
                            mesh_surface_header_length = R.read_long_unsigned()
                            mesh_section_surface_count = R.read_long_unsigned()
                            mesh_surface_name_index = R.read_long_unsigned()
                            mesh_surface_section_blank = R.read_long_unsigned()
                            mesh_surface_section_header4 = R.read_short_unsigned()
                            mesh_surface_section_header5 = R.read_short_unsigned()
                            # f.seek(8, 1)  # skip unused header values
                            face_loop_count = R.read_long_unsigned()

                            # gets the name of this surface
                            mesh_surface_index = 0
                            mesh_surface_object = model.strings[mesh_surface_name_index]
                            # converts to material
                            for i, sur in enumerate(model.surfaces):
                                if sur.name == mesh_surface_object:
                                    mesh_surface_index = i
                                    mesh_surface_object = sur
                                    break

                            if nep_tools.debug:
                                print("      Mesh Surface: Indices @ %s  SectionCount %s  FaceLoopCount %s   Blank: %s   Header4: %s   Header5: %s   Surface: %s" % (
                                    hex(current_mesh_section_offset), mesh_section_surface_count, face_loop_count,
                                    mesh_surface_section_blank, mesh_surface_section_header4, mesh_surface_section_header5, mesh_surface_object.name if hasattr(mesh_surface_object, 'name') else "\'noName\'"))

                            mesh_section_surface_offset_array = []
                            for mesh_section_surface_current_index in range(mesh_section_surface_count):
                                mesh_section_surface_offset_array.append(R.read_long_unsigned())

                            for mesh_section_surface_current_index in range(mesh_section_surface_count):
                                mesh_surface_section_current_offset = mesh_section_surface_offset_array[mesh_section_surface_current_index]
                                R.goto(mesh_surface_section_current_offset)
                                mesh_surface_section_type = R.read_long_unsigned()

                                if mesh_surface_section_type == 0x45:  # 69 # Mesh Surface: Face Loops
                                    # face_loops_block_length = R.read_long_unsigned()  # consistant
                                    R.seek(4)  # skip block length
                                    face_loops_count = R.read_long_unsigned()
                                    face_loops_type = R.read_short_unsigned()
                                    face_loops_type2 = R.read_short_unsigned()
                                    face_loops_blank = R.read_long_unsigned()
                                    # f.seek(4, 1)  # skip blank

                                    if nep_tools.debug:
                                        print("        Face Loops (Triangles) @ %s   Type1 %s  Type2 %s  Blank=%s " % (
                                            hex(mesh_surface_section_current_offset), face_loops_type, face_loops_type2, face_loops_blank))

                                    # Determine Face Loop Type
                                    face_vertex_count: int = 3  # default
                                    if face_loops_type == 0x05:
                                        def readVerticies() -> (int,):
                                            return R.read_short_unsigned(), R.read_short_unsigned(), R.read_short_unsigned()
                                    elif face_loops_type == 0x07:
                                        def readVerticies() -> (int,):
                                            return R.read_long_unsigned(), R.read_long_unsigned(), R.read_long_unsigned()
                                    else:
                                        def readVerticies() -> (int,):  # IF the 'face_loop_type' is unknown THEN use this as a default AND report the situation with the print function
                                            return R.read_long_unsigned(), R.read_long_unsigned(), R.read_long_unsigned()

                                        print("        Face Loop Type: <not implemented>  @ %s" % mesh_surface_section_current_offset)

                                    # Read verticies based on the Face Loop Type
                                    face_indicies: (int,)
                                    material_index_local = model.surfaces[mesh_surface_index].material_index
                                    for i in range(int(face_loops_count / face_vertex_count)):
                                        face_indicies = readVerticies()
                                        if 0 <= material_index_local < len(model.materials):  # Avoid index-out-of-bounds. Also some surface have no material assigned SO the material_index will be -1
                                            for VI in face_indicies:
                                                if any(VC != 1 for VC in model.vertices[VI].rgba):  # IF any vertex-color-value is not 1 THEN vertex coloring should be enabled in Blender
                                                    model.materials[material_index_local].enable_vertex_coloring = True
                                        model.faces.append(import_to_blender.Face(face_indicies, mesh_surface_index))

                                elif mesh_surface_section_type == 0x6E:  # 110 # Mesh Surface Bounding Box
                                    if option_parse_bounding_boxes:
                                        R.seek(0x0C)
                                        min_x, min_y, min_z = transform_to_blender_space.transform(R.read_float(), R.read_float(), R.read_float())
                                        R.seek(0x04)
                                        max_x, max_y, max_z = transform_to_blender_space.transform(R.read_float(), R.read_float(), R.read_float())
                                        mesh_surface_object.bounding_box = import_to_blender.BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)
                                        if nep_tools.debug:
                                            R.seek(0x0C)
                                            print("        Bounding Box %s %s %s\n                     %s %s %s" % (
                                                ("%.4f" % min_x).rjust(10),
                                                ("%.4f" % min_y).rjust(10),
                                                ("%.4f" % min_z).rjust(10),
                                                ("%.4f" % max_x).rjust(10),
                                                ("%.4f" % max_y).rjust(10),
                                                ("%.4f" % max_z).rjust(10)))
                                else:
                                    if nep_tools.debug:
                                        print("        Mesh Surface Section %s <not-implemented>  @ %s" % (mesh_surface_section_type, hex(mesh_surface_section_current_offset)))

                        elif mesh_section_type == 0x6E:  # 110 # Mesh Bounding Box
                            if option_parse_bounding_boxes:
                                R.seek(0x0C)
                                min_x, min_y, min_z = transform_to_blender_space.transform(R.read_float(), R.read_float(), R.read_float())
                                R.seek(0x04)
                                max_x, max_y, max_z = transform_to_blender_space.transform(R.read_float(), R.read_float(), R.read_float())
                                model.bounding_box = import_to_blender.BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)
                                bboxCount += 1
                                if nep_tools.debug:
                                    R.seek(0x0C)
                                    print("      Mesh: Bounding Box %s %s %s\n                         %s %s %s" % (
                                        ("%.4f" % min_x).rjust(10),
                                        ("%.4f" % min_y).rjust(10),
                                        ("%.4f" % min_z).rjust(10),
                                        ("%.4f" % max_x).rjust(10),
                                        ("%.4f" % max_y).rjust(10),
                                        ("%.4f" % max_z).rjust(10)))

        # TODO Animations
        # elif current_file_section_type == 0x34:  # 52 # Armature Animations
        #     # armature_animations_block_type  # Duplicate Data
        #     # armature_animations_header_length  # Always the same
        #     R.seek(0x08)  # skip block_type and header_length
        #     animation_bone_count = R.read_long_unsigned()
        #     # armature_animations_header03  # * Unknown
        #     # armature_animations_header04  # * Unknown
        #     R.seek(0x08)
        #     animation_duration = R.read_float()  # float Unknown
        #     # armature_animations_header06  # float Unknown
        #     # armature_animations_header07  # long Unknown
        #     R.seek(0x08)
        #
        #     mo_ = import_to_blender.Motion(filename, animation_duration)
        #
        #     if nep_tools.debug:
        #         print("\n  File Section Type %s == %s  @ %s  'Animation Bones'  Count %i   Duration: %s" % (hex(current_file_section_type), current_file_section_type, hex(current_file_section_offset), animation_bone_count, animation_duration))
        #
        #     armature_animations_offset_array: List[int] = []
        #     for current_armature_animation in range(animation_bone_count):
        #         armature_animations_offset_array.append(R.read_long_unsigned())
        #
        #     for current_armature_animation_bone_number, current_armature_animation_bone_offset in enumerate(armature_animations_offset_array):
        #         R.goto(current_armature_animation_bone_offset)
        #
        #         armature_animation_bone = R.read_long_unsigned()
        #
        #         if armature_animation_bone == 0x50:  # 80 # Animation Bone
        #             # armature_animation_attribute_header_length  # always the same
        #             R.seek(4)  # Skip header length
        #             armature_animation_bone_count = R.read_long_unsigned()
        #             armature_animation_bone_name_index = R.read_long_unsigned()
        #
        #             mo_bone = import_to_blender.MotionBone(model.strings[armature_animation_bone_name_index])
        #
        #             print("    Armature Animation Bone %s  Type 0x50 == 80   @ %s    %s   Bone: %s" % (
        #                 current_armature_animation_bone_number,
        #                 hex(current_armature_animation_bone_offset).rjust(7),
        #                 str(armature_animation_bone_count).rjust(2), model.strings[armature_animation_bone_name_index].rjust(3)))
        #
        #             R.goto(current_armature_animation_bone_offset + 0x20)
        #             armature_animation_bone_offset_array = []
        #             for current_animation_bone_attribute in range(armature_animation_bone_count):
        #                 armature_animation_bone_offset_array.append(R.read_long_unsigned())
        #             for current_animation_bone_attribute_number, current_animation_bone_attribute_offset in enumerate(armature_animation_bone_offset_array):
        #                 R.goto(current_animation_bone_attribute_offset)
        #                 armature_animation_bone_attribute_type = R.read_long_unsigned()
        #
        #                 mo_type = import_to_blender.MotionType()
        #
        #                 if armature_animation_bone_attribute_type == 0x0F:  # 15 # Dunno yet
        #                     # header length  # always 0x40
        #                     # count  # always 1
        #                     # armature_animation_bone_attribute_header03 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header04 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header05 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header06 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header07 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header08 = R.read_long_unsigned()  # always 73
        #                     # armature_animation_bone_attribute_header09 = R.read_long_unsigned()  # always 0
        #                     R.seek(36)
        #                     armature_animation_bone_attribute_header10 = R.read_long_unsigned()  # name of bone
        #                     armature_animation_bone_attribute_header11 = R.read_long_unsigned()
        #                     armature_animation_bone_attribute_header12a = R.read_short_unsigned()
        #                     # armature_animation_bone_attribute_header12b = R.read_short_unsigned()  # always 6
        #                     # armature_animation_bone_attribute_header13 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header14 = R.read_long_unsigned()  # always 0
        #                     # armature_animation_bone_attribute_header15 = R.read_long_unsigned()  # always 0
        #                     R.seek(14)
        #
        #                     if nep_tools.debug:
        #                         print("      AnimBoneAttrib %s:  %s   %s %s %s" % (
        #                             current_animation_bone_attribute_number,
        #                             hex(current_animation_bone_attribute_offset).rjust(10),
        #                             model.strings[armature_animation_bone_attribute_header10].ljust(20),
        #                             armature_animation_bone_attribute_header11,
        #                             armature_animation_bone_attribute_header12a))
        #
        #                     armature_animation_bone_type2 = R.read_long_unsigned()
        #                     if armature_animation_bone_type2 == 0x44:  # 68 # Dunno yet
        #                         # header length  # always 0x20
        #                         R.seek(4)  # skip header length
        #                         armature_animation_bone_4byte_block_length = R.read_long_unsigned()  # Total Length of Block in 4-bytes
        #                         # armature_animation_bone_type2_header03 = R.read_long_unsigned()  # always 0
        #                         R.seek(4)
        #                         armature_animation_bone_type2_header04a = R.read_short_unsigned()
        #                         # armature_animation_bone_type2_header04b = R.read_short_unsigned()  # always 1
        #                         R.seek(2)
        #                         armature_animation_bone_4byte_entry_length = R.read_long_unsigned()  # Length of each entry in 4-bytes
        #                         # armature_animation_bone_type2_header06 = R.read_long_unsigned()  # always 0
        #                         # armature_animation_bone_type2_header07 = R.read_long_unsigned()  # always 0
        #                         R.seek(8)
        #
        #                         armature_animation_frame_count = armature_animation_bone_4byte_block_length // armature_animation_bone_4byte_entry_length
        #
        #                         if nep_tools.debug:
        #                             print("        AnimBoneAttrib2:  %s %s %s   Length: %s" % (
        #                                 str(armature_animation_bone_4byte_block_length).rjust(3), armature_animation_bone_type2_header04a,
        #                                 str(armature_animation_bone_4byte_entry_length).rjust(2), armature_animation_frame_count))
        #
        #                         if armature_animation_bone_type2_header04a == 0x0C:  # 12 # float array (probably vertices or matrices)
        #                             for _ in range(armature_animation_frame_count):
        #                                 armature_animation_keyframe_time_stamp = R.read_float()
        #                                 armature_animation_keyframe_type1 = R.read_short_unsigned()
        #                                 armature_animation_keyframe_type2 = R.read_short_unsigned()
        #                                 armature_animation_keyframe_data: List[float] = []
        #                                 for __ in range(armature_animation_bone_4byte_entry_length - 2):
        #                                     armature_animation_keyframe_data.append(R.read_float())
        #
        #                                 mo_type.motion_data.append(import_to_blender.MotionFrame(armature_animation_keyframe_time_stamp, armature_animation_keyframe_data))
        #
        #                                 if nep_tools.debug:
        #                                     print("        Keyframe %s  Type %s %s" % (armature_animation_keyframe_time_stamp, armature_animation_keyframe_type1, armature_animation_keyframe_type2))
        #                                     print("          (%s)" % ", ".join([("%.4f" % _s_).rjust(7) for _s_ in armature_animation_keyframe_data]))
        #                         elif armature_animation_bone_type2_header04a == 0x12:  # 18 # I have no idea what this is yet
        #                             for _ in range(armature_animation_frame_count):
        #                                 armature_animation_keyframe_time_stamp = R.read_half_float()
        #                                 armature_animation_keyframe_type = R.read_short_unsigned()
        #                                 armature_animation_keyframe_data = []
        #                                 for __ in range(armature_animation_bone_4byte_entry_length - 2):
        #                                     armature_animation_keyframe_data.append(R.read_half_float())
        #
        #                                 mo_type.motion_data.append(import_to_blender.MotionFrame(armature_animation_keyframe_time_stamp, armature_animation_keyframe_data))
        #
        #                                 if nep_tools.debug:
        #                                     print("        Keyframe????? %s  Type %s" % (("%.3f" % armature_animation_keyframe_time_stamp).rjust(6), armature_animation_keyframe_type))
        #                                     print("          (%s)" % ", ".join([str(_s_) for _s_ in armature_animation_keyframe_data]))
        #                         else:
        #                             if nep_tools.debug:
        #                                 print("armature_animation_bone_type2_header04a == %s == %s   <not supported>" % (hex(armature_animation_bone_type2_header04a), armature_animation_bone_type2_header04a))
        #                     else:
        #                         if nep_tools.debug:
        #                             print("        AnimBoneAttrib2: Type %s <not implemented>" % armature_animation_bone_type2)
        #                 else:
        #                     if nep_tools.debug:
        #                         print("Armature Animation Type %s == %s <not implemented>" % (hex(current_animation_bone_attribute_offset).rjust(10), current_animation_bone_attribute_offset))
        #                 mo_bone.motion_types.append(mo_type)
        #         else:
        #             if nep_tools.debug:
        #                 print("    Armature Animation Attribute Type %i == Unknown @ %s" % (armature_animation_bone, hex(current_armature_animation_bone_offset)))
        #         mo_.motion_bones.append(mo_bone)
        #     model.motions.append(mo_)
        else:
            if nep_tools.debug:
                print("\n  File Section Type %s == %s   @ %s  <not-implemented>" % (
                    hex(file_section_codes[file_section_index]),
                    file_section_codes[file_section_index],
                    hex(file_section_offset)))
    R.close()

    # Stored is a seperate file called face.anm (in the same directory)
    if option_parse_face_anm:
        model.face_anm = parse_face_anm(filedirectory + "face.anm")

    # Stored as a list of files inside the "motion" directory
    if option_parse_motion:
        parse_motion(filedirectory + "motion\\")

    return model


def parse_motion(filepath: str):
    pass


EXPRESSION_TYPES = ("Base", "R.Pupil", "L.Pupil", "R.Eyelid", "L.Eyelid", "R.Eyebrow", "L.Eyebrow", "Mouth")


def parse_face_anm(filepath: str) -> import_to_blender.FaceAnm:  # returns None if parsing fails
    if not os.path.isfile(filepath):
        print("File path does not exist - %s" % filepath)
        return None
    if not os.path.isfile(filepath):
        print("File path is not a file - %s" % filepath)
        return None  # Path exists but is not a file.

    f = open(filepath, 'rb')
    # Check Endian -- This is a count which will always have a low positive integer
    # Stream Reader Functions :: Some are created based on endian
    f.seek(4)
    R: binary_file.LD_BinaryReader = binary_file.LD_BinaryReader(f, not (0 < binary_file.struct_ULongL.unpack_from(f.read(4))[0] < 0x10000))

    lines = []
    R.goto(0x0)
    line = "Face Anims Version: %.1f  File: \"%s\"" % (R.read_float(), filepath)
    print(line)
    lines.append(line)

    something_count = R.read_long_unsigned()
    line = "Something Count: %s" % something_count
    if nep_tools.debug:
        print(line)
    lines.append(line)
    for i in range(something_count):
        header00 = R.read_long_signed()
        header01 = R.read_long_signed()
        header02 = R.read_long_signed()
        header03 = R.read_long_signed()
        header04 = R.read_long_signed()
        header05 = R.read_long_signed()
        header06 = R.read_long_signed()
        header07 = R.read_long_signed()
        header08 = R.read_long_signed()
        header09 = R.read_long_signed()
        header10 = R.read_long_signed()
        header11 = R.read_long_signed()
        header12 = R.read_long_signed()
        header13 = R.read_long_signed()
        header14 = R.read_long_signed()
        header15 = R.read_long_signed()
        header16 = R.read_long_signed()
        header17 = R.read_long_signed()
        header18 = R.read_long_signed()
        header19 = R.read_long_signed()
        header20 = R.read_long_signed()
        header21 = R.read_long_signed()
        header22 = R.read_float()
        header23 = R.read_float()
        line = "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % (
            str(header00).rjust(2), str(header01).rjust(2), str(header02).rjust(2), str(header03).rjust(2),
            str(header04).rjust(2), str(header05).rjust(2), str(header06).rjust(2), str(header07).rjust(2),
            str(header08).rjust(2), str(header09).rjust(2), str(header10).rjust(2), str(header11).rjust(2),
            str(header12).rjust(2), str(header13).rjust(2), str(header14).rjust(2), str(header15).rjust(2),
            str(header16).rjust(2), str(header17).rjust(2), str(header18).rjust(2), str(header19).rjust(2),
            str(header20).rjust(2), str(header21).rjust(2), str("%.1f" % header22).rjust(6), str("%.1f" % header23).rjust(6))
        if nep_tools.debug:
            print(line)
        lines.append(line)

    # f.seek(0x60 * something_count, 1)
    face_parts_count = R.read_long_unsigned()
    f_location = 12 + 0x60 * face_parts_count
    line = "Face Parts Count: %i" % face_parts_count
    if nep_tools.debug:
        print(line)
    lines.append(line)
    for i in range(face_parts_count):
        texnum = R.read_long_unsigned()
        expression_type = EXPRESSION_TYPES[R.read_long_unsigned()]
        header3 = R.read_long_unsigned()
        header4 = R.read_long_unsigned()
        chunk = R.read_long_unsigned()
        tex_center_x = R.read_float()
        tex_center_y = R.read_float()
        tex_size_x = R.read_float()
        tex_size_y = R.read_float()
        header13 = R.read_float()
        header14 = R.read_float()
        header15 = R.read_float()
        header16 = R.read_float()
        header17 = R.read_float()
        header18 = R.read_byte_unsigned()

        line = "@%s  ID: %s  Tex #%s  ExpressionType: %s  H3:%s  H4:%s  Chunk:%s  TexCenter: (%s, %s), TexSize: (%s, %s)  H13:%s  H14:%s  H15:%s  H16:%s  H17:%s  H18:%s" % (
            str(hex(f_location)).rjust(6), str(i).rjust(2), texnum, str(expression_type).ljust(10), str(header3).rjust(2), str(header4).rjust(2), str(chunk).rjust(3),
            str(tex_center_x).rjust(6), str(tex_center_y).rjust(6), str(tex_size_x).rjust(6), str(tex_size_y).rjust(6),
            ("%.3f" % header13).rjust(7), ("%.3f" % header14).rjust(7), ("%.3f" % header15).rjust(7), ("%.3f" % header16).rjust(7), ("%.3f" % header17).rjust(7), ("%i" % header18).rjust(2))
        if nep_tools.debug:
            print(line)
        lines.append(line)
        f_location += 53

    extra_count = R.read_long_unsigned()
    f.seek(extra_count * 0x20, 1)
    extra_count = R.read_long_unsigned()
    f_location += 8 + 0x20
    line = "Extra Count: %i" % extra_count
    if nep_tools.debug:
        print(line)
    lines.append(line)
    for i in range(extra_count):
        texnum = R.read_long_unsigned()
        expression_type = EXPRESSION_TYPES[R.read_long_unsigned()]
        header3 = R.read_long_unsigned()
        header4 = R.read_long_unsigned()
        chunk_start = R.read_long_unsigned()
        chunk_end = R.read_long_unsigned()
        header7 = R.read_float()
        header8 = R.read_byte_unsigned()
        tex_center_x = R.read_float()
        tex_center_y = R.read_float()
        tex_size_x = R.read_float()
        tex_size_y = R.read_float()
        header13 = R.read_float()
        header14 = R.read_float()
        header15 = R.read_byte_unsigned()
        header16 = R.read_byte_unsigned()
        line = "@%s  ID: %s  Tex #%s  ExpressionType:%s  H3:%s  H4:%s  Chunk Range: (%s, %s) H7:%s H8:%s  TexCenter: (%s, %s), TexSize: (%s, %s)  H13:%s  H14:%s  H15:%s  H16:%s" % (
            str(hex(f_location)).rjust(6), str(i).rjust(2), texnum, str(expression_type).rjust(10), str(header3).rjust(2), str(header4).rjust(2), str(chunk_start).rjust(3), str(chunk_end).rjust(3),
            str(header7).rjust(5), str(header8).rjust(2), ("%.3f" % tex_center_x).rjust(8), ("%.3f" % tex_center_y).rjust(8), ("%.3f" % tex_size_x).rjust(8), ("%.3f" % tex_size_y).rjust(8),
            header13, header14, header15, header16)
        if nep_tools.debug:
            print(line)
        lines.append(line)
        f_location += 55
    f.close()
    return import_to_blender.FaceAnm("\n".join(lines))


if __name__ == "__main__":
    nep_tools.debug = True
    read_ism2("C:\\Program Files (x86)\\Steam\\steamapps\\common\\Superdimension Neptune VS Sega Hard Girls\\data\\GAME200000\\model\\chara\\101", "002.ism2")
