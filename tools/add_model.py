"""Attach a project 3D model to every instance of a footprint on the board and in the project library.

Usage: python3 add_model.py <project dir> <footprint name> <model file in 3dmodels/> "<ox> <oy> <oz>" "<rx> <ry> <rz>"
Re-running replaces the previous entry for the same model file.
"""
import re, sys

proj, fp_name, model, offset, rotate = sys.argv[1:6]
name = proj.rstrip('/').split('/')[-1]
path = f'${{KIPRJMOD}}/3dmodels/{model}'

def block(indent):
    i = '\t' * indent
    return (f'{i}(model "{path}"\n{i}\t(offset\n{i}\t\t(xyz {offset})\n{i}\t)\n{i}\t(scale\n{i}\t\t(xyz 1 1 1)\n'
            f'{i}\t)\n{i}\t(rotate\n{i}\t\t(xyz {rotate})\n{i}\t)\n{i})\n')

def attach(text, indent):
    old = re.compile(r'\t{%d}\(model "%s".*?\n\t{%d}\)\n' % (indent, re.escape(path), indent), re.S)
    text = old.sub('', text)
    close = '\n' + '\t' * (indent - 1) + ')'
    end = text.index(close, 1) if indent > 1 else text.rstrip().rindex(close)   # footprint's own closing paren
    return text[:end + 1] + block(indent) + text[end + 1:]

pcb = f'{proj}/{name}.kicad_pcb'
t = open(pcb).read()
blocks = re.split(r'(?=\n\t\(footprint ")', t)
n = 0
for k, b in enumerate(blocks):
    if b.startswith(f'\n\t(footprint "{name}-import-fps:{fp_name}"'):
        blocks[k] = attach(b, 2); n += 1
open(pcb, 'w').write(''.join(blocks))

lib = f'{proj}/{name}-import-fps.pretty/{fp_name}.kicad_mod'
new = attach(open(lib).read(), 1)
open(lib, 'w').write(new)
print(f'{fp_name}: {model} on {n} footprint(s) + library')
