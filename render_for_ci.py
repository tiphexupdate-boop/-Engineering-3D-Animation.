"""CPU-only renderer for GitHub-hosted Linux Actions runners.

This script is run by Blender AFTER scene01_traffic_city.py has created
and saved the original Scene01_TrafficMystery.blend scene.

RENDER_MODE=test_frame: render one still to confirm the pipeline works.
RENDER_MODE=full_animation: render all 192 frames, then workflow builds an MP4.

Uses Cycles on CPU deliberately: hosted GitHub Linux runners do not
normally include a hardware GPU, and EEVEE can require a graphics context.
The original EEVEE .blend project remains unmodified.
"""
import os
import shutil
from pathlib import Path

import bpy

mode = os.environ.get('RENDER_MODE', 'test_frame')
if mode not in ('test_frame', 'full_animation'):
    raise ValueError('Unknown RENDER_MODE: ' + repr(mode))

output = Path(os.environ.get('OUTPUT_DIR', 'render_output')).expanduser().resolve()
output.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
# The source scene uses EEVEE. Hosted Linux Actions VMs lack GPU rendering,
# so render the saved scene using CPU Cycles without editing the original.
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8 if mode == 'test_frame' else 12
scene.cycles.use_denoising = True
scene.render.resolution_percentage = 40 if mode == 'test_frame' else 60
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
scene.render.film_transparent = False

# Save the original .blend in the artifact so the editable model survives.
original_blend = Path(bpy.data.filepath)
if not original_blend.is_file():
    raise FileNotFoundError('The first Blender step did not create the .blend file')
shutil.copy2(original_blend, output / 'Scene01_TrafficMystery.blend')

print(f'RENDER_MODE={mode}, engine={scene.render.engine}, samples={scene.cycles.samples}')
print(f'Output directory: {output}')

if mode == 'test_frame':
    scene.frame_set(96)
    scene.render.filepath = str(output / 'Scene01_Test_Frame.png')
    bpy.ops.render.render(write_still=True)
else:
    frames_dir = output / 'frames'
    frames_dir.mkdir(exist_ok=True)
    scene.render.filepath = str(frames_dir / 'scene01_')
    scene.frame_start = 1
    scene.frame_end = 192
    bpy.ops.render.render(animation=True)
