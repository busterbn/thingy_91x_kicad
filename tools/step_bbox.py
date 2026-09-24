"""Print the vertex bounding box and length unit of STEP files (to work out 3D model offset/rotation)."""
import re, sys

for path in sys.argv[1:]:
    t = open(path, errors='ignore').read().replace(' ', '')
    pts = {m.group(1): tuple(map(float, m.group(2, 3, 4))) for m in re.finditer(
        r"#(\d+)=CARTESIAN_POINT\('[^']*',\(([-\d.E+]+),([-\d.E+]+),([-\d.E+]+)\)\)", t)}
    verts = [pts[m] for m in re.findall(r"VERTEX_POINT\('[^']*',#(\d+)\)", t) if m in pts]
    unit = 'inch' if 'INCH' in t.upper() else ('mm' if '.MILLI.' in t else 'm?')
    box = [(round(min(p[i] for p in verts), 3), round(max(p[i] for p in verts), 3)) for i in range(3)]
    print(f'{path.split("/")[-1]}: unit {unit}, x {box[0]}, y {box[1]}, z {box[2]}')
