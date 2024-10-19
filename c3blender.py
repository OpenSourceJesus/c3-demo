#!/usr/bin/python3
import os, sys, subprocess, atexit, webbrowser, math, base64, string
from random import random, uniform
_thisdir = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(_thisdir)

C3 = '/usr/local/bin/c3c'

islinux=iswindows=c3gz=c3zip=None
if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-windows.zip'
	C3 = os.path.join(_thisdir,'c3/c3c.exe')
	iswindows=True
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-macos.zip'
else:
	BLENDER = 'blender'
	c3gz = 'https://github.com/c3lang/c3c/releases/download/latest/c3-ubuntu-20.tar.gz'
	islinux=True

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
			elif c3zip and iswindows:
				if not os.path.isfile('c3-windows.zip'):
					cmd = ['C:/Windows/System32/curl.exe', '-o', 'c3-windows.zip', c3zip]
					print(cmd)
					subprocess.check_call(cmd)
			elif c3zip:
				if not os.path.isfile('c3-macos.zip'):
					cmd = ['curl', '-o', 'c3-macos.zip', c3zip]
					print(cmd)
					subprocess.check_call(cmd)

		if islinux:
			C3 = os.path.abspath('./c3/c3c')
		elif iswindows:
			C3 = os.path.abspath('./c3/c3c.exe')

print('c3c:', C3)
assert os.path.isfile(C3)

EMSDK = os.path.join(_thisdir, "emsdk")
if "--install-wasm" in sys.argv and not os.path.isdir(EMSDK):
	cmd = [
		"git","clone","--depth","1",
		"https://github.com/emscripten-core/emsdk.git",
	]
	print(cmd)
	subprocess.check_call(cmd)
	emsdk_update()

if iswindows:
	EMCC = os.path.join(EMSDK, "upstream/emscripten/emcc.exe")
	WASM_OBJDUMP = os.path.join(EMSDK, "upstream/bin/llvm-objdump.exe")
else:
	EMCC = os.path.join(EMSDK, "upstream/emscripten/emcc")
	WASM_OBJDUMP = os.path.join(EMSDK, "upstream/bin/llvm-objdump")
if not EMCC and "--install-wasm" in sys.argv:
	emsdk_update()


def build(input='./demo.c3', output='demo', wasm='--wasm' in sys.argv, opt='--opt' in sys.argv, run=True, raylib='./raylib.c3'):
	cmd = [C3]
	if wasm: cmd += ['--target', 'wasm32']
	else: cmd += ['--target', 'linux-x64', '-l', './raylib-5.0_linux_amd64/lib/libraylib.a']
	mode = 'compile'

	cmd += [
		'--output-dir', '/tmp',
		'--obj-out', '/tmp',
		'--build-dir', '/tmp',
		'--print-output',
		'-o', output,
	]
	if wasm:
		cmd += ['--link-libc=no', '--use-stdlib=no', '--no-entry', '--reloc=none', '-z', '--export-table']
	else:
		cmd += ['-l', 'glfw']

	if opt:
		if type(opt) is str:
			cmd.append('-'+opt)
		else:
			cmd.append('-Oz')

	cmd += [mode, input, raylib]
	print(cmd)
	res = subprocess.check_output(cmd).decode('utf-8')
	ofiles = []
	for ln in res.splitlines():
		if ln.endswith('.o'):
			ofiles.append(ln.strip())
	print(ofiles)
	if run and not wasm: subprocess.check_call(['/tmp/'+output])
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
	elif '--c3demo' in sys.argv:
		## runs simple test without blender
		build()
		sys.exit()

	else:
		cmd = [BLENDER]
		for arg in sys.argv:
			if arg.endswith('.blend'):
				cmd.append(arg)
				break
		cmd +=['--python', __file__]
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


## blender ##
MAX_SCRIPTS_PER_OBJECT = 8
MAX_OBJECTS_PER_TEXT = 4
if not bpy:
	if islinux:
		if not os.path.isfile('/usr/bin/blender'):
			print('did you install blender?')
			print('snap install blender')
	else:
		print('download blender from: https://blender.org')

	sys.exit()

HEADER = '''
import raylib;
def Entry = fn void();
extern fn void raylib_js_set_entry(Entry entry) @extern("_") @wasm;
const Vector2 GRAVITY = {0, 1000};
const int N = 10;
const float COLLISION_DAMP = 1;

bitstruct Vector2_4bits : ichar {
	ichar x : 4..7;
	ichar y : 0..3;
}

bitstruct Vector2_6bits : int {
	ichar x0 : 26..31;  // 6bits
	ichar y0 : 20..25;  // 6bits
	ichar x1 : 15..19;  // 5bits
	ichar y1 : 10..14;  // 5bits
	ichar x2 : 5..9;    // 5bits
	ichar y2 : 0..4;    // 5bits
}

bitstruct Vector2_7bits : int {
	ichar x0 : 24..31;  // 8bits
	ichar y0 : 17..23;  // 8bits
	ichar x1 : 12..16;  // 4bits
	ichar y1 : 8..11;  // 4bits
	ichar x2 : 4..7;    // 4bits
	ichar y2 : 0..3;    // 4bits
}

struct Vector2_8bits @packed {
	ichar x;
	ichar y;
}

struct Vector2_16bits @packed {
	short x;
	short y;
}

'''

HEADER_OBJECT = '''
struct Object {
	Vector2 position;
	Vector2 velocity;
	Vector2 scale;
	Color color;
	int id;
	bool hide;
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
	html_canvas_resize(%s, %s);
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

WASM_EXTERN = '''
extern fn float random () @extern("random");

extern fn void draw_circle_wasm (int x, int y, float radius, Color color) @extern("DrawCircleWASM");
extern fn void draw_spline_wasm (Vector2 *points, int pointCount, float thick, int use_fill, char r, char g, char b, float a) @extern("DrawSplineLinearWASM");

extern fn int html_new (char *ptr) @extern("html_new");
extern fn int html_new_text (char *ptr, float x, float y, float sz, bool viz, char *id) @extern("html_new_text");

extern fn void html_set_text (int id, char *ptr) @extern("html_set_text");
extern fn void html_add_char (int id, char c) @extern("html_add_char");

extern fn void html_set_position (int id, float x, float y) @extern("html_set_position");
extern fn void html_css_scale (int id, float scale) @extern("html_css_scale");
extern fn void html_css_scale_y (int id, float scale) @extern("html_css_scale_y");

extern fn void html_css_zindex (int id, int z) @extern("html_css_zindex");
extern fn void html_canvas_clear () @extern("html_canvas_clear");
extern fn void html_canvas_resize (int x, int y) @extern("html_canvas_resize");

def JSCallback = fn void( int );
extern fn void html_bind_onclick (int id, JSCallback ptr, int ob_index) @extern("html_bind_onclick");

extern fn void html_eval (char *ptr) @extern("html_eval");

extern fn char wasm_memory (int idx) @extern("wasm_memory");
extern fn int wasm_size () @extern("wasm_size");

'''

def get_scripts(ob):
	scripts = []
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		txt = getattr(ob, "c3_script" + str(i))
		if txt: scripts.append(macro_pointers(txt))
	return scripts

def has_scripts(ob):
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		txt = getattr(ob, "c3_script" + str(i))
		if txt: return True
	return False


def blender_to_c3(world, wasm=False, html=None, use_html=False, methods={}):
	resx = world.c3_export_res_x
	resy = world.c3_export_res_y
	SCALE = world.c3_export_scale
	offx = world.c3_export_offset_x
	offy = world.c3_export_offset_y

	unpackers = {}
	head  = [HEADER, HEADER_OBJECT]
	if wasm:
		head.append(HEADER_OBJECT_WASM)
		if world.c3_miniapi:
			s = WASM_EXTERN
			for fname in c3dom_api_mini:
				key = '@extern("%s")' % fname
				assert key in s
				s = s.replace(key, '@extern("%s")' % c3dom_api_mini[fname]['sym'])

			for fname in raylib_like_api_mini:
				key = '@extern("%s")' % fname
				s = s.replace(key, '@extern("%s")' % raylib_like_api_mini[fname]['sym'])

			head.append( s )
		else:
			head.append(WASM_EXTERN)

		head.append(WASM_HELPERS)

	setup = ['fn void main() @extern("main") @wasm {']
	draw  = [
		'fn void game_frame() @extern("$") @wasm {',
		'	Object self;',
		'	Object parent;',
		'	float dt = raylib::get_frame_time();',
	]
	if wasm:
		draw.append('	html_canvas_clear();')
	else:
		draw.append('	raylib::begin_drawing();')
		draw.append('	raylib::clear_background({0xFF, 0xFF, 0xFF, 0xFF});')

	meshes = []
	datas = {}
	ascii_letters = list(string.ascii_uppercase)
	prevparent = None
	for ob in bpy.data.objects:
		if ob.hide_get(): continue
		print(ob)
		sname = safename(ob)
		x,y,z = ob.location * SCALE
		z = -z
		x += offx
		z += offy
		sx,sy,sz = ob.scale * SCALE
		idx = len(meshes)
		if not ob.name.startswith('_'):
			head.append('short %s_id=%s;' % (sname,idx))

		scripts = []
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			txt = getattr(ob, "c3_script" + str(i))
			if txt:
				scripts.append(macro_pointers(txt))

			txt = getattr(ob, "c3_method" + str(i))
			if txt and txt.name not in methods:
				tname = txt.name

				assert '(' in tname
				assert tname.endswith(')')
				fname, args = tname.split('(')
				exdef = txt.c3_extern
				if not exdef.startswith('extern') and not exdef.startswith('fn'):
					exdef = 'fn ' + exdef
				if not exdef.startswith('extern'):
					exdef = 'extern ' + exdef
				if not exdef.endswith(';'): exdef += ';'

				args_def = exdef.split('@')[0].split('(')[-1].split(')')[0]

				assert fname+'(' in exdef
				exdef = exdef.replace(fname+'(', '%s(int _eltid,' % fname)

				head.append(exdef)
				args = args[:-1] ## strip )
				head += [

					'fn void Object.%s(Object *_obj, %s) {' % (fname, args_def),
					'	%s(_obj.id, %s);' % (fname, args),
					'}', 
				]


				if '@extern("' in txt.c3_extern:
					tname = txt.c3_extern.split('@extern("')[-1].split('"')[0]
					if len(tname) <= 1:
						print(txt)
						raise SyntaxError('@extern names must be at least two characters: %s' % txt.c3_extern)
					tname += '(' + txt.name.split('(')[-1]

				methods[tname] = macro_pointers(txt)




		if ob.type=="MESH":
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			setup.append('	objects[%s].scale={%s,%s};' % (idx, sx,sz))
			#setup.append('	objects[%s].color=raylib::color_from_hsv(%s,1,1);' % (idx, random()))
			setup.append('	objects[%s].color={%s,%s,%s,0xFF};' % (idx, int(random()*255), int(random()*255), int(random()*255) ))

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
			if has_scripts(ob):
				setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
				sx,sy,sz = ob.scale
				setup.append('	objects[%s].scale={%s,%s};' % (idx, sx,sz))

			if wasm:
				grease_to_c3_wasm(ob, datas, head, draw, setup, scripts, idx)
			else:
				grease_to_c3_raylib(ob, datas, head, draw, setup)

		elif ob.type=='FONT' and wasm:
			cscale = ob.data.size*SCALE
			if use_html:
				css = 'position:absolute; left:%spx; top:%spx; font-size:%spx;' %(x+(cscale*0.1),z-cscale, cscale)
				div = '<div id="%s" style="%s">%s</div>' %(sname, css, ob.data.body)
				html.append(div)
				continue

			meshes.append(ob)
			hide = 'false'
			if ob.c3_hide:
				setup.append('	objects[%s].hide=true;' % idx)
				hide = 'true'

			if ob.parent:
				x,y,z = ob.location * SCALE
				z = -z

			dom_name = ob.name
			if dom_name.startswith('_'):
				dom_name = ''

			if ob.parent and has_scripts(ob.parent):
				setup += [
					'	objects[%s].position={%s,%s};' % (idx, x+(cscale*0.1),z-(cscale*1.8)),
					'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' % (idx, ob.data.body, x+(cscale*0.1),z-(cscale*1.8), cscale, hide, dom_name),
				]
			elif ob.parent:
				fx = x+(cscale*0.1)
				fy = z-(cscale*1.8)
				fx += (ob.parent.location.x * SCALE) + offx
				fy += (ob.parent.location.z * SCALE) + offy
				setup += [
					'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' % (idx, ob.data.body, fx,fy, cscale, hide, dom_name),
				]

			if ob.c3_onclick:
				tname = safename(ob.c3_onclick)
				if wasm and ascii_letters:
					head += [
						'fn void _onclick_%s(int _index_) @extern("%s") {' % (tname,ascii_letters.pop()),
						'	Object self = objects[_index_];',
						macro_pointers(ob.c3_onclick),
						'}',
					]
				else:
					head += [
						'fn void _onclick_%s(int _index_){' % tname,
						'	Object self = objects[_index_];',
						macro_pointers(ob.c3_onclick),
						'}',
					]
				setup.append('	html_bind_onclick(objects[%s].id, &_onclick_%s, %s);' %(idx, tname, idx))
			if ob.location.y >= 0.1:
				setup.append('	html_css_zindex(objects[%s].id, -%s);' % (idx, int(ob.location.y*10)))
			elif ob.location.y <= -0.1:
				setup.append('	html_css_zindex(objects[%s].id, %s);' % (idx, abs(int(ob.location.y*10))) )

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

			if ob.parent and has_scripts(ob.parent):
				if prevparent != ob.parent.name:
					prevparent = ob.parent.name
					draw.append('parent = objects[%s_id];' % safename(ob.parent))
				draw += [
					#'parent = objects[%s_id];' % safename(ob.parent),
					#'self.position.x=parent.position.x;',
					#'self.position.y=parent.position.y;',
					'html_set_position(self.id, self.position.x + parent.position.x, self.position.y + parent.position.y);',
				]

	if wasm:
		setup.append(MAIN_WASM % (resx, resy))
	else:
		setup.append(MAIN % (resx, resy))

	setup.append('}')
	if not wasm:
		draw.append('	raylib::end_drawing();')
	draw.append('}')

	head.append('Object[%s] objects;' % len(meshes))

	if unpackers:
		for gkey in unpackers:
			head += unpackers[gkey]

	for dname in datas:
		print(dname)
		print('orig-points:', datas[dname]['orig-points'])
		print('total-points:',datas[dname]['total-points'])
	return head + setup + draw

def grease_to_c3_wasm(ob, datas, head, draw, setup, scripts, obj_index):
	SCALE = WORLD.c3_export_scale
	offx = WORLD.c3_export_offset_x
	offy = WORLD.c3_export_offset_y
	sx,sy,sz = ob.scale * SCALE
	x,y,z = ob.location * SCALE

	dname = safename(ob.data)
	gquant = False
	if ob.data.c3_grease_quantize != '32bits':
		gquant = ob.data.c3_grease_quantize

	gopt = ob.data.c3_grease_optimize

	if dname not in datas:
		datas[dname]={'orig-points':0, 'total-points':0, 'draw':[]}
		data = []
		for lidx, layer in enumerate( ob.data.layers ):
			for sidx, stroke in enumerate( layer.frames[0].strokes ):
				datas[dname]['orig-points'] += len(stroke.points)
				mat = ob.data.materials[stroke.material_index]
				use_fill = 0
				if mat.grease_pencil.show_fill: use_fill = 1

				if gopt:
					points = []
					for pidx in range(0, len(stroke.points), gopt):
						points.append( stroke.points[pidx] )
				else:
					points = stroke.points

				s = []
				if gquant:
					qstroke = quantizer(points, gquant)
					n = len(qstroke['points'])
					if not len(qstroke['points']):
						print('stroke quantized away:', stroke)
						continue
					datas[dname]['total-points'] += len(qstroke['points'])
					x0,y0,z0 = points[0].co
					q = qstroke['q']
					qs = qstroke['qs']
					setup += [
						'_unpacker_%s(&__%s__%s_%s_pak,' %(dname, dname,lidx,sidx),
						'	&__%s__%s_%s,' %(dname,lidx,sidx),
						'	%s,' % n,
						'	%s, %s' % (x0*q, z0*q),
						');',
					]

					data.append('Vector2_%s[%s] __%s__%s_%s_pak = {%s};' % (gquant,n,dname, lidx, sidx, ','.join(qstroke['points']) ))

					if gquant in ('6bits', '7bits'):
						data.append('Vector2[%s] __%s__%s_%s;' % ( (n*3),dname, lidx, sidx ))
					else:
						data.append('Vector2[%s] __%s__%s_%s;' % (n+1,dname, lidx, sidx ))
						n += 1

				else:
					## default 32bit floats ##
					s = []
					if scripts:
						for pnt in points:
							x1,y1,z1 = pnt.co * SCALE
							s.append('{%s,%s}' % (x1,-z1))
					else:
						for pnt in points:
							x1,y1,z1 = pnt.co
							x1 *= sx
							z1 *= sz
							s.append('{%s,%s}' % (x1+offx+x,-z1+offy+z))

					data.append('Vector2[%s] __%s__%s_%s = {%s};' % (len(points),dname, lidx, sidx, ','.join(s) ))
					n = len(s)


				if gquant in ('6bits', '7bits'):
					nn = n*3
				else:
					nn = n

				r,g,b,a = mat.grease_pencil.fill_color
				swidth = calc_stroke_width(stroke)
				datas[dname]['draw'].append({'layer':lidx, 'index':sidx, 'length':nn, 'width':swidth, 'fill':use_fill, 'color':[r,g,b,a]})

		head += data
		if gquant:
			if gquant in ('6bits', '7bits'):
				head += gen_delta_delta_unpacker(ob, dname, gquant, SCALE, qs, offx, offy)
			else:
				head += gen_delta_unpacker(ob, dname, gquant, SCALE, qs, offx, offy)

	oname = sname = safename(ob)
	if scripts:
		draw.append('	self = objects[%s];' % obj_index)
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
		draw.append('	objects[%s] = self;' % obj_index)

	for a in datas[dname]['draw']:
		r,g,b,alpha = a['color']
		r = int(r*255)
		g = int(g*255)
		b = int(b*255)
		if not scripts:
			## static grease pencil
			if a['fill']:
				draw.append('	draw_spline_wasm(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (dname, a['layer'], a['index'], a['length'], a['width'], a['fill'], r,g,b,alpha))
			else:
				draw.append('	draw_spline_wasm(&__%s__%s_%s,%s,%s, 0, 0,0,0,0);' % (dname, a['layer'], a['index'], a['length'], a['width']))
		else:
			tag = [oname, a['layer'], a['index']]
			head.append('Vector2[%s] _%s_%s_%s;' % tuple([a['length']]+tag) )
			dtag = [dname, a['layer'], a['index']]
			draw += [
				'	transform_spline_wasm(&__%s__%s_%s, &_%s_%s_%s, %s, objects[%s].position, objects[%s].scale);' %tuple(dtag+tag+[a['length'],obj_index, obj_index]),
				'	draw_spline_wasm(&_%s_%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (oname, a['layer'], a['index'], a['length'], a['width'], a['fill'], r,g,b,alpha)
			]

def gen_delta_delta_unpacker(ob, dname, gquant, SCALE, qs, offx, offy):
	x,y,z = ob.location * SCALE
	sx,sy,sz = ob.scale
	gkey = (dname, gquant)
	## TODO only gen single packer per quant
	qkey = gquant.split('bit')[0]
	return [
		'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0) @extern("u%s") {' %(dname, gquant, qkey),
		'	int j=0;',
		'	out[0].x = (x0*%sf) + %sf;' %(qs*sx, offx+x),
		'	out[0].y = -(z0*%sf) + %sf;'  % (qs*sz, offy+z),
		'	for (int i=0; i<len; i++){',
		'		float ax = ( (x0 - pak[i].x0) * %sf) + %sf;' %(qs*sx, offx+x),
		'		float ay = ( -(z0 - pak[i].y0) * %sf) + %sf;' % (qs*sz, offy+z),

		'		j++;',
		'		out[j].x = ax;',
		'		out[j].y = ay;',

		'		j++;',
		'		out[j].x = ((x0 - (float)(pak[i].x0 - pak[i].x1)) * %sf) + %sf;' % (qs*sx, offx+x),
		'		out[j].y = ( -(z0 - (float)(pak[i].y0 - pak[i].y1)) * %sf) + %sf;' % (qs*sz, offy+z),

		'		j++;',
		'		out[j].x = ((x0 - (float)(pak[i].x0 - pak[i].x2)) * %sf) + %sf;' % (qs*sx, offx+x),
		'		out[j].y = ( -(z0 - (float)(pak[i].y0 - pak[i].y2)) * %sf) + %sf;' % (qs*sz, offy+z),


		'	}',
		'}'
	]


def gen_delta_unpacker(ob, dname, gquant, SCALE, qs, offx, offy):
	x,y,z = ob.location * SCALE
	sx,sy,sz = ob.scale
	gkey = (dname, gquant)
	return [
		'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0){' %gkey,
		'	out[0].x = (x0*%sf) + %sf;' %(qs*sx, offx+x),
		'	out[0].y = -(z0*%sf) + %sf;'  % (qs*sz, offy+z),
		'	for (int i=0; i<len; i++){',
		'		float a = ( (x0 - pak[i].x) * %sf) + %sf;' %(qs*sx, offx+x),
		'		out[i+1].x = a;',
		'		a = ( -(z0 - pak[i].y) * %sf) + %sf;' % (qs*sz, offy+z),
		'		out[i+1].y = a;',
		'	}',
		'}'
	]


def grease_to_c3_raylib(ob, datas, head, draw, setup):
	SCALE = WORLD.c3_export_scale
	offx = WORLD.c3_export_offset_x
	offy = WORLD.c3_export_offset_y
	sx,sy,sz = ob.scale * SCALE
	x,y,z = ob.location * SCALE

	dname = safename(ob.data)
	gquant = False
	if ob.data.c3_grease_quantize != '32bits':
		gquant = ob.data.c3_grease_quantize

	if dname not in datas:
		datas[dname]=0
		data = []
		for lidx, layer in enumerate( ob.data.layers ):
			for sidx, stroke in enumerate( layer.frames[0].strokes ):
				datas[dname] += len(stroke.points)
				mat = ob.data.materials[stroke.material_index]
				use_fill = 0
				if mat.grease_pencil.show_fill: use_fill = 1
				s = []
				if use_fill:
					if mat.c3_export_trifan:
						x1,y1,z1 = calc_center(stroke.points)
						x1 *= sx
						z1 *= sz
						s.append('{%s,%s}' % (x1+offx+x,-z1+offy+z))
					elif mat.c3_export_tristrip:
						tri_strip = True
					else:
						tris = []
						for tri in stroke.triangles:
							tris.append(tri.v1)
							tris.append(tri.v2)
							tris.append(tri.v3)
						tris = ','.join([str(vidx) for vidx in tris])
						data.append('int[%s] __%s__%s_%s_tris = {%s};' % (len(stroke.triangles)*3,dname, lidx, sidx, tris ))

					## default 32bit floats ##
					for pnt in stroke.points:
						x1,y1,z1 = pnt.co
						x1 *= sx
						z1 *= sz
						s.append('{%s,%s}' % (x1+offx+x,-z1+offy+z))

					n = len(s)
					data.append('Vector2[%s] __%s__%s_%s = {%s};' % (n, dname, lidx, sidx, ','.join(s) ))

				elif gquant:
					qstroke = quantizer(stroke.points, gquant)
					n = len(qstroke['points'])
					if not len(qstroke['points']):
						print('stroke quantized away:', stroke)
						continue
					data.append('Vector2[%s] __%s__%s_%s;' % (n+1,dname, lidx, sidx ))
					data.append('Vector2_%s[%s] __%s__%s_%s_pak = {%s};' % (gquant,n,dname, lidx, sidx, ','.join(qstroke['points']) ))

					x0,y0,z0 = stroke.points[0].co
					q = qstroke['q']
					qs = qstroke['qs']
					setup += [
						'_unpacker_%s(&__%s__%s_%s_pak,' %(dname, dname,lidx,sidx),
						'	&__%s__%s_%s,' %(dname,lidx,sidx),
						'	%s,' % len(stroke.points),
						'	%s, %s' % (x0*q, z0*q),
						');',
					]
				else:
					## default 32bit floats ##
					s = []
					for pnt in stroke.points:
						x1,y1,z1 = pnt.co
						x1 *= sx
						z1 *= sz
						s.append('{%s,%s}' % (x1+offx+x,-z1+offy+z))

					data.append('Vector2[%s] __%s__%s_%s = {%s};' % (len(stroke.points),dname, lidx, sidx, ','.join(s) ))
					n = len(s)

				r,g,b,a = mat.grease_pencil.fill_color
				swidth = calc_stroke_width(stroke)


				if use_fill:
					clr = '{%s,%s,%s,%s}' % (int(r*255), int(g*255), int(b*255), int(a*255))
					if mat.c3_export_trifan:
						draw.append('	raylib::draw_triangle_fan(&__%s__%s_%s, %s, %s);' % (dname, lidx, sidx, n, clr))
					elif mat.c3_export_tristrip:
						draw.append('	raylib::draw_triangle_strip(&__%s__%s_%s, %s, %s);' % (dname, lidx, sidx, n, clr))
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
							'	}',
						]

					if mat.grease_pencil.show_stroke:
						draw.append('	raylib::draw_spline( (&__%s__%s_%s), %s, 4.0, {0x00,0x00,0x00,0xFF});' % (dname, lidx, sidx, n))
				else:
					draw.append('	raylib::draw_spline(&__%s__%s_%s, %s, %s, {0x00,0x00,0x00,0xFF});' % (dname, lidx, sidx, n, swidth))

		head += data
		if gquant:
			x,y,z = ob.location * SCALE
			sx,sy,sz = ob.scale
			gkey = (dname, gquant)
			head += [
				'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0){' %gkey,
				'	out[0].x = (x0*%sf) + %sf;' %(qs*sx, offx+x),
				'	out[0].y = -(z0*%sf) + %sf;'  % (qs*sz, offy+z),
				'	for (int i=0; i<len; i++){',
				'		float a = ( (x0 - pak[i].x) * %sf) + %sf;' %(qs*sx, offx+x),
				'		out[i+1].x = a;',
				'		a = ( -(z0 - pak[i].y) * %sf) + %sf;' % (qs*sz, offy+z),
				'		out[i+1].y = a;',
				'	}',
				'}'
			]

def quantizer(points, quant, trim=True):
	SCALE = WORLD.c3_export_scale

	s = []
	if quant=='4bits':
		q = SCALE * 0.125
		qs = 8
	elif quant=='6bits' or quant=='7bits':
		q = SCALE * 0.5
		qs = 2
	elif quant=='8bits' or quant == "7x5x4bits":
		q = SCALE * 0.5
		qs = 2
		#q = SCALE * 0.75
		#qs = 1.333
	else:
		q = SCALE
		qs = 1

	x0,y0,z0 = points[0].co

	mvec = []
	for pnt in points[1:]:
		x1,y1,z1 = pnt.co
		dx = int( (x0-x1)*q )
		dz = int( (z0-z1)*q )
		if quant=='4bits':
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
		elif quant=='6bits':
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
				## delta of delta
				ddx = mdx-dx
				ddy = mdz-dz
				if quant == '6bits':  ## after 5bits
					if ddx >= 16: ddx = 15
					elif ddx < -16: ddx = -16
					if ddy >= 16: ddy = 15
					elif ddy < -16: ddy = -16
				else:  ## after 4bits
					if ddx >= 8: ddx = 7
					elif ddx < -8: ddx = -8
					if ddy >= 8: ddy = 7
					elif ddy < -8: ddy = -8
				v = ( ddx, ddy )
			else:
				v = ( dx, dz )
			mvec.append(v)

			if len(mvec) >= 3:
				s.append('{%s}' % ', '.join( '%s,%s' % v for v in mvec))
				#s.append('{%s}' % (str(mvec)[1:-1]))
				mvec = []
		else:
			vec = '{%s,%s}' % ( dx, dz )
			if trim:
				#if (dx==0 and dz==0):
				#	continue
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
		s.append('{%s}' % ', '.join( '%s,%s' % v for v in mvec))

	return {'q':q, 'qs':qs, 'points':s}


def calc_stroke_width(stroke):
	sw = 0.0
	for p in stroke.points:
		sw += p.pressure
		#sw += p.strength
	sw /= len(stroke.points)
	return sw * stroke.line_width * 0.05


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

_BUILD_INFO = {
	'native': None,
	'wasm'  : None,
	'native-size':None,
	'wasm-size':None,
	'zip'     : None,
	'zip-size': None,
}
@bpy.utils.register_class
class C3Export(bpy.types.Operator):
	bl_idname = "c3.export"
	bl_label = "C3 Export EXE"
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		exe = build_linux(context.world)
		_BUILD_INFO['native']=exe
		_BUILD_INFO['native-size']=len(open(exe,'rb').read())
		return {"FINISHED"}

@bpy.utils.register_class
class C3Export(bpy.types.Operator):
	bl_idname = "c3.export_wasm"
	bl_label = "C3 Export WASM"
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		exe = build_wasm(context.world)
		return {"FINISHED"}

@bpy.utils.register_class
class C3WorldPanel(bpy.types.Panel):
	bl_idname = "WORLD_PT_C3World_Panel"
	bl_label = "C3 Export"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"

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

		self.layout.operator("c3.export_wasm", icon="CONSOLE")
		self.layout.operator("c3.export", icon="CONSOLE")
		if _BUILD_INFO['native-size']:
			self.layout.label(text="exe KB=%s" %( _BUILD_INFO['native-size']//1024 ))

@bpy.utils.register_class
class JS13KB_Panel(bpy.types.Panel):
	bl_idname = "WORLD_PT_JS13KB_Panel"
	bl_label = "js13kgames.com"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"
	def draw(self, context):
		self.layout.prop(context.world, 'c3_js13kb')
		row = self.layout.row()
		row.prop(context.world, 'c3_miniapi')
		row.prop(context.world, 'c3_invalid_html')
		if context.world.c3_js13kb:
			self.layout.prop(context.world, 'c3_export_zip')
			if _BUILD_INFO['zip-size']:
				self.layout.label(text=_BUILD_INFO['zip'])
				if _BUILD_INFO['zip-size'] <= 1024*13:
					self.layout.label(text="zip bytes=%s" %( _BUILD_INFO['zip-size'] ))
				else:
					self.layout.label(text="zip KB=%s" %( _BUILD_INFO['zip-size']//1024 ))

				self.layout.label(text='html-size=%s' % _BUILD_INFO['html-size'])
				self.layout.label(text='jslib-size=%s' % _BUILD_INFO['jslib-size'])
				self.layout.label(text='jslib-gz-size=%s' % _BUILD_INFO['jslib-gz-size'])

		if _BUILD_INFO['wasm-size']:
			if _BUILD_INFO['wasm-size'] < 1024*16:
				self.layout.label(text="wasm bytes=%s" %( _BUILD_INFO['wasm-size'] ))
			else:
				self.layout.label(text="wasm KB=%s" %( _BUILD_INFO['wasm-size']//1024 ))


def build_linux(world):
	global WORLD
	WORLD = world
	o = blender_to_c3(world)
	o = '\n'.join(o)
	#print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	bin = build(input=tmp, opt=world.c3_export_opt)
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
function color_hex_unpacked(r,g,b,a){
	r=r.toString(16).padStart(2,'0');
	g=g.toString(16).padStart(2,'0');
	b=b.toString(16).padStart(2,'0');
	a=a.toString(16).padStart(2,'0');
	return "#"+r+g+b+a
}
function getColorFromMemory(buf,ptr){
	const [r,g,b,a]=new Uint8Array(buf,ptr,4);
	return color_hex_unpacked(r,g,b,a)
}
'''

JS_LIB_API_ENV = '''
function make_environment(e){
	return new Proxy(e,{
		get(t,p,r) {
			if(e[p]!==undefined){return e[p].bind(e)}
			return(...args)=>{throw p}
		}
	});
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
function cstrlen(m,p){
	var l=0;
	while(m[p]!=0){l++;p++}
	return l;
}

function cstr_by_ptr(m,p){
	const l=cstrlen(new Uint8Array(m),p);
	const b=new Uint8Array(m,p,l);
	return new TextDecoder().decode(b)
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
	'html_new' : '''
	html_new(ptr){
		var elt=document.createElement(cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr));
		elt.style.position='absolute';
		this.elts.push(elt);
		document.body.appendChild(elt);
		return this.elts.length-1
	}
	''',

	'html_new_text' : '''
	html_new_text(ptr,x,y,sz,viz,id){
		var elt=document.createElement('pre');
		elt.style.transformOrigin='left';
		elt.style.position='absolute';
		elt.style.left=x;
		elt.style.top=y;
		elt.style.fontSize=sz;
		elt.hidden=viz;
		elt.id=cstr_by_ptr(this.wasm.instance.exports.memory.buffer,id);
		this.elts.push(elt);
		document.body.appendChild(elt);
		elt.append(cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr));
		return this.elts.length-1
	}
	''',

	'html_set_text':'''
	html_set_text(idx,ptr){
		this.elts[idx].firstChild.nodeValue=cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr)
	}
	''',

	'html_add_char':'''
	html_add_char(idx, c){
		this.elts[idx].append(String.fromCharCode(c))
	}
	''',


	'html_css_scale':'''
	html_css_scale(idx, sz){
		this.elts[idx].style.transform='scale('+sz+')'
	}
	''',

	'html_css_scale_y':'''
	html_css_scale_y(idx, sz){
		this.elts[idx].style.transform='scaleY('+sz+')'
	}
	''',


	'html_set_position':'''
	html_set_position(idx,x,y){
		var elt = this.elts[idx];
		elt.style.left = x;
		elt.style.top = y
	}
	''',

	'html_css_zindex':'''
	html_css_zindex(idx,z){
		this.elts[idx].style.zIndex=z
	}
	''',

	'html_bind_onclick':'''
	html_bind_onclick(idx,f,oidx){
		var elt=this.elts[idx];
		elt._onclick_=this.wasm.instance.exports.__indirect_function_table.get(f);
		elt.onclick=function(){
			self=elt;
			elt._onclick_(oidx)
		}
	}
	''',


	'html_eval':'''
	html_eval(ptr){
		var _=cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		eval(_)
	}
	''',


	'html_canvas_clear':'''
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


	'wasm_memory':'''
	wasm_memory(idx){
		return this.bytes[idx]
	}
	''',
	'wasm_size':'''
	wasm_size(){
		return this.bytes.length
	}
	''',

	'random':'''
	random(){
		return Math.random()
	}
	''',


}

raylib_like_api = {
	'raylib_js_set_entry':'''
	_(f) {
		this.entryFunction = this.wasm.instance.exports.__indirect_function_table.get(f)
	}
	''',

	'InitWindow' : '''
	InitWindow(w,h,ptr){
		this.canvas.width=w;
		this.canvas.height=h;
		const buf=this.wasm.instance.exports.memory.buffer;
		document.title = cstr_by_ptr(buf,ptr)
	}
	''',
	'GetScreenWidth':'''
	GetScreenWidth(){
		return this.canvas.width
	}
	''',

	'GetScreenHeight':'''
	GetScreenHeight(){
		return this.canvas.height
	}
	''',

	'GetFrameTime':'''
	GetFrameTime(){
		return Math.min(this.dt,1/30/2)
	}
	''',

	'DrawRectangleV':'''
	DrawRectangleV(pptr,sptr,cptr){
		const buf=this.wasm.instance.exports.memory.buffer;
		const p=new Float32Array(buf,pptr,2);
		const s=new Float32Array(buf,sptr,2);
		this.ctx.fillStyle = getColorFromMemory(buf, cptr);
		this.ctx.fillRect(p[0],p[1],s[0],s[1])
	}
	''',

	'DrawSplineLinearWASM':'''
	DrawSplineLinearWASM(ptr,l,t,fill,r,g,b,a){
		const buf=this.wasm.instance.exports.memory.buffer;
		const p=new Float32Array(buf,ptr,l*2);
		this.ctx.strokeStyle='black';
		if(fill)this.ctx.fillStyle='rgba('+r+','+g+','+b+','+a+')';
		this.ctx.lineWidth=t;
		this.ctx.beginPath();
		this.ctx.moveTo(p[0], p[1]);
		for(var i=2;i<p.length;i+=2)this.ctx.lineTo(p[i],p[i+1]);
		if(fill){
			this.ctx.closePath();
			this.ctx.fill()
		}
		this.ctx.stroke()
	}
	''',

	'DrawCircleWASM':'''
	DrawCircleWASM(x,y,rad,ptr){
		const buf=this.wasm.instance.exports.memory.buffer;
		const [r,g,b,a]=new Uint8Array(buf, ptr, 4);
		this.ctx.strokeStyle = 'black';
		this.ctx.beginPath();
		this.ctx.arc(x,y,rad,0,2*Math.PI,false);
		this.ctx.fillStyle = color_hex_unpacked(r,g,b,a);
		this.ctx.closePath();
		this.ctx.stroke()
	}
	''',

	'ClearBackground':'''
	ClearBackground(ptr) {
		this.ctx.fillStyle = getColorFromMemory(this.wasm.instance.exports.memory.buffer, ptr);
		this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height)
	}
	''',


	'GetRandomValue':'''
	GetRandomValue(min,max) {
		return min+Math.floor(Math.random()*(max-min+1))
	}
	''',

	'ColorFromHSV':'''
	ColorFromHSV(result_ptr, hue, saturation, value) {
		const buffer = this.wasm.instance.exports.memory.buffer;
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

}

raylib_like_api_mini = {}
c3dom_api_mini = {}
def gen_mini_api():
	syms = list(string.ascii_lowercase)
	syms.remove('j')
	for fname in raylib_like_api:
		code = raylib_like_api[fname].strip()
		if code.startswith(fname):
			sym = syms.pop()
			code = sym + code[len(fname):]
			raylib_like_api_mini[fname] = {'sym':sym,'code':code.replace('\t','')}
		else:
			sym = code.split('(')[0]
			raylib_like_api_mini[fname] = {'sym':sym,'code':code.replace('\t','')}


	for fname in c3dom_api:
		code = c3dom_api[fname].strip()
		assert code.startswith(fname)
		sym = syms.pop()
		code = sym + code[len(fname):]
		c3dom_api_mini[fname] = {'sym':sym,'code':code.replace('\t','')}

gen_mini_api()


def gen_js_api(world, c3, user_methods):
	skip = []
	if 'raylib::color_from_hsv' not in c3:
		skip.append('ColorFromHSV')
	if 'draw_circle_wasm(' not in c3:
		skip.append('DrawCircleWASM')
	if 'raylib::draw_rectangle_v' not in c3:
		skip.append('DrawRectangleV')
	if 'raylib::clear_background' not in c3:
		skip.append('ClearBackground')
	if 'raylib::get_random_value' not in c3:
		skip.append('GetRandomValue')
	if 'draw_spline_wasm' not in c3:
		skip.append('DrawSplineLinearWASM')
	if 'raylib::get_screen_width' not in c3:
		skip.append('GetScreenWidth')
	if 'raylib::get_screen_height' not in c3:
		skip.append('GetScreenHeight')

	if world.c3_js13kb:
		js = [JS_LIB_API_ENV_MINI, JS_LIB_API]
	else:
		js = [
			JS_LIB_API_ENV,
			JS_LIB_API,
		]
	for fname in raylib_like_api:
		if fname in skip:
			print('skipping:', fname)
			continue

		if world.c3_miniapi:
			if fname in raylib_like_api_mini:
				js.append(raylib_like_api_mini[fname]['code'])
		else:
			js.append(raylib_like_api[fname])

	for fname in c3dom_api:
		used = fname+'(' in c3
		if fname in 'html_set_text html_add_char html_css_scale html_css_scale_y html_css_zindex'.split():
			scall = 'self.%s(' % fname.split('html_')[-1]
			if scall in c3: used = True
			scall = '].%s(' % fname.split('html_')[-1]
			if scall in c3: used = True

		if used:
			print('used:', fname)
			if world.c3_miniapi:
				js.append(c3dom_api_mini[fname]['code'])
			else:
				js.append(c3dom_api[fname])
		else:
			print('skipping:', fname)

	for fname in user_methods:
		fudge = fname.replace('(', '(_,')
		js += [
			fudge + '{',
				'self=this.elts[_]',
				'this._%s;' % fname,
			'}',

			'_'+fname + '{',
			user_methods[fname],
			'}',
		]

	js.append('}')
	js.append('new api()')
	js = '\n'.join(js)

	if 'getColorFromMemory' in js or 'color_hex_unpacked' in js:
		js = JS_LIB_COLOR_HELPERS + js

	if world.c3_js13kb:
		js = js.replace('\t','').replace('\n','')
		rmap = {
			'const ': 'var ', 'entryFunction':'ef', 'make_environment':'me', 
			'color_hex_unpacked':'cu', 'getColorFromMemory':'gm', 
			'cstr_by_ptr':'cp', 'cstrlen':'cl',
			'this.canvas':'this.can',
		}
		for rep in rmap:
			if rep in js:
				js = js.replace(rep, rmap[rep])
	return js

def gen_html(world, wasm, c3, user_html=None, background='', user_methods={}, debug='--debug' in sys.argv):
	cmd = ['gzip', '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/c3api.js'
	jslib = gen_js_api(world, c3, user_methods)

	open(jtmp,'w').write(jslib)
	cmd = ['gzip', '--keep', '--force', '--verbose', '--best', jtmp]
	print(cmd)
	subprocess.check_call(cmd)
	js = open(jtmp+'.gz','rb').read()
	jsb = base64.b64encode(js).decode('utf-8')

	if '--debug' in sys.argv:
		background = 'red'
	if background:
		background = 'style="background-color:%s"' % background

	if world.c3_invalid_html:
		o = [
			'<canvas id=$><script>',
			'$1="%s"' % b,
			'$0="%s"' % jsb,
			#JS_DECOMP.replace('\t','').replace('var ', '').replace('\n',''), ## breaks invalid canvas above
			JS_DECOMP.replace('\t','').replace('var ', ''), 
			'</script>',
		]
		hsize = len('\n'.join(o))

	else:
		o = [
			'<html>',
			'<body %s>' % background,
			'<canvas id="$"></canvas>',
			'<script>', 
			'var $0="%s"' % jsb,
			'var $1="%s"' % b,
			JS_DECOMP.replace('\t',''), 
			'</script>',
		]
		if user_html:
			o += user_html

		hsize = len('\n'.join(o)) + len('</body></html>')

	_BUILD_INFO['html-size'] = hsize
	_BUILD_INFO['jslib-size'] = len(jslib)
	_BUILD_INFO['jslib-gz-size'] = len(js)

	if debug:
		if world.c3_invalid_html:
			o.append('</canvas>')

		o += [
			'<pre>',
			'jslib bytes=%s' % len(jslib),
			'jslib.gz bytes=%s' % len(js),
			'jslib.base64 bytes=%s' % len(jsb),
			'wasm bytes=%s' % len(wa),
			'gzip bytes=%s' % len(w),
			'base64 bytes=%s' % len(b),
			'html bytes=%s' % (hsize- (len(b)+len(jsb)) ),
			'total bytes=%s' % hsize,
			'C3 optimization=%s' % WORLD.c3_export_opt,

		]
		for ob in bpy.data.objects:
			if ob.type=='GPENCIL':
				o.append('%s = %s' % (ob.name, ob.data.c3_grease_quantize))

		o.append('</pre>')

	if not world.c3_invalid_html:
		o += [
			'</body>',
			'</html>',

		]

	return '\n'.join(o)

SERVER_PROC = None
WORLD = None
def build_wasm( world ):
	global SERVER_PROC, WORLD
	WORLD = world
	if SERVER_PROC: SERVER_PROC.kill()
	user_html = []
	user_methods = {}
	o = blender_to_c3(world, wasm=True, html=user_html, methods=user_methods)
	o = '\n'.join(o)
	#print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	if world.c3_miniapi:
		rtmp = '/tmp/miniraylib.c3'
		raylib = open('./raylib.c3').read()
		for fname in raylib_like_api_mini:
			b = raylib_like_api_mini[fname]['sym']
			raylib = raylib.replace('@extern("%s")' %fname, '@extern("%s")' % b)
		open(rtmp,'w').write(raylib)
		wasm = build(input=tmp, wasm=True, opt=world.c3_export_opt, raylib=rtmp)
	else:
		wasm = build(input=tmp, wasm=True, opt=world.c3_export_opt)


	_BUILD_INFO['wasm']=wasm
	_BUILD_INFO['wasm-size']=len(open(wasm,'rb').read())

	#os.system('cp -v ./index.html /tmp/.')
	#os.system('cp -v ./raylib.js /tmp/.')
	html = gen_html(world, wasm, o, user_html, user_methods=user_methods)
	open('/tmp/index.html', 'w').write(html)
	if world.c3_js13kb:
		if os.path.isfile('/usr/bin/zip'):
			cmd = ['zip', '-9', 'index.html.zip', 'index.html']
			print(cmd)
			subprocess.check_call(cmd, cwd='/tmp')
			zip = open('/tmp/index.html.zip','rb').read()
			_BUILD_INFO['zip-size'] = len(zip)

			if world.c3_export_zip:
				out = os.path.expanduser(world.c3_export_zip)
				if not out.endswith('.zip'): out += '.zip'
				_BUILD_INFO['zip'] = out
				print('saving:', out)
				open(out,'wb').write(zip)
			else:
				_BUILD_INFO['zip'] = '/tmp/index.html.zip'

		else:
			if len(html.encode('utf-8')) > 1024*13:
				raise SyntaxError('final html is over 13KB')

	if WASM_OBJDUMP:
		cmd = [WASM_OBJDUMP, '--syms', wasm]
		print(cmd)
		subprocess.check_call(cmd)

	if world.c3_export_html:
		out = os.path.expanduser(world.c3_export_html)
		print('saving:', out)
		open(out,'w').write(html)
		webbrowser.open(out)
	else:
		cmd = ['python', '-m', 'http.server', '6969']
		SERVER_PROC = subprocess.Popen(cmd, cwd='/tmp')
		atexit.register(lambda:SERVER_PROC.kill())
		webbrowser.open('http://localhost:6969')
	return wasm

bpy.types.Material.c3_export_trifan = bpy.props.BoolProperty(name="triangle fan")
bpy.types.Material.c3_export_tristrip = bpy.props.BoolProperty(name="triangle strip")

bpy.types.World.c3_export_res_x = bpy.props.IntProperty(name="resolution X", default=800)
bpy.types.World.c3_export_res_y = bpy.props.IntProperty(name="resolution Y", default=600)
bpy.types.World.c3_export_scale = bpy.props.FloatProperty(name="scale", default=100)
bpy.types.World.c3_export_offset_x = bpy.props.IntProperty(name="offset X", default=100)
bpy.types.World.c3_export_offset_y = bpy.props.IntProperty(name="offset Y", default=100)

bpy.types.World.c3_export_html = bpy.props.StringProperty(name="c3 export (.html)")
bpy.types.World.c3_export_zip = bpy.props.StringProperty(name="c3 export (.zip)")
bpy.types.World.c3_miniapi = bpy.props.BoolProperty(name="c3 minifiy js/wasm api calls")
bpy.types.World.c3_js13kb = bpy.props.BoolProperty(name="js13k: error on export if output is over 13KB")
bpy.types.World.c3_invalid_html = bpy.props.BoolProperty(name="save space with invalid html wrapper")

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

bpy.types.GreasePencil.c3_grease_optimize = bpy.props.IntProperty(name="grease pencil optimize", min=0, max=8)
bpy.types.GreasePencil.c3_grease_quantize = bpy.props.EnumProperty(
	name='quantize',
	items=[
		("32bits", "32bits", "32bit vertices"), 
		("16bits", "16bits", "16bit vertices"), 
		("8bits", "8bits", "8bit vertices"), 
		#("7x5x4bits", "7x5x4bits", "vertices(7bits, 7bits, 5bits, 5bits, 4bits, 4bits)"), 
		("7bits", "7bits", "vertex chunk(8bits, 8bits, 4bits, 4bits, 4bits, 4bits)"), 
		("6bits", "6bits", "vertex chunk(6bits, 6bits, 5bits, 5bits, 5bits, 5bits)"), 
		("4bits", "4bits", "4bit vertices"), 
	]
)

bpy.types.Object.c3_hide     = bpy.props.BoolProperty( name="hidden on spawn")
bpy.types.Object.c3_onclick     = bpy.props.PointerProperty( name="on click script", type=bpy.types.Text)
bpy.types.Object.c3_script_init = bpy.props.PointerProperty( name="init script", type=bpy.types.Text)

for i in range(MAX_SCRIPTS_PER_OBJECT):
	setattr(
		bpy.types.Object,
		"c3_script" + str(i),
		bpy.props.PointerProperty(name="script%s" % i, type=bpy.types.Text),
	)
	setattr(
		bpy.types.Object,
		"c3_method" + str(i),
		bpy.props.PointerProperty(name="method%s" % i, type=bpy.types.Text),
	)

for i in range(MAX_OBJECTS_PER_TEXT):
	setattr(
		bpy.types.Text,
		"object" + str(i),
		bpy.props.PointerProperty(name="object%s" % i, type=bpy.types.Object),
	)
	setattr(
		bpy.types.Text,
		"color" + str(i),
		bpy.props.FloatVectorProperty(name="color%s" % i, subtype='COLOR'),
	)

bpy.types.Text.c3_extern = bpy.props.StringProperty(name="fn extern")


def macro_pointers(txt):
	t = txt.as_string()
	for i in range(MAX_OBJECTS_PER_TEXT):
		tag = 'object%s' % i
		ob = getattr(txt, tag)
		if '$'+tag+'.' in t:
			if not ob:
				raise RuntimeError('%s text object pointer not set: %s' % (txt, tag) )
			t = t.replace('$'+tag+'.', 'objects[%s_id].' % safename(ob))
		elif '$'+tag in t:
			if not ob:
				raise RuntimeError('%s text object pointer not set: %s' % (txt, tag) )
			t = t.replace('$'+tag, ob.name)  ## only works inside of quotes in html dom

		tag = 'color%s' % i
		clr = getattr(txt, tag)
		if '$'+tag in t:
			t = t.replace('$'+tag, ','.join([str(v) for v in clr]))

	return t

@bpy.utils.register_class
class C3ScriptsPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Scripts_Panel"
	bl_label = "C3 Script Pointers"
	bl_space_type = "TEXT_EDITOR"
	bl_region_type = "UI"
	def draw(self, context):
		txt = context.space_data.text
		if txt:
			self.layout.label(text=txt.name)
		else:
			self.layout.label(text="(no text)")
			return

		if txt.name.endswith(')'):
			self.layout.prop(txt, 'c3_extern')

		self.layout.label(text="object pointers")
		for i in range(MAX_OBJECTS_PER_TEXT):
			self.layout.prop(txt, 'object%s' % i)

		self.layout.label(text="color pointers")
		for i in range(MAX_OBJECTS_PER_TEXT):
			self.layout.prop(txt, 'color%s' % i)


@bpy.utils.register_class
class C3ObjectPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Object_Panel"
	bl_label = "C3 Object Options"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"

	def draw(self, context):
		if not context.active_object: return
		ob = context.active_object
		if ob.type=='GPENCIL':
			self.layout.prop(ob.data, 'c3_grease_optimize')
			self.layout.prop(ob.data, 'c3_grease_quantize')

		self.layout.prop(ob, "c3_hide")
		self.layout.prop(ob, "c3_onclick")

		self.layout.label(text="Attach C3 Scripts")
		self.layout.prop(ob, "c3_script_init")
		foundUnassignedScript = False
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			hasProperty = (
				getattr(ob, "c3_script" + str(i)) != None
			)
			if hasProperty or not foundUnassignedScript:
				self.layout.prop(ob, "c3_script" + str(i))
			if not foundUnassignedScript:
				foundUnassignedScript = not hasProperty

		foundUnassignedScript = False
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			hasProperty = (
				getattr(ob, "c3_method" + str(i)) != None
			)
			if hasProperty or not foundUnassignedScript:
				self.layout.prop(ob, "c3_method" + str(i))
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
		self.layout.prop(mat, 'c3_export_tristrip')

if __name__=='__main__':
	q = o = test = None
	for arg in sys.argv:
		if arg.endswith('bits'):
			q = arg.split('--')[-1]
		elif arg.startswith('--stroke-opt='):
			o = arg.split('=')[-1]
		elif arg.startswith('--test='):
			test = arg.split('=')[-1]
		elif arg.startswith('--O'):
			bpy.data.worlds[0].c3_export_opt = arg[2:]
		elif arg.startswith('--output='):
			bpy.data.worlds[0].c3_export_html = arg.split('=')[-1]
		elif arg=='--minifiy':
			bpy.data.worlds[0].c3_miniapi = True
		elif arg=='--js13k':
			bpy.data.worlds[0].c3_miniapi = True
			bpy.data.worlds[0].c3_js13kb = True
			bpy.data.worlds[0].c3_invalid_html = True

	if '--test' in sys.argv or test:
		import c3blendgen
		if test:
			getattr(c3blendgen,test)(q,o)
		else:
			c3blendgen.gen_test_scene(q,o)
	if '--wasm' in sys.argv:
		build_wasm( bpy.data.worlds[0] )
	elif '--linux' in sys.argv:
		build_linux( bpy.data.worlds[0] )


