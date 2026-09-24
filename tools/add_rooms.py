"""Recreate Altium rooms used by design rules as KiCad rule areas (run with KiCad's bundled python)."""
import sys
import pcbnew

MIL = 0.0254
OX, OY = 47.8321, 181.9162   # Altium board coords -> KiCad mm, calibrated on footprint positions
ROOMS = {
    'nRF53':   [(3477.0399, 2843.748), (3762.0399, 2843.748), (3762.0399, 3056.2242), (3477.0399, 3056.2242)],
    'nPM6001': [(3464.2263, 3248.5622), (3638.0148, 3248.5622), (3638.0148, 3364.4304), (3464.2263, 3364.4304)],
}

board = pcbnew.LoadBoard(sys.argv[1])
existing = {z.GetZoneName() for z in board.Zones()}
for name, pts in ROOMS.items():
    if name in existing:
        continue
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    for f in (z.SetDoNotAllowTracks, z.SetDoNotAllowVias, z.SetDoNotAllowPads,
              z.SetDoNotAllowZoneFills, z.SetDoNotAllowFootprints):
        f(False)
    outline = z.Outline()
    outline.NewOutline()
    for x, y in pts:
        outline.Append(pcbnew.FromMM(x * MIL + OX), pcbnew.FromMM(-y * MIL + OY))
    board.Add(z)
pcbnew.SaveBoard(sys.argv[1], board)
print('rule areas:', [z.GetZoneName() for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName()])
