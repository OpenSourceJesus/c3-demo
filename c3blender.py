#!/usr/bin/python3
import os, sys, subprocess, atexit, webbrowser
from random import random, uniform
_thisdir = os.path.split(os.path.abspath(__file__))[0]
EMSDK = os.path.join(_thisdir, "emsdk")
BLENDER = 'blender'
SCALE = 100

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
		if os.path.isfile('./emsdk/upstream/bin/wasm-ld'):
			cmd += ['--linker=custom', './emsdk/upstream/bin/wasm-ld']
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
		cmd += [#'--link-libc=no', '--use-stdlib=no', 
			'--no-entry', '--reloc=none', '-z', '--export-table']
	else:
		cmd += ['-l', 'glfw']

	if opt:
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
	elif '--blender' in sys.argv:
		cmd = [BLENDER, '--python', __file__]
		print(cmd)
		subprocess.check_call(cmd)
		sys.exit()
	else:
		build()

## blender ##
import bpy

HEADER = '''
import raylib;
def Entry = fn void();
extern fn void raylib_js_set_entry(Entry entry) @wasm;
const Vector2 PLAYER_SIZE = {100, 100};
const Vector2 GRAVITY = {0, 1000};
const int N = 10;
const float COLLISION_DAMP = 1;

struct Object {
	Vector2 position;
	Vector2 velocity;
	Color color;
}
'''

MAIN = '''
	raylib::init_window(800, 600, "Hello, from C3 WebAssembly");
	raylib::set_target_fps(60);

	$if $feature(PLATFORM_WEB):
		raylib_js_set_entry(&game_frame);
	$else
		while (!raylib::window_should_close()) {
			game_frame();
		}
		raylib::close_window();
	$endif
'''

def safename(ob):
	return ob.name.lower().replace('.', '_')

def blender_to_c3():
	head  = [HEADER]
	setup = ['fn void main() @extern("main") @wasm {']
	draw  = [
		'fn void game_frame() @wasm {',
		'	Object object;',
		'	float dt = raylib::get_frame_time();',
		'	raylib::begin_drawing();',
		'	raylib::clear_background({0xFF, 0xFF, 0xFF, 0xFF});',
	]
	meshes = []
	datas = {}
	for ob in bpy.data.objects:
		sname = safename(ob)
		x,y,z = ob.location * SCALE
		x += 100
		y += 100
		idx = len(meshes)
		if ob.type=="MESH":
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			setup.append('	objects[%s].color=raylib::color_from_hsv(%s,1,1);' % (idx, random()))

			draw.append('	object = objects[%s];' % idx)
			draw.append('	raylib::draw_rectangle_v(object.position, PLAYER_SIZE, object.color);')
		elif ob.type=='GPENCIL':
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			dname = safename(ob.data)
			if dname not in datas:
				datas[dname]=1
				data = []
				for sidx, stroke in enumerate( ob.data.layers[0].frames[0].strokes ):
					data.append('Vector2[%s] __%s__%s = {' % (len(stroke.points),dname, sidx ))
					s = []
					for pnt in stroke.points:
						x,y,z = pnt.co * SCALE
						s.append('{%s,%s}' % (x,-z))
					data.append('\t' + ','.join(s))
					data.append('};')
				head += data

			for sidx, stroke in enumerate( ob.data.layers[0].frames[0].strokes ):
				n = len(stroke.points)
				draw.append('	raylib::draw_spline(&__%s__%s, %s, 2.0, raylib::color_from_hsv(0,1,0.5));' % (dname, sidx, n))


	setup.append(MAIN)
	setup.append('}')
	draw.append('	raylib::end_drawing();')
	draw.append('}')

	head.append('Object[%s] objects;' % len(meshes))

	return head + setup + draw


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
		self.layout.operator("c3.export_wasm", icon="CONSOLE")
		self.layout.operator("c3.export", icon="CONSOLE")

def build_linux():
	o = blender_to_c3()
	o = '\n'.join(o)
	print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	bin = build(input=tmp)

SERVER_PROC = None
def build_wasm():
	global SERVER_PROC
	if SERVER_PROC: SERVER_PROC.kill()
	o = blender_to_c3()
	o = '\n'.join(o)
	print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	wasm = build(input=tmp, wasm=True)
	os.system('cp -v ./index.html /tmp/.')
	os.system('cp -v ./raylib.js /tmp/.')
	cmd = ['python', '-m', 'http.server', '6969']
	SERVER_PROC = subprocess.Popen(cmd, cwd='/tmp')
	atexit.register(lambda:SERVER_PROC.kill())
	webbrowser.open('http://localhost:6969')


bpy.ops.object.gpencil_add(type='MONKEY')
bpy.context.active_object.location.x += 2
#build_wasm()
