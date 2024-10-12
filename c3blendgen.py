import bpy, math, mathutils
from random import random, uniform, choice

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
		ob.data.c3_grease_quantize = quant

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


EXAMPLE3 = '''
if (raylib::get_random_value(0,100) < 10){
	self.set_text(" 👁️‍🗨️ 👁️");
	self.css_scale(0.4);
} else {
	self.set_text("Oo");
	self.css_scale(1.0);
}
'''

def test2(quant=None, wasm_simple_stroke_opt=None):
	cube = bpy.data.objects['Cube']
	txt = bpy.data.texts.new(name='example1.c3')
	txt.from_string(EXAMPLE1)
	cube.c3_script0 = txt

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = 'hello world'
	ob.location.x = 2
	ob.location.z = 1
	ob.rotation_euler.x = math.pi/2
	ob.parent = cube

	bpy.ops.object.gpencil_add(type='MONKEY')
	ob = bpy.context.active_object
	if wasm_simple_stroke_opt:
		ob.data.c3_grease_optimize=int(wasm_simple_stroke_opt)
	if quant:
		ob.data.c3_grease_quantize = quant

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = 'Oo'
	ob.rotation_euler.x = math.pi/2
	ob.location.x -= 0.73
	ob.location.z -= 0.13
	ob.data.extrude = 0.18
	txt = bpy.data.texts.new(name='example3.c3')
	txt.from_string(EXAMPLE3)
	ob.c3_script0 = txt

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = '-_-/'
	ob.data.size *= 0.5
	ob.rotation_euler.x = math.pi/2
	ob.location.x = -0.4
	ob.location.z = 0.3

def test3(quant=None, wasm_simple_stroke_opt=None):
	cube = bpy.data.objects['Cube']
	cube.hide_set(True)


	bpy.ops.object.gpencil_add(type='MONKEY')
	mob = bpy.context.active_object
	txt = bpy.data.texts.new(name='example1.c3')
	txt.from_string(EXAMPLE1)
	mob.c3_script0 = txt

	if wasm_simple_stroke_opt:
		mob.data.c3_grease_optimize=int(wasm_simple_stroke_opt)
	if quant:
		mob.data.c3_grease_quantize = quant

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = '🗯️'
	ob.data.size *= 2.2
	ob.rotation_euler.x = math.pi/2
	ob.location.x = 0.1
	ob.location.z = 0.1
	ob.parent = mob


	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = 'hello C3'
	ob.data.size *= 0.25
	ob.location.x = 0.8
	ob.location.z = 0.5
	ob.rotation_euler.x = math.pi/2
	ob.parent = mob

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = choice(['🧥', '🥼'])
	ob.data.size *= 2
	ob.rotation_euler.x = math.pi/2
	ob.location = [-1, 0.2, -2]
	ob.parent = mob

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = choice(['🩳', '👖'])
	ob.data.size *= 1.5
	ob.rotation_euler.x = math.pi/2
	ob.location = [-0.7, 0.3, -3]
	ob.parent = mob

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = choice(['👞👞', '👟👟', '🥾🥾', '👢👢'])
	ob.data.size *= 0.8
	ob.rotation_euler.x = math.pi/2
	ob.location = [-0.6, 0.4, -3.5]
	ob.parent = mob

EXAMPLE4 = '''
document.getElementById('BUBBLE').hidden=false;
document.getElementById('CHAT').hidden=false;
'''

def test4(quant=None, wasm_simple_stroke_opt=None, example=EXAMPLE4):
	cube = bpy.data.objects['Cube']
	cube.hide_set(True)

	bpy.ops.object.gpencil_add(type='MONKEY')
	mob = bpy.context.active_object
	txt = bpy.data.texts.new(name='example1.c3')
	txt.from_string(EXAMPLE1)
	mob.c3_script0 = txt

	if wasm_simple_stroke_opt:
		mob.data.c3_grease_optimize=int(wasm_simple_stroke_opt)
	if quant:
		mob.data.c3_grease_quantize = quant

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.name = 'BUBBLE'
	ob.c3_hide = True
	ob.data.body = '🗯️'
	ob.data.size *= 2.2
	ob.rotation_euler.x = math.pi/2
	ob.location.x = 0.1
	ob.location.z = 0.1
	ob.parent = mob

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.name = 'CHAT'
	ob.c3_hide = True
	ob.data.body = 'hello C3'
	ob.data.size *= 0.25
	ob.location.x = 0.8
	ob.location.z = 0.5
	ob.rotation_euler.x = math.pi/2
	ob.parent = mob

	bpy.ops.object.text_add()
	ob = bpy.context.active_object
	ob.data.body = choice(['🎩', '🎓', '🧢', '👒'])
	ob.data.size *= 1.5
	ob.rotation_euler.x = math.pi/2
	ob.location = [-0.8, -0.1, 0.7]
	ob.parent = mob

	txt = bpy.data.texts.new(name='example4.c3')
	txt.from_string('html_eval(`%s`);' % example)
	ob.c3_onclick = txt

