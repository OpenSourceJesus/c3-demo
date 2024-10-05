#!/usr/bin/python3
import os, sys, subprocess, atexit, webbrowser, math
from random import random, uniform
_thisdir = os.path.split(os.path.abspath(__file__))[0]
EMSDK = os.path.join(_thisdir, "emsdk")
BLENDER = 'blender'
MAX_SCRIPTS_PER_OBJECT = 8

if not os.path.isdir('c3'):
	if not os.path.isfile('c3-ubuntu-20.tar.gz'):
		cmd = 'wget -c https://github.com/c3lang/c3c/releases/download/latest/c3-ubuntu-20.tar.gz'
		print(cmd)
		subprocess.check_call(cmd.split())
	cmd = 'tar -xvf c3-ubuntu-20.tar.gz'
	print(cmd)
	subprocess.check_call(cmd.split())

C3 = os.path.abspath('./c3/c3c')
assert os.path.isfile(C3)

if "--wasm" in sys.argv and not os.path.isdir(EMSDK):
	cmd = [
		"git",
		"clone",
		"--depth",
		"1",
		"https://github.com/emscripten-core/emsdk.git",
	]
	print(cmd)
	subprocess.check_call(cmd)
	emsdk_update()

EMCC = os.path.join(EMSDK, "upstream/emscripten/emcc")
if not EMCC and "--wasm" in sys.argv:
	emsdk_update()


def build(input='./demo.c3', output='demo', wasm=False, opt=False, run=True):
	cmd = [C3]
	if wasm:
		cmd += ['--target', 'wasm32']
		#if os.path.isfile('./emsdk/upstream/bin/wasm-ld'):
		#	cmd += ['--linker=custom', './emsdk/upstream/bin/wasm-ld']
	else:
		cmd += ['--target', 'linux-x64', '-l', './raylib-5.0_linux_amd64/lib/libraylib.a']
	mode = 'compile'

	cmd += [
		'--output-dir', '/tmp',
		'--obj-out', '/tmp',
		'--build-dir', '/tmp',
		'--print-output',
		'-o', output,
	]
	if wasm:
		cmd += ['--link-libc=no', '--use-stdlib=no', 
			'--no-entry', '--reloc=none', '-z', '--export-table']
	else:
		cmd += ['-l', 'glfw']

	if opt:
		if type(opt) is str:
			cmd.append('-'+opt)
		else:
			cmd.append('-Oz')

	cmd += [mode, input, './raylib.c3']
	print(cmd)
	res = subprocess.check_output(cmd).decode('utf-8')
	ofiles = []
	for ln in res.splitlines():
		if ln.endswith('.o'):
			ofiles.append(ln.strip())
	print(ofiles)
	if run and not wasm:
		subprocess.check_call(['/tmp/'+output])

	if wasm:
		return '/tmp/%s.wasm' % output
	else:
		return '/tmp/%s' % output


try:
	import bpy
except:
	bpy = None

if __name__=='__main__':
	if bpy:
		pass
	elif '--blender' in sys.argv or os.path.isfile('/usr/bin/blender'):
		cmd = [BLENDER, '--python', __file__]
		print(cmd)
		subprocess.check_call(cmd)
		sys.exit()
	else:
		build()

## blender ##
if not bpy:
	if not os.path.isfile('/usr/bin/blender'):
		print('did you install blender?')
		print('snap install blender')
	print('run: python3 c3blender.py --blender')
	sys.exit()

#const Vector2 PLAYER_SIZE = {100, 100};

HEADER = '''
import raylib;
def Entry = fn void();
extern fn void raylib_js_set_entry(Entry entry) @wasm;
const Vector2 GRAVITY = {0, 1000};
const int N = 10;
const float COLLISION_DAMP = 1;

struct Object {
	Vector2 position;
	Vector2 velocity;
	Vector2 scale;
	Color color;
}
'''

MAIN_WASM = '''
	raylib::init_window(%s, %s, "Hello, from C3 WebAssembly");
	raylib::set_target_fps(60);
	raylib_js_set_entry(&game_frame);

'''

MAIN = '''
	raylib::init_window(%s, %s, "Hello, from C3");
	raylib::set_target_fps(60);
	while (!raylib::window_should_close()) {
		game_frame();
	}
	raylib::close_window();
'''

def is_maybe_circle(ob):
	if len(ob.data.vertices)==32 and len(ob.data.polygons) == 1:
		return True
	else:
		return False

def safename(ob):
	return ob.name.lower().replace('.', '_')

def blender_to_c3(wasm=False):
	resx = bpy.context.world.c3_export_res_x
	resy = bpy.context.world.c3_export_res_y
	SCALE = bpy.context.world.c3_export_scale
	offx = bpy.context.world.c3_export_offset_x
	offy = bpy.context.world.c3_export_offset_y

	head  = [HEADER]
	if wasm:
		head.append('extern fn void draw_circle_wasm(int x, int y, float radius, Color color) @extern("DrawCircleWASM");')
		head.append('extern fn void draw_spline_wasm(Vector2 *points, int pointCount, float thick, int use_fill, float r, float g, float b, float a) @extern("DrawSplineLinearWASM");')
	setup = ['fn void main() @extern("main") @wasm {']
	draw  = [
		'fn void game_frame() @wasm {',
		'	Object self;',
		'	float dt = raylib::get_frame_time();',
		'	raylib::begin_drawing();',
		'	raylib::clear_background({0xFF, 0xFF, 0xFF, 0xFF});',
	]
	meshes = []
	datas = {}
	for ob in bpy.data.objects:
		sname = safename(ob)
		x,y,z = ob.location * SCALE
		z = -z
		x += offx
		z += offy
		sx,sy,sz = ob.scale * SCALE
		idx = len(meshes)

		scripts = []
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			txt = getattr(ob, "c3_script" + str(i))
			if txt:
				scripts.append(txt.as_string())


		if ob.type=="MESH":
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			setup.append('	objects[%s].scale={%s,%s};' % (idx, sx,sz))
			setup.append('	objects[%s].color=raylib::color_from_hsv(%s,1,1);' % (idx, random()))

			draw.append('	self = objects[%s];' % idx)
			if scripts:
				props = {}
				for prop in ob.keys():
					if prop.startswith( ('_', 'c3_') ): continue
					head.append('float %s_%s = %s;' %(sname, prop, ob[prop]))
					props[prop] = ob[prop]

				## user C3 scripts
				for s in scripts:
					for prop in props:
						if 'self.'+prop in s:
							s = s.replace('self.'+prop, '%s_%s'%(sname,prop))
					draw.append('\t' + s)
				## save object state: from stack back to heap
				draw.append('	objects[%s] = self;' % idx)

			if is_maybe_circle(ob):
				if wasm:
					draw.append('	draw_circle_wasm((int)self.position.x,(int)self.position.y, self.scale.x, self.color);')
				else:
					draw.append('	raylib::draw_circle_v(self.position, self.scale.x, self.color);')
			else:
				draw.append('	raylib::draw_rectangle_v(self.position, self.scale, self.color);')
		elif ob.type=='GPENCIL':
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			dname = safename(ob.data)
			if dname not in datas:
				datas[dname]=1
				data = []
				for lidx, layer in enumerate( ob.data.layers ):
					for sidx, stroke in enumerate( layer.frames[0].strokes ):
						mat = ob.data.materials[stroke.material_index]
						use_fill = mat.grease_pencil.show_fill
						s = []

						if use_fill and not wasm:
							if mat.c3_export_trifan:
								x1,y1,z1 = calc_center(stroke.points)
								x1 *= sx
								z1 *= sz
								s.append('{%s,%s}' % (x1+offx+x,-z1+offy+z))
								data.append('Vector2[%s] __%s__%s_%s = {' % (len(stroke.points)+1,dname, lidx, sidx ))
							else:
								tris = []
								for tri in stroke.triangles:
									tris.append(tri.v1)
									tris.append(tri.v2)
									tris.append(tri.v3)
								tris = ','.join([str(vidx) for vidx in tris])
								data.append('int[%s] __%s__%s_%s_tris = {%s};' % (len(stroke.triangles)*3,dname, lidx, sidx, tris ))
								data.append('Vector2[%s] __%s__%s_%s = {' % (len(stroke.points),dname, lidx, sidx ))
						else:
							data.append('Vector2[%s] __%s__%s_%s = {' % (len(stroke.points),dname, lidx, sidx ))
						for pnt in stroke.points:
							x1,y1,z1 = pnt.co
							x1 *= sx
							z1 *= sz
							s.append('{%s,%s}' % (x1+offx+x,-z1+offy+z))
						data.append('\t' + ','.join(s))
						data.append('};')
				head += data
			for lidx, layer in enumerate( ob.data.layers ):
				for sidx, stroke in enumerate( layer.frames[0].strokes ):
					n = len(stroke.points)
					mat = ob.data.materials[stroke.material_index]
					use_fill = 0
					if mat.grease_pencil.show_fill: use_fill = 1
					r,g,b,a = mat.grease_pencil.fill_color
					swidth = calc_stroke_width(stroke)

					if wasm:
						draw.append('	draw_spline_wasm(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (dname, lidx, sidx, n, swidth, use_fill, r,g,b,a))
					else:
						if use_fill:
							clr = '{%s,%s,%s,%s}' % (int(r*255), int(g*255), int(b*255), int(a*255))
							if mat.c3_export_trifan:
								draw.append('	raylib::draw_triangle_fan(&__%s__%s_%s, %s, %s);' % (dname, lidx, sidx, n+1, clr))
							else:
								draw += [
									'	for (int i=0; i<%s; i+=3){' % (len(stroke.triangles)*3),
									'		int idx = __%s__%s_%s_tris[i+2];' %(dname, lidx, sidx),
									'		Vector2 v1 = __%s__%s_%s[idx];' %(dname, lidx, sidx),
									'		idx = __%s__%s_%s_tris[i+1];'   %(dname, lidx, sidx),
									'		Vector2 v2 = __%s__%s_%s[idx];' %(dname, lidx, sidx),
									'		idx = __%s__%s_%s_tris[i+0];'   %(dname, lidx, sidx),
									'		Vector2 v3 = __%s__%s_%s[idx];' %(dname, lidx, sidx),
									'		raylib::draw_triangle(v1,v2,v3, %s);' % clr,
									'}',
								]

							if mat.grease_pencil.show_stroke:
								draw.append('	raylib::draw_spline( (&__%s__%s_%s), %s, 4.0, {0x00,0x00,0x00,0xFF});' % (dname, lidx, sidx, n))
						else:
							draw.append('	raylib::draw_spline(&__%s__%s_%s, %s, %s, {0x00,0x00,0x00,0xFF});' % (dname, lidx, sidx, n, swidth))

	if wasm:
		setup.append(MAIN_WASM % (resx, resy))
	else:
		setup.append(MAIN % (resx, resy))

	setup.append('}')
	draw.append('	raylib::end_drawing();')
	draw.append('}')

	head.append('Object[%s] objects;' % len(meshes))

	return head + setup + draw

def calc_stroke_width(stroke):
	sw = 0.0
	for p in stroke.points:
		sw += p.pressure
		#sw += p.strength
	sw /= len(stroke.points)
	return sw * 4


def calc_center(points):
	ax = ay = az = 0.0
	for p in points:
		ax += p.co.x
		ay += p.co.y
		az += p.co.z
	ax /= len(points)
	ay /= len(points)
	az /= len(points)
	return (ax,ay,az)

@bpy.utils.register_class
class C3Export(bpy.types.Operator):
	bl_idname = "c3.export"
	bl_label = "C3 Export EXE"
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		build_linux()
		return {"FINISHED"}

@bpy.utils.register_class
class C3Export(bpy.types.Operator):
	bl_idname = "c3.export_wasm"
	bl_label = "C3 Export WASM"
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		build_wasm()
		return {"FINISHED"}

@bpy.utils.register_class
class C3WorldPanel(bpy.types.Panel):
	bl_idname = "WORLD_PT_C3World_Panel"
	bl_label = "C3 Export"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"

	def draw(self, context):
		self.layout.prop(context.world, 'c3_export_res_x')
		self.layout.prop(context.world, 'c3_export_res_y')
		self.layout.prop(context.world, 'c3_export_scale')
		self.layout.prop(context.world, 'c3_export_offset_x')
		self.layout.prop(context.world, 'c3_export_offset_y')
		self.layout.prop(context.world, 'c3_export_opt')

		self.layout.operator("c3.export_wasm", icon="CONSOLE")
		self.layout.operator("c3.export", icon="CONSOLE")

def build_linux():
	o = blender_to_c3()
	o = '\n'.join(o)
	print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	bin = build(input=tmp, opt=bpy.context.world.c3_export_opt)

SERVER_PROC = None
def build_wasm():
	global SERVER_PROC
	if SERVER_PROC: SERVER_PROC.kill()
	o = blender_to_c3(wasm=True)
	o = '\n'.join(o)
	print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	wasm = build(input=tmp, wasm=True, opt=bpy.context.world.c3_export_opt)
	os.system('cp -v ./index.html /tmp/.')
	os.system('cp -v ./raylib.js /tmp/.')
	cmd = ['python', '-m', 'http.server', '6969']
	SERVER_PROC = subprocess.Popen(cmd, cwd='/tmp')
	atexit.register(lambda:SERVER_PROC.kill())
	webbrowser.open('http://localhost:6969')

bpy.types.Material.c3_export_trifan = bpy.props.BoolProperty(name="triangle fan")

bpy.types.World.c3_export_res_x = bpy.props.IntProperty(name="resolution X", default=800)
bpy.types.World.c3_export_res_y = bpy.props.IntProperty(name="resolution Y", default=600)
bpy.types.World.c3_export_scale = bpy.props.FloatProperty(name="scale", default=100)
bpy.types.World.c3_export_offset_x = bpy.props.IntProperty(name="offset X", default=100)
bpy.types.World.c3_export_offset_y = bpy.props.IntProperty(name="offset Y", default=100)
bpy.types.World.c3_export_opt = bpy.props.EnumProperty(
	name='optimize',
	items=[
		("O0", "O0", "Safe, no optimizations, emit debug info."), 
		("O1", "O1", "Safe, high optimization, emit debug info."), 
		("O2", "O2", "Unsafe, high optimization, emit debug info."), 
		("O3", "O3", "Unsafe, high optimization, single module, emit debug info."), 
		("O4", "O4", "Unsafe, highest optimization, relaxed maths, single module, emit debug info, no panic messages."),
		("O5", "O5", "Unsafe, highest optimization, fast maths, single module, emit debug info, no panic messages, no backtrace."),
		("Os", "Os", "Unsafe, high optimization, small code, single module, no debug info, no panic messages."),
		("Oz", "Oz", "Unsafe, high optimization, tiny code, single module, no debug info, no panic messages, no backtrace."),
	]
)

bpy.types.Object.c3_script_init = bpy.props.PointerProperty(
	name="script init", type=bpy.types.Text
)

for i in range(MAX_SCRIPTS_PER_OBJECT):
	setattr(
		bpy.types.Object,
		"c3_script" + str(i),
		bpy.props.PointerProperty(name="script%s" % i, type=bpy.types.Text),
	)



@bpy.utils.register_class
class C3ScriptsPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Scripts_Panel"
	bl_label = "C3 Scripts"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"

	def draw(self, context):
		if not context.active_object:
			return
		self.layout.label(text="Attach C3 Scripts")
		self.layout.prop(context.active_object, "c3_script_init")

		foundUnassignedScript = False
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			hasProperty = (
				getattr(context.active_object, "c3_script" + str(i)) != None
			)
			if hasProperty or not foundUnassignedScript:
				self.layout.prop(context.active_object, "c3_script" + str(i))
			if not foundUnassignedScript:
				foundUnassignedScript = not hasProperty


@bpy.utils.register_class
class C3MaterialPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Material_Panel"
	bl_label = "C3 Material Settings"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "material"

	def draw(self, context):
		if not context.active_object: return
		ob = context.active_object
		if not ob.type=='GPENCIL': return
		if not ob.data.materials: return
		mat = ob.data.materials[ ob.active_material_index ]
		self.layout.prop(mat, 'c3_export_trifan')


EXAMPLE1 = '''
self.velocity += GRAVITY*dt;
float nx = self.position.x + self.velocity.x*dt;
if (nx < 0 || nx + self.scale.x > raylib::get_screen_width()) {
	self.velocity.x *= -COLLISION_DAMP;
	self.color = raylib::color_from_hsv(360*((float)raylib::get_random_value(0, 100)/100.0), 1, 1);
} else {
	self.position.x = nx;
}
float ny = self.position.y + self.velocity.y*dt;
if (ny < 0 || ny + self.scale.y > raylib::get_screen_height()) {
	self.velocity.y *= -COLLISION_DAMP;
	self.color = raylib::color_from_hsv(360*((float)raylib::get_random_value(0, 100)/100.0), 1, 1);
} else {
	self.position.y = ny;
}
'''

EXAMPLE2 = '''
self.position.x += self.myprop;
if (self.position.x >= raylib::get_screen_width()) self.position.x = 0;
'''


def gen_test_scene():
	ob = bpy.data.objects['Cube']
	ob.scale.z += random()
	txt = bpy.data.texts.new(name='example1.c3')
	txt.from_string(EXAMPLE1)
	ob.c3_script0 = txt

	bpy.ops.object.gpencil_add(type='MONKEY')
	ob = bpy.context.active_object
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

gen_test_scene()
