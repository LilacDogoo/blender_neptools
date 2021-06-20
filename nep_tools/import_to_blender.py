"""
IMPORT TO BLENDER

This file serves as a connection between 'any Neptunia 3D Model file type' and 'Blender'.
No matter the file format, the file should be able to be decoded into a 'PreBlender_Model' object.
The 'PreBlender_Model' object is primarily to make the code very readable and easy to debug.
After a 'PreBlender_Model' is built, it can be imported with the 'to_blender()' function.
"""

from typing import List

import os
import random

import bpy
import bmesh

import nep_tools
from nep_tools.utils.matrix4f import Matrix4f


class BoundingBox:
    def __init__(self, min_x: float, min_y: float, min_z: float, max_x: float, max_y: float, max_z: float) -> None:
        super().__init__()
        self.min_x, self.min_y, self.min_z = min_x, min_y, min_z
        self.max_x, self.max_y, self.max_z = max_x, max_y, max_z

    def get_verts(self):
        return ((self.min_x, self.min_y, self.max_z),
                (self.min_x, self.min_y, self.min_z),
                (self.max_x, self.min_y, self.min_z),
                (self.max_x, self.min_y, self.max_z),
                (self.min_x, self.max_y, self.max_z),
                (self.min_x, self.max_y, self.min_z),
                (self.max_x, self.max_y, self.min_z),
                (self.max_x, self.max_y, self.max_z))

    def get_quads(self):
        return ((0, 1, 2, 3),
                (3, 2, 6, 7),
                (7, 6, 5, 4),
                (4, 5, 1, 0),
                (4, 0, 3, 7),
                (1, 5, 6, 2))


class Bone:
    def __init__(self, name: str, bone_id: int, bone_index) -> None:
        super().__init__()
        self.name = name
        self.bone_id = bone_id
        self.bone_index = bone_index
        self.parentid: int = -1
        self.transform: Matrix4f = None

    def __str__(self) -> str:
        return "Index:%s ID:%s, PID:%s Name: %s" % (str(self.bone_index).rjust(3), str(self.bone_id).rjust(3), str(self.parentid).rjust(3), self.name)


class Bones(List[Bone]):
    def __init__(self, count: int) -> None:
        super().__init__()
        self.bones_by_id: [int] = [-1] * count

    def __str__(self) -> str:
        return "Count: %i" % len(self.bones_by_id)

    def __len__(self) -> int:
        return len(self.bones_by_id)

    def append(self, b: Bone) -> None:
        super().append(b)
        if b.bone_id >= 0:
            self.bones_by_id[b.bone_id] = b.bone_index

    def trim(self):
        i = len(self.bones_by_id) - 1
        while self.bones_by_id[i] < 0:
            i -= 1
            if i < 0:  # no bones have any IDs
                self.bones_by_id = None
                return
        self.bones_by_id = self.bones_by_id[0:i + 1]

    def get_by_id(self, bone_id: int) -> Bone:
        if bone_id == None:
            print("BoneID's don't exist")
            return None
        if bone_id < 0 or bone_id >= len(self.bones_by_id):
            print("BoneID Out Of Range: %s" % bone_id)
            return None
        return self[self.bones_by_id[bone_id]]


class BoneWeight:
    def __init__(self, bone_id: int, bone_weight: float) -> None:
        super().__init__()
        self.bone_id = bone_id
        self.bone_weight = bone_weight

    def __str__(self) -> str:
        return "%i, %.3f" % (self.bone_id, self.bone_weight)


class TextureDirectory:
    def __init__(self, name: str, path: str):
        super().__init__()
        # This name should match the folder it was found in. For Maps it should be 'None'.
        self.name: str = name
        # This is the absolute path to the location that the textures are found in.
        self.path: str = path

    def __str__(self) -> str:
        return "Texture Directory '%s'  < %s >" % (self.name, self.path)


class Material:
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name
        self.enable_vertex_coloring: bool = False
        # Diffuse Texture - C <-- Letter in the file name
        self.texture_diffuse_filename: str = None
        # Diffuse Texture - S
        self.texture_specular_filename: str = None
        # Diffuse Texture - N
        self.texture_normal_filename: str = None
        # Diffuse Texture - I
        self.texture_emission_filename: str = None
        # Diffuse Texture - M
        self.texture_cyangreen_filename: str = None

    def __str__(self) -> str:
        return "Material(%s, vertex_coloring: %s)" % (self.name, self.enable_vertex_coloring)


class Surface:
    def __init__(self, name: str, material_index: int) -> None:
        super().__init__()
        self.name: str = name
        self.material_index: int = material_index
        self.bounding_box: BoundingBox = None

    def __str__(self) -> str:
        return "Surface(%s,  %s)" % (self.name, self.material_index)


class Vertex:
    def __init__(self, x: float, y: float, z: float, u: float, v: float, r: float, g: float, b: float, a: float, nx: float, ny: float, nz: float) -> None:
        # This is able to have a second set of Normals - though, I do not know for what purpose
        super().__init__()
        self.position: (float, float, float) = (x, y, z)
        self.uv: (float, float) = (u, v)
        self.rgba: (float, float, float, float) = (r, g, b, a)
        self.normal: (float, float, float) = (nx, ny, nz)
        self.boneWeights: list[BoneWeight,] = []


class Face:
    def __init__(self, indices: (), surface_index: int) -> None:
        super().__init__()
        self.indices: (int,) = indices  # indices
        self.surface_index: int = surface_index

    def __str__(self) -> str:
        return "(%04i, %04i, %04i)  %i" % (self.indices[0], self.indices[1], self.indices[2], self.surface_index)


class FaceAnm:
    def __init__(self, face_anm: str) -> None:
        super().__init__()
        self.face_anm: str = face_anm  # Todo: for now just a simple long string


class MotionFrame:
    def __init__(self, frame_position: float, data: List[float]) -> None:
        super().__init__()
        self.frame_position = frame_position
        self.data = data

    def __str__(self) -> str:
        return "%s: (%s)" % (str(self.frame_position).rjust(6), ", ".join("%.4f" % a for a in self.data))


class MotionType:
    def __init__(self) -> None:
        super().__init__()
        self.motion_data: List[MotionFrame] = []

    def __str__(self) -> str:
        return "MF"


class MotionBone:
    def __init__(self, bone_name: str) -> None:
        super().__init__()
        self.bone_name = bone_name
        self.motion_types: List[MotionType] = []

    def __str__(self) -> str:
        return self.bone_name


class Motion:
    def __init__(self, name: str, duration: float) -> None:
        super().__init__()
        self.name = name
        self.duration = duration
        self.motion_bones: List[MotionBone] = []

    def __str__(self) -> str:
        return "%s :: %s :: #bones:%s" % (self.name, self.duration, len(self.motion_bones))


class PreBlender_Model:
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name

        # Buffers
        self.strings: List[str] = []
        self.texture_directories: List[TextureDirectory] = []
        self.textures: dict = {}
        self.materials: List[Material] = []
        self.surfaces: List[Surface] = []
        self.vertices: List[Vertex] = []
        self.faces: List[Face] = []
        self.bounding_box: BoundingBox = None
        self.bones: Bones = None
        self.motions: List[Motion] = []
        self.face_anm: FaceAnm = None

    def getName(self):
        return self.name

    def getMaterialByName(self, name: str) -> int:
        for material_index, material in enumerate(self.materials):
            if material.name == name:
                return material_index
        return -1


def to_blender(models: List[PreBlender_Model],
               option_cull_back_facing: bool = True,
               option_merge_vertices: bool = False,
               option_import_location=(0, 0, 0)):
    target_collection: bpy.types.Collection = bpy.data.collections.new("ISM2 Import.000")
    bpy.context.scene.collection.children.link(target_collection)

    print("Importing %i models" % len(models))

    for model in models:
        # Todo: Merge Vertices if option is enabled - Process Heavy
        #     Maybe this should move to the 'PreBlender_Model' class.
        #     Maybe this should be done after imported into Blender to take advantage of it's effieciency.
        #   The goal here is to merge as much as possible while saving the double sided geometry.
        #   A method I use in Blender is to select UV-islands then perform a merge on those vertices.
        #   Blender does not actually support double sided geometry so if you merge with all vertices
        #     selected then you will lose all the double sided geometry.
        #
        # Todo: Try to make more efficient
        #
        # model.vertices_merged: List[model_types.Vertex] = []
        # model.faces_merged_verts: List[model_types.Face] = []
        # face_counter = 0
        # face_counter_last_report = 0
        # for face in model.faces:
        #     new_face_poly = []
        #     for vert_index_old in face.poly:
        #         vert = model.vertices[vert_index_old]
        #         # check if duplicate exists
        #         vert_duplicate_found = -1
        #         for vert_index_new in range(len(model.vertices_merged)):
        #             if vert == model.vertices_merged[vert_index_new]:
        #                 vert_duplicate_found = vert_index_new
        #                 break
        #         if vert_duplicate_found >= 0:
        #             # Use existing Vertex
        #             new_face_poly.append(vert_duplicate_found)
        #         else:
        #             # Create a new Vertex
        #             new_face_poly.append(len(model.vertices_merged))
        #             model.vertices_merged.append(model.vertices[vert_index_old])
        #     new_face: model_types.Face = model_types.Face(new_face_poly, face.surface_index)
        #     model.faces_merged_verts.append(new_face)
        #     face_counter += 1
        #     if face_counter - face_counter_last_report > len(model.faces) / 100:
        #         print("Merging Verts: %i" % (face_counter / len(model.faces) * 100))
        #         face_counter_last_report = face_counter
        #
        # model.vertices = model.vertices_merged
        # model.faces = model.faces_merged_verts

        # CREATE BLENDER STUFF
        blender_mesh: bpy.types.Mesh = bpy.data.meshes.new(model.getName())
        blender_object: bpy.types.Object = bpy.data.objects.new(model.getName(), blender_mesh)

        # Armature
        hasArmature: bool = model.bones is not None
        if hasArmature:
            blender_armature: bpy.types.Armature = bpy.data.armatures.new(model.getName())
            blender_object_armature: bpy.types.Object = bpy.data.objects.new(model.getName() + " Armature", blender_armature)
            target_collection.objects.link(blender_object_armature)
            bpy.context.view_layer.objects.active = blender_object_armature
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            eb: bpy.types.ArmatureEditBones = blender_armature.edit_bones

            blender_bones = []  # Need this to reference bones added to Blender
            for B in model.bones:
                blender_bone: bpy.types.EditBone = eb.new(B.name)
                blender_bones.append(blender_bone)
                blender_bone.parent = blender_bones[B.parentid] if B.parentid >= 0 else None

                m: Matrix4f = B.transform
                blender_bone.head = (0.0, 0.0, 0.0)
                blender_bone.tail = (0.0, 0.02, 0.0)
                blender_bone.transform(m.toBlenderMatrix())

            bpy.ops.object.mode_set()
            blender_armature.display_type = 'STICK'

            blender_armature.show_names = False  # True
            blender_object_armature.show_in_front = True
            blender_armature.show_axes = True

        blender_bMesh: bmesh.types.BMesh = bmesh.new()
        blender_bMesh.from_mesh(blender_mesh)

        # Add Data to Face Loops (UV, Color)
        blender_bMesh_uvLayer = blender_bMesh.loops.layers.uv.new()
        blender_bMesh_colorLayer = blender_bMesh.loops.layers.color.new()
        if hasArmature:
            blender_bmesh_weight_layer = blender_bMesh.verts.layers.deform.new()

        # Create Vertices
        blender_bMesh_verts = []  # Need to access this to create faces
        for vertex_index in range(len(model.vertices)):
            blender_bMesh_verts.append(blender_bMesh.verts.new(model.vertices[vertex_index].position))
        blender_bMesh.verts.index_update()

        # Create Vertex Groups
        if model.bones.bones_by_id is not None:
            for current_bone_id in model.bones.bones_by_id:
                blender_object.vertex_groups.new(name=model.bones[current_bone_id].name)

        # Set Vertex Weights
        if hasArmature:
            for vert in blender_bMesh.verts:
                # print("Vertex: %s    Vertex Bone ID: %s   BoneWeight: %s" % (i, model.vertex_bones[i], model.vertex_bone_weights[i]))
                dvert = vert[blender_bmesh_weight_layer]
                for bone_weight_link in model.vertices[vert.index].boneWeights:
                    dvert[bone_weight_link.bone_id] = bone_weight_link.bone_weight

        # Create Faces
        # You can send any tuple size greater than 2
        # 3 makes a triangle, 4 makes a quad, 5+ makes n-gons
        # Although it seems that ISM2 files (so far) only use triangles
        # MOST do not reuse Vertices which is quite annoying. Every triangle will be disconnected.
        # Some DO reuse vertices which can produce a new problem. Double sided geometry causes an error in blender.
        error_faces: int = 0
        for face in model.faces:
            blender_face_loop = []
            for vertex_index in face.indices:  # Loops through the vertices in this Face Loop
                blender_face_loop.append(blender_bMesh_verts[vertex_index])  # Converts to Blender format
            # TODO This sometimes causes an error. I assume it is because the mesh contains double sided geometry. Blender doesn't like that.
            #  I have no good solution right now. For now the problem faces are ignored. Which also causes the custom normals to be discarded.
            try:
                blender_bMesh_face: bmesh.types.BMFace = blender_bMesh.faces.new(blender_face_loop)
            except:
                error_faces += 1
                nep_tools.serious_error_notify = True
                continue
            blender_bMesh_face.material_index = face.surface_index
            # Assign UV coords, Vertex Color, Materials, and Bone Weights
            for vertex_index, loop_vertex in enumerate(blender_bMesh_face.loops):  # Loops through the vertices in this Face Loop
                VI = face.indices[vertex_index]
                # UV coordinates
                loop_vertex[blender_bMesh_uvLayer].uv = model.vertices[VI].uv
                # Vertex Colors
                loop_vertex[blender_bMesh_colorLayer] = model.vertices[VI].rgba

        # Push BMesh to Mesh
        blender_bMesh.to_mesh(blender_mesh)
        blender_bMesh.free()

        if error_faces:
            print("\n:: SERIOUS ERROR :: Model '%s' had Geometry Error(s) - To save the model: %i faces AND all normals were discarded.\n" % (model.getName(), error_faces))
        else:
            # Some Mesh Data must be added after conversion from BMesh to Mesh

            # Assign Normals
            blender_mesh.use_auto_smooth = True
            # Set normal vectors to (0, 0, 0) to keep auto normal - Maybe implement this

            blender_normals: List[float] = []
            for face in model.faces:
                for vertex_index in face.indices:
                    n = model.vertices[vertex_index].normal
                    blender_normals.append(n)
            blender_mesh.normals_split_custom_set(blender_normals)
            # blender_mesh.normals_split_custom_set([c.normal for c in model.vertices])  # Old way - works with models that do not reuse vertices

        # Assign Materials (Use the surfaces to create Blender Materials)
        r = random.Random()

        def addMaterialToObject(material: Material, texture_directory: TextureDirectory, activate: bool):
            def isMaterialEqual(material: Material, texture_directory: TextureDirectory, blender_material_name: str) -> bool:
                if bpy.data.materials.find(blender_material_name) == -1: return False  # A Material by this name does not exist
                blender_material: bpy.types.Material = bpy.data.materials[blender_material_name]
                # IF any of these conditions fails THEN it is not a match
                if not blender_material.use_nodes: return False
                nodes: bpy.types.Nodes = blender_material.node_tree.nodes

                def isTextureMapEqual(node_name: str, image_filename: str) -> bool:
                    if nodes.find(node_name) == -1:  # Node does not exist
                        if image_filename is not None: return False  # Node should exist - Fail
                    else:  # Node does exist
                        N = nodes[node_name]
                        if N.image is None: return False  # Node has no image assigned - Fail
                        if N.image.filepath != os.path.join(texture_directory.path, "%s.png" % image_filename): return False  # Node lists a different file - Fail
                    return True

                if isTextureMapEqual("Diffuse Map", material.texture_diffuse_filename) \
                        and isTextureMapEqual("Specular Map", material.texture_specular_filename) \
                        and isTextureMapEqual("Emission Map", material.texture_emission_filename) \
                        and isTextureMapEqual("Normal Map", material.texture_normal_filename) \
                        and isTextureMapEqual("M Map", material.texture_cyangreen_filename):
                    return True

            # Determine the name to be used in Blender for this Material
            if texture_directory.name is not None:
                blender_material_name = "%s__%s" % (material.name, texture_directory.name)  # Material name followed by Location name
            else:
                blender_material_name = "%s" % material.name  # Material name

            blender_material: bpy.types.Material
            # IF a match is found THEN use existing material ELSE create new material
            if isMaterialEqual(material, texture_directory, blender_material_name):
                blender_material = bpy.data.materials[blender_material_name]
            else:
                blender_material = bpy.data.materials.new(blender_material_name)
                # blender_material.use_fake_user = True
                blender_material.diffuse_color = (r.random(), r.random(), r.random(), 1.0)
                blender_material.use_backface_culling = option_cull_back_facing
                blender_material.use_nodes = True

                nodes: bpy.types.Nodes = blender_material.node_tree.nodes
                node_bsdf: bpy.types.Node = nodes['Principled BSDF']
                links: bpy.types.NodeLinks = blender_material.node_tree.links

                baseNodeX: int = int(node_bsdf.location[0] - (700 if material.enable_vertex_coloring else 400))
                baseNodeY: int = int(node_bsdf.location[1] + 200)

                # UVMap
                nodes_uvmap: bpy.types.Node = nodes.new('ShaderNodeUVMap')
                nodes_uvmap.name = "UV Map"
                nodes_uvmap.label = "UV Map"
                # nodes_uvmap.uv_map = blender_bMesh_uvLayer
                nodes_uvmap.location = (node_bsdf.location[0] - (1000 if material.enable_vertex_coloring else 700), node_bsdf.location[1])

                # Vertex Color
                if material.enable_vertex_coloring:
                    nodes_mix_vertex_color: bpy.types.Node = nodes.new('ShaderNodeMixRGB')
                    nodes_mix_vertex_color.name = "Vertex Shading"
                    nodes_mix_vertex_color.label = "Vertex Shading"
                    nodes_mix_vertex_color.blend_type = 'MULTIPLY'
                    nodes_mix_vertex_color.inputs['Fac'].default_value = 1.0
                    nodes_mix_vertex_color.inputs['Color1'].default_value = (1.0, 1.0, 1.0, 1.0)
                    nodes_mix_vertex_color.inputs['Color2'].default_value = (1.0, 1.0, 1.0, 1.0)
                    nodes_mix_vertex_color.location = (node_bsdf.location[0] - 200, node_bsdf.location[1] + 140)
                    links.new(nodes_mix_vertex_color.outputs['Color'], node_bsdf.inputs['Base Color'])

                    nodes_vertex_color: bpy.types.Node = nodes.new('ShaderNodeVertexColor')
                    nodes_vertex_color.name = "Vertex Color"
                    nodes_vertex_color.label = "Vertex Color"
                    nodes_vertex_color.location = (node_bsdf.location[0] - 400, node_bsdf.location[1] - 5)
                    links.new(nodes_vertex_color.outputs['Color'], nodes_mix_vertex_color.inputs['Color2'])

                # Diffuse Map
                if material.texture_diffuse_filename is not None:
                    nodes_texture_diffuse: bpy.types.Node = nodes.new('ShaderNodeTexImage')
                    nodes_texture_diffuse.name = "Diffuse Map"  # Diffuse Texture Name
                    nodes_texture_diffuse.label = "Diffuse Map"  # Diffuse Texture Name
                    nodes_texture_diffuse.location = (baseNodeX, baseNodeY)
                    F = os.path.join(texture_directory.path, "%s.png" % material.texture_diffuse_filename)  # Filepath of image to add to blender
                    if os.path.isfile(F):
                        nodes_texture_diffuse.image = bpy.data.images.load(filepath=F, check_existing=True)
                    if material.enable_vertex_coloring:
                        links.new(nodes_texture_diffuse.outputs['Color'], nodes_mix_vertex_color.inputs['Color1'])
                    else:
                        links.new(nodes_texture_diffuse.outputs[0], node_bsdf.inputs['Base Color'])
                    links.new(nodes_uvmap.outputs['UV'], nodes_texture_diffuse.inputs['Vector'])

                # Specular Map
                if material.texture_specular_filename is not None:
                    nodes_texture_specular: bpy.types.Node = nodes.new('ShaderNodeTexImage')
                    nodes_texture_specular.name = "Specular Map"  # Diffuse Texture Name
                    nodes_texture_specular.label = "Specular Map"  # Diffuse Texture Name
                    nodes_texture_specular.location = (baseNodeX, baseNodeY - 300)
                    F = os.path.join(texture_directory.path, "%s.png" % material.texture_diffuse_filename)  # Filepath of image to add to blender
                    if os.path.isfile(F):
                        nodes_texture_specular.image = bpy.data.images.load(filepath=F, check_existing=True)
                    links.new(nodes_texture_specular.outputs[0], node_bsdf.inputs['Specular'])
                    links.new(nodes_uvmap.outputs['UV'], nodes_texture_specular.inputs['Vector'])

                # Emission Map
                if material.texture_emission_filename is not None:
                    nodes_texture_emission: bpy.types.Node = nodes.new('ShaderNodeTexImage')
                    nodes_texture_emission.name = "Emission Map"  # Diffuse Texture Name
                    nodes_texture_emission.label = "Emission Map"  # Diffuse Texture Name
                    nodes_texture_emission.location = (baseNodeX, baseNodeY - 600)
                    F = os.path.join(texture_directory.path, "%s.png" % material.texture_emission_filename)  # Filepath of image to add to blender
                    if os.path.isfile(F):
                        nodes_texture_emission.image = bpy.data.images.load(filepath=F, check_existing=True)
                    links.new(nodes_texture_emission.outputs[0], node_bsdf.inputs['Emission'])
                    links.new(nodes_uvmap.outputs['UV'], nodes_texture_emission.inputs['Vector'])

                # Normal Map
                if material.texture_normal_filename is not None:
                    nodes_texture_normal: bpy.types.Node = nodes.new('ShaderNodeTexImage')
                    nodes_texture_normal.name = "Normal Map"  # Diffuse Texture Name
                    nodes_texture_normal.label = "Normal Map"  # Diffuse Texture Name
                    nodes_texture_normal.location = (baseNodeX, baseNodeY - 900)
                    F = os.path.join(texture_directory.path, "%s.png" % material.texture_normal_filename)  # Filepath of image to add to blender
                    if os.path.isfile(F):
                        nodes_texture_normal.image = bpy.data.images.load(filepath=F, check_existing=True)
                    links.new(nodes_texture_normal.outputs[0], node_bsdf.inputs['Normal'])
                    links.new(nodes_uvmap.outputs['UV'], nodes_texture_normal.inputs['Vector'])

                # # 'M' Map (I dont know what this is)
                if material.texture_cyangreen_filename is not None:
                    nodes_texture_cyangreen: bpy.types.Node = nodes.new('ShaderNodeTexImage')
                    nodes_texture_cyangreen.name = "M Map"  # Diffuse Texture Name
                    nodes_texture_cyangreen.label = "M Map"  # Diffuse Texture Name
                    nodes_texture_cyangreen.location = (baseNodeX, baseNodeY - 1200)
                    F = os.path.join(texture_directory.path, "%s.png" % material.texture_cyangreen_filename)  # Filepath of image to add to blender
                    if os.path.isfile(F):
                        nodes_texture_cyangreen.image = bpy.data.images.load(filepath=F, check_existing=True)
                    # links.new(nodes_texture_cyangreen.outputs[0], node_bsdf.inputs['I_DONT_KNOW'])
                    links.new(nodes_uvmap.outputs['UV'], nodes_texture_cyangreen.inputs['Vector'])

            if activate:
                blender_mesh.materials.append(blender_material)

        # IF surfaces exist THEN add materials by surface. - More complex models rely on the surface to point to the correct material.
        # The order that surfaces are added are always correct whereas materials are not. Luckily each surface points the correct material.
        active_texture_directory_index: int = int(r.random() * len(model.texture_directories))
        for texture_directory_index, texture_directory in enumerate(model.texture_directories):  # There should always be at least one location
            if len(model.surfaces) > 0:
                for S in model.surfaces:
                    if 0 <= S.material_index < len(model.materials):  # IF surface pointer points outside of the range of materials THEN do not add material (pointer is -1 when no material should be used)
                        addMaterialToObject(model.materials[S.material_index], texture_directory, active_texture_directory_index == texture_directory_index)
            else:
                for M in model.materials:  # TODO handle a zero material count (I get an IndexOutOfRange for 'active_mat_location_index' sometimes)
                    addMaterialToObject(M, texture_directory, active_texture_directory_index == texture_directory_index)

        # Place in Scene
        if hasArmature:
            blender_object_armature.location = option_import_location
        target_collection.objects.link(blender_object)
        bpy.ops.object.mode_set()
        if hasArmature:
            blender_object.parent = blender_object_armature
            blender_object.modifiers.new(name="Armature", type='ARMATURE').object = blender_object_armature

        # Bounding Boxes
        if model.bounding_box is not None:
            def create_bb(name: str, bb: BoundingBox):
                blender_mesh_bb: bpy.types.Mesh = bpy.data.meshes.new(name)
                blender_object_bb: bpy.types.Object = bpy.data.objects.new(name, blender_mesh_bb)
                blender_bMesh_bb: bmesh.types.BMesh = bmesh.new()
                blender_bMesh_bb.from_mesh(blender_mesh_bb)

                blender_bMesh_bb_verts = []
                verts = bb.get_verts()
                for vert in verts:
                    blender_bMesh_bb_verts.append(blender_bMesh_bb.verts.new(vert))
                blender_bMesh_bb.verts.index_update()

                faces = bb.get_quads()
                for face in faces:
                    blender_face_loop = []
                    for vert in face:
                        blender_face_loop.append(blender_bMesh_bb_verts[vert])
                    blender_bMesh_bb.faces.new(blender_face_loop)
                blender_bMesh_bb.to_mesh(blender_mesh_bb)
                blender_bMesh_bb.free()
                blender_object_bb.color = (r.random(), r.random(), r.random(), 0.9)
                blender_object_bb.display_type = 'BOUNDS'
                blender_object_bb.parent = blender_object
                target_collection.objects.link(blender_object_bb)

            create_bb(model.getName() + "_BoundingBox", model.bounding_box)
            for S in model.surfaces:
                create_bb(model.getName() + "_" + S.name + "_BoundingBox", S.bounding_box)

        # Face ANM Data
        if model.face_anm is not None:
            if nep_tools.debug:
                print(model.face_anm)
            text_block: bpy.types.Text = bpy.data.texts.new(model.getName() + "_face.anm")
            text_block.from_string(model.face_anm)

        # Todo: Motion
        # if model.motions is not None:
        #     # TODO determine what rotation_method ISM2 used and then apply it to the bones upon creation of those bones.
        #     for motion in model.motions:
        #         action: bpy.types.Action = bpy.data.actions.new(motion.name)
        #         action.frame_range = (0, motion.duration)
        #         for bone in motion.motion_bones:
        #             fcx: bpy.types.FCurve = action.fcurves.new(datapath="pose.bones[\"%s\"]" % bone.bone_name, index=0)
        #             fcy: bpy.types.FCurve = action.fcurves.new(datapath="pose.bones[\"%s\"]" % bone.bone_name, index=1)
        #             fcz: bpy.types.FCurve = action.fcurves.new(datapath="pose.bones[\"%s\"]" % bone.bone_name, index=2)
        #             kp: bpy.types.Keyframe
        #             # fcx.keyframe_points.add()
        #     pass
