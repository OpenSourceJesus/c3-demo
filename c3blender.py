import os, sys, subprocess, atexit, webbrowser, base64, string
from random import random, uniform
_thisdir = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(_thisdir)

C3 = '/usr/local/bin/c3c'
C3_STRIP_TAIL = True
isLinux = isWindows = c3gz = c3zip = None
if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-windows.zip'
	C3 = os.path.join(_thisdir, 'c3/c3c.exe')
	isWindows = True
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-macos.zip'
else:
	BLENDER = 'blender'
	c3gz = 'https://github.com/c3lang/c3c/releases/download/latest/c3-ubuntu-20.tar.gz'
	isLinux = True

if not os.path.isfile(C3):
	C3 = '/opt/c3/c3c'
	if not os.path.isfile(C3):
		if not os.path.isdir('./c3'):
			if c3gz:
				if not os.path.isfile('c3-ubuntu-20.tar.gz'):
					cmd = 'wget -c %s' % c3gz
					print(cmd)
					subprocess.check_call(cmd.split())
				cmd = 'tar -xvf c3-ubuntu-20.tar.gz'
				print(cmd)
				subprocess.check_call(cmd.split())
			elif c3zip and isWindows:
				if not os.path.isfile('c3-windows.zip'):
					cmd = [ 'C:/Windows/System32/curl.exe', '-o', 'c3-windows.zip', c3zip ]
					print(cmd)
					subprocess.check_call(cmd)
			elif c3zip:
				if not os.path.isfile('c3-macos.zip'):
					cmd = [ 'curl', '-o', 'c3-macos.zip', c3zip ]
					print(cmd)
					subprocess.check_call(cmd)

		if isLinux:
			C3 = os.path.abspath('./c3/c3c')
		elif isWindows:
			C3 = os.path.abspath('./c3/c3c.exe')
print('c3c:', C3)
assert os.path.isfile(C3)

EMSDK = os.path.join(_thisdir, 'emsdk')
if '--install-wasm' in sys.argv and not os.path.isdir(EMSDK):
	cmd = [
		'git','copy','--depth','1',
		'https://github.com/emscripten-core/emsdk.git',
	]
	print(cmd)
	subprocess.check_call(cmd)

if isWindows:
	EMCC = os.path.join(EMSDK, 'upstream/emscripten/emcc.exe')
	WASM_OBJDUMP = os.path.join(EMSDK, 'upstream/bin/llvm-objdump.exe')
else:
	# EMCC = os.path.join(EMSDK, 'upstream/emscripten/emcc')
	EMCC = 'wasm-ld'
	# WASM_OBJDUMP = os.path.join(EMSDK, 'upstream/bin/llvm-objdump')
	WASM_OBJDUMP = ''

def C3ToWasmStrip (wasm):
	#a = b'.rodata\x00,\x0ftarget_features\x02+\x0fmutable-globals+\x08sign-ext' # wasm-opt: parse exception: Section extends beyond end of input
	a = b'\x00,\x0ftarget_features\x02+\x0fmutable-globals+\x08sign-ext'
	b = open(wasm,'rb').read()
	print(b)
	assert b.endswith(a)
	c = b[: -len(a)]
	print(c)
	open(wasm,'wb').write(c)

def Build (input = './demo.c3', output = 'demo', wasm = '--wasm' in sys.argv, opt = '--opt' in sys.argv, run = True, raylib = './raylib.c3'):
	cmd = [C3]
	if wasm:
		cmd += [ '--target', 'wasm32' ]
	else:
		cmd += [ '--target', 'linux-x64', '-l', './raylib-5.0_linux_amd64/lib/libraylib.a' ]
	mode = 'compile'
	cmd += [
		'--output-dir', '/tmp',
		'--obj-out', '/tmp',
		'--build-dir', '/tmp',
		'--print-output',
		'-o', output,
	]
	if wasm:
		cmd += [ '--link-libc=no', '--use-stdlib=no', '--no-entry', '--reloc=none', '-z', '--export-table' ]
	else:
		cmd += [ '-l', 'glfw' ]
	if opt:
		if type(opt) is str:
			cmd.append('-' + opt)
		else:
			cmd.append('-Oz')
	cmd += [mode, input, raylib]
	print(cmd)
	res = subprocess.check_output(cmd).decode('utf-8')
	oFiless = []
	for ln in res.splitlines():
		if ln.endswith('.o'):
			oFiless.append(ln.strip())
	print(oFiless)
	if run and not wasm:
		subprocess.check_call(['/tmp/' + output])

	if wasm:
		w = '/tmp/%s.wasm' %output
		if C3_STRIP_TAIL:
			C3ToWasmStrip(w)
		if os.path.isfile('SlimeJump.py') and os.path.isfile('/tmp/demo.opt.wasm'):
			import SlimeJump as slimJump
			slimJump.GenLevel ()
		return w
	else:
		return '/tmp/%s' %output

try:
	import bpy
	from mathutils import *
except:
	bpy = None

if __name__ == '__main__':
	if bpy:
		pass
	elif '--c3demo' in sys.argv:
		# Runs simple test without blender
		Build ()
		sys.exit()

	else:
		cmd = [ BLENDER ]
		for arg in sys.argv:
			if arg.endswith('.blend'):
				cmd.append(arg)
				break
		cmd += [ '--python-exit-code', '1', '--python', __file__, '--python', os.path.join(_thisdir, 'blender-curve-to-svg', 'curve_to_svg.py') ]
		exargs = []
		for arg in sys.argv:
			if arg.startswith('--'):
				exargs.append(arg)
		if exargs:
			cmd.append('--')
			cmd += exargs
		print(cmd)
		subprocess.check_call(cmd)
		sys.exit()

# blender #
MAX_SCRIPTS_PER_OBJECT = 16
if not bpy:
	if isLinux:
		if not os.path.isfile('/usr/bin/blender'):
			print('Did you install blender?')
			print('snap install blender')
	else:
		print('Download blender from: https://blender.org')
	sys.exit()

HEADER = '''
import raylib;
def Entry = fn void();
extern fn void raylib_js_set_entry(Entry entry) @extern("_") @wasm;

//bitstruct Vector2_4bits : ichar {
//	ichar x : 4..7;
//	ichar y : 0..3;
//}

//bitstruct Vector2_6bits : int {
//	ichar x0 : 26..31;  // 6bits
//	ichar y0 : 20..25;  // 6bits
//	ichar x1 : 15..19;  // 5bits
//	ichar y1 : 10..14;  // 5bits
//	ichar x2 : 5..9;    // 5bits
//	ichar y2 : 0..4;    // 5bits
//}

//bitstruct Vector2_7bits : int {
//	ichar x0 : 24..31;  // 8bits
//	ichar y0 : 17..23;  // 8bits
//	ichar x1 : 12..16;  // 4bits
//	ichar y1 : 8..11;  // 4bits
//	ichar x2 : 4..7;    // 4bits
//	ichar y2 : 0..3;    // 4bits
//}

//struct Vector2_8bits @packed {
//	ichar x;
//	ichar y;
//}

//struct Vector2_16bits @packed {
//	short x;
//	short y;
//}
'''
HEADER_OBJECT = '''
struct Object {
	Vector2 pos;
	Vector2 scale;
	Color color;
	int id;
}
'''
HEADER_EVENT = '''
struct Event
{
	char[]* key;
}
'''
HEADER_OBJECT_WASM = '''
fn void Object.set_text(Object *obj, char *txt) {
	html_set_text (obj.id, txt);
}
fn void Object.add_char(Object *obj, char c) {
	html_add_char (obj.id, c);
}
fn void Object.css_scale(Object *obj, float scale) {
	html_css_scale (obj.id, scale);
}
fn void Object.css_scale_y(Object *obj, float scale) {
	html_css_scale_y (obj.id, scale);
}
fn void Object.css_zindex(Object *obj, int z) {
	html_css_zindex (obj.id, z);
}
fn void Object.css_string(Object *obj, char *key, char *val) {
	html_css_string (obj.id, key,val);
}
fn void Object.css_int(Object *obj, char *key, int val) {
	html_css_int (obj.id, key,val);
}
'''
WASM_HELPERS = '''
fn void transform_spline_wasm (Vector2 *source, Vector2 *target, int len, Vector2 pos, Vector2 scl){
	for (int i=0; i<len; i++){
		target[i].x = (source[i].x + pos.x) * scl.x;
		target[i].y = (source[i].y + pos.y) * scl.y;
	}
}
'''
MAIN_WASM = '''
	//html_canvas_resize(%s, %s);
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

def IsCircle (ob):
	if len(ob.data.vertices) == 32 and len(ob.data.polygons) == 1:
		return True
	else:
		return False

def GetSafeName (ob):
	return ob.name.replace('é', 'e').lower().replace('(', '_').replace(')', '_').replace('.', '_').replace(' ', '_')

WASM_EXTERN = '''
//extern fn void html_css_string (int id, char *key, char *val) @extern("html_css_string");
//extern fn void html_css_int (int id, char *key, int val) @extern("html_css_int");

extern fn float method (float arg, float arg2, int idx) @extern("method");

//extern fn void draw_circle_wasm (int x, int y, float radius, Color color) @extern("DrawCircleWASM");
//extern fn void draw_spline_wasm (Vector2 *points, int pointCount, float thick, int use_fill, char r, char g, char b, float a) @extern("DrawSplineLinearWASM");

extern fn void draw_svg (Vector2* pos, Vector2* size, Color* fillColor, float lineWidth, Color* lineColor, char[]* id, int idLen, usz[]* pathData, int pathDataLen, int zIndex, bool cyclic, bool collide, int quantizeType) @extern("draw_svg");

//extern fn int html_new_text (char *ptr, float x, float y, float sz, bool viz, char *id) @extern("html_new_text");
//extern fn void html_set_text (int id, char *ptr) @extern("html_set_text");
//extern fn void html_add_char (int id, char c) @extern("html_add_char");

//extern fn void html_set_position (int id, float x, float y) @extern("html_set_position");
//extern fn void html_css_scale (int id, float scale) @extern("html_css_scale");
//extern fn void html_css_scale_y (int id, float scale) @extern("html_css_scale_y");

//extern fn void html_css_zindex (int id, int z) @extern("html_css_zindex");
//extern fn void html_canvas_clear () @extern("html_canvas_clear");
//extern fn void html_canvas_resize (int x, int y) @extern("html_canvas_resize");

//def JSCallback = fn void( int );
//extern fn void html_bind_onclick (int id, JSCallback ptr, int ob_index) @extern("html_bind_onclick");

//extern fn void html_eval (char *ptr) @extern("html_eval");

//extern fn char wasm_memory (int idx) @extern("wasm_memory");
//extern fn int wasm_size () @extern("wasm_size");

extern fn void add_group (char[]* id, int idLen, char[]* firstAndLastChildIds, int firstAndLastChildIdsLen) @extern("add_group");
extern fn void copy_node (char[]* id, int idLen, Vector2* pos) @extern("copy_node");
//extern fn void random (float min, float max) @extern("random");
'''

def GetScripts (ob, isAPI : bool):
	scripts = []
	type = 'runtime'
	if isAPI:
		type = 'api'
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, type + 'Script%sDisable' %i):
			continue
		txt = getattr(ob, type + 'Script' + str(i))
		if txt != None:
			if isAPI:
				scripts.append(( txt.as_string(), getattr(ob, 'jsScript' + str(i)), getattr(ob, 'c3Script' + str(i)) ))
			else:
				scripts.append(( txt.as_string(), getattr(ob, 'initScript' + str(i)) ))
	return scripts

def HasScript (ob, isMethod : bool):
	type = 'runtime'
	if isMethod:
		type = 'method'
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		txt = getattr(ob, type + 'Script' + str(i))
		if txt != None:
			return True
	return False

# def CurveToMesh (curve):
# 	deg = bpy.context.evaluated_depsgraph_get()
# 	mesh = bpy.data.meshes.new_from_object(curve.evaluated_get(deg), depsgraph = deg)
# 	ob = bpy.data.objects.new(curve.name + "_Mesh", mesh)
# 	bpy.context.collection.objects.link(ob)
# 	ob.matrix_world = curve.matrix_world
# 	return ob

# def ToVector2 (v : Vector):
# 	return Vector((v.x, v.y))

def ToVector3 (v : Vector):
	return Vector(( v.x, v.y, 0 ))

# def ToC3 (v : Vector, is2d = False, round = False):
# 	if is2d:
# 		if round:
# 			return '{' + str(int(v.x)) + ', ' + str(int(v.y)) + '}'
# 		else:
# 			return '{' + str(v.x) + ', ' + str(v.y) + '}'
# 	elif round:
# 		return '{' + str(int(v.x)) + ', ' + str(int(v.y)) + ', ' + str(int(v.z)) + '}'
# 	else:
# 		return '{' + str(v.x) + ', ' + str(v.y) + ', ' + str(v.z) + '}'

# def Abs (v : Vector, is2d : bool = False):
# 	if is2d:
# 		return Vector((abs(v.x), abs(v.y)))
# 	else:
# 		return Vector((abs(v.x), abs(v.y), abs(v.z)))

# def Round (v : Vector, is2d : bool = False):
# 	if is2d:
# 		return Vector((int(v.x), int(v.y)))
# 	else:
# 		return Vector((int(v.x), int(v.y), int(v.z)))

def GetMinComponents (v : Vector, v2 : Vector, use2D : bool = False):
	if use2D:
		return Vector(( min(v.x, v2.x), min(v.y, v2.y) ))
	else:
		return Vector(( min(v.x, v2.x), min(v.y, v2.y), min(v.z, v2.z) ))

def GetMaxComponents (v : Vector, v2 : Vector, use2D : bool = False):
	if use2D:
		return Vector(( max(v.x, v2.x), max(v.y, v2.y) ))
	else:
		return Vector(( max(v.x, v2.x), max(v.y, v2.y), max(v.z, v2.z) ))

def Divide (v : Vector, v2 : Vector, use2D : bool = False):
	if use2D:
		return Vector(( v.x / v2.x, v.y / v2.y ))
	else:
		return Vector(( v.x / v2.x, v.y / v2.y, v.z / v2.z ))

def ToNormalizedPoint (minMax : [],  v : Vector):
	return Divide(Vector(( 1, 1 )), (minMax[1] - minMax[0]), True) * (v - minMax[0])

def ToC3 (s : str):
	newStr = '{'
	charCount = 0
	for char in s:
		newStr += str(ord(char)) + ','
		charCount += 1
	if not newStr.endswith('\n'):
		newStr += '10'
		charCount += 1
	newStr += '}'
	return newStr, charCount

def GetCurveRectMinMax (ob):
	bounds = [( ob.matrix_world @ Vector(corner) ) for corner in ob.bound_box]
	box = []
	box.append(min([ bounds[0][0], bounds[1][0], bounds[2][0], bounds[3][0] ]))
	box.append(min([ bounds[0][1], bounds[1][1], bounds[4][1], bounds[5][1] ]))
	box.append(max([ bounds[4][0], bounds[5][0], bounds[6][0], bounds[7][0] ]))
	box.append(max([ bounds[2][1], bounds[3][1], bounds[6][1], bounds[7][1] ]))
	_min = Vector(( box[0], box[1] ))
	_max = Vector(( box[2], box[3] ))
	return _min, _max

def IsInAnyElement (o, arr : list):
	for elmt in arr:
		if o in elmt:
			return True
	return False

def Copy (ob, copyData = True, copyActions = True, collection = None):
	copy = ob.copy()
	if copyData:
		copy.data = copy.data.copy()
	if copyActions and copy.animation_data:
		copy.animation_data.action = copy.animation_data.action.copy()
	if collection == None:
		collection = bpy.context.collection
	collection.objects.link(copy)
	for child in ob.children:
		childCopy = Copy(child, copyData, copyActions, collection)
		childCopy.parent = copy
	return copy

DEFAULT_COLOR = [ 0, 0, 0, 0 ]
exportedObs = []
meshes = []
curves = []
empties = []
datas = {}
head = [ HEADER, HEADER_OBJECT ]#, HEADER_EVENT ]
setup = [ 'fn void main() @extern("main") @wasm {' ]
draw  = []
svgText = ''
userWasmExtern = ''
userJsLibAPI = ''

def ExportObject (ob, wasm = False, html = None, useHtml = False):
	global draw
	global setup
	if ob.hide_get() or ob in exportedObs:
		return
	world = bpy.data.worlds[0]
	resX = world.c3_export_res_x
	resY = world.c3_export_res_y
	SCALE = world.c3_export_scale
	offX = world.c3_export_offset_x
	offY = world.c3_export_offset_y
	off = Vector(( offX, offY ))
	sname = GetSafeName(ob)
	x, y, z = ob.location * SCALE
	y = -y
	z = -z
	x += offX
	y += offY
	z += offY
	sx, sy, sz = ob.scale * SCALE
	idx = len(meshes + curves + empties)
	scripts = []
	if ob.type == 'EMPTY' and len(ob.children) > 0:
		empties.append(ob)
		setup.append('	objects[%s].pos = {%s,%s};' %( idx, x, z ))
		if HandleCopyObject(ob, idx):
			return
		idData, idDataLen = ToC3(ob.name)
		head.append('const char[%s] ID_%s = %s;' %( idDataLen, sname.upper(), idData ))
		firstAndLastChildIdsTxt = ''
		firstAndLastChildIdsTxt += str(ob.children[0].name) + ',' + str(ob.children[-1].name)
		firstAndLastChildIdsData, firstAndLastChildIdsDataLen = ToC3(firstAndLastChildIdsTxt)
		head.append('const char[%s] FIRST_AND_LAST_CHILD_IDS_%s = %s;' %( firstAndLastChildIdsDataLen, sname.upper(), firstAndLastChildIdsData ))
		setup.append('	add_group((char[]*) &%s, %s, (char[]*) &%s, %s);' %( 'ID_' + sname.upper(), idDataLen, 'FIRST_AND_LAST_CHILD_IDS_' + sname.upper(), firstAndLastChildIdsDataLen ))
		for child in ob.children:
			ExportObject (child)
	elif ob.type == "MESH":
		meshes.append(ob)
		setup.append('	objects[%s].pos = {%s,%s};' %( idx, x, z ))
		setup.append('	objects[%s].scale = {%s,%s};' %( idx, sx, sz ))
		#setup.append('	objects[%s].color=raylib::color_from_hsv(%s,1,1);' %( idx, random() ))
		if len(ob.material_slots) > 0:
			materialColor = ob.material_slots[0].material.diffuse_color
		else:
			materialColor = DEFAULT_COLOR
		setup.append('	objects[%s].color = { %s, %s, %s, %s };' %( idx, round(materialColor[0] * 255), round(materialColor[1] * 255), round(materialColor[2] * 255) ))
		draw.append('	self = objects[%s]; //MESH: %s' %( idx, ob.name ))
		if scripts:
			props = {}
			for prop in ob.keys():
				if prop.startswith(( '_', 'c3_' )):
					continue
				#head.append('float %s_%s = %s;' %( sname, prop, ob[prop] ))
				head.append('float %s_%s = %s;' %( prop, sname, ob[prop] ))
				props[prop] = ob[prop]
			# user C3 scripts
			for s in scripts:
				for prop in props:
					if 'self.' + prop in s:
						#s = s.replace('self.'+prop, '%s_%s'%( sname, prop ))
						s = s.replace('self.' + prop, '%s_%s' %( prop, sname ))
				draw.append('\t' + s)
			# save object state: from stack back to heap
			draw.append('	objects[%s] = self; //MESH: %s' %( idx, ob.name ))
		if ob.display_type in ( 'TEXTURED', 'SOLID' ):
			if IsCircle(ob):
				rad = ob.data.vertices[0].co.y
				if not rad:
					for v in ob.data.vertices:
						print(v.co)
					print('WARN: not a circle? %s' %ob.name)
					rad = 1.0
				if wasm:
					#draw.append('	draw_circle_wasm((int)self.position.x,(int) self.position.y, self.scale.x, self.color);')
					draw.append('	draw_circle_wasm((int) self.position.x,(int) self.position.y, self.scale.x * %s, self.color);' %rad)
				else:
					#draw.append('	raylib::draw_circle_v(self.position, self.scale.x, self.color);')
					draw.append('	raylib::draw_circle_v(self.position, self.scale.x * %s, self.color);' %rad)
			else:
				draw.append('	raylib::draw_rectangle_v(self.position, self.scale, self.color);')
	elif ob.type == 'GREASEPENCIL':
		meshes.append(ob)
		if HasScript(ob, False):
			setup.append('	objects[%s].pos = { %s, %s };' %( idx, x, z ))
			sx, sy, sz = ob.scale
			setup.append('	objects[%s].scale = { %s, %s };' %( idx, sx, sz ))
		if wasm:
			GreaseToC3Wasm (ob, datas, head, draw, setup, scripts, idx)
		else:
			GreaseToC3Raylib (ob, datas, head, draw, setup)
	elif ob.type == 'CURVE':
		curves.append(ob)
		bpy.ops.object.select_all(action = 'DESELECT')
		ob.select_set(True)
		bpy.ops.curve.export_svg()
		svgText = open('/tmp/Output.svg', 'r').read()
		svgText_ = svgText
		indexOfName = svgText_.find(ob.name)
		indexOfGroupStart = svgText_.rfind('\n', 0, indexOfName)
		groupEndIndicator = '</g>'
		indexOfGroupEnd = svgText_.find(groupEndIndicator, indexOfGroupStart) + len(groupEndIndicator)
		group = svgText_[indexOfGroupStart : indexOfGroupEnd]
		parentGroupIndicator = '\n  <g'
		indexOfParentGroupStart = svgText_.find(parentGroupIndicator)
		indexOfParentGroupContents = svgText_.find('\n', indexOfParentGroupStart + len(parentGroupIndicator))
		indexOfParentGroupEnd = svgText_.rfind('</g')
		min, max = GetCurveRectMinMax(ob)
		# min *= Vector((sx, sy))
		# max *= Vector((sx, sy))
		min *= SCALE
		min += off
		max *= SCALE
		max += off
		setup.append('	objects[%s].pos = { %s, %s };' %( idx, round(min.x), round(max.y) ))
		if HandleCopyObject(ob, idx):
			return
		print(ob.name)
		if len(ob.material_slots) > 0:
			materialColor = ob.material_slots[0].material.diffuse_color
		else:
			materialColor = DEFAULT_COLOR
		size = max - min
		setup.append('	objects[%s].scale = { %s, %s };' %( idx, round(size.x), round(size.y) ))
		setup.append('	objects[%s].color = { %s, %s, %s, %s };' %( idx, round(materialColor[0] * 255), round(materialColor[1] * 255), round(materialColor[2] * 255), round(materialColor[3] * 255) ))
		svgText_ = svgText_[: indexOfParentGroupContents] + group + svgText_[indexOfParentGroupEnd :]
		pathDataIndicator = ' d="'
		indexOfPathDataStart = svgText_.find(pathDataIndicator) + len(pathDataIndicator)
		indexOfPathDataEnd = svgText_.find('"', indexOfPathDataStart)
		pathData = svgText_[indexOfPathDataStart : indexOfPathDataEnd]
		pathData = pathData.replace('.0', '')
		pathData_ = []
		pathDataLen = 0
		vectors = pathData.split(' ')
		minPathValue = Vector(( float('inf'), float('inf') ))
		maxPathValue = Vector(( -float('inf'), -float('inf') ))
		for vector in vectors:
			if len(vector) == 1:
				continue
			components = vector.split(',')
			x = int(components[0])
			y = int(components[1])
			vector = Vector(( x, y ))
			minPathValue = GetMinComponents(minPathValue, vector, True)
			maxPathValue = GetMaxComponents(maxPathValue, vector, True)
			pathData_.append(x)
			pathData_.append(y)
			pathDataLen += 2
		minPathValue *= SCALE
		maxPathValue *= SCALE
		offset = -minPathValue
		for i, pathValue in enumerate(pathData_):
			pathData_[i] = int(pathValue + offset[i % 2])
		pathData_ = '{' + str(pathData_)[1 : -1] + '}'
		for i, quantizeTypeEnumItem in enumerate(QUANTIZE_TYPES_ENUM_ITEMS):
			if quantizeTypeEnumItem[0] == ob.quantizeType:
				quantizeType = i
				break
		pathDataType = 'char'
		if quantizeType == 1:
			pathDataType = 'ushort'
		head.append('const %s[%s] PATH_DATA_%s = %s;' %( pathDataType, pathDataLen, sname.upper(), pathData_ ))
		idData, idDataLen = ToC3(ob.name)
		head.append('const char[%s] ID_%s = %s;' %( idDataLen, sname.upper(), idData ))
		cyclic = ob.data.splines[0].use_cyclic_u
		isCyclicStr = str(cyclic).lower()
		collideStr = str(ob.collide).lower()
		strokeColorArg = 'null'
		strokeWidth = 0
		if ob.useSvgStroke:
			strokeColorStr = '{ %s, %s, %s, 0 }' %( round(ob.svgStrokeColor[0] * 255), round(ob.svgStrokeColor[1] * 255), round(ob.svgStrokeColor[2] * 255) )
			head.append('const Color LINE_COLOR_%s = %s;' %( sname.upper(), strokeColorStr ))
			strokeColorArg = '(Color*) &LINE_COLOR_' + sname.upper()
			strokeWidth = ob.svgStrokeWidth
		setup.append('	draw_svg(&(objects[%s].pos), &(objects[%s].scale), &(objects[%s].color), %s, %s, (char[]*) &%s, %s, (%s[]*) &%s, %s, %s, %s, %s, %s);'
			%( idx, idx, idx, strokeWidth, strokeColorArg, 'ID_' + sname.upper(), idDataLen, 'usz', 'PATH_DATA_' + sname.upper(), pathDataLen, round(ob.location.z), isCyclicStr, collideStr, quantizeType ))
	elif ob.type == 'FONT' and wasm:
		cscale = ob.data.size * SCALE
		if useHtml:
			css = 'position:absolute; left:%spx; top:%spx; font-size:%spx;' %( x + (cscale * 0.1), z - cscale, cscale )
			div = '<div id="%s" style="%s">%s</div>' %( sname, css, ob.data.body )
			html.append(div)
			return
		meshes.append(ob)
		hide = 'false'
		if ob.hide:
			setup.append('	objects[%s].hide = true;' %idx)
			hide = 'true'
		if ob.parent:
			x, y, z = ob.location * SCALE
			z = -z
		dom_name = ob.name
		if dom_name.startswith('_'):
			dom_name = ''
		if ob.parent and HasScript(ob.parent, False):
			setup += [
				'	objects[%s].pos = {%s, %s};' %( idx, x + (cscale * 0.1), z - (cscale * 1.8) ),
				'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' %( idx, ob.data.body, x + (cscale * 0.1), z - (cscale * 1.8), cscale, hide, dom_name ),
			]
		elif ob.parent:
			fx = x + (cscale * 0.1)
			fy = z - (cscale * 1.8)
			fx += (ob.parent.location.x * SCALE) + offX
			fy += (ob.parent.location.z * SCALE) + offY
			setup += [
				'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' %( idx, ob.data.body, fx,fy, cscale, hide, dom_name ),
			]
		else:
			fx = x + (cscale * 0.1)
			fy = z - (cscale * 1.8)
			setup += [
				'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' %( idx, ob.data.body, fx,fy, cscale, hide, dom_name ),
			]
		if ob.scale.y != 1.0:
			setup += [
				'	objects[%s].css_scale_y(%s);' %( idx, ob.scale.y ),
			]
		if ob.location.y >= 0.1:
			setup.append('	html_css_zindex(objects[%s].id, -%s);' %( idx, int(ob.location.y * 10) ))
		elif ob.location.y <= -0.1:
			setup.append('	html_css_zindex(objects[%s].id, %s);' %( idx, abs(int(ob.location.y * 10)) ))
		# slightly bigger than using html_css_zindex
		#if ob.location.y >= 0.1:
		#	setup.append('	html_css_int(objects[%s].id,"zIndex",-%s);' %( idx, int(ob.location.y * 10) ))
		#elif ob.location.y <= -0.1:
		#	setup.append('	html_css_int(objects[%s].id,"zIndex", %s);' %( idx, abs(int(ob.location.y * 10)) ))
		if scripts or (ob.parent and HasScript(ob.parent, False)):
			draw.append('	self = objects[%s]; // %s' %( idx, ob.name ))
		if scripts:
			props = {}
			for prop in ob.keys():
				if prop.startswith( ('_', 'c3_') ):
					continue
				#head.append('float %s_%s = %s;' %( sname, prop, ob[prop] )) 
				# Error: A letter must precede any digit `__001` (object copy in blender renames with .00N)
				if ob[prop] == 0:
					head.append('float %s_%s;' %( prop, sname )) 
				else:
					head.append('float %s_%s = %s;' %( prop, sname, ob[prop] ))
				props[prop] = ob[prop]
			# user C3 scripts
			for s in scripts:
				for prop in props:
					if 'self.' + prop in s:
						#s = s.replace('self.'+prop, '%s_%s' %(sname,prop))
						s = s.replace('self.' + prop, '%s_%s' %( prop, sname ))
				draw.append('\t' + s)
		if ob.parent != None and HasScript(ob.parent, False):
			if prevParentName != ob.parent.name:
				prevParentName = ob.parent.name
				#draw.append('parent = objects[%s_id];' % GetSafeName(ob.parent))
				draw.append('parent = objects[%s_ID];' %GetSafeName(ob.parent).upper())
			draw += [
				#'parent = objects[%s_id];' % GetSafeName(ob.parent),
				#'self.position.x=parent.position.x;',
				#'self.position.y=parent.position.y;',
				'html_set_position(self.id, self.position.x + parent.position.x, self.position.y + parent.position.y);',
			]
	exportedObs.append(ob)

def HandleCopyObject (ob, idx):
	for exportedOb in exportedObs:
		indexOfPeriod = ob.name.find('.')
		if indexOfPeriod == -1:
			obNameWithoutPeriod = ob.name
		else:
			obNameWithoutPeriod = ob.name[: indexOfPeriod]
		indexOfPeriod = exportedOb.name.find('.')
		if indexOfPeriod == -1:
			exportedObNameWithoutPeriod = exportedOb.name
		else:
			exportedObNameWithoutPeriod = exportedOb.name[: indexOfPeriod]
		if obNameWithoutPeriod == exportedObNameWithoutPeriod:
			idData, idDataLen = ToC3(exportedOb.name)
			setup.append('	copy_node((char[]*) &%s, %s, &(objects[%s].pos));' %( 'ID_' + GetSafeName(exportedOb).upper(), idDataLen, idx ))
			exportedObs.append(ob)
			return True
	return False

def BlenderToC3 (world, wasm = False, html = None, useHtml = False, methods = {}):
	global head
	global draw
	global setup
	global datas
	global meshes
	global curves
	global empties
	global svgText
	global exportedObs
	global userJsLibAPI
	global userWasmExtern
	for ob in bpy.data.objects:
		if '_Clone' in ob.name:
			for child in ob.children:
				bpy.data.objects.remove(child, do_unlink = True)
			bpy.data.objects.remove(ob, do_unlink = True)
	exportedObs = []
	userWasmExtern = ''
	userJsLibAPI = ''
	resX = world.c3_export_res_x
	resY = world.c3_export_res_y
	SCALE = world.c3_export_scale
	offX = world.c3_export_offset_x
	offY = world.c3_export_offset_y
	off = Vector(( offX, offY ))
	unpackers = {}
	drawHeader = [ 'fn void game_frame() @extern("$") @wasm {' ]
	head = [ HEADER, HEADER_OBJECT ]#, HEADER_EVENT ]
	setup = [ 'fn void main() @extern("main") @wasm {' ]
	draw = []
	if wasm:
		setup.append(MAIN_WASM %( resX, resY ))
		# draw.append('	html_canvas_clear();')
		# head.append(HEADER_OBJECT_WASM)
		head.append(WASM_EXTERN)
		# head.append(WASM_HELPERS)
	else:
		setup.append(MAIN %( resX, resY ))
		draw.append('	raylib::begin_drawing();')
		draw.append('	raylib::clear_background({ 0xFF, 0xFF, 0xFF, 0xFF });')
	global_v2arrays = {}
	meshes = []
	curves = []
	empties = []
	datas = {}
	prevParentName = None
	for ob in bpy.data.objects:
		ExportObject (ob, wasm, useHtml, html)
	for ob in bpy.data.objects:
		for scriptInfo in GetScripts(ob, True):
			script = scriptInfo[0]
			isJs = scriptInfo[1]
			isC3 = scriptInfo[2]
			if isJs and not isC3:
				userJsLibAPI += script
				continue
			elif '(' not in script or (isC3 and not isJs):
				userWasmExtern += script
			else:
				lns = script.split('\n')
				braceTier = 0
				currentMethod = ''
				for ln in lns:
					if '{' in ln:
						braceTier += 1
					if braceTier == 0:
						indexOfArgsStart = ln.find('(')
						if indexOfArgsStart == -1:
							userWasmExtern += ln + '\n'
							currentMethod += ln + '\n'
							continue
						indexOfArgsEnd = ln.find(')')
						args = ln[indexOfArgsStart : indexOfArgsEnd]
						argsList = args.split(', ')
						indexOfMethodNameEnd = ln.rfind(' ', 0, indexOfArgsStart)
						if indexOfMethodNameEnd == -1:
							indexOfMethodNameEnd = indexOfArgsStart
						methodName = ln[: indexOfMethodNameEnd]
						if isJs:
							newMethodName = ''
							argNum = 0
							for char in methodName:
								if argNum > 0 and char.isupper():
									newMethodName += '_'
								newMethodName += char.lower()
								argNum += 1
							argsNames = ''
							for arg in argsList:
								argNameAndValue = arg.split(' ')
								if len(argNameAndValue) == 2:
									argsNames += argNameAndValue[1] + ','
							argsNames = argsNames[: -1]
							if len(argsNames) == 0:
								currentMethod = ln + '\n'
							else:
								currentMethod = ln.replace(args[1 :], argsNames) + '\n'
							wasmExternTxt = 'extern fn void ' + newMethodName + ' ' + args
							wasmExternTxt += ') @extern("' + methodName + '");'
							userWasmExtern += wasmExternTxt + '\n'
					else:
						currentMethod += ln + '\n'
						if '}' in ln:
							braceTier -= 1
							if braceTier == 0:
								raylib_like_api[methodName] = currentMethod
								currentMethod = ''
		for scriptInfo in GetScripts(ob, False):
			script = scriptInfo[0]
			isInit = scriptInfo[1]
			if isInit:
				setup.append(script)
			else:
				draw.append(script)
	head.append(userWasmExtern)
	if global_v2arrays:
		for gname in global_v2arrays:
			head.append(global_v2arrays[gname])
	setup.append('}')
	if 'self' in '\n'.join(draw):
		drawHeader.append('	Object self;')
	if 'parent' in '\n'.join(draw):
		drawHeader.append('	Object parent;')
	if 'delta_time' in '\n'.join(draw):
		drawHeader.append('	float delta_time = raylib::get_frame_time();')
	if not wasm:
		draw.append('	raylib::end_drawing();')
	draw.append('}')
	head.append('Object[%s] objects;' %len(meshes + curves + empties))
	if unpackers:
		for gkey in unpackers:
			head += unpackers[gkey]
	for dname in datas:
		print(dname)
		print('orig-points:', datas[dname]['orig-points'])
		print('total-points:', datas[dname]['total-points'])
	return head + setup + drawHeader + draw

def GreaseToC3Wasm (ob, datas, head, draw, setup, scripts, obIndex):
	SCALE = WORLD.c3_export_scale
	offX = WORLD.c3_export_offset_x
	offY = WORLD.c3_export_offset_y
	sx, sy, sz = ob.scale * SCALE
	x, y, z = ob.location * SCALE
	dname = GetSafeName(ob.data)
	gquant = False
	if ob.data.c3_grease_quantize != '32bits':
		gquant = ob.data.c3_grease_quantize
	gopt = ob.data.c3_grease_optimize
	if dname not in datas:
		datas[dname] = { 'orig-points' : 0, 'total-points' : 0, 'draw' : [] }
		data = []
		for lidx, layer in enumerate(ob.data.layers):
			for sidx, stroke in enumerate(layer.frames[0].drawing.strokes):
				datas[dname]['orig-points'] += len(stroke.points)
				mat = ob.data.materials[stroke.material_index]
				use_fill = 0
				if mat.grease_pencil.show_fill:
					use_fill = 1
				if gopt:
					points = []
					for pidx in range(0, len(stroke.points), gopt):
						points.append(stroke.points[pidx])
				else:
					points = stroke.points
				s = []
				if gquant:
					qstroke = Quantizer(points, gquant)
					n = len(qstroke['points'])
					if not len(qstroke['points']):
						print('stroke quantized away:', stroke)
						continue
					datas[dname]['total-points'] += len(qstroke['points'])
					x0, y0,z0 = points[0].position
					q = qstroke['q']
					qs = qstroke['qs']
					setup += [
						'_unpacker_%s(&__%s__%s_%s_pak,' %(dname, dname, lidx, sidx),
						'	&__%s__%s_%s,' %(dname, lidx, sidx),
						'	%s,' % n,
						'	%s, %s' %(x0 * q, z0 * q),
						');',
					]
					data.append('Vector2_%s[%s] __%s__%s_%s_pak = {%s};' %(gquant, n, dname, lidx, sidx, ','.join(qstroke['points'])))
					if gquant in ('6bits', '7bits'):
						data.append('Vector2[%s] __%s__%s_%s;' %( (n * 3), dname, lidx, sidx ))
					else:
						data.append('Vector2[%s] __%s__%s_%s;' %(n + 1, dname, lidx, sidx ))
						n += 1
				else:
					# Default 32bit floats #
					s = []
					if scripts:
						for pnt in points:
							x1,y1,z1 = pnt.position * SCALE
							s.append('{%s,%s}' %(x1, -z1))
					else:
						for pnt in points:
							x1, y1, z1 = pnt.position
							x1 *= sx
							z1 *= sz
							s.append('{%s,%s}' %(x1 + offX + x, -z1 + offY + z))
					data.append('Vector2[%s] __%s__%s_%s = {%s};' %(len(points), dname, lidx, sidx, ','.join(s)))
					n = len(s)
				if gquant in ('6bits', '7bits'):
					nn = n*3
				else:
					nn = n
				r, g, b, a = mat.grease_pencil.fill_color
				swidth = GetStrokeWidth(stroke)
				datas[dname]['draw'].append({'layer' : lidx, 'index' : sidx, 'length' : nn, 'width' : swidth, 'fill' : use_fill, 'color' : [ r, g, b, a ]})
		head += data
		if gquant:
			if gquant in ('6bits', '7bits'):
				head += GetDeltaDeltaUnpacker(ob, dname, gquant, SCALE, qs, offX, offY)
			else:
				head += GetDeltaUnpacker(ob, dname, gquant, SCALE, qs, offX, offY)
	oname = sname = GetSafeName(ob)
	if scripts:
		draw.append('	self = objects[%s];' %obIndex)
		props = {}
		for prop in ob.keys():
			if prop.startswith( ('_', 'c3_') ):
				continue
			head.append('float %s_%s = %s;' %(sname, prop, ob[prop]))
			props[prop] = ob[prop]
		# User C3 scripts
		for s in scripts:
			for prop in props:
				if 'self.' + prop in s:
					s = s.replace('self.' + prop, '%s_%s' %(sname,prop))
			draw.append('\t' + s)
		# Save object state from stack back to heap
		draw.append('	objects[%s] = self; // %s' %(obIndex, ob.name))
	for a in datas[dname]['draw']:
		r, g, b, alpha = a['color']
		r = int(r * 255)
		g = int(g * 255)
		b = int(b * 255)
		if not scripts:
			# Static grease pencil
			if a['fill']:
				draw.append('	draw_spline_wasm(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' %(dname, a['layer'], a['index'], a['length'], a['width'], a['fill'], r, g, b, alpha))
			else:
				draw.append('	draw_spline_wasm(&__%s__%s_%s,%s,%s, 0, 0,0,0,0);' %(dname, a['layer'], a['index'], a['length'], a['width']))
		else:
			tag = [oname, a['layer'], a['index']]
			head.append('Vector2[%s] _%s_%s_%s;' % tuple([a['length']] + tag) )
			dtag = [dname, a['layer'], a['index']]
			draw += [
				'	transform_spline_wasm(&__%s__%s_%s, &_%s_%s_%s, %s, objects[%s].position, objects[%s].scale);' %tuple(dtag + tag + [ a['length'], obIndex, obIndex ]),
				'	draw_spline_wasm(&_%s_%s_%s, %s, %s, %s, %s,%s,%s,%s);' %(oname, a['layer'], a['index'], a['length'], a['width'], a['fill'], r, g, b, alpha)
			]

def GetDeltaDeltaUnpacker (ob, dname, gquant, SCALE, qs, offX, offY):
	x, y, z = ob.location * SCALE
	sx, sy, sz = ob.scale
	gkey = (dname, gquant)
	# TODO Only gen single packer per quant
	qkey = gquant.split('bit')[0]
	return [
		'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0) @extern("u%s") {' %( dname, gquant, qkey ),
		'	int j=0;',
		'	out[0].x = (x0*%sf) + %sf;' %( qs * sx, offX + x ),
		'	out[0].y = -(z0*%sf) + %sf;'  %( qs * sz, offY + z ),
		'	for (int i=0; i<len; i++){',
		'		float ax = ( (x0 - pak[i].x0) * %sf) + %sf;' %( qs * sx, offX + x ),
		'		float ay = ( -(z0 - pak[i].y0) * %sf) + %sf;' %( qs * sz, offY + z ),

		'		j++;',
		'		out[j].x = ax;',
		'		out[j].y = ay;',

		'		j++;',
		'		out[j].x = ((x0 - (float)(pak[i].x0 - pak[i].x1)) * %sf) + %sf;' %( qs * sx, offX + x ),
		'		out[j].y = ( -(z0 - (float)(pak[i].y0 - pak[i].y1)) * %sf) + %sf;' %( qs * sz, offY + z ),

		'		j++;',
		'		out[j].x = ((x0 - (float)(pak[i].x0 - pak[i].x2)) * %sf) + %sf;' %( qs * sx, offX + x ),
		'		out[j].y = ( -(z0 - (float)(pak[i].y0 - pak[i].y2)) * %sf) + %sf;' %( qs * sz, offY + z ),
		'	}',
		'}'
	]

def GetDeltaUnpacker (ob, dname, gquant, SCALE, qs, offX, offY):
	x, y, z = ob.location * SCALE
	sx, sy, sz = ob.scale
	gkey = (dname, gquant)
	return [
		'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0){' %gkey,
		'	out[0].x = (x0*%sf) + %sf;' %( qs * sx, offX + x ),
		'	out[0].y = -(z0*%sf) + %sf;'  %( qs * sz, offY + z ),
		'	for (int i = 0; i < len; i ++){',
		'		float a = ( (x0 - pak[i].x) * %sf) + %sf;' %( qs * sx, offX + x ),
		'		out[i + 1].x = a;',
		'		a = ( -(z0 - pak[i].y) * %sf) + %sf;' %( qs * sz, offY + z ),
		'		out[i + 1].y = a;',
		'	}',
		'}'
	]

def GreaseToC3Raylib (ob, datas, head, draw, setup):
	SCALE = WORLD.c3_export_scale
	offX = WORLD.c3_export_offset_x
	offY = WORLD.c3_export_offset_y
	sx, sy, sz = ob.scale * SCALE
	x, y, z = ob.location * SCALE
	dname = GetSafeName(ob.data)
	gquant = False
	if ob.data.c3_grease_quantize != '32bits':
		gquant = ob.data.c3_grease_quantize
	if dname not in datas:
		datas[dname] = 0
		data = []
		for lidx, layer in enumerate(ob.data.layers):
			for sidx, stroke in enumerate(layer.frames[0].drawing.strokes):
				datas[dname] += len(stroke.points)
				mat = ob.data.materials[stroke.material_index]
				use_fill = 0
				if mat.grease_pencil.show_fill: use_fill = 1
				s = []
				if use_fill:
					if mat.c3_export_trifan:
						x1,y1,z1 = GetCenter(stroke.points)
						x1 *= sx
						z1 *= sz
						s.append('{%s,%s}' %(x1 + offX + x, -z1 + offY + z))
					elif mat.c3_export_tristrip:
						tri_strip = True
					else:
						tris = []
						for tri in stroke.triangles:
							tris.append(tri.v1)
							tris.append(tri.v2)
							tris.append(tri.v3)
						tris = ','.join([str(vidx) for vidx in tris])
						data.append('int[%s] __%s__%s_%s_tris = {%s};' %( len(stroke.triangles) * 3,dname, lidx, sidx, tris ))
					# Default 32bit floats
					for pnt in stroke.points:
						x1,y1,z1 = pnt.position
						x1 *= sx
						z1 *= sz
						s.append('{%s,%s}' %( x1 + offX + x, -z1 + offY + z ))
					n = len(s)
					data.append('Vector2[%s] __%s__%s_%s = {%s};' %( n, dname, lidx, sidx, ','.join(s) ))
				elif gquant:
					qstroke = Quantizer(stroke.points, gquant)
					n = len(qstroke['points'])
					if not len(qstroke['points']):
						print('stroke quantized away:', stroke)
						continue
					data.append('Vector2[%s] __%s__%s_%s;' %(n+1,dname, lidx, sidx ))
					data.append('Vector2_%s[%s] __%s__%s_%s_pak = {%s};' %( gquant,n,dname, lidx, sidx, ','.join(qstroke['points']) ))
					x0, y0, z0 = stroke.points[0].position
					q = qstroke['q']
					qs = qstroke['qs']
					setup += [
						'_unpacker_%s(&__%s__%s_%s_pak,' %(dname, dname, lidx, sidx),
						'	&__%s__%s_%s,' %(dname, lidx, sidx),
						'	%s,' % len(stroke. points),
						'	%s, %s' %( x0 * q, z0 * q ),
						');',
					]
				else:
					# Default 32bit floats
					s = []
					for pnt in stroke.points:
						x1,y1,z1 = pnt.position
						x1 *= sx
						z1 *= sz
						s.append('{%s,%s}' %(x1 + offX + x, -z1 + offY + z))
					data.append('Vector2[%s] __%s__%s_%s = {%s};' %( len(stroke.points),dname, lidx, sidx, ','.join(s) ))
					n = len(s)
				r, g, b, a = mat.grease_pencil.fill_color
				swidth = GetStrokeWidth(stroke)
				if use_fill:
					clr = '{%s,%s,%s,%s}' %(int(r * 255), int(g * 255), int(b * 255), int(a * 255))
					if mat.c3_export_trifan:
						draw.append('	raylib::draw_triangle_fan(&__%s__%s_%s, %s, %s);' %( dname, lidx, sidx, n, clr ))
					elif mat.c3_export_tristrip:
						draw.append('	raylib::draw_triangle_strip(&__%s__%s_%s, %s, %s);' %( dname, lidx, sidx, n, clr ))
					else:
						draw += [
							'	for (int i=0; i<%s; i+=3){' %(len(stroke.triangles) * 3),
							'		int idx = __%s__%s_%s_tris[i+2];' %( dname, lidx, sidx ),
							'		Vector2 v1 = __%s__%s_%s[idx];' %( dname, lidx, sidx ),
							'		idx = __%s__%s_%s_tris[i+1];'   %( dname, lidx, sidx ),
							'		Vector2 v2 = __%s__%s_%s[idx];' %( dname, lidx, sidx ),
							'		idx = __%s__%s_%s_tris[i+0];'   %( dname, lidx, sidx ),
							'		Vector2 v3 = __%s__%s_%s[idx];' %( dname, lidx, sidx ),
							'		raylib::draw_triangle(v1,v2,v3, %s);' % clr,
							'	}',
						]
					if mat.grease_pencil.show_stroke:
						draw.append('	raylib::draw_spline( (&__%s__%s_%s), %s, 4.0, {0x00,0x00,0x00,0xFF});' %( dname, lidx, sidx, n ))
				else:
					draw.append('	raylib::draw_spline(&__%s__%s_%s, %s, %s, {0x00,0x00,0x00,0xFF});' %( dname, lidx, sidx, n, swidth ))
		head += data
		if gquant:
			x, y, z = ob.location * SCALE
			sx, sy, sz = ob.scale
			gkey = ( dname, gquant )
			head += [
				'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0){' %gkey,
				'	out[0].x = (x0*%sf) + %sf;' %( qs * sx, offX + x ),
				'	out[0].y = -(z0*%sf) + %sf;'  %( qs * sz, offY + z ),
				'	for (int i = 0; i < len; i ++){',
				'		float a = ( (x0 - pak[i].x) * %sf) + %sf;' %( qs * sx, offX + x ),
				'		out[i + 1].x = a;',
				'		a = ( -(z0 - pak[i].y) * %sf) + %sf;' %( qs * sz, offY + z ),
				'		out[i + 1].y = a;',
				'	}',
				'}'
			]

def Quantizer (points, quant, trim = True):
	SCALE = WORLD.c3_export_scale
	s = []
	if quant == '4bits':
		q = SCALE * 0.125
		qs = 8
	elif quant == '6bits' or quant == '7bits':
		q = SCALE * 0.5
		qs = 2
	elif quant == '8bits' or quant == "7x5x4bits":
		q = SCALE * 0.5
		qs = 2
	else:
		q = SCALE
		qs = 1
	x0, y0, z0 = points[0].position
	mvec = []
	for pnt in points[1:]:
		x1,y1,z1 = pnt.position
		dx = int((x0 - x1) * q)
		dz = int((z0 - z1) * q)
		if quant == '4bits':
			if dx > 7:
				print('WARN: 4bit vertex clip x=', dx)
				dx = 7
			elif dx < -8:
				print('WARN: 4bit vertex clip x=', dx)
				dx = -8
			if dz > 7:
				print('WARN: 4bit vertex clip z=', dz)
				dz = 7
			elif dz < -8:
				print('WARN: 4bit vertex clip z=', dz)
				dz = -8
		elif quant == '6bits':
			if dx >= 32:
				print('WARN: 6bit vertex clip x=', dx)
				dx = 31
			elif dx < -32:
				print('WARN: 6bit vertex clip x=', dx)
				dx = -32
			if dz >= 32:
				print('WARN: 6bit vertex clip z=', dz)
				dz = 31
			elif dz < -32:
				print('WARN: 6bit vertex clip z=', dz)
				dz = -32
		if quant in ('6bits', '7bits'):
			if mvec:
				mdx, mdz = mvec[0]
				# Delta of delta
				ddx = mdx-dx
				ddy = mdz-dz
				if quant == '6bits':  # After 5bits
					if ddx >= 16: ddx = 15
					elif ddx < -16: ddx = -16
					if ddy >= 16: ddy = 15
					elif ddy < -16: ddy = -16
				else:  # After 4bits
					if ddx >= 8: ddx = 7
					elif ddx < -8: ddx = -8
					if ddy >= 8: ddy = 7
					elif ddy < -8: ddy = -8
				v = ( ddx, ddy )
			else:
				v = ( dx, dz )
			mvec.append(v)
			if len(mvec) >= 3:
				s.append('{%s}' % ', '.join('%s,%s' %v for v in mvec))
				mvec = []
		else:
			vec = '{%s,%s}' %(dx, dz)
			if trim:
				if s and s[-1] == vec:
					continue
			s.append(vec)
	if mvec:
		print('tooshort:', mvec)
		if len(mvec) == 1:
			while len(mvec) < 3:
				mvec.append((0,0))
		else:
			while len(mvec) < 3:
				mvec.append(mvec[-1])
		print('filled:', mvec)
		s.append('{%s}' % ', '.join('%s,%s' %v for v in mvec))
	return { 'q' : q, 'qs' : qs, 'points' : s }

def GetStrokeWidth (stroke):
	sw = 0.0
	for p in stroke.points:
		sw += p.radius
		#sw += p.strength
	sw /= len(stroke.points)
	return sw * stroke.softness * 0.05

def GetCenter (points):
	ax = ay = az = 0.0
	for p in points:
		ax += p.position.x
		ay += p.position.y
		az += p.position.z
	ax /= len(points)
	ay /= len(points)
	az /= len(points)
	return (ax, ay, az)

_BUILD_INFO = {
	'native': None,
	'wasm'  : None,
	'native-size':None,
	'wasm-size':None,
	'zip'     : None,
	'zip-size': None,
}

@bpy.utils.register_class
class C3Export (bpy.types.Operator):
	bl_idname = 'c3.export'
	bl_label = 'C3 Export EXE'

	@classmethod
	def poll (cls, context):
		return True

	def execute (self, context):
		exe = BuildLinux(context.world)
		_BUILD_INFO['native'] = exe
		_BUILD_INFO['native-size'] = len(open(exe, 'rb').read())
		return {'FINISHED'}

@bpy.utils.register_class
class C3Export (bpy.types.Operator):
	bl_idname = 'c3.export_wasm'
	bl_label = 'C3 Export WASM'

	@classmethod
	def poll (cls, context):
		return True

	def execute (self, context):
		exe = BuildWasm(context.world)
		return {'FINISHED'}

@bpy.utils.register_class
class C3WorldPanel (bpy.types.Panel):
	bl_idname = 'WORLD_PT_C3World_Panel'
	bl_label = 'C3 Export'
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'world'

	def draw(self, context):
		row = self.layout.row()
		row.prop(context.world, 'c3_export_res_x')
		row.prop(context.world, 'c3_export_res_y')
		row.prop(context.world, 'c3_export_scale')
		row = self.layout.row()
		row.prop(context.world, 'c3_export_offset_x')
		row.prop(context.world, 'c3_export_offset_y')
		self.layout.prop(context.world, 'c3_export_opt')
		self.layout.prop(context.world, 'c3_export_html')

		self.layout.operator('c3.export_wasm', icon = 'CONSOLE')
		self.layout.operator('c3.export', icon = 'CONSOLE')
		if _BUILD_INFO['native-size']:
			self.layout.label(text = 'exe KB=%s' %( _BUILD_INFO['native-size']//1024 ))

@bpy.utils.register_class
class JS13KB_Panel (bpy.types.Panel):
	bl_idname = "WORLD_PT_JS13KB_Panel"
	bl_label = "js13kgames.com"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"

	def draw (self, context):
		self.layout.prop(context.world, 'c3_js13kb')
		row = self.layout.row()
		row.prop(context.world, 'minify')
		row.prop(context.world, 'c3_invalid_html')
		if context.world.c3_js13kb:
			self.layout.prop(context.world, 'c3_export_zip')
			if _BUILD_INFO['zip-size']:
				self.layout.label(text = _BUILD_INFO['zip'])
				if _BUILD_INFO['zip-size'] <= 1024*13:
					self.layout.label(text = "zip bytes=%s" %( _BUILD_INFO['zip-size'] ))
				else:
					self.layout.label(text = "zip KB=%s" %( _BUILD_INFO['zip-size']//1024 ))
				self.layout.label(text = 'html-size=%s' % _BUILD_INFO['html-size'])
				self.layout.label(text = 'jslib-size=%s' % _BUILD_INFO['jslib-size'])
				self.layout.label(text = 'jslib-gz-size=%s' % _BUILD_INFO['jslib-gz-size'])
		if _BUILD_INFO['wasm-size']:
			if _BUILD_INFO['wasm-size'] < 1024*16:
				self.layout.label(text = "wasm bytes=%s" %( _BUILD_INFO['wasm-size'] ))
			else:
				self.layout.label(text = "wasm KB=%s" %( _BUILD_INFO['wasm-size']//1024 ))

def BuildLinux (world):
	global WORLD
	WORLD = world
	o = BlenderToC3(world)
	o = '\n'.join(o)
	#print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	bin = Build(input = tmp, opt = world.c3_export_opt)
	return bin

JS_DECOMP = '''
var $d=async(u,t)=>{
	var d=new DecompressionStream('gzip')
	var r=await fetch('data:application/octet-stream;base64,'+u)
	var b=await r.blob()
	var s=b.stream().pipeThrough(d)
	var o=await new Response(s).blob()
	if(t) return await o.text()
	else return await o.arrayBuffer()
}
$d($0,1).then((j)=>{
	$=eval(j)
	$d($1).then((r)=>{
		WebAssembly.instantiate(r,{env:$.proxy()}).then((c)=>{$.reset(c,"$",r)});
	});
});
'''
JS_LIB_COLOR_HELPERS = '''
function color_hex_unpacked(r, g, b, a){
	r=r.toString(16).padStart(2,'0');
	g=g.toString(16).padStart(2,'0');
	b=b.toString(16).padStart(2,'0');
	a=a.toString(16).padStart(2,'0');
	return "#"+r+g+b+a
}
function getColorFromMemory(buf,ptr){
	const [r, g, b, a]=new Uint8Array(buf,ptr,4);
	return color_hex_unpacked(r, g, b, a)
}
'''
JS_LIB_API_ENV = '''
function make_environment(e){
	return new Proxy(e,{
		get(t,p,r) {
			if(e[p]!==undefined){return e[p].bind(e)}
			return(...args)=>{throw p}
		}
	})
}
'''
JS_LIB_API_ENV_MINI = '''
function make_environment(e){
	return new Proxy(e,{
		get(t,p,r){return e[p].bind(e)}
	});
}
'''
JS_LIB_API = '''
function wasm_memory ()
{
	return $.wasm.instance.exports.memory.buffer;
}
function get_svg_path (pathData, pathDataLen, cyclic)
{
	var path = 'M ' + pathData[0] + ',' + pathData[1] + ' ';
	for (var i = 2; i < pathDataLen; i += 2)
	{
		if (i - 2 % 6 == 0)
			path += 'C ';
		path += '' + pathData[i] + ',' + pathData[i + 1] + ' ';
	}
	if (cyclic)
		path += 'Z';
	return path;
}
function get_pos_and_size (elmt)
{
	var posXTxt = elmt.getAttribute('x');
	var posX = parseFloat(posXTxt);
	var posYTxt = elmt.getAttribute('y');
	var posY = parseFloat(posYTxt);
	var sizeXTxt = elmt.getAttribute('width');
	var sizeX = parseFloat(sizeXTxt);
	var sizeYTxt = elmt.getAttribute('height');
	var sizeY = parseFloat(sizeYTxt);
	return [ [ posX, posY ], [ sizeX, sizeY ] ]
}
function lerp (min, max, t)
{
	return min + t * (max - min)
}
function clamp (n, min, max)
{
	return Math.min(Math.max(n, min), max);
}
function inv_lerp (from, to, n)
{
	return (n - from) / (to - from);
}
function remap (inFrom, inTo, outFrom, outTo, n)
{
	var t = inv_lerp(inFrom, inTo, n);
	return lerp(outFrom, outTo, t);
}
function overlaps (pos, size, pos2, size2)
{
	return !(pos[0] + size[0] < pos2[0]
		|| pos[0] > pos2[0] + size2[0]
		|| pos[1] + size[1] < pos2[1]
		|| pos[1] > pos2[1] + size2[1])
}
function copy_node (id, pos)
{
	var copy = document.getElementById(id).cloneNode(true);
	copy.setAttribute('x', pos[0]);
	copy.setAttribute('y', pos[1]);
	document.body.appendChild(copy);
	return copy;
}
function random_vector_2d (mD)
{
    var dt = random(0, mD);
    var ag = random(0, 2 * Math.PI);
    return [ Math.cos(ag) * dt, Math.sin(ag) * dt ];
}
function random (min, max)
{
	return Math.random() * (max - min) + min;
}

class api{
	proxy(){
		return make_environment(this)
	}
	reset(wasm,id,bytes){
		this.elts=[];
		this.wasm=wasm;
		this.bytes=new Uint8Array(bytes);
		this.canvas=document.getElementById(id);
		this.ctx=this.canvas.getContext('2d');
		this.wasm.instance.exports.main();
		const f=(ts)=>{
			this.dt=(ts-this.prev)/1000;
			this.prev=ts;
			this.entryFunction();
			window.requestAnimationFrame(f)
		};
		window.requestAnimationFrame((ts)=>{
			this.prev=ts;
			window.requestAnimationFrame(f)
		});
	}
'''
c3dom_api = {
	'html_new_text' : '''
	html_new_text(ptr, r, g, b, h, id)
	{
		var e = document.createElement('pre');
		e.style = 'position:absolute;left:' + r + '; top:' + g + '; font-size:' + b;
		e.hidden = h;
		e.id=cstr_by_ptr(wasm_memory(), id);
		document.body.append(e);
		e.append(cstr_by_ptr(wasm_memory(), ptr));
		return this.elts.push(e) - 1
	}
	''',
	'html_css_string' : '''
	html_css_string(idx,a,b){
		a=cstr_by_ptr(wasm_memory(),a);
		this.elts[idx].style[a]=cstr_by_ptr(wasm_memory(),b)
	}
	''',
	'html_css_int' : '''
	html_css_int(idx,a,b){
		a=cstr_by_ptr(wasm_memory(),a);
		this.elts[idx].style[a]=b
	}
	''',
	'html_set_text' : '''
	html_set_text(idx,ptr){
		this.elts[idx].firstChild.nodeValue=cstr_by_ptr(wasm_memory(),ptr)
	}
	''',
	'html_add_char' : '''
	html_add_char(idx,c){
		this.elts[idx].append(String.fromCharCode(c))
	}
	''',
	'html_css_scale' : '''
	html_css_scale(idx,z){
		this.elts[idx].style.transform='scale('+z+')'
	}
	''',
	'html_css_scale_y' : '''
	html_css_scale_y(idx,z){
		this.elts[idx].style.transform='scaleY('+z+')'
	}
	''',
	'html_set_position' : '''
	html_set_position(idx,x,y){
		var elt = this.elts[idx];
		elt.style.left = x;
		elt.style.top = y
	}
	''',
	'html_css_zindex' : '''
	html_css_zindex(idx,z){
		this.elts[idx].style.zIndex=z
	}
	''',
	'html_bind_onclick' : '''
	html_bind_onclick(idx,f,oidx){
		var elt=this.elts[idx];
		elt._onclick_=$.wasm.instance.exports.__indirect_function_table.get(f);
		elt.onclick=function(){
			self=elt;
			elt._onclick_(oidx)
		}
	}
	''',
	'html_eval' : '''
	html_eval(ptr){
		var _=cstr_by_ptr(wasm_memory(),ptr);
		eval(_)
	}
	''',
	'html_canvas_clear' : '''
	html_canvas_clear(){
		this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height)
	}
	''',
	'html_canvas_resize' : '''
	html_canvas_resize(w,h){
		this.canvas.width=w;
		this.canvas.height=h
	}
	''',
	'wasm_memory' : '''
	wasm_memory(idx){
		return this.bytes[idx]
	}
	''',
	'wasm_size' : '''
	wasm_size(){
		return this.bytes.length
	}
	''',
	'random' : '''
	random(){
		return Math.random()
	}
	''',
}
raylib_like_api = {
	'raylib_js_set_entry' : '''
	_(f){
		this.entryFunction=$.wasm.instance.exports.__indirect_function_table.get(f)
	}
	''',
	'InitWindow' : '''
	InitWindow(w,h,ptr){
		this.canvas.width=w;
		this.canvas.height=h;
		document.title=cstr_by_ptr(wasm_memory(),ptr)
	}
	''',
	'GetScreenWidth' : '''
	GetScreenWidth(){
		return this.canvas.width
	}
	''',
	'GetScreenHeight' : '''
	GetScreenHeight(){
		return this.canvas.height
	}
	''',
	'GetFrameTime' : '''
	GetFrameTime(){
		return Math.min(this.dt,1/30/2)
	}
	''',
	'DrawRectangleV' : '''
	DrawRectangleV(pptr,sptr,cptr){
		const buf=wasm_memory();
		const p=new Float32Array(buf,pptr,2);
		const s=new Float32Array(buf,sptr,2);
		this.ctx.sStyle = getColorFromMemory(buf, cptr);
		this.ctx.fillRect(p[0],p[1],s[0],s[1])
	}
	''',
	'DrawSplineLinearWASM' : '''
	DrawSplineLinearWASM(ptr,l,t,fill,r, g, b, a){
		const buf=wasm_memory();
		const p=new Float32Array(buf,ptr,l*2);
		this.ctx.strokeStyle='black';
		if(fill)this.ctx.fillStyle='rgba('+r+','+g+','+b+','+a+')';
		this.ctx.lineWidth=t;
		this.ctx.beginPath();
		this.ctx.moveTo(p[0],p[1]);
		for(var i=2;i<p.length;i+=2)
			this.ctx.lineTo(p[i],p[i+1]);
		if(fill){
			this.ctx.closePath();
			this.ctx.fill()
		}
		this.ctx.stroke()
	}
	''',
	'DrawCircleWASM' : '''
	DrawCircleWASM(x,y,rad,ptr){
		const buf=wasm_memory();
		const [r, g, b, a]=new Uint8Array(buf, ptr, 4);
		this.ctx.strokeStyle = 'black';
		this.ctx.beginPath();
		this.ctx.arc(x,y,rad,0,2*Math.PI,false);
		this.ctx.fillStyle = color_hex_unpacked(r, g, b, a);
		this.ctx.closePath();
		this.ctx.stroke()
	}
	''',
	'draw_svg' : '''
	draw_svg (pos, size, fillColor, lineWidth, lineColor, id, idLen, pathData, pathDataLen, zIndex, cyclic, collide, quantizeType)
	{
		const buf = wasm_memory();
		const pos_ = new Float32Array(buf, pos, 8);
		const size_ = new Float32Array(buf, size, 8);
		const fillColor_ = new Uint8Array(buf, fillColor, 4);
		var fillColorTxt = 'transparent';
		if (fillColor_[3] > 0)
			fillColorTxt = 'rgb(' + fillColor_[0] + ' ' + fillColor_[1] + ' ' + fillColor_[2] + ')';
		const lineColor_ = new Uint8Array(buf, lineColor, 4);
		var lineColorTxt = 'transparent';
		if (lineWidth > 0)
			lineColorTxt = 'rgb(' + lineColor_[0] + ' ' + lineColor_[1] + ' ' + lineColor_[2] + ')';
		const id_ = new TextDecoder().decode(new Uint8Array(buf, id, idLen - 1));
		if (quantizeType == 0)
			var pathData_ = new Uint8Array(buf, pathData, pathDataLen);
		else if (quantizeType == 1)
			var pathData_ = new Uint16Array(buf, pathData, pathDataLen);
		else if (quantizeType == 2)
			var pathData_ = new Uint32Array(buf, pathData, pathDataLen);
		else
			var pathData_ = new Uint64Array(buf, pathData, pathDataLen);
		var path = get_svg_path(pathData_, pathDataLen, cyclic);
		var prefix = '<svg xmlns="www.w3.org/2000/svg"id="' + id_ + '"viewBox="0 0 ' + (size_[0] + lineWidth * 2) + ' ' + (size_[1] + lineWidth * 2) + '"style="z-index:' + zIndex + ';position:absolute"collide=' + collide + ' x=' + pos_[0] + ' y=' + pos_[1] + ' width=' + size_[0] + ' height=' + size_[1] + ' transform="scale(1,-1)translate(' + pos_[0] + ',' + pos_[1] + ')"><g><path style="fill:' + fillColorTxt + ';stroke-width:' + lineWidth + ';stroke:' + lineColorTxt + '" d="';
		var suffix = '"/></g></svg>';
		document.body.innerHTML += prefix + path + suffix;
	}
	''',
	'ClearBackground' : '''
	ClearBackground(ptr) {
		this.ctx.fillStyle = getColorFromMemory(wasm_memory(), ptr);
		this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height)
	}
	''',
	'GetRandomValue' : '''
	GetRandomValue(min,max) {
		return min+Math.floor(Math.random()*(max-min+1))
	}
	''',
	'ColorFromHSV' : '''
	ColorFromHSV(result_ptr, hue, saturation, value) {
		const buffer = wasm_memory();
		const result = new Uint8Array(buffer, result_ptr, 4);

		// Red channel
		let k = (5.0 + hue/60.0)%6;
		let t = 4.0 - k;
		k = (t < k)? t : k;
		k = (k < 1)? k : 1;
		k = (k > 0)? k : 0;
		result[0] = Math.floor((value - value*saturation*k)*255.0);

		// Green channel
		k = (3.0 + hue/60.0)%6;
		t = 4.0 - k;
		k = (t < k)? t : k;
		k = (k < 1)? k : 1;
		k = (k > 0)? k : 0;
		result[1] = Math.floor((value - value*saturation*k)*255.0);

		// Blue channel
		k = (1.0 + hue/60.0)%6;
		t = 4.0 - k;
		k = (t < k)? t : k;
		k = (k < 1)? k : 1;
		k = (k > 0)? k : 0;
		result[2] = Math.floor((value - value*saturation*k)*255.0);

		result[3] = 255;
	}
	''',
	'add_group' : '''
	add_group (id, idLen, firstAndLastChildIds, firstAndLastChildIdsLen)
	{
		const buf = wasm_memory();
		var decoder = new TextDecoder();
		const id_ = decoder.decode(new Uint8Array(buf, id, idLen - 1));
		const firstAndLastChildIds_ = decoder.decode(new Uint8Array(buf, firstAndLastChildIds, firstAndLastChildIdsLen));
		var children = firstAndLastChildIds_.split(',');
		var html = document.body.innerHTML;
		var indexOfFirstChild = html.indexOf(children[1]);
		indexOfLastChild = html.indexOf('</svg>', indexOfFirstChild) + 6;
		var indexOfLastChild = html.indexOf(children[0]);
		indexOfLastChild = html.lastIndexOf('<', indexOfLastChild);
		document.body.innerHTML = html.slice(0, indexOfFirstChild) + '</g>' + html.slice(indexOfFirstChild);
		document.body.innerHTML = html.slice(0, indexOfLastChild) + '<g id="' + id_ + '">' + html.slice(indexOfLastChild);
	}
	''',
	'copy_node' : '''
	copy_node (id, idLen, pos)
	{
		const buf = wasm_memory();
		if (idLen > 0)
			var id_ = new TextDecoder().decode(new Uint8Array(buf, id, idLen - 1));
		else
			var id_ = id;
		const pos_ = new Float32Array(buf, pos, 8);
		copy_node (id_, pos_);
	}
	''',
}

raylib_like_api_mini = {}
c3dom_api_mini = {}
def GenMiniAPI ():
	syms = list(string.ascii_lowercase)
	symsTier = 1
	for fName in raylib_like_api:
		code = raylib_like_api[fName].strip()
		if code.startswith(fName):
			if len(syms) == 0:
				for char in string.ascii_lowercase:
					sym = char
					for i in range(symsTier):
						sym += char
					syms.append(sym)
				symsTier += 1
			sym = syms.pop()
			code = sym + code[len(fName) :]
			raylib_like_api_mini[fName] = { 'sym' : sym, 'code' : code.replace('\t','') }
		else:
			# Hard coded syms
			sym = code.split('(')[0]
			raylib_like_api_mini[fName] = {'sym' : sym, 'code' : code.replace('\t','') }
	for fName in c3dom_api:
		code = c3dom_api[fName].strip()
		assert code.startswith(fName)
		if len(syms) == 0:
			for char in string.ascii_lowercase:
				sym = char
				for i in range(symsTier):
					sym += char
				syms.append(sym)
			symsTier += 1
		sym = syms.pop()
		code = sym + code[len(fName) :]
		c3dom_api_mini[fName] = { 'sym' : sym, 'code' : code.replace('\t','') }

GenMiniAPI ()

def GenJsAPI (world, c3, userMethods):
	global draw
	global setup
	global userJsLibAPI
	draw_ = '\n'.join(draw)
	setup_ = '\n'.join(setup)
	skip = []
	if not IsInAnyElement('raylib::color_from_hsv', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('ColorFromHSV')
	if not IsInAnyElement('draw_circle_wasm', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('DrawCircleWASM')
	if not IsInAnyElement('raylib::draw_rectangle_v', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('DrawRectangleV')
	if not IsInAnyElement('raylib::clear_background', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('ClearBackground')
	if not IsInAnyElement('raylib::get_random_value', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('GetRandomValue')
	if not IsInAnyElement('draw_spline_wasm', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('DrawSplineLinearWASM')
	if not IsInAnyElement('raylib::get_screen_width', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('GetScreenWidth')
	if not IsInAnyElement('raylib::get_screen_height', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('GetScreenHeight')
	if not IsInAnyElement('draw_svg', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('draw_svg')
	if not IsInAnyElement('add_group', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('add_group')
	if not IsInAnyElement('copy_node', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('copy_node')
	if not IsInAnyElement('clamp', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('clamp')
	if not IsInAnyElement('get_pos_and_size', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('get_pos_and_size')
	if not IsInAnyElement('lerp', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('lerp')
	if not IsInAnyElement('inv_lerp', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('inv_lerp')
	if not IsInAnyElement('remap', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('remap')
	if not IsInAnyElement('get_svg_path', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('get_svg_path')
	if not IsInAnyElement('overlaps', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('overlaps')
	if not IsInAnyElement('random', [ c3, userJsLibAPI, draw_, setup_ ]):
		skip.append('random')
	if world.c3_js13kb:
		js = [ userJsLibAPI, JS_LIB_API_ENV_MINI, JS_LIB_API ]
	else:
		js = [ userJsLibAPI, JS_LIB_API_ENV, JS_LIB_API ]
	for fName in raylib_like_api:
		if fName in skip:
			print('Skipping:', fName)
			continue
		else:
			js.append(raylib_like_api[fName])
	for fName in c3dom_api:
		print(fName)
		used = fName + '(' in c3
		if fName in 'html_set_text html_add_char html_css_scale html_css_scale_y html_css_zindex html_css_string html_css_int html_canvas_resize'.split():
			scall = 'self.%s(' % fName.split('html_')[-1]
			if scall in c3:
				used = True
			scall = '].%s(' % fName.split('html_')[-1]
			if scall in c3:
				used = True
		if used:
			print('Used:', fName)
			js.append(c3dom_api[fName])
		else:
			print('Skipping:', fName)
	for fName in userMethods:
		fudge = fName.replace('(', '(_,')
		js += [
			fudge + '{',
				'self=this.elts[_]',
				'this._%s;' % fName,
			'}',
			'_' + fName + '{',
			userMethods[fName],
			'}',
		]
	js.append('}')
	js.append('new api()')
	js = '\n'.join(js)
	if 'getColorFromMemory' in js or 'color_hex_unpacked' in js:
		js = JS_LIB_COLOR_HELPERS + js
	if world.minify:
		for methodName in raylib_like_api_mini:
			if methodName != 'raylib_js_set_entry':
				js = js.replace(methodName, raylib_like_api_mini[methodName]['sym'])
		rmap = {
			'const ': 'var ', 'entryFunction' : 'ef', 'make_environment' : 'me', 
			'color_hex_unpacked' : 'cu', 'getColorFromMemory' : 'gm', 
			'cstr_by_ptr' : 'cp', 'cstrlen' : 'cl',
			'this.canvas' : 'this._a',
			'window.requestAnimationFrame' : 'self.requestAnimationFrame',
		}
		for rep in rmap:
			if rep in js:
				js = js.replace(rep, rmap[rep])
	return js

def GenHtml (world, wasm, c3, userHTML = None, background = '', userMethods = {}, debug = '--debug' in sys.argv):
	cmd = [ 'gzip', '--keep', '--force', '--verbose', '--best', wasm ]
	print(cmd)
	subprocess.check_call(cmd)
	
	wa = open(wasm,'rb').read()
	w = open(wasm +'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')
	jsTmp = '/tmp/c3api.js'
	jsLib = GenJsAPI(world, c3, userMethods)
	open(jsTmp, 'w').write(jsLib)
	if world.minify:
		jsLib = subprocess.run(('uglifyjs -m -- ' + jsTmp).split(), capture_output = True).stdout
		open(jsTmp, 'wb').write(jsLib)
		if os.path.isfile('SlimeJump.py'):
			import SlimeJump as slimJump
			slimJump.Minify (jsTmp)
	cmd = [ 'gzip', '--keep', '--force', '--verbose', '--best', jsTmp ]
	print(cmd)
	subprocess.check_call(cmd)
	
	js = open(jsTmp + '.gz', 'rb').read()
	jsB = base64.b64encode(js).decode('utf-8')
	if debug:
		background = 'red'
	if background:
		background = 'style="background-color:%s"' %background
	if world.c3_invalid_html:
		o = [
			'<canvas id=$><script>',
			'$1="%s"' % b,
			'$0="%s"' % jsB,
			#JS_DECOMP.replace('\t','').replace('var ', '').replace('\n',''), # Breaks invalid canvas above
			JS_DECOMP.replace('\t','').replace('var ', ''), 
			'</script>',
		]
		hsize = len('\n'.join(o))
	else:
		o = [
			'<!DOCTYPE html>',
			'<html>',
			'<body %s style="width:600px;height:300px;overflow:hidden;">' %background,
			'<canvas id="$"></canvas>',
			'<script>', 
			'var $0="%s"' % jsB,
			'var $1="%s"' % b,
			JS_DECOMP.replace('\t',''), 
			'</script>',
		]
		if userHTML:
			o += userHTML
		hsize = len('\n'.join(o)) + len('</body></html>')
	_BUILD_INFO['html-size'] = hsize
	_BUILD_INFO['jslib-size'] = len(jsLib)
	_BUILD_INFO['jslib-gz-size'] = len(js)
	if debug:
		if world.c3_invalid_html:
			o.append('</canvas>')
		o += [
			'<pre>',
			'jslib bytes=%s' % len(jsLib),
			'jslib.gz bytes=%s' % len(js),
			'jslib.base64 bytes=%s' % len(jsB),
			'wasm bytes=%s' % len(wa),
			'gzip bytes=%s' % len(w),
			'base64 bytes=%s' % len(b),
			'html bytes=%s' %(hsize - (len(b) + len(jsB))),
			'total bytes=%s' % hsize,
			'C3 optimization=%s' % WORLD.c3_export_opt,
		]
		for ob in bpy.data.objects:
			if ob.type == 'GPENCIL':
				o.append('%s = %s' %(ob.name, ob.data.c3_grease_quantize))
		o.append('</pre>')
	if not world.c3_invalid_html:
		o += [
			'</body>',
			'</html>',
		]
	return '\n'.join(o)

def WasmOpt (wasm):
	o = wasm.replace('.wasm', '.opt.wasm')
	cmd = [ 'wasm-opt', '-o',o, '-Oz', wasm ]
	print(cmd)
	subprocess.check_call(cmd)
	 
	return o

SERVER_PROC = None
WORLD = None
def BuildWasm (world):
	global SERVER_PROC, WORLD
	WORLD = world
	if SERVER_PROC:
		SERVER_PROC.kill()
	userHTML = []
	userMethods = {}
	o = BlenderToC3(world, wasm = True, html = userHTML, methods = userMethods)
	oStr = '\n'.join(o)
	if world.minify:
		lns = oStr.split('\n')
		oStr = ''
		for ln in lns:
			indexOfComment = ln.find('//')
			if indexOfComment != -1:
				ln = ln[: indexOfComment]
			oStr += ln
		for methodName in raylib_like_api_mini:
			if methodName != 'raylib_js_set_entry':
				oStr = oStr.replace(methodName, raylib_like_api_mini[methodName]['sym'])
		oStr = oStr.replace('\t', '').replace('  ', '').replace(', ', ',').replace(' (', '(').replace(' {', '{').replace('{ ', '{').replace(' }', '}').replace(' =', '=').replace('= ', '=').replace(' : ', ':').replace(' + ', '+').replace(' / ', '/').replace('] ', ']').replace(' *', '*').replace('* ', '*').replace(') ', ')')
	# print(oStr)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(oStr)
	wasm = Build(input = tmp, wasm = True, opt = world.c3_export_opt)
	wasm = WasmOpt(wasm)
	_BUILD_INFO['wasm'] = wasm
	_BUILD_INFO['wasm-size'] = len(open(wasm,'rb').read())
	html = GenHtml(world, wasm, oStr, userHTML, userMethods = userMethods)
	open('/tmp/index.html', 'w').write(html)
	if world.c3_js13kb:
		if os.path.isfile('/usr/bin/zip'):
			cmd = [ 'zip', '-9', 'index.html.zip', 'index.html' ]
			print(cmd)
			subprocess.check_call(cmd, cwd='/tmp')

			zip = open('/tmp/index.html.zip','rb').read()
			_BUILD_INFO['zip-size'] = len(zip)
			if world.c3_export_zip:
				out = os.path.expanduser(world.c3_export_zip)
				if not out.endswith('.zip'):
					out += '.zip'
				_BUILD_INFO['zip'] = out
				print('saving:', out)
				open(out, 'wb').write(zip)
			else:
				_BUILD_INFO['zip'] = '/tmp/index.html.zip'
		else:
			if len(html.encode('utf-8')) > 1024 * 13:
				raise SyntaxError('Final HTML is over 13kb')
	if WASM_OBJDUMP:
		cmd = [ WASM_OBJDUMP, '--syms', wasm ]
		print(cmd)
		subprocess.check_call(cmd)

	if world.c3_export_html:
		out = os.path.expanduser(world.c3_export_html)
		print('saving:', out)
		open(out,'w').write(html)
		webbrowser.open(out)

	else:
		cmd = [ 'python', '-m', 'http.server', '6969' ]
		SERVER_PROC = subprocess.Popen(cmd, cwd = '/tmp')

		atexit.register(lambda: SERVER_PROC.kill())
		webbrowser.open('http://localhost:6969')

	return wasm

def Update ():
	for ob in bpy.data.objects:
		if len(ob.material_slots) == 0 or ob.material_slots[0].material == None:
			continue
		mat = ob.material_slots[0].material
		mat.use_nodes = False
		indexOfPeriod = mat.name.find('.')
		if indexOfPeriod != -1:
			origName = mat.name[: indexOfPeriod]
			for ob2 in bpy.data.objects:
				if len(ob2.material_slots) > 0 and ob2.material_slots[0].material.name == origName:
					ob.material_slots[0].material = ob2.material_slots[0].material
			bpy.data.materials.remove(mat)
	for txt in bpy.data.texts:
		indexOfPeriod = txt.name.find('.')
		if indexOfPeriod != -1:
			for ob in bpy.data.objects:
				for i in range(MAX_SCRIPTS_PER_OBJECT):
					attachedTxt = getattr(ob, 'apiScript' + str(i))
					if attachedTxt == txt:
						for origTxt in bpy.data.texts:
							if origTxt.name == txt.name[: indexOfPeriod]:
								setattr(ob, 'apiScript' + str(i), origTxt)
								break
					attachedTxt = getattr(ob, 'runtimeScript' + str(i))
					if attachedTxt == txt:
						for origTxt in bpy.data.texts:
							if origTxt.name == txt.name[: indexOfPeriod]:
								setattr(ob, 'runtimeScript' + str(i), origTxt)
								break
			bpy.data.texts.remove(txt)
	return 0.1

bpy.types.Material.c3_export_trifan = bpy.props.BoolProperty(name = 'Triangle fan')
bpy.types.Material.c3_export_tristrip = bpy.props.BoolProperty(name = 'Triangle strip')

bpy.types.World.c3_export_res_x = bpy.props.IntProperty(name = 'Resolution X', default = 800)
bpy.types.World.c3_export_res_y = bpy.props.IntProperty(name = 'Resolution Y', default = 600)
bpy.types.World.c3_export_scale = bpy.props.FloatProperty(name = 'Scale', default = 100)
bpy.types.World.c3_export_offset_x = bpy.props.IntProperty(name = 'Offset X', default = 100)
bpy.types.World.c3_export_offset_y = bpy.props.IntProperty(name = 'Offset Y', default = 100)

bpy.types.World.c3_export_html = bpy.props.StringProperty(name = 'C3 export (.html)')
bpy.types.World.c3_export_zip = bpy.props.StringProperty(name = 'C3 export (.zip)')
bpy.types.World.minify = bpy.props.BoolProperty(name = 'Minifiy')
bpy.types.World.c3_js13kb = bpy.props.BoolProperty(name = 'js13k: Error on export if output is over 13KB')
bpy.types.World.c3_invalid_html = bpy.props.BoolProperty(name = 'Save space with invalid html wrapper')

bpy.types.World.c3_export_opt = bpy.props.EnumProperty(
	name = 'Optimize',
	items = [
		('O0', 'O0', 'Safe, no optimizations, emit debug info.'), 
		('O1', 'O1', 'Safe, high optimization, emit debug info.'), 
		('O2', 'O2', 'Unsafe, high optimization, emit debug info.'), 
		('O3', 'O3', 'Unsafe, high optimization, single module, emit debug info.'), 
		('O4', 'O4', 'Unsafe, highest optimization, relaxed maths, single module, emit debug info, no panic messages.'),
		('O5', 'O5', 'Unsafe, highest optimization, fast maths, single module, emit debug info, no panic messages, no backtrace.'),
		('Os', 'Os', 'Unsafe, high optimization, small code, single module, no debug info, no panic messages.'),
		('Oz', 'Oz', 'Unsafe, high optimization, tiny code, single module, no debug info, no panic messages, no backtrace.'),
	]
)

bpy.types.GreasePencilv3.c3_grease_optimize = bpy.props.IntProperty(name = 'Grease pencil optimize', min = 0, max = 8)
bpy.types.GreasePencilv3.c3_grease_quantize = bpy.props.EnumProperty(
	name = 'Quantize',
	items = [
		('32bits', '32bits', '32bit vertices'), 
		('16bits', '16bits', '16bit vertices'), 
		('8bits', '8bits', '8bit vertices'), 
		('7bits', '7bits', 'vertex chunk(8bits, 8bits, 4bits, 4bits, 4bits, 4bits)'), 
		('6bits', '6bits', 'vertex chunk(6bits, 6bits, 5bits, 5bits, 5bits, 5bits)'), 
		('4bits', '4bits', '4bit vertices'), 
	]
)

bpy.types.Object.hide = bpy.props.BoolProperty(name = 'Hide')
bpy.types.Object.collide = bpy.props.BoolProperty(name = 'Collide')
QUANTIZE_TYPES_ENUM_ITEMS = [ ('UInt8', 'UInt8', ''),
	('UInt16', 'UInt16', ''),
	('UInt32', 'UInt32', '') ]
bpy.types.Object.quantizeType = bpy.props.EnumProperty(
	name = 'Svg quantize type',
	description = '',
	items = QUANTIZE_TYPES_ENUM_ITEMS
)
bpy.types.Object.useSvgStroke = bpy.props.BoolProperty(name = 'Use svg stroke')
bpy.types.Object.svgStrokeWidth = bpy.props.FloatProperty(name='Svg stroke width', default = 0)
bpy.types.Object.svgStrokeColor = bpy.props.FloatVectorProperty(name='Svg stroke color', subtype = 'COLOR', default = [0, 0, 0])

for i in range(MAX_SCRIPTS_PER_OBJECT):
	setattr(
		bpy.types.Object,
		'apiScript' + str(i),
		bpy.props.PointerProperty(name = 'API script%s' % i, type = bpy.types.Text),
	)
	setattr(
		bpy.types.Object,
		'apiScript%sDisable' %i,
		bpy.props.BoolProperty(name = 'Disable'),
	)
	setattr(
		bpy.types.Object,
		'jsScript' + str(i),
		bpy.props.BoolProperty(name = 'JS'),
	)
	setattr(
		bpy.types.Object,
		'c3Script' + str(i),
		bpy.props.BoolProperty(name = 'C3'),
	)
	setattr(
		bpy.types.Object,
		'runtimeScript' + str(i),
		bpy.props.PointerProperty(name = 'Runtime script%s' % i, type = bpy.types.Text),
	)
	setattr(
		bpy.types.Object,
		'runtimeScript%sDisable' %i,
		bpy.props.BoolProperty(name = 'Disable'),
	)
	setattr(
		bpy.types.Object,
		'initScript' + str(i),
		bpy.props.BoolProperty(name = 'Is init'),
	)

@bpy.utils.register_class
class ScriptsPanel (bpy.types.Panel):
	bl_idname = 'OBJECT_PT_Object_Panel'
	bl_label = 'Object'
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'object'

	def draw (self, context):
		if not context.active_object:
			return
		ob = context.active_object
		if ob.type == 'GPENCIL':
			self.layout.prop(ob.data, 'c3_grease_optimize')
			self.layout.prop(ob.data, 'c3_grease_quantize')
		self.layout.prop(ob, 'hide')
		self.layout.prop(ob, 'collide')
		self.layout.prop(ob, 'quantizeType')
		self.layout.prop(ob, 'useSvgStroke')
		self.layout.prop(ob, 'svgStrokeWidth')
		self.layout.prop(ob, 'svgStrokeColor')
		self.layout.label(text = 'Scripts')
		foundUnassignedScript = False
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			hasProperty = getattr(ob, 'apiScript' + str(i)) != None
			if hasProperty or not foundUnassignedScript:
				row = self.layout.row()
				row.prop(ob, 'apiScript' + str(i))
				row.prop(ob, 'jsScript' + str(i))
				row.prop(ob, 'c3Script' + str(i))
				row.prop(ob, 'apiScript%sDisable' %i)
			if not foundUnassignedScript:
				foundUnassignedScript = not hasProperty
		foundUnassignedScript = False
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			hasProperty = getattr(ob, 'runtimeScript' + str(i)) != None
			if hasProperty or not foundUnassignedScript:
				row = self.layout.row()
				row.prop(ob, 'runtimeScript' + str(i))
				row.prop(ob, 'initScript' + str(i))
				row.prop(ob, 'runtimeScript%sDisable' %i)
			if not foundUnassignedScript:
				foundUnassignedScript = not hasProperty

@bpy.utils.register_class
class C3MaterialPanel (bpy.types.Panel):
	bl_idname = 'OBJECT_PT_C3_Material_Panel'
	bl_label = 'C3 Material Settings'
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'material'

	def draw (self, context):
		if not context.active_object:
			return
		ob = context.active_object
		if not ob.type == 'GPENCIL':
			return
		if not ob.data.materials:
			return
		mat = ob.data.materials[ ob.active_material_index ]
		self.layout.prop(mat, 'c3_export_trifan')
		self.layout.prop(mat, 'c3_export_tristrip')

if __name__ == '__main__':
	q = o = test = None
	for arg in sys.argv:
		if arg.endswith('bits'):
			q = arg.split('--')[-1]
		elif arg.startswith('--stroke-opt='):
			o = arg.split('=')[-1]
		elif arg.startswith('--test='):
			test = arg.split('=')[-1]
		elif arg.startswith('--O'):
			bpy.data.worlds[0].c3_export_opt = arg[2 :]
		elif arg.startswith('--output='):
			bpy.data.worlds[0].c3_export_html = arg.split('=')[-1]
		elif arg == '--minifiy':
			bpy.data.worlds[0].minify = True
		elif arg == '--js13k':
			bpy.data.worlds[0].minify = True
			bpy.data.worlds[0].c3_js13kb = True
			bpy.data.worlds[0].c3_invalid_html = True
	bpy.app.timers.register(Update)
	for ob in bpy.data.objects:
		if ob.type in [ 'MESH', 'CURVE', 'EMPTY' ]:
			ob.name = ob.name.replace('é', 'e').replace('(', '_').replace(')', '_')
	if '--test' in sys.argv or test:
		import c3blendgen
		if test:
			getattr(c3blendgen, test)(q, o)
		else:
			c3blendgen.gen_test_scene (q, o)
	if '--wasm' in sys.argv:
		BuildWasm (bpy.data.worlds[0])
	elif '--linux' in sys.argv:
		BuildLinux (bpy.data.worlds[0])