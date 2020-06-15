from typing import List

import os
import random

import bpy
import bmesh

import blender_neptools
from blender_neptools.matrix4f import Matrix4f


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
        self.count: int = count
        self.bones_by_id: [] = [-1] * count

    def __str__(self) -> str:
        return "Count: %i" % self.count

    def append(self, b: Bone) -> None:
        super().append(b)
        if b.bone_id >= 0:
            self.bones_by_id[b.bone_id] = b.bone_index

    def trim(self):
        i = len(self.bones_by_id) - 1
        while self.bones_by_id[i] < 0:
            i -= 1
        self.bones_by_id = self.bones_by_id[0:i + 1]

    def get_by_id(self, bone_id: int) -> Bone:
        if bone_id < 0 or bone_id >= len(self.bones_by_id):
            print("OOR: %s" % bone_id)
        return self[self.bones_by_id[bone_id]]


class BoneWeight:
    def __init__(self, bone_id: int, bone_weight: float) -> None:
        super().__init__()
        self.bone_id = bone_id
        self.bone_weight = bone_weight

    def __str__(self) -> str:
        return "%i, %.3f" % (self.bone_id, self.bone_weight)


class Texture:
    def __init__(self, name: str, name2: str, filepath: str, filename: str) -> None:
        super().__init__()
        self.name = name
        self.name2 = name2
        self.filepath = filepath
        self.filename = filename

    def __str__(self) -> str:
        return "    Texture(%s, %s, %s, %s)" % (self.name.ljust(8), self.name2.ljust(8), self.filepath.ljust(55), self.filename)


class Material:
    def __init__(self, name: str, texture_name: str, texture_path: str) -> None:
        super().__init__()
        self.name = name
        self.texture_name = texture_name
        self.texture_path = texture_path

    def __str__(self) -> str:
        return "Material(%s, %s)" % (self.name, self.texture_name)


class Surface:
    def __init__(self, name: str, material_index: int) -> None:
        super().__init__()
        self.name = name
        self.material = material_index
        self.bounding_box: BoundingBox = None

    def __str__(self) -> str:
        return "Surface(%s,  %s)" % (self.name, self.material.__str__())


class Vertex:
    def __init__(self, x: float, y: float, z: float, u: float, v: float, r: float, g: float, b: float, a: float, nx: float, ny: float, nz: float) -> None:
        # This is able to have a second set of Normals - though, I do not know for what purpose
        super().__init__()
        self.position = (x, y, z)
        self.uv = (u, v)
        self.rgba = (r, g, b, a)
        self.normal = (nx, ny, nz)
        self.boneWeights: list[BoneWeight,] = []


class Face:
    def __init__(self, indices: (), surface_index: int) -> None:
        super().__init__()
        self.indices: (int,) = indices  # indices
        self.surface_index: int = surface_index


class FaceAnm:
    def __init__(self, face_anm: str) -> None:
        super().__init__()
        self.face_anm: str = face_anm  # TODO for now just a simple long string


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
    def __init__(self) -> None:
        super().__init__()

        # Buffers
        self.strings: List[str] = []
        self.armature_name: str = ""
        self.bones: Bones
        self.textures: List[Texture] = []
        self.materials: List[Material] = []
        self.surfaces: List[Surface] = []
        self.vertices: List[Vertex] = []
        self.faces: List[Face] = []
        self.bounding_box: BoundingBox = None
        self.face_anm: FaceAnm = None
        self.motions: List[Motion] = []

    def getName(self):
        return self.armature_name


def to_blender(model: PreBlender_Model,
               option_cull_back_facing: bool = True,
               option_merge_vertices: bool = False,
               option_import_location=(0, 0, 0)):
    # TODO Merge Vertices if option is enabled - Process Heavy    (This, maybe, should move to the Model class)
    #   The goal here is to merge as much as possible while saving the double sided geometry.
    #   A method I use in Blender is to select UV islands then perform a merge on those vertices.
    #   Blender does not actually support double sided geometry so if you merge with all vertices
    #     selected then you will lose all the double sided geometry.
    # TODO Try to make more efficient
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
    blender_armature: bpy.types.Armature = bpy.data.armatures.new(model.getName())
    blender_object_armature: bpy.types.Object = bpy.data.objects.new(model.getName() + " Armature", blender_armature)
    bpy.context.scene.collection.objects.link(blender_object_armature)
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
    # TODO
    blender_armature.show_names = False  # True
    blender_object_armature.show_in_front = True
    blender_armature.show_axes = True

    blender_bMesh: bmesh.types.BMesh = bmesh.new()
    blender_bMesh.from_mesh(blender_mesh)

    #
    # Add Data to Face Loops (UV, Color)
    blender_bMesh_uvLayer = blender_bMesh.loops.layers.uv.new()
    blender_bMesh_colorLayer = blender_bMesh.loops.layers.color.new()
    blender_bmesh_weight_layer = blender_bMesh.verts.layers.deform.new()

    # Create Vertices
    blender_bMesh_verts = []  # Need to access this to create faces
    for vertex_index in range(len(model.vertices)):
        blender_bMesh_verts.append(blender_bMesh.verts.new(model.vertices[vertex_index].position))
    blender_bMesh.verts.index_update()

    # Create Vertex Groups
    for current_bone_id in model.bones.bones_by_id:
        blender_object.vertex_groups.new(name=model.bones[current_bone_id].name)

    # Set Vertex Weights
    for vert in blender_bMesh.verts:
        # print("Vertex: %s    Vertex Bone ID: %s   BoneWeight: %s" % (i, model.vertex_bones[i], model.vertex_bone_weights[i]))
        dvert = vert[blender_bmesh_weight_layer]
        for bone_weight_link in model.vertices[vert.index].boneWeights:
            dvert[bone_weight_link.bone_id] = bone_weight_link.bone_weight

    # TODO Smoothing Groups ?? Do I need ??

    # Create Faces
    # I think you can send any tuple size greater than 2
    # 3 makes a triangle, 4 makes a quad, 5+ makes n-gons
    # Although it seems that ISM2 files (so far) only use triangles
    #   They also do not reuse Vertices which is quite annoying. Every triangle will be disconnected.
    for face in model.faces:
        blender_face_loop = []
        for vertex_index in face.indices:  # Loops through the vertices in this Face Loop
            blender_face_loop.append(blender_bMesh_verts[vertex_index])  # Converts to Blender format
        blender_bMesh_face: bmesh.types.BMFace = blender_bMesh.faces.new(blender_face_loop)
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

    # Some Mesh Data must be added after conversion to Mesh from BMesh

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

    # TODO There is more to these shaders but this is all I am doing for now
    # Assign Materials (Use the surfaces to create Blender Materials)
    blender_images: List[bpy.types.Image] = bpy.data.images
    r = random.Random()
    if blender_neptools.debug:
        for surface in model.surfaces:
            print(surface)
    for surface in model.surfaces:
        material: bpy.types.Material = bpy.data.materials.new("%s__%s" % (model.materials[surface.material].name, surface.name))
        material.diffuse_color = (r.random(), r.random(), r.random(), 1.0)
        material.use_backface_culling = option_cull_back_facing
        material.use_nodes = True

        nodes: bpy.types.Nodes = material.node_tree.nodes
        node_bsdf: bpy.types.Node = nodes['Principled BSDF']

        if len(model.materials) > 0:  # IF option_load_textures
            nodes_texture_diffuse: bpy.types.Node = nodes.new('ShaderNodeTexImage')
            nodes_texture_diffuse.label = model.materials[surface.material].texture_name  # Diffuse Texture Name
            nodes_texture_diffuse.location = (node_bsdf.location[0] - nodes_texture_diffuse.width - 50, node_bsdf.location[1])

            F = model.materials[surface.material].texture_path  # Filepath of image to add to blender
            if os.path.isfile(F):
                found_image: bool = False
                for bimage in bpy.data.images:  # Check if image with this filepath already exists in blender
                    if F == bimage.filepath:
                        nodes_texture_diffuse.image = bimage
                        found_image = True
                        break
                if not found_image:  # IF image not found THEN add image
                    nodes_texture_diffuse.image = bpy.data.images.load(filepath=F)
            links: bpy.types.NodeLinks = material.node_tree.links
            links.new(nodes_texture_diffuse.outputs[0], node_bsdf.inputs['Base Color'])

        blender_mesh.materials.append(material)

    # Place in Scene
    blender_object_armature.location = option_import_location
    bpy.context.scene.collection.objects.link(blender_object)
    bpy.ops.object.mode_set()
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
            bpy.context.scene.collection.objects.link(blender_object_bb)

        create_bb(model.getName() + "_BoundingBox", model.bounding_box)
        for surface in model.surfaces:
            create_bb(model.getName() + "_" + surface.name + "_BoundingBox", surface.bounding_box)

    # Face ANM Data
    if model.face_anm is not None:  # IF option_parse_face_anims
        if blender_neptools.debug:
            print(model.face_anm)
        if model.face_anm is not None:
            text_block: bpy.types.Text = bpy.data.texts.new(model.getName() + "_face.anm")
            text_block.from_string(model.face_anm)

    # Motion
    if model.motions is not None:
        # TODO determine what rotation mode ISM2 used and them apply it to the bone upon creation of those bones.
        for motion in model.motions:
            action: bpy.types.Action = bpy.data.actions.new(motion.name)
            action.frame_range = (0, motion.duration)
            for bone in motion.motion_bones:
                fcx: bpy.types.FCurve = action.fcurves.new(datapath="pose.bones[\"%s\"]" % bone.bone_name, index=0)
                fcy: bpy.types.FCurve = action.fcurves.new(datapath="pose.bones[\"%s\"]" % bone.bone_name, index=1)
                fcz: bpy.types.FCurve = action.fcurves.new(datapath="pose.bones[\"%s\"]" % bone.bone_name, index=2)
                kp: bpy.types.Keyframe
                fc.keyframe_points.append()
        pass
