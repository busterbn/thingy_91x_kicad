"""Restore Altium harness connectivity in the imported KiCad schematic.

The importer turns each harness connector into a bus labelled "{TYPE}" plus bus entries, but drops
the entry (member) names, and the unprefixed "{TYPE}" label makes two harnesses of the same type on
one sheet share member nets. Here every "{TYPE}" bus label gets the prefix of the hierarchical label
on the same bus ("VCOM0{UART}"), and every harness entry wire gets a "PREFIX.MEMBER" label.
Other local labels on those wires are renamed (sheet-wide) to the member name.

Usage: python3 fix_harness.py <kicad project dir> <Altium Designer files dir>   (needs olefile)
"""
import re, sys, uuid
from collections import defaultdict
import olefile, struct

KI, ALT = sys.argv[1], sys.argv[2]
SHEETS = ['connections', 'nrf9151', 'nrf5340', 'nrf7002', 'sensors_and_leds', 'power_supply',
          'interface', 'switch_fsa', 'switch_nx', 'rf_front-end']
MM = 0.254

def additional(path):
    d = olefile.OleFileIO(path).openstream('Additional').read()
    i, out = 0, []
    while i + 4 <= len(d):
        n = struct.unpack('<I', d[i:i + 4])[0] & 0xFFFFFF
        body = d[i + 4:i + 4 + n].rstrip(b'\0').decode('latin-1')
        i += 4 + n
        out.append({k.upper(): v for k, v in (kv.split('=', 1) for kv in body.split('|') if '=' in kv)})
    return out[1:]

def overbar(name):
    return '~{' + name.replace('\\', '') + '}' if name.endswith('\\') else name

def num(r, key):
    return float(r.get(key, 0)) + float(r.get(key + '_FRAC1', 0)) / 1e6

def pt(x, y):
    return (round(float(x), 4), round(float(y), 4))

def harness_entries(path):
    recs = additional(path)
    out = []
    for r in recs:
        if r.get('RECORD') != '216':
            continue
        c = recs[int(r.get('OWNERINDEX', 0))]
        x, y, w, h = num(c, 'LOCATION.X'), num(c, 'LOCATION.Y'), num(c, 'XSIZE'), num(c, 'YSIZE')
        d = num(r, 'DISTANCEFROMTOP') * 10
        px, py = {'0': (x, y - d), '1': (x + w, y - d), '2': (x + d, y), '3': (x + d, y - h)}[r.get('SIDE', '0')]
        out.append((overbar(r['NAME']), pt(px * MM, 297 - py * MM)))
    return out

BLOCK = re.compile(r'\n\t\((bus_entry|bus|wire|label|hierarchical_label|global_label)\b.*?\n\t\)', re.S)
AT = re.compile(r'\(at ([-\d.]+) ([-\d.]+)')

def parse(t):
    items = []
    for m in BLOCK.finditer(t):
        kind, s = m.group(1), m.group(0)
        if kind in ('bus', 'wire'):
            pts = [pt(*p) for p in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', s)]
        elif kind == 'bus_entry':
            x, y = AT.search(s).groups()
            w, h = re.search(r'\(size ([-\d.]+) ([-\d.]+)', s).groups()
            pts = [pt(x, y), pt(float(x) + float(w), float(y) + float(h))]
        else:
            pts = [pt(*AT.search(s).groups())]
        name = re.match(r'\n\t\(\w+ "([^"]*)"', s)
        items.append(dict(kind=kind, span=m.span(), pts=pts, name=name and name.group(1)))
    return items

def on_seg(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    return abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < 1e-3 and \
        min(x1, x2) - 1e-3 <= x <= max(x1, x2) + 1e-3 and min(y1, y2) - 1e-3 <= y <= max(y1, y2) + 1e-3

def groups(items, kind):
    """Union-find over segments of one kind (bus or wire) connected at endpoints/T-junctions."""
    segs = [i for i in items if i['kind'] == kind]
    parent = list(range(len(segs)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for i, a in enumerate(segs):
        for j, b in enumerate(segs[:i]):
            if any(on_seg(p, *b['pts']) for p in a['pts']) or any(on_seg(p, *a['pts']) for p in b['pts']):
                parent[find(i)] = find(j)
    g = defaultdict(list)
    for i, s in enumerate(segs):
        g[find(i)].append(s)
    return list(g.values())

def touching(group, p):
    return any(on_seg(p, *s['pts']) for s in group)

def label(name, p):
    return (f'\t(label "{name}"\n\t\t(at {p[0]} {p[1]} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uuid.uuid4()}")\n\t)')

for s in SHEETS:
    kf = f'{KI}/pca20065.kicad_sch' if s == 'connections' else f'{KI}/pca20065_{s}.kicad_sch'
    t = open(kf).read()
    items = parse(t)
    buses, wires = groups(items, 'bus'), groups(items, 'wire')
    labels = [i for i in items if i['kind'] in ('label', 'hierarchical_label', 'global_label')]
    entries = [i for i in items if i['kind'] == 'bus_entry']
    edits = {}  # span -> replacement text ('' = delete)

    # 1. prefix of each bus network, from the "P{T}" hierarchical label or sheet pin on it
    named = [(l['name'].split('{')[0], l['pts'][0]) for l in labels
             if l['name'] and '{' in l['name'] and not l['name'].startswith('{')]
    # sheet pins: several child sheets may share pin names, so qualify with the child's file name
    for sm in re.finditer(r'\n\t\(sheet\n.*?\n\t\)', t, re.S):
        blk = sm.group(0)
        short = re.search(r'"Sheetfile" "pca20065_([^".]+)', blk).group(1).replace('switch_', '').upper()
        named += [(f'{short}_{m.group(1)}' if s != 'connections' else m.group(1), pt(m.group(2), m.group(3)))
                  for m in re.finditer(r'\(pin "([^"{]+)\{[^"]*\}" \w+\s+\(at ([-\d.]+) ([-\d.]+)', blk)]
    bus_prefix = {}
    for bi, g in enumerate(buses):
        pre = {n for n, p in named if touching(g, p)}
        if len(pre) == 1:
            bus_prefix[bi] = pre.pop()
        elif pre:
            print(f'  {s}: bus with several prefixes {pre}')
        for l in labels:
            if bi in bus_prefix and l['kind'] == 'label' and l['name'].startswith('{') and touching(g, l['pts'][0]):
                old = t[l['span'][0]:l['span'][1]]
                edits[l['span']] = old.replace(f'"{l["name"]}"', f'"{bus_prefix[bi]}{l["name"]}"', 1)

    # 2. member labels on harness entry wires; other local labels on such a wire are renamed
    #    (everywhere on the sheet) to the member name so same-sheet connections by name survive.
    added, rename, noprefix = [], {}, []
    for name, p in harness_entries(f'{ALT}/pca20065_{s}.SchDoc'):
        e = next(e for e in entries if any(abs(q[0] - p[0]) + abs(q[1] - p[1]) < 0.01 for q in e['pts']))
        i = min((0, 1), key=lambda k: abs(e['pts'][k][0] - p[0]) + abs(e['pts'][k][1] - p[1]))
        p, other = e['pts'][i], e['pts'][1 - i]
        bi = next((i for i, g in enumerate(buses) if touching(g, other)), None)
        if bi not in bus_prefix:
            noprefix.append(name); continue
        full = f'{bus_prefix[bi]}.{name}'
        wg = next((g for g in wires if touching(g, p)), [])
        for l in labels:
            if l['kind'] == 'label' and wg and touching(wg, l['pts'][0]) and '{' not in l['name'] and l['name'] != full:
                if rename.get(l['name'], full) != full:
                    print(f'  {s}: CONFLICT {l["name"]} -> {rename[l["name"]]} / {full}')
                rename[l['name']] = full
        added.append(label(full, p))
    for l in labels:
        if l['kind'] == 'label' and l['name'] in rename and l['span'] not in edits:
            old = t[l['span'][0]:l['span'][1]]
            edits[l['span']] = old.replace(f'"{l["name"]}"', f'"{rename[l["name"]]}"', 1)

    for span in sorted(edits, reverse=True):
        t = t[:span[0]] + edits[span] + t[span[1]:]
    i = t.rstrip().rindex(')')
    t = t[:i] + '\n'.join(added) + '\n' + t[i:]
    open(kf, 'w').write(t)
    print(f'{s}: {len(added)} member labels, renamed {rename}, no prefix: {noprefix}')

# 3. Altium hidden pins tied to GND (hidden net name) -> hidden power inputs, which KiCad joins to GND by name
for s in SHEETS:
    kf = f'{KI}/pca20065.kicad_sch' if s == 'connections' else f'{KI}/pca20065_{s}.kicad_sch'
    t = open(kf).read()
    t2 = re.sub(r'\(pin passive line(\n(?:(?!\(pin ).)*?\(hide yes\)(?:(?!\(pin ).)*?\(name "GND")',
                r'(pin power_in line\1', t, flags=re.S)
    if t2 != t:
        open(kf, 'w').write(t2)
        print(f'{s}: hidden GND pins -> power_in')
