"""Scene 1: Traffic mystery — an original cinematic engineering Short.
Compatible target: Blender 4.5 LTS / 5.2 LTS.
Run from Blender > Scripting > Open > Run Script (in a NEW, unsaved Blender scene).
Creates an editable 8-second vertical 3D animation. No add-ons/assets needed.
Output project: ~/Documents/EngineeringChannel/Scene01_TrafficMystery.blend
Output frames:  ~/Documents/EngineeringChannel/Scene01_Frames/

Change PREVIEW=False for a higher-quality 720x1280 render.
"""
import bpy
import math
import os
import random
from mathutils import Vector

# ========= 0. YOUR CHANNEL'S REUSABLE SETTINGS =========
PREVIEW = True                         # True = lighter preview for 8GB laptops
FPS = 24
DURATION_SECONDS = 8
RES_X, RES_Y = 720, 1280              # 9:16 YouTube Short
random.seed(23)                       # Repeatable layout

HOME = os.path.expanduser('~')
PROJECT = os.path.join(HOME, 'Documents', 'EngineeringChannel')
FRAME_DIR = os.path.join(PROJECT, 'Scene01_Frames')
os.makedirs(FRAME_DIR, exist_ok=True)

# Run on a fresh scene only: everything in the current scene will be deleted.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FPS * DURATION_SECONDS
scene.render.fps = FPS
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 60 if PREVIEW else 100

# Blender's official engine ID varies between versions.
engine_ids = {e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items}
if 'BLENDER_EEVEE' in engine_ids:
    scene.render.engine = 'BLENDER_EEVEE'
elif 'BLENDER_EEVEE_NEXT' in engine_ids:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
else:
    raise RuntimeError('EEVEE is unavailable. Try Blender 4.5 or 5.2 LTS.')

if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 16 if PREVIEW else 32
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(FRAME_DIR, 'scene01_')
scene.render.film_transparent = False
scene.render.image_settings.color_depth = '8'

# AgX handles bright emissive surfaces more gracefully.
try:
    scene.view_settings.view_transform = 'AgX'
except Exception:
    pass

# ========= 1. CREATE MATERIALS =========
def mat(name, rgb, metallic=0.0, roughness=0.55):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return m


def glowing(name, rgb, strength=2.5):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    em = nodes.new('ShaderNodeEmission')
    em.name = 'Glow_Color'
    em.inputs['Color'].default_value = (*rgb, 1.0)
    em.inputs['Strength'].default_value = strength
    m.node_tree.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m

ROAD = mat('Road • matte charcoal', (0.017, 0.024, 0.042), roughness=0.86)
GROUND = mat('Ground • midnight blue', (0.012, 0.029, 0.052))
SIDEWALK = mat('Sidewalk • graphite', (0.065, 0.085, 0.12))
BUILDINGS = [mat('Building material %d' % i, c, metallic=.2, roughness=.4) for i,c in enumerate([
    (0.036,.075,.108), (.055,.075,.105), (.025,.055,.089), (.065,.090,.11)
])]
GLASS = mat('Car glass • dark blue', (.030,.13,.19), metallic=.12, roughness=.23)
WHEELS = mat('Rubber tires', (.012,.014,.018))
WHITE = mat('Lane stripes', (.45,.52,.56))
WINDOW_BLUE = glowing('Windows • aqua', (.020,.44,.57), 1.15)
WINDOW_WARM = glowing('Windows • pale amber', (.80,.38,.10), 1.0)
TEAL = glowing('Channel signature • teal blue', (.015,.65,.80), 2.5)
RED = glowing('Congestion • coral red', (1.0,.045,.02), 3.5)
HEAD = glowing('Headlights • pearl', (.88,.97,1.0), 2.0)
BRAKE = glowing('Brake lights • adjustable', (.95,.022,.008), 1.0)
CAR_PAINTS = [mat('Car paint %d' % i, c, metallic=.4, roughness=.32) for i,c in enumerate([
    (.16,.21,.26), (.38,.40,.43), (.075,.20,.29), (.23,.12,.16), (.50,.50,.48)
])]

# ========= 2. BASIC MODELING HELPERS =========
def box(name, location, scale, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new('Gentle architectural edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        if hasattr(mod, 'affect'):
            mod.affect = 'EDGES'
    return obj


def curve_line(name, coords, material, thickness=.08):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = thickness
    curve.bevel_resolution = 2
    poly = curve.splines.new('POLY')
    poly.points.add(len(coords)-1)
    for p, xyz in zip(poly.points, coords):
        p.co = (*xyz,1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

# ========= 3. MODEL AN ORIGINAL NIGHT CITY =========
box('Large dark city base', (0,0,-.35), (66,120,.60), GROUND)
box('Main road / north-south', (0,0,.005), (8.3,104,.065), ROAD)
for y in (-21, 5, 30):
    box('Cross-road at %s' % y, (0,y,.028), (66,5.0,.07), ROAD)

# Sidewalks, repeated dashed centerlines, and subtle lit boundaries.
for x in (-5.5,5.5):
    box('Raised sidewalk', (x,0,.12), (1.7,104,.24), SIDEWALK)
for y in range(-48,48,6):
    if any(abs(y-cross)<4 for cross in (-21,5,30)):
        continue
    box('Painted center stripe', (0,y,.076), (.10,2.8,.012), WHITE)
for x in (-3.95,3.95):
    curve_line('Street edge • teal', [(x,-51,.104), (x,52,.104)], TEAL, .024)

# Compact skyline: random building heights for an authored, repeatable look.
for side in (-1,1):
    for col in (0,1):
        x = side * (10.5 + col * 7.4)
        for y in range(-41,46,10):
            if any(abs(y-cross)<5 for cross in (-21,5,30)):
                continue
            width = 5.4 if col == 0 else 6.4
            depth = 7.1
            height = random.uniform(7.5,22.0)
            building = box('Tower %s %s %s' % (side,col,y), (x,y,height/2+.12),
                           (width,depth,height), random.choice(BUILDINGS), .12)
            # Put visible windows on the wall facing the central road.
            inner_x = x - side * (width/2 + .035)
            for level in range(2, int(height)-1, 3):
                for yi in (-2.1,0,2.1):
                    if random.random() < .22:
                        continue
                    window = box('Window', (inner_x,y+yi,level+.35),
                                 (.075,1.0,.58),
                                 WINDOW_WARM if random.random()<.13 else WINDOW_BLUE)

# ========= 4. MODEL CARS AND ANIMATE A TRAFFIC JAM =========
def car(name, x, y, paint, progress, slow=True):
    # Parent all parts to an empty so a whole car can move in one keyframe.
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x,y,0)
    body = box(name+' chassis', (0,0,.46), (1.27,2.60,.48), paint, .12)
    cabin = box(name+' roof', (0,-.12,.86), (1.07,1.37,.42), GLASS, .10)
    parts = [body,cabin]
    # Small tire blocks and rectangular light lenses keep this fast on old laptops.
    for wx in (-.62,.62):
        for wy in (-.78,.78):
            parts.append(box(name+' tire', (wx,wy,.27), (.22,.46,.50), WHEELS, .05))
    for lx in (-.37,.37):
        parts.append(box(name+' headlamp', (lx,1.32,.42), (.24,.055,.11), HEAD))
        parts.append(box(name+' brake lamp', (lx,-1.32,.46), (.24,.055,.13), BRAKE))
    for p in parts:
        # Objects were created at local-looking coordinates; parent without transform.
        p.parent = root
        p.matrix_parent_inverse.identity()
    root.keyframe_insert(data_path='location', frame=1)
    root.location.y = y+progress
    root.keyframe_insert(data_path='location', frame=scene.frame_end)
    # Default Blender keyframes use smooth Bezier interpolation.
    return root

for lane_x, offset in ((-1.65,0),(1.65,3.0)):
    for index, yy in enumerate((-10,-4,2,8,14,20,26)):
        car('Congested car %s-%s' % (lane_x,index), lane_x, yy+offset,
            random.choice(CAR_PAINTS), progress=random.uniform(.8,2.0))
for idx, (xx,yy) in enumerate(((-1.65,-36), (1.65,-33),(-1.65,-26),(1.65,-23))):
    car('Approaching car %d' % idx, xx, yy, random.choice(CAR_PAINTS), progress=7.5)

# Brake lights brighten as vehicles bunch up (frame 90 onward).
brake_strength = BRAKE.node_tree.nodes['Glow_Color'].inputs['Strength']
for frame, value in ((1,1.0),(85,1.15),(108,4.2),(192,4.2)):
    brake_strength.default_value = value
    brake_strength.keyframe_insert('default_value', frame=frame)

# Two holographic road-status paths turn red as congestion is detected.
STATUS = glowing('Live traffic indication / animates cyan to red', (.018,.80,.88), 2.7)
status_color = STATUS.node_tree.nodes['Glow_Color'].inputs['Color']
for frame, rgba in ((1,(.018,.80,.88,1)),(87,(.018,.80,.88,1)),
                    (110,(1.0,.043,.017,1)),(192,(1.0,.043,.017,1))):
    status_color.default_value = rgba
    status_color.keyframe_insert('default_value', frame=frame)
for xx in (-3.30, 3.30):
    curve_line('Congestion data / glowing path', [(xx,-4,.145),(xx,34,.145)], STATUS, .08)

# Pulse ring marks slowdown hot spot: illustrative, not a literal GPS signal.
ring_points = []
for i in range(65):
    angle = (i/64.0)*math.tau
    ring_points.append((3.0*math.cos(angle),12 + 5.0*math.sin(angle),.16))
ring = curve_line('Traffic slowdown pulse', ring_points, RED, .055)
for frame, scale in ((1,.001),(92,.001),(114,1.0),(150,1.15),(192,1.12)):
    ring.scale = (scale,scale,1)
    ring.keyframe_insert(data_path='scale', frame=frame)

# ========= 5. REUSABLE CINEMATIC LIGHTING =========
world = bpy.data.worlds.new('Channel world • midnight blue')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (.010,.025,.052,1)
bg.inputs['Strength'].default_value = .5

def area(name, loc, power, rgb, size):
    data = bpy.data.lights.new(name,'AREA')
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.data.energy = power
    obj.data.color = rgb
    obj.data.shape = 'DISK'
    obj.data.size = size
    # Point the light at the center of the traffic.
    direction = Vector((0,8,0)) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()
    return obj

area('Key light • cool softbox', (-9,-8,28), 2400, (.55,.82,1.0), 24)
area('Rim light • teal blue', (14,20,19), 2300, (.03,.78,1.0), 15)
area('Warm accent • congested city', (-16,13,13), 1200, (1.0,.30,.13), 14)

# ========= 6. CAMERA CRANE / AERIAL PUSH-IN =========
cam_data = bpy.data.cameras.new('Shorts cinematic camera / 28mm')
cam = bpy.data.objects.new('Camera / moving aerial reveal', cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 28
# Animate the look-at target independently from the camera.
target = bpy.data.objects.new('Camera target / congested boulevard', None)
bpy.context.collection.objects.link(target)
track = cam.constraints.new('TRACK_TO')
track.target = target
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

for frame, position, look_at in (
    (1,   (-21,-29,37), (0,-1,.4)),
    (56,  (-16,-22,31), (0,5,.4)),
    (120, (-11,-12,25), (0,11,.4)),
    (192, (-9,-3,21),  (0,15,.4)),
):
    cam.location = position
    target.location = look_at
    cam.keyframe_insert(data_path='location', frame=frame)
    target.keyframe_insert(data_path='location', frame=frame)

# Important: return to beginning before saving and test rendering.
scene.frame_set(1)
# Camera view by default after running script, easier for beginners.
# In Blender background mode (e.g. GitHub Actions), context.screen can be None.
if bpy.context.screen is not None:
    for area_obj in bpy.context.screen.areas:
        if area_obj.type == 'VIEW_3D':
            area_obj.spaces.active.region_3d.view_perspective = 'CAMERA'

project_file = os.path.join(PROJECT,'Scene01_TrafficMystery.blend')
bpy.ops.wm.save_as_mainfile(filepath=project_file)
print('\nScene 1 created!')
print('Blend project:',project_file)
print('PNG animation frames:', FRAME_DIR)
print('Preview mode:', PREVIEW)
print('Press F12 for a still; Ctrl+F12 for all 192 PNG frames.')
