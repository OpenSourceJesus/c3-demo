#!/usr/bin/python3
import os, sys, subprocess
from random import random, uniform
_thisdir = os.path.split(os.path.abspath(__file__))[0]
EMSDK = os.path.join(_thisdir, "emsdk")
BLENDER = 'blender'

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


def build(input='./demo.c3', output='c3-demo.bin', wasm=False, opt=False):
	cmd = [C3, '-l', './raylib-5.0_linux_amd64/lib/libraylib.a']
	if wasm:
		cmd += [
			'--target', 'wasm32',
			'--linker=custom', './emsdk/upstream/bin/wasm-ld'
		]
	else:
		cmd += ['--target', 'linux-x64']
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
			'--no-entry', '--reloc=none']
		pass
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
	subprocess.check_call(['/tmp/'+output])


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
	return ob.name.replace('.', '_')

def blender_to_c3():
	head  = [HEADER]
	setup = ['fn void main() @extern("main") @wasm {']
	draw  = [
		'fn void game_frame() @wasm {',
		'	Object object;',
		'	float dt = raylib::get_frame_time();',
		'	raylib::begin_drawing();',
		'	raylib::clear_background({0x18, 0x18, 0x18, 0xFF});',
	]
	meshes = []
	for ob in bpy.data.objects:
		sname = safename(ob)
		idx = len(meshes)
		x,y,z = ob.location
		if ob.type=="MESH":
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			setup.append('	objects[%s].color=raylib::color_from_hsv(%s,1,1);' % (idx, random()))

			draw.append('	object = objects[%s];' % idx)
			draw.append('	raylib::draw_rectangle_v(object.position, PLAYER_SIZE, object.color);')

	setup.append(MAIN)
	setup.append('}')
	draw.append('raylib::end_drawing();')
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
		#blender_to_c3()
		test()
		return {"FINISHED"}

@bpy.utils.register_class
class C3WorldPanel(bpy.types.Panel):
	bl_idname = "WORLD_PT_C3World_Panel"
	bl_label = "C3 Export"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"

	def draw(self, context):
		#self.layout.operator("c3.export_wasm", icon="CONSOLE")
		self.layout.operator("c3.export", icon="CONSOLE")


def test():
	o = blender_to_c3()
	o = '\n'.join(o)
	print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	build(input=tmp)
