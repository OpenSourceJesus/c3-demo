import bpy, math, mathutils
from random import random, uniform

EXAMPLE1 = '''
self.velocity += GRAVITY*dt;
float nx = self.position.x + self.velocity.x*dt;
if (nx < 0 || nx + self.scale.x > raylib::get_screen_width()) {
	self.velocity.x *= -COLLISION_DAMP;
	self.color = {(char)raylib::get_random_value(0, 255), (char)raylib::get_random_value(0, 255), (char)raylib::get_random_value(0, 255), 0xFF};
} else {
	self.position.x = nx;
}
float ny = self.position.y + self.velocity.y*dt;
if (ny < 0 || ny + self.scale.y > raylib::get_screen_height()) {
	self.velocity.y *= -COLLISION_DAMP;
	self.color = {(char)raylib::get_random_value(0, 255), (char)raylib::get_random_value(0, 255), (char)raylib::get_random_value(0, 255), 0xFF};
} else {
	self.position.y = ny;
}
'''

EXAMPLE2 = '''
self.position.x += self.myprop;
if (self.position.x >= raylib::get_screen_width()) self.position.x = 0;
'''


def gen_test_scene(quant=None, wasm_simple_stroke_opt=None):
	ob = bpy.data.objects['Cube']
	ob.scale.z += random()
	txt = bpy.data.texts.new(name='example1.c3')
	txt.from_string(EXAMPLE1)
	ob.c3_script0 = txt

	bpy.ops.object.gpencil_add(type='MONKEY')
	ob = bpy.context.active_object
	if wasm_simple_stroke_opt:
		## only works with WASM export
		ob.data.c3_grease_optimize=int(wasm_simple_stroke_opt)
	if quant:
		ob.c3_grease_quantize = quant

	ob.location.x += 2
	ob.scale.z += random()
	for mat in ob.data.materials:
		if mat.name=='Skin': continue
		mat.c3_export_trifan = True

	bpy.ops.mesh.primitive_circle_add(fill_type="NGON")
	ob = bpy.context.active_object
	ob.location.x = 5
	ob.rotation_euler.x = math.pi / 2
	txt = bpy.data.texts.new(name='example2.c3')
	txt.from_string(EXAMPLE2)
	ob.c3_script0 = txt
	ob['myprop'] = 1.0

def test2(quant=None, wasm_simple_stroke_opt=None):
	ob = bpy.data.objects['Cube']
	ob.hide_set(True)

	bpy.ops.object.gpencil_add(type='MONKEY')
	ob = bpy.context.active_object
	if wasm_simple_stroke_opt:
		ob.data.c3_grease_optimize=int(wasm_simple_stroke_opt)
	if quant:
		ob.c3_grease_quantize = quant

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = 'Oo'
	ob.rotation_euler.x = math.pi/2
	ob.location.x -= 0.73
	ob.location.z -= 0.13
	ob.data.extrude = 0.18
	print(ob.type)
