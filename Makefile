all: demo.wasm demo-linux

demo-linux: demo.c3
	c3c compile -l ./raylib-5.0_linux_amd64/lib/libraylib.a -o demo-linux demo.c3 raylib.c3

demo.wasm: demo.c3
	c3c compile -D PLATFORM_WEB --reloc=none --target wasm32 -O3 -g0 --link-libc=no --use-stdlib=no --no-entry -o demo -z --export-table demo.c3 raylib.c3

demo.wat: demo.wasm
	wasm2wat demo.wasm > demo.wat

install-blender:
	sudo snap install blender
install-blender-fedora:
	sudo dnf install blender
blender:
	python3 ./c3blender.py --test --linux
blender-wasm:
	python3 ./c3blender.py --test --wasm
blender-8bit:
	python3 ./c3blender.py --test --linux --8bits
blender-wasm-8bit:
	python3 ./c3blender.py --test --wasm --8bits
blender-wasm-8bit-opt:
	python3 ./c3blender.py --test --wasm --8bits --stroke-opt=4
