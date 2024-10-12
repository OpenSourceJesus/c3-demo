#!/usr/bin/python3
import os, sys, subprocess, atexit, webbrowser, math, base64
from random import random, uniform
_thisdir = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(_thisdir)

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

if "--install-wasm" in sys.argv and not os.path.isdir(EMSDK):
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
if not EMCC and "--install-wasm" in sys.argv:
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
	else:
		build()

## blender ##
if not bpy:
	if not os.path.isfile('/usr/bin/blender'):
		print('did you install blender?')
		print('snap install blender')
	print('run: python3 c3blender.py --blender')
	sys.exit()

HEADER = '''
import raylib;
def Entry = fn void();
extern fn void raylib_js_set_entry(Entry entry) @wasm;
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
	html_set_text(obj.id, txt);
}
fn void Object.css_scale(Object *obj, float scale) {
	html_css_scale(obj.id, scale);
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
	raylib::init_window(%s, %s, "Hello, from C3 WebAssembly");
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

def blender_to_c3(world, wasm=False, html=None, use_html=False):
	resx = world.c3_export_res_x
	resy = world.c3_export_res_y
	SCALE = world.c3_export_scale
	offx = world.c3_export_offset_x
	offy = world.c3_export_offset_y

	unpackers = {}
	head  = [HEADER, HEADER_OBJECT]
	if wasm:
		head.append(HEADER_OBJECT_WASM)
		head.append('extern fn void draw_circle_wasm (int x, int y, float radius, Color color) @extern("DrawCircleWASM");')
		head.append('extern fn void draw_spline_wasm (Vector2 *points, int pointCount, float thick, int use_fill, float r, float g, float b, float a) @extern("DrawSplineLinearWASM");')

		head.append('extern fn int html_new (char *ptr) @extern("html_new");')
		head.append('extern fn int html_new_text (char *ptr, float x, float y, float sz, bool viz, char *id) @extern("html_new_text");')
		head.append('extern fn void html_set_text (int id, char *ptr) @extern("html_set_text");')
		head.append('extern fn void html_set_position (int id, float x, float y) @extern("html_set_position");')
		head.append('extern fn void html_css_scale (int id, float scale) @extern("html_css_scale");')

		head.append('extern fn void html_set_zindex (int id, int z) @extern("html_set_zindex");')
		head.append('extern fn void html_canvas_clear () @extern("html_canvas_clear");')

		head.append('def JSCallback = fn void( int );')
		head.append('extern fn void html_bind_onclick (int id, JSCallback ptr, int ob_index) @extern("html_bind_onclick");')

		head.append('extern fn void html_eval (char *ptr) @extern("html_eval");')

		head.append(WASM_HELPERS)



	setup = ['fn void main() @extern("main") @wasm {']
	draw  = [
		'fn void game_frame() @wasm {',
		'	Object self;',
		'	Object parent;',
		#'	int __self__;',
		'	float dt = raylib::get_frame_time();',
	]
	if wasm:
		#draw.append('	raylib::clear_background({0x00, 0x00, 0x00, 0x00});')  ## this fails?
		draw.append('	html_canvas_clear();')
	else:
		draw.append('	raylib::begin_drawing();')
		draw.append('	raylib::clear_background({0xFF, 0xFF, 0xFF, 0xFF});')
	meshes = []
	tobjects = []
	datas = {}
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
		head.append('short %s_id=%s;' % (sname,idx))

		scripts = []
		for i in range(MAX_SCRIPTS_PER_OBJECT):
			txt = getattr(ob, "c3_script" + str(i))
			if txt:
				scripts.append(txt.as_string())


		if ob.type=="MESH":
			#ob['c3_index'] = idx
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
			#ob['c3_index'] = idx
			meshes.append(ob)
			setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			sx,sy,sz = ob.scale
			setup.append('	objects[%s].scale={%s,%s};' % (idx, sx,sz))

			if wasm:
				grease_to_c3_wasm(ob, datas, head, draw, setup, scripts, idx)
			else:
				grease_to_c3_raylib(ob, datas, head, draw, setup)

		elif ob.type=='FONT' and wasm:
			#idx = len(tobjects)
			#tobjects.append(ob)


			cscale = ob.data.size*SCALE
			if use_html:
				css = 'position:absolute; left:%spx; top:%spx; font-size:%spx;' %(x+(cscale*0.1),z-cscale, cscale)
				div = '<div id="%s" style="%s">%s</div>' %(sname, css, ob.data.body)
				html.append(div)
				continue

			meshes.append(ob)
			#setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
			hide = 'false'
			if ob.c3_hide:
				setup.append('	objects[%s].hide=true;' % idx)
				hide = 'true'

			if ob.parent:
				x,y,z = ob.location * SCALE
				z = -z

			setup += [
				#'int _elt = html_new("div");',
				#'html_set_text(_elt, "%s");' %ob.data.body,
				#'html_set_position(_elt, %s,%s);' %(x+(cscale*0.1),z-cscale),
				#'text_objects[%s] = html_new_text("%s", %s,%s, %s);' % (idx, ob.data.body, x+(cscale*0.1),z-cscale, cscale)

				#'	objects[%s].position={%s,%s};' % (idx, x,z),
				'	objects[%s].position={%s,%s};' % (idx, x+(cscale*0.1),z-(cscale*1.8)),


				#'	objects[%s].id = html_new_text("%s", %s,%s, %s);' % (idx, ob.data.body, x+(cscale*0.1),z-cscale, cscale)
				#'	objects[%s].id = html_new_text("%s", %s,%s, %s);' % (idx, ob.data.body, x,z, cscale)
				'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' % (idx, ob.data.body, x+(cscale*0.1),z-(cscale*1.8), cscale, hide, ob.name),

			]
			if ob.c3_onclick:
				tname = safename(ob.c3_onclick)
				head += [
					'fn void _onclick_%s(int _index_){' % tname,
					'	Object self = objects[_index_];',
					ob.c3_onclick.as_string(),
					'}',
				]
				setup.append('	html_bind_onclick(objects[%s].id, &_onclick_%s, %s);' %(idx, tname, idx))
			if ob.location.y >= 0.1:
				setup.append('	html_set_zindex(objects[%s].id, -%s);' % (idx, int(ob.location.y*10)))
			elif ob.location.y <= -0.1:
				setup.append('	html_set_zindex(objects[%s].id, %s);' % (idx, abs(int(ob.location.y*10))) )

			#draw.append('	__self__ = text_objects[%s];' % idx)
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
					#if 'self.set_text(' in s:
					#	s = s.replace('self.set_text(', 'html_set_text(__self__,')
					draw.append('\t' + s)

			if ob.parent:
				print(ob, ob.parent)
				draw += [

					#'parent = objects[%s];' % ob.parent['c3_index'],
					'parent = objects[%s_id];' % safename(ob.parent),

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
	if tobjects:
		head.append('int[%s] text_objects;' % len(tobjects))
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

				#if gquant in ('6bits', '7bits'):
				#	draw.append('	draw_spline_wasm(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (dname, lidx, sidx, n*3, swidth, use_fill, r,g,b,a))
				#else:
				#	draw.append('	draw_spline_wasm(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (dname, lidx, sidx, n, swidth, use_fill, r,g,b,a))

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
		if not scripts:
			## static grease pencil
			draw.append('	draw_spline_wasm(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (dname, a['layer'], a['index'], a['length'], a['width'], a['fill'], r,g,b,alpha))
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
	return [
		'fn void _unpacker_%s(Vector2_%s *pak, Vector2 *out, int len, float x0, float z0){' %gkey,
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


		#s.append('{%s,%s}' % ( int(x1*q), int(-z1*q) ))
		#s.append('{%s,%s}' % ( int(dx*q), int(dz*q) ))

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

_BUILD_INFO = {
	'native': None,
	'wasm'  : None,
	'native-size':None,
	'wasm-size':None,
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
		_BUILD_INFO['wasm']=exe
		_BUILD_INFO['wasm-size']=len(open(exe,'rb').read())
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
		self.layout.prop(context.world, 'c3_export_html')

		self.layout.operator("c3.export_wasm", icon="CONSOLE")
		if _BUILD_INFO['wasm-size']:
			if _BUILD_INFO['wasm-size'] < 1024*16:
				self.layout.label(text="wasm bytes=%s" %( _BUILD_INFO['wasm-size'] ))
			else:
				self.layout.label(text="wasm KB=%s" %( _BUILD_INFO['wasm-size']//1024 ))
		self.layout.operator("c3.export", icon="CONSOLE")
		if _BUILD_INFO['native-size']:
			self.layout.label(text="exe KB=%s" %( _BUILD_INFO['native-size']//1024 ))

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
var $=null
var $deco = async (u,t) => {
	var d=new DecompressionStream('gzip')
	var r=await fetch('data:application/octet-stream;base64,'+u)
	var b=await r.blob()
	var s=b.stream().pipeThrough(d)
	var o=await new Response(s).blob()
	if (t) return await o.text();
	else return await o.arrayBuffer();
}
$deco($0,1).then((js)=>{
	console.log(js);
	$=eval(js);
	$deco($1).then((r)=>{
		var io={env:$.api_proxy()};
		WebAssembly.instantiate(r,io).then((res)=>{
			console.log(res.instance);
			$.api_reset(res, "game");
		});
	});
});
'''

JS_LIB_NOT_USED_YET = '''
function color_hex(color) {
	const r = ((color>>(0*8))&0xFF).toString(16).padStart(2, '0');
	const g = ((color>>(1*8))&0xFF).toString(16).padStart(2, '0');
	const b = ((color>>(2*8))&0xFF).toString(16).padStart(2, '0');
	const a = ((color>>(3*8))&0xFF).toString(16).padStart(2, '0');
	return "#"+r+g+b+a;
}
'''

JS_LIB_API = '''
function make_environment(e){
	return new Proxy(e,{
		get(t,p,r) {
			if (e[p] !== undefined) {
				return e[p].bind(e)
			}
			return (...args) => {
				throw new Error(p)
			}
		}
	});
}

function cstrlen(mem, ptr) {
	let len = 0
	while (mem[ptr] != 0) {
		len++
		ptr++
	}
	return len
}

function cstr_by_ptr(mbuf, ptr) {
	const mem= new Uint8Array(mbuf)
	const len= cstrlen(mem,ptr)
	const bytes= new Uint8Array(mbuf,ptr,len)
	return new TextDecoder().decode(bytes)
}

function color_hex_unpacked(r, g, b, a) {
	r=r.toString(16).padStart(2,'0')
	g=g.toString(16).padStart(2,'0')
	b=b.toString(16).padStart(2,'0')
	a=a.toString(16).padStart(2,'0')
	return "#"+r+g+b+a
}

function getColorFromMemory(buf,ptr) {
	const [r,g,b,a] = new Uint8Array(buf,ptr,4)
	return color_hex_unpacked(r,g,b,a)
}

class api{
	api_proxy(){
		return make_environment(this)
	}
	api_reset( wasm, id ){
		this.elts=[]
		this.wasm = wasm
		this.canvas = document.getElementById(id)
		this.ctx = this.canvas.getContext("2d")
		this.wasm.instance.exports.main()
		const next = (timestamp)=>{
			if (this.quit) {
				return;
			}
			this.dt = (timestamp - this.previous)/1000.0
			this.previous = timestamp
			this.entryFunction()
			window.requestAnimationFrame(next)
		};
		window.requestAnimationFrame((timestamp)=>{
			this.previous = timestamp
			window.requestAnimationFrame(next)
		});
	}
'''


c3dom_api = {
	'html_new_div' : '''
	html_new(ptr){
		var elt=document.createElement(cstr_by_ptr(this.wasm.instance.exports.memory.buffer, ptr))
		elt.style.position='absolute'
		this.elts.push(elt)
		document.body.appendChild(elt)
		return this.elts.length-1
	}
	''',

	'html_new_text' : '''
	html_new_text(ptr, x,y, sz, viz, id){
		var elt=document.createElement('pre')
		elt.style.transformOrigin='left'
		elt.style.position='absolute'
		elt.style.left=x
		elt.style.top=y
		elt.style.fontSize=sz
		elt.hidden=viz
		elt.id=cstr_by_ptr(this.wasm.instance.exports.memory.buffer, id)
		this.elts.push(elt)
		document.body.appendChild(elt)
		elt.append(cstr_by_ptr(this.wasm.instance.exports.memory.buffer, ptr))
		return this.elts.length-1
	}
	''',

	'html_set_text':'''
	html_set_text(idx, ptr){
		var elt = this.elts[idx]
		var txt = cstr_by_ptr(this.wasm.instance.exports.memory.buffer, ptr)
		elt.firstChild.nodeValue=txt
	}
	''',

	'html_css_scale':'''
	html_css_scale(idx, sz){
		this.elts[idx].style.transform='scale('+sz+')'
	}
	''',

	'html_set_position':'''
	html_set_position(idx, x, y){
		var elt = this.elts[idx]
		elt.style.left = x
		elt.style.top = y
	}
	''',

	'html_set_zindex':'''
	html_set_zindex(idx, z){
		this.elts[idx].style.zIndex = z
	}
	''',

	'html_bind_onclick':'''
	html_bind_onclick(idx, f, oidx){
		var func = this.wasm.instance.exports.__indirect_function_table.get(f)
		this.elts[idx].onclick = function (){
			func(oidx)
		}
	}
	''',

	'html_eval':'''
	html_eval(ptr){
		var _ = cstr_by_ptr(this.wasm.instance.exports.memory.buffer, ptr)
		eval(_)
	}
	''',


	'html_canvas_clear':'''
	html_canvas_clear(){
		this.ctx.clearRect(0,0,this.ctx.canvas.width,this.ctx.canvas.height)
	}
	''',

}

raylib_like_api = {
	'InitWindow' : '''
	InitWindow(w,h,ptr){
		this.ctx.canvas.width=w
		this.ctx.canvas.height=h
		const buf=this.wasm.instance.exports.memory.buffer
		document.title = cstr_by_ptr(buf,ptr)
	}
	''',
	'GetScreenWidth':'''
	GetScreenWidth(){
		return this.ctx.canvas.width
	}
	''',

	'GetScreenHeight':'''
	GetScreenHeight(){
		return this.ctx.canvas.height
	}
	''',

	'GetFrameTime':'''
	GetFrameTime(){
		return Math.min(this.dt, 1.0/60)
	}
	''',

	'DrawRectangleV':'''
	DrawRectangleV(pptr,sptr,cptr){
		const buf=this.wasm.instance.exports.memory.buffer
		const p=new Float32Array(buf,pptr,2)
		const s=new Float32Array(buf,sptr,2)
		this.ctx.fillStyle = getColorFromMemory(buf, cptr)
		this.ctx.fillRect(p[0],p[1],s[0],s[1])
	}
	''',

	'DrawSplineLinearWASM':'''
	DrawSplineLinearWASM(ptr,len,thick,fill, r,g,b,a){
		const buf = this.wasm.instance.exports.memory.buffer
		const p = new Float32Array(buf,ptr,len*2)
		this.ctx.strokeStyle = 'black'
		if(fill) this.ctx.fillStyle='rgba('+(r*255)+','+(g*255)+','+(b*255)+','+a+')'
		this.ctx.lineWidth=thick
		this.ctx.beginPath()
		this.ctx.moveTo(p[0], p[1])
		for (var i=2; i<p.length; i+=2){
			this.ctx.lineTo(p[i], p[i+1])
		}
		if (fill){
			this.ctx.closePath()
			this.ctx.fill()
		}
		this.ctx.stroke()
	}
	''',

	'DrawCircleWASM':'''
	DrawCircleWASM(x,y,rad,ptr){
		const buf=this.wasm.instance.exports.memory.buffer
		const [r,g,b,a]=new Uint8Array(buf, ptr, 4)
		this.ctx.strokeStyle = 'black'
		this.ctx.beginPath()
		this.ctx.arc(x,y,rad,0,2*Math.PI,false)
		this.ctx.fillStyle = color_hex_unpacked(r,g,b,a)
		this.ctx.closePath()
		this.ctx.stroke()
	}
	''',

	'ClearBackground':'''
	ClearBackground(ptr) {
		this.ctx.fillStyle = getColorFromMemory(this.wasm.instance.exports.memory.buffer, ptr)
		this.ctx.fillRect(0,0,this.ctx.canvas.width,this.ctx.canvas.height)
	}
	''',

	'raylib_js_set_entry':'''
	raylib_js_set_entry(f) {
		this.entryFunction = this.wasm.instance.exports.__indirect_function_table.get(f)
	}
	''',

	'':'''
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


def gen_js_api(c3):
	skip = []
	if 'raylib::color_from_hsv' not in c3:
		skip.append('ColorFromHSV')
	if 'draw_circle_wasm(' not in c3:
		skip.append('DrawCircleWASM')
	if 'raylib::draw_rectangle_v' not in c3:
		skip.append('DrawRectangleV')
	if 'raylib::clear_background' not in c3:
		skip.append('ClearBackground')

	js = [
		JS_LIB_API,
	]
	for fname in raylib_like_api:
		if fname in skip:
			print('skipping:', fname)
			continue
		js.append(raylib_like_api[fname])

	for fname in c3dom_api:
		if fname+'(' in c3:
			js.append(c3dom_api[fname])

	js.append('}')
	js.append('new api()')
	return '\n'.join(js)

def compress_js(js):
	assert '`' not in js
	js = js.replace('\t', '')
	js = js.replace('this.ctx', 'this.c').replace('const ', 'let ')
	rep = [
		'this.c.', 'this.wasm.instance.exports.memory.buffer', 'this.', 'Uint8Array', 'Float32Array', 
		'window.requestAnimationFrame', 'function', 'return', 'canvas.', 
		#'getColorFromMemory','.toString(16).padStart',
	]
	o = []
	if 0:
		vars = []
		for idx, r in enumerate(rep):
			if idx == 0:
				key = '_'
			else:
				key = '_%s' % idx
			vars.append('%s="%s"' % (key, r))
			js = js.replace(r, '${%s}' % key)
		o.append('var %s;' % ','.join(vars) )
		o.append('eval`%s`' % js)
		return '\n'.join(o)
	else:
		o=[
		#'String.prototype.r=(a)=>{',
		'	function $r(r,a){',
		'	for(k in a){',
		'		r=r.replaceAll(String.fromCharCode(k), a[k])',
		'	}',
		'	return r',
		'}',
		]
		#ascii_bytes = [chr(i) for i in list(range(1,10))+list(range(14,31))]
		#ascii_bytes.reverse()
		ascii_bytes = [chr(i) for i in range(1,10)]
		g = []
		for idx, r in enumerate(rep):
			bite = ascii_bytes.pop()
			js = js.replace(r, bite)
			#g[ord(bite)] = r
			g.append(r)


		o.append('var _$_=$r(`%s`,"%s".split(" "))' %(js, ' '.join(g) ))
		return '\n'.join(o)

def gen_html(wasm, c3, user_html=None, background='', test_precomp=False):
	cmd = ['gzip', '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/c3api.js'
	jslib = gen_js_api(c3)

	if test_precomp:
		## after gz this will be a few bytes bigger
		jslibcomp = compress_js(jslib)
		print(jslibcomp)
		print('jslib bytes:', len(jslib))
		print('compressed:', len(jslibcomp))

	open(jtmp,'w').write(jslib)
	cmd = ['gzip', '--keep', '--force', '--verbose', '--best', jtmp]
	print(cmd)
	subprocess.check_call(cmd)
	js = open(jtmp+'.gz','rb').read()
	jsb = base64.b64encode(js).decode('utf-8')

	if test_precomp:
		jtmp = '/tmp/c3api.comp.js'
		open(jtmp,'w').write(jslibcomp)
		cmd = ['gzip', '--keep', '--force', '--verbose', '--best', jtmp]
		print(cmd)
		subprocess.check_call(cmd)
		jsc = open(jtmp+'.gz','rb').read()
		print('compressed.gz:', len(jsc))
		jsbc = base64.b64encode(jsc).decode('utf-8')

	if '--debug' in sys.argv:
		background = 'red'
	if background:
		background = 'style="background-color:%s"' % background

	o = [
		'<html>',
		'<body %s>' % background,
		'<canvas id="game"></canvas>',
		'<script>', 
		'var $0="%s"' % jsb,
		'var $1="%s"' % b,
		JS_DECOMP, 
		'</script>',
	]
	if user_html:
		o += user_html

	hsize = len('\n'.join(o)) + len('</body></html>')

	o += [
		'<pre>',
		'jslib bytes=%s' % len(jslib),
		'jslib.gz bytes=%s' % len(js),
		'jslib.base64 bytes=%s' % len(jsb),

		#'jslib.comp.gz bytes=%s' % len(jsc),
		#'jslib.comp.base64 bytes=%s' % len(jsbc),

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

	o += [
		'<pre>',
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
	o = blender_to_c3(world, wasm=True, html=user_html)
	o = '\n'.join(o)
	#print(o)
	tmp = '/tmp/c3blender.c3'
	open(tmp, 'w').write(o)
	wasm = build(input=tmp, wasm=True, opt=world.c3_export_opt)
	#os.system('cp -v ./index.html /tmp/.')
	#os.system('cp -v ./raylib.js /tmp/.')
	html = gen_html(wasm, o, user_html)
	open('/tmp/index.html', 'w').write(html)
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

bpy.types.World.c3_export_html = bpy.props.StringProperty(name="c3 export path (.html)")

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



@bpy.utils.register_class
class C3ScriptsPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Scripts_Panel"
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


