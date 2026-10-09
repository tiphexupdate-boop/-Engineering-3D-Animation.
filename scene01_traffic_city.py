"""
Scene 1 V2: Premium cinematic traffic-wave animation
Topic: Why Traffic Jams Happen Without an Accident

Compatible target: Blender 4.5 LTS
No add-ons / external assets required.

Designed for your existing GitHub workflow:
- Builds an editable .blend scene
- Saves to ~/Documents/EngineeringChannel/Scene01_TrafficMystery.blend
- render_for_ci.py can remain unchanged

Format:
- 9:16 vertical
- 8 seconds
- 24 FPS
- 192 frames
"""

import bpy
import math
import os
import random
from mathutils import Vector, Euler

# =========================================================
# 0) GLOBAL SETTINGS
# =========================================================
PREVIEW = True
FPS = 24
DURATION_SECONDS = 8
FRAME_END = FPS * DURATION_SECONDS
RES_X, RES_Y = 720, 1280
random.seed(42)

HOME = os.path.expanduser("~")
PROJECT = os.path.join(HOME, "Documents", "EngineeringChannel")
FRAME_DIR = os.path.join(PROJECT, "Scene01_Frames")
os.makedirs(FRAME_DIR, exist_ok=True)

# =========================================================
# 1) CLEAN START
# =========================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Remove orphan data blocks to keep scene tidy
for block_collection in (
    bpy.data.meshes,
    bpy.data.materials,
    bpy.data.curves,
    bpy.data.cameras,
    bpy.data.lights,
    bpy.data.worlds,
):
    for block in list(block_collection):
        if block.users == 0:
            block_collection.remove(block)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.fps = FPS
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 60 if PREVIEW else 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.render.filepath = os.path.join(FRAME_DIR, 'scene01_')
scene.render.film_transparent = False

# Use EEVEE for authoring scene; render_for_ci.py will switch to Cycles on CPU
engine_ids = {e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items}
if 'BLENDER_EEVEE_NEXT' in engine_ids:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
elif 'BLENDER_EEVEE' in engine_ids:
    scene.render.engine = 'BLENDER_EEVEE'
else:
    raise RuntimeError("EEVEE unavailable. Use Blender 4.5 LTS.")

if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 32 if not PREVIEW else 16

try:
    scene.view_settings.view_transform = 'AgX'
except Exception:
    pass

# =========================================================
# 2) HELPERS
# =========================================================
def set_origin_to_geometry(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.select_set(False)

def add_bevel(obj, width=0.03, segments=2):
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = width
    mod.segments = segments
    if hasattr(mod, "affect"):
        mod.affect = 'EDGES'
    return mod

def make_principled_material(name, base_color=(0.8, 0.8, 0.8, 1.0), metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.name = "Principled"
    bsdf.inputs['Base Color'].default_value = base_color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness

    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def make_emission_material(name, color=(1, 1, 1, 1), strength=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    em = nodes.new('ShaderNodeEmission')
    em.name = "Glow"
    em.inputs['Color'].default_value = color
    em.inputs['Strength'].default_value = strength

    links.new(em.outputs['Emission'], out.inputs['Surface'])
    return mat

def assign_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def cube(name, location=(0, 0, 0), scale=(1, 1, 1), material=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2.0, scale[1] / 2.0, scale[2] / 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        assign_material(obj, material)
    if bevel > 0:
        add_bevel(obj, width=bevel, segments=2)
    return obj

def plane(name, location=(0, 0, 0), size=1.0, material=None, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if material:
        assign_material(obj, material)
    return obj

def cylinder(name, location=(0, 0, 0), radius=0.25, depth=1.0, rotation=(0, 0, 0), material=None, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        assign_material(obj, material)
    return obj

def curve_line(name, coords, material, thickness=0.03):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 8
    curve.bevel_depth = thickness
    curve.bevel_resolution = 4
    spline = curve.splines.new('POLY')
    spline.points.add(len(coords) - 1)
    for p, co in zip(spline.points, coords):
        p.co = (*co, 1.0)

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, material)
    return obj

def smooth_object(obj):
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth()
        obj.select_set(False)

def add_area_light(name, location, rotation, power, color, size=5.0):
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.energy = power
    light_data.color = color
    light_data.shape = 'RECTANGLE'
    light_data.size = size
    light_data.size_y = size * 0.55

    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    light_obj.rotation_euler = rotation
    return light_obj

def add_point_light(name, location, power, color, radius=0.25):
    light_data = bpy.data.lights.new(name=name, type='POINT')
    light_data.energy = power
    light_data.color = color
    light_data.shadow_soft_size = radius
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    return light_obj

# =========================================================
# 3) MATERIALS
# =========================================================
ROAD_MAT = make_principled_material(
    "Road_Asphalt",
    base_color=(0.035, 0.042, 0.056, 1.0),
    metallic=0.0,
    roughness=0.82,
)

ROAD_SHOULDER = make_principled_material(
    "Road_Shoulder",
    base_color=(0.06, 0.072, 0.09, 1.0),
    metallic=0.0,
    roughness=0.74,
)

SIDEWALK_MAT = make_principled_material(
    "Sidewalk",
    base_color=(0.10, 0.11, 0.125, 1.0),
    metallic=0.0,
    roughness=0.78,
)

GROUND_MAT = make_principled_material(
    "Ground_Midnight",
    base_color=(0.015, 0.022, 0.038, 1.0),
    metallic=0.0,
    roughness=0.95,
)

LANE_WHITE = make_principled_material(
    "Lane_White",
    base_color=(0.82, 0.86, 0.90, 1.0),
    metallic=0.0,
    roughness=0.45,
)

TEAL_GLOW = make_emission_material(
    "Teal_Glow",
    color=(0.06, 0.88, 1.0, 1.0),
    strength=2.8
)

RED_GLOW = make_emission_material(
    "Red_Glow",
    color=(1.0, 0.10, 0.06, 1.0),
    strength=4.2
)

ORANGE_GLOW = make_emission_material(
    "Orange_Glow",
    color=(1.0, 0.45, 0.18, 1.0),
    strength=2.4
)

WINDOW_BLUE = make_emission_material(
    "Window_Blue",
    color=(0.18, 0.82, 1.0, 1.0),
    strength=0.85
)

WINDOW_WARM = make_emission_material(
    "Window_Warm",
    color=(1.0, 0.55, 0.22, 1.0),
    strength=0.75
)

GLASS_MAT = make_principled_material(
    "Glass_Dark",
    base_color=(0.05, 0.12, 0.18, 1.0),
    metallic=0.0,
    roughness=0.08,
)

WHEEL_MAT = make_principled_material(
    "Rubber",
    base_color=(0.015, 0.015, 0.018, 1.0),
    metallic=0.0,
    roughness=0.92,
)

HEADLIGHT_MAT_BASE = make_emission_material(
    "Headlight_Base",
    color=(0.92, 0.97, 1.0, 1.0),
    strength=3.0
)

BRAKELIGHT_MAT_BASE = make_emission_material(
    "Brakelight_Base",
    color=(1.0, 0.06, 0.03, 1.0),
    strength=1.0
)

CAR_COLORS = [
    (0.18, 0.23, 0.28, 1.0),
    (0.30, 0.34, 0.38, 1.0),
    (0.11, 0.19, 0.28, 1.0),
    (0.38, 0.14, 0.15, 1.0),
    (0.42, 0.42, 0.40, 1.0),
    (0.14, 0.16, 0.20, 1.0),
]

BUILDING_COLORS = [
    (0.06, 0.09, 0.12, 1.0),
    (0.05, 0.08, 0.11, 1.0),
    (0.08, 0.10, 0.14, 1.0),
    (0.04, 0.07, 0.10, 1.0),
]

# =========================================================
# 4) WORLD / FOG / ATMOSPHERE
# =========================================================
world = bpy.data.worlds.new("Grasumstudio_Night")
scene.world = world
world.use_nodes = True

bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.008, 0.014, 0.030, 1.0)
bg.inputs["Strength"].default_value = 0.75

# =========================================================
# 5) CITY BASE / ROAD
# =========================================================
# Big base
cube("Ground_Base", location=(0, 0, -0.4), scale=(90, 150, 0.8), material=GROUND_MAT)

# Main road
cube("Main_Road", location=(0, 0, 0.02), scale=(10.8, 118, 0.08), material=ROAD_MAT)
cube("Road_Shoulder_L", location=(-5.45, 0, 0.04), scale=(0.95, 118, 0.10), material=ROAD_SHOULDER)
cube("Road_Shoulder_R", location=(5.45, 0, 0.04), scale=(0.95, 118, 0.10), material=ROAD_SHOULDER)

# Sidewalks
cube("Sidewalk_L", location=(-7.05, 0, 0.12), scale=(2.2, 118, 0.24), material=SIDEWALK_MAT)
cube("Sidewalk_R", location=(7.05, 0, 0.12), scale=(2.2, 118, 0.24), material=SIDEWALK_MAT)

# Lane divider dashes
for y in range(-52, 56, 7):
    cube(f"Dash_{y}", location=(0, y, 0.07), scale=(0.16, 3.2, 0.015), material=LANE_WHITE)

# Outer line markers
for x in (-3.45, 3.45):
    for y in range(-56, 56, 8):
        cube(f"OuterDash_{x}_{y}", location=(x, y, 0.07), scale=(0.10, 4.0, 0.012), material=LANE_WHITE)

# Teal road-edge strips
edge_left = curve_line(
    "Road_Edge_Left",
    [(-4.75, -56, 0.10), (-4.75, 56, 0.10)],
    TEAL_GLOW,
    thickness=0.032
)
edge_right = curve_line(
    "Road_Edge_Right",
    [(4.75, -56, 0.10), (4.75, 56, 0.10)],
    TEAL_GLOW,
    thickness=0.032
)

# =========================================================
# 6) BUILDINGS
# =========================================================
def create_building(name, x, y, width, depth, height):
    mat = make_principled_material(
        f"{name}_BodyMat",
        base_color=random.choice(BUILDING_COLORS),
        metallic=0.08,
        roughness=0.52,
    )
    building = cube(name, location=(x, y, height / 2.0 + 0.12), scale=(width, depth, height), material=mat, bevel=0.08)

    # Windows on face toward road
    side_sign = -1 if x > 0 else 1
    face_x = x + side_sign * (width / 2.0 + 0.03)

    rows = max(3, int(height // 2.3))
    cols = max(2, int(depth // 1.8))
    z_start = 1.6
    y_start = y - depth / 2.0 + 0.8

    for r in range(rows):
        z = z_start + r * 2.0
        if z > height - 1.0:
            continue
        for c in range(cols):
            yy = y_start + c * 1.55
            if yy > y + depth / 2.0 - 0.7:
                continue
            if random.random() < 0.18:
                continue
            wmat = WINDOW_WARM if random.random() < 0.16 else WINDOW_BLUE
            win = cube(
                f"{name}_win_{r}_{c}",
                location=(face_x, yy, z),
                scale=(0.05, 0.8, 0.55),
                material=wmat
            )
            building.select_set(False)
            win.parent = building
            win.matrix_parent_inverse = building.matrix_world.inverted()

    return building

# Left side blocks
for idx, y in enumerate(range(-42, 48, 12)):
    create_building(f"L_Build_A_{idx}", x=-14.5, y=y, width=7.0, depth=8.0, height=random.uniform(11, 24))
    create_building(f"L_Build_B_{idx}", x=-23.5, y=y + random.uniform(-2, 2), width=8.0, depth=9.0, height=random.uniform(13, 26))

# Right side blocks
for idx, y in enumerate(range(-40, 50, 12)):
    create_building(f"R_Build_A_{idx}", x=14.5, y=y, width=7.2, depth=8.2, height=random.uniform(12, 25))
    create_building(f"R_Build_B_{idx}", x=24.0, y=y + random.uniform(-2, 2), width=8.2, depth=9.0, height=random.uniform(14, 28))

# Foreground mass blocks to add depth
cube("Foreground_Block_L", location=(-18, -54, 4), scale=(10, 14, 8), material=make_principled_material("FG_L", (0.04, 0.05, 0.07, 1), 0.03, 0.7))
cube("Foreground_Block_R", location=(19, -50, 5), scale=(12, 16, 10), material=make_principled_material("FG_R", (0.05, 0.06, 0.08, 1), 0.03, 0.7))

# =========================================================
# 7) STREETLIGHTS
# =========================================================
def create_streetlight(name, x, y, side=1):
    pole = cylinder(name + "_Pole", location=(x, y, 2.0), radius=0.06, depth=4.0, material=make_principled_material(name + "_PoleMat", (0.20, 0.22, 0.25, 1), 0.2, 0.45))
    arm = cube(name + "_Arm", location=(x + 0.45 * side, y, 3.8), scale=(0.9, 0.08, 0.08), material=make_principled_material(name + "_ArmMat", (0.22, 0.23, 0.27, 1), 0.2, 0.45))
    lamp = cube(name + "_Lamp", location=(x + 0.85 * side, y, 3.65), scale=(0.22, 0.18, 0.12), material=ORANGE_GLOW)
    arm.parent = pole
    lamp.parent = pole
    lamp.matrix_parent_inverse = pole.matrix_world.inverted()
    arm.matrix_parent_inverse = pole.matrix_world.inverted()

    add_point_light(name + "_Light", location=(x + 0.9 * side, y, 3.35), power=350, color=(1.0, 0.78, 0.62), radius=0.45)
    return pole

for y in range(-46, 48, 14):
    create_streetlight(f"SL_L_{y}", x=-6.0, y=y, side=1)
    create_streetlight(f"SL_R_{y}", x=6.0, y=y + 6, side=-1)

# =========================================================
# 8) VEHICLE CREATION
# =========================================================
def create_car_material(name, color):
    return make_principled_material(name, base_color=color, metallic=0.35, roughness=0.28)

def create_car(name, x, y, body_color):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0)

    body_mat = create_car_material(name + "_BodyMat", body_color)
    brake_mat_l = BRAKELIGHT_MAT_BASE.copy()
    brake_mat_l.name = name + "_BrakeMat_L"
    brake_mat_r = BRAKELIGHT_MAT_BASE.copy()
    brake_mat_r.name = name + "_BrakeMat_R"
    head_mat_l = HEADLIGHT_MAT_BASE.copy()
    head_mat_l.name = name + "_HeadMat_L"
    head_mat_r = HEADLIGHT_MAT_BASE.copy()
    head_mat_r.name = name + "_HeadMat_R"

    # Body
    body = cube(name + "_Body", location=(0, 0, 0.42), scale=(1.24, 2.72, 0.42), material=body_mat, bevel=0.08)
    roof = cube(name + "_Roof", location=(0, -0.08, 0.77), scale=(0.96, 1.40, 0.34), material=GLASS_MAT, bevel=0.07)
    hood = cube(name + "_Hood", location=(0, 0.72, 0.36), scale=(1.10, 0.72, 0.18), material=body_mat, bevel=0.06)
    trunk = cube(name + "_Trunk", location=(0, -0.92, 0.38), scale=(1.10, 0.50, 0.16), material=body_mat, bevel=0.06)

    # Wheels
    wheels = []
    wheel_positions = [(-0.56, 0.74, 0.22), (0.56, 0.74, 0.22), (-0.56, -0.74, 0.22), (0.56, -0.74, 0.22)]
    for i, pos in enumerate(wheel_positions):
        wheel = cylinder(
            name + f"_Wheel_{i}",
            location=pos,
            radius=0.23,
            depth=0.18,
            rotation=(math.radians(90), 0, 0),
            material=WHEEL_MAT,
            vertices=20
        )
        smooth_object(wheel)
        wheels.append(wheel)

    # Windshield panels
    windshield = plane(
        name + "_Windshield",
        location=(0, 0.48, 0.67),
        size=0.62,
        material=GLASS_MAT,
        rotation=(math.radians(69), 0, 0)
    )
    rear_glass = plane(
        name + "_RearGlass",
        location=(0, -0.56, 0.66),
        size=0.54,
        material=GLASS_MAT,
        rotation=(math.radians(112), 0, 0)
    )

    # Headlights
    h1 = cube(name + "_HeadL", location=(-0.30, 1.37, 0.36), scale=(0.18, 0.06, 0.10), material=head_mat_l)
    h2 = cube(name + "_HeadR", location=(0.30, 1.37, 0.36), scale=(0.18, 0.06, 0.10), material=head_mat_r)

    # Brake lights
    b1 = cube(name + "_BrakeL", location=(-0.30, -1.37, 0.39), scale=(0.18, 0.06, 0.10), material=brake_mat_l)
    b2 = cube(name + "_BrakeR", location=(0.30, -1.37, 0.39), scale=(0.18, 0.06, 0.10), material=brake_mat_r)

    parts = [body, roof, hood, trunk, windshield, rear_glass, h1, h2, b1, b2] + wheels
    for part in parts:
        part.parent = root
        part.matrix_parent_inverse = root.matrix_world.inverted()

    return {
        "root": root,
        "brakes": [brake_mat_l, brake_mat_r],
    }

def keyframe_brake_materials(brake_mats, keyframes):
    for mat in brake_mats:
        node = mat.node_tree.nodes["Glow"]
        inp = node.inputs["Strength"]
        for frame, value in keyframes:
            inp.default_value = value
            inp.keyframe_insert("default_value", frame=frame)

def animate_car_y(root_obj, start_y, points):
    """
    points: list of (frame, y_position)
    """
    root_obj.location.y = start_y
    root_obj.keyframe_insert(data_path="location", frame=1)
    for frame, y in points:
        root_obj.location.y = y
        root_obj.keyframe_insert(data_path="location", frame=frame)

# =========================================================
# 9) TRAFFIC LAYOUT / STORY
# =========================================================
cars = []

lane_left_x = -1.65
lane_right_x = 1.65

# Front cluster
start_positions_left = [-10, -16, -22, -28, -34, -40]
start_positions_right = [-6, -12, -18, -24, -30, -36]

all_positions = []
for i, y in enumerate(start_positions_left):
    all_positions.append((lane_left_x, y, i))
for i, y in enumerate(start_positions_right):
    all_positions.append((lane_right_x, y, i + 6))

# Create cars
for idx, (x, y, n) in enumerate(all_positions):
    car = create_car(
        name=f"Car_{idx:02d}",
        x=x,
        y=y,
        body_color=random.choice(CAR_COLORS)
    )
    cars.append((car, x, y, n))

# Animate traffic wave:
# Story timing
# 0-36 frames: normal flow
# 36-68 frames: lead car slight braking
# 68-120: chain reaction
# 120-192: congestion wave visible

for idx, (car_data, x, start_y, n) in enumerate(cars):
    root = car_data["root"]
    delay = n * 5

    # Base story:
    # front-most cars react earlier, rear cars react later
    slow_start = 40 + delay
    slow_end = 72 + delay
    recover_end = 118 + delay

    # Clamp frames inside timeline
    slow_start = min(slow_start, FRAME_END - 60)
    slow_end = min(slow_end, FRAME_END - 30)
    recover_end = min(recover_end, FRAME_END - 4)

    # Distance profile
    y1 = start_y + 14.0                      # smooth motion before slow-down
    y2 = y1 + 1.8 + max(0, 2.4 - 0.10 * n)  # compressed during slow-down
    y3 = y2 + 4.6                           # partial recovery
    y4 = y3 + 4.8                           # end movement

    # Rear cars catch up more (creates compression)
    if n >= 4:
        y2 += 0.4
        y3 += 0.2
    if n >= 8:
        y1 += 0.3
        y2 += 0.5

    points = [
        (slow_start - 1, y1),
        (slow_end, y2),
        (recover_end, y3),
        (FRAME_END, y4),
    ]
    animate_car_y(root, start_y, points)

    # Brake lights:
    # Lead vehicles flare earlier, others react as wave reaches them
    brake_on = slow_start
    brake_peak = min(slow_start + 8, FRAME_END)
    brake_hold = min(slow_end, FRAME_END)
    brake_release = min(recover_end + 5, FRAME_END)

    keyframe_brake_materials(
        car_data["brakes"],
        [
            (1, 1.0),
            (brake_on - 1, 1.0),
            (brake_peak, 4.6),
            (brake_hold, 4.2),
            (brake_release, 1.4),
            (FRAME_END, 1.0),
        ]
    )

# =========================================================
# 10) ENGINEERING OVERLAYS / TRAFFIC WAVE EFFECT
# =========================================================
# Teal flow path (visible early)
flow_path = curve_line(
    "Flow_Path",
    [(0.0, -42, 0.18), (0.0, 28, 0.18)],
    TEAL_GLOW,
    thickness=0.045
)
flow_path.scale = (1, 1, 1)
flow_path.keyframe_insert(data_path="scale", frame=1)
flow_path.scale = (1, 1, 1)
flow_path.keyframe_insert(data_path="scale", frame=82)
flow_path.scale = (0.001, 0.001, 1)
flow_path.keyframe_insert(data_path="scale", frame=116)

# Red congestion wave line appears and moves backward
wave_path = curve_line(
    "Congestion_Wave",
    [(0.0, 12, 0.20), (0.0, 34, 0.20)],
    RED_GLOW,
    thickness=0.06
)
wave_path.scale = (0.001, 0.001, 1)
wave_path.keyframe_insert(data_path="scale", frame=1)
wave_path.scale = (0.001, 0.001, 1)
wave_path.keyframe_insert(data_path="scale", frame=84)
wave_path.scale = (1.0, 1.0, 1.0)
wave_path.keyframe_insert(data_path="scale", frame=98)

wave_path.location = (0, 0, 0)
wave_path.keyframe_insert(data_path="location", frame=98)
wave_path.location = (0, -18, 0)
wave_path.keyframe_insert(data_path="location", frame=152)

# Pulse ring at congestion hot spot
ring_points = []
for i in range(64):
    ang = (i / 64.0) * math.tau
    ring_points.append((2.6 * math.cos(ang), 18.5 + 4.0 * math.sin(ang), 0.22))
pulse_ring = curve_line("Pulse_Ring", ring_points, RED_GLOW, thickness=0.045)
pulse_ring.scale = (0.001, 0.001, 1)
pulse_ring.keyframe_insert(data_path="scale", frame=1)
pulse_ring.scale = (0.001, 0.001, 1)
pulse_ring.keyframe_insert(data_path="scale", frame=92)
pulse_ring.scale = (1.0, 1.0, 1)
pulse_ring.keyframe_insert(data_path="scale", frame=110)
pulse_ring.scale = (1.20, 1.20, 1)
pulse_ring.keyframe_insert(data_path="scale", frame=145)
pulse_ring.scale = (1.08, 1.08, 1)
pulse_ring.keyframe_insert(data_path="scale", frame=FRAME_END)

# Simple hero arrow overlay for ending
arrow_line = curve_line(
    "Wave_Arrow_Line",
    [(-2.2, 23, 0.25), (-0.6, 20.5, 0.25), (0.8, 17.8, 0.25)],
    RED_GLOW,
    thickness=0.05
)
arrow_head_a = cube("Arrow_Head_A", location=(0.95, 17.5, 0.25), scale=(0.38, 0.12, 0.05), material=RED_GLOW, bevel=0.02)
arrow_head_b = cube("Arrow_Head_B", location=(0.55, 17.9, 0.25), scale=(0.12, 0.38, 0.05), material=RED_GLOW, bevel=0.02)

for obj in [arrow_line, arrow_head_a, arrow_head_b]:
    obj.scale = (0.001, 0.001, 1)
    obj.keyframe_insert(data_path="scale", frame=1)
    obj.scale = (0.001, 0.001, 1)
    obj.keyframe_insert(data_path="scale", frame=150)
    obj.scale = (1, 1, 1)
    obj.keyframe_insert(data_path="scale", frame=168)

# =========================================================
# 11) LIGHTING
# =========================================================
# Soft cool moon-like key
add_area_light(
    "Key_Cool",
    location=(-16, -18, 26),
    rotation=(math.radians(62), 0, math.radians(35)),
    power=3200,
    color=(0.66, 0.82, 1.0),
    size=18.0
)

# Teal rim
add_area_light(
    "Rim_Teal",
    location=(18, 12, 18),
    rotation=(math.radians(68), 0, math.radians(-120)),
    power=2500,
    color=(0.08, 0.88, 1.0),
    size=15.0
)

# Warm contrast
add_area_light(
    "Accent_Warm",
    location=(-20, 18, 13),
    rotation=(math.radians(80), 0, math.radians(18)),
    power=1600,
    color=(1.0, 0.42, 0.24),
    size=10.0
)

# Extra fill down the corridor
add_area_light(
    "Road_Fill",
    location=(0, -10, 20),
    rotation=(math.radians(90), 0, 0),
    power=1300,
    color=(0.46, 0.58, 0.75),
    size=12.0
)

# =========================================================
# 12) CAMERA
# =========================================================
cam_data = bpy.data.cameras.new("Grasumstudio_Camera")
cam = bpy.data.objects.new("Grasumstudio_Camera", cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 28
cam_data.clip_end = 500

target = bpy.data.objects.new("Camera_Target", None)
bpy.context.collection.objects.link(target)

track = cam.constraints.new(type='TRACK_TO')
track.target = target
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

# Shot-by-shot camera path
camera_keys = [
    (1,   (-18, -38, 28), (0, -8, 0.6)),   # Establishing flow
    (36,  (-14, -24, 23), (0,  1, 0.6)),   # Push in
    (68,  (-10,  -8, 18), (0, 11, 0.6)),   # Disturbance / reaction
    (108, ( -2,  14, 28), (0, 18, 0.6)),   # Pull up into reveal
    (152, ( -1,  23, 34), (0, 18, 0.6)),   # Overhead congestion wave
    (192, ( -7,  16, 22), (0, 18, 0.6)),   # Hero ending
]

for frame, cam_pos, look_at in camera_keys:
    cam.location = cam_pos
    target.location = look_at
    cam.keyframe_insert(data_path='location', frame=frame)
    target.keyframe_insert(data_path='location', frame=frame)

# Slight lens change for subtle documentary feel
cam_data.lens = 26
cam_data.keyframe_insert(data_path="lens", frame=1)
cam_data.lens = 28
cam_data.keyframe_insert(data_path="lens", frame=68)
cam_data.lens = 32
cam_data.keyframe_insert(data_path="lens", frame=152)
cam_data.lens = 30
cam_data.keyframe_insert(data_path="lens", frame=192)

# =========================================================
# 13) OPTIONAL VIEWPORT CAMERA MODE FOR MANUAL USE
# =========================================================
scene.frame_set(1)
if bpy.context.screen is not None:
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'

# =========================================================
# 14) SAVE PROJECT
# =========================================================
project_file = os.path.join(PROJECT, 'Scene01_TrafficMystery.blend')
bpy.ops.wm.save_as_mainfile(filepath=project_file)

print("\nScene 1 V2 created successfully!")
print("Blend project:", project_file)
print("Frames directory:", FRAME_DIR)
print("Preview mode:", PREVIEW)
print("Topic: Why Traffic Jams Happen Without an Accident")
print("Use existing render_for_ci.py + GitHub workflow to render test_frame or full_animation.")