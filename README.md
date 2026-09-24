# Thingy:91 X in KiCad

KiCad 10 port of Nordic's Thingy:91 X hardware files (v2.0.0), converted from the original Altium project.

- `pca20065/` main board (PCA20065 v2.0.0)
- `pca64165/` current measurement and debug board (PCA64165 v1.1.0)
- `casing/` enclosure STEP files
- `tools/` scripts used for the conversion

Open the `.kicad_pro` files in KiCad 10 or newer. Footprints, symbols and 3D models are included in the project folders.

## Notes

Schematic and PCB connectivity was checked pin by pin against the original Altium board, and they match.

Altium harnesses are now KiCad bus groups, so some nets were renamed, e.g. `BMI270_INT` is `INTERRUPT.INT2`.

Nordic's design rules are in the `.kicad_dru` files. DRC still shows some warnings that come from the original design (stacked vias, a few 0.09 mm clearances around the nRF5340, silkscreen).

`kicad-cli` schematic parity reports "No corresponding pin" for unlabeled nets. Update PCB from Schematic in the GUI shows no changes, so this looks like a CLI issue.

## License

The design is Nordic Semiconductor's. See `License.txt` and `Legal_Disclaimer.pdf`. This is not an official Nordic release.
