"""Close Edge.Cuts gaps left by the Altium import: snap outline endpoints closer than TOL together.

Usage: <kicad python> fix_outline.py <board.kicad_pcb>
"""
import sys
import pcbnew

TOL = pcbnew.FromMM(0.001)

board = pcbnew.LoadBoard(sys.argv[1])
shapes = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts
          and d.GetShape() in (pcbnew.SHAPE_T_SEGMENT, pcbnew.SHAPE_T_ARC)]

key = lambda p: (p.x, p.y)  # VECTOR2I has no usable == in the python binding

# cluster endpoints; each cluster snaps to its first point
anchors = []
def snap(p):
    for a in anchors:
        if (a - p).EuclideanNorm() <= TOL:
            return a
    anchors.append(p)
    return p

moved = 0
for s in shapes:
    start, end = snap(s.GetStart()), snap(s.GetEnd())
    if key(start) == key(s.GetStart()) and key(end) == key(s.GetEnd()):
        continue
    if s.GetShape() == pcbnew.SHAPE_T_ARC:
        s.SetArcGeometry(start, s.GetArcMid(), end)
    else:
        s.SetStart(start); s.SetEnd(end)
    moved += 1

# drop segments that collapsed to (almost) nothing
for s in list(shapes):
    if s.GetShape() == pcbnew.SHAPE_T_SEGMENT and (s.GetEnd() - s.GetStart()).EuclideanNorm() <= TOL:
        board.Remove(s); shapes.remove(s); moved += 1

# a short segment doubling back over a longer one (overlap = self-intersection): keep the long one,
# ending it where the short one ended
ends = lambda s: [(s.GetStartX(), s.GetStartY()), (s.GetEndX(), s.GetEndY())]
segs = [s for s in shapes if s.GetShape() == pcbnew.SHAPE_T_SEGMENT]
removed = set()
for a in segs:
    for b in segs:
        if a is b or id(a) in removed or id(b) in removed:
            continue
        ea, eb = ends(a), ends(b)
        shared = set(ea) & set(eb)
        if not shared:
            continue
        p = shared.pop()
        a_far, b_far = ea[1 - ea.index(p)], eb[1 - eb.index(p)]
        da = (a_far[0] - p[0], a_far[1] - p[1]); db = (b_far[0] - p[0], b_far[1] - p[1])
        la, lb = (da[0] ** 2 + da[1] ** 2) ** 0.5, (db[0] ** 2 + db[1] ** 2) ** 0.5
        if lb < la and da[0] * db[0] + da[1] * db[1] > 0.9999 * la * lb:
            new = pcbnew.VECTOR2I(*b_far)
            a.SetStart(new) if ea.index(p) == 0 else a.SetEnd(new)
            board.Remove(b); removed.add(id(b)); moved += 1

pcbnew.SaveBoard(sys.argv[1], board)
print(f'{len(shapes)} outline shapes, {moved} fixed')
