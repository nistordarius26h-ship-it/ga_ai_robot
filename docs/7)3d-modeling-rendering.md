# 3D Modeling & Rendering

Chassis and mechanical layout designed in Autodesk Fusion 360.

## Files

- `media/gaairobot3dmodel.step` — full assembly, exported as STEP so it opens in any CAD package (Fusion 360, SolidWorks, FreeCAD) without vendor lock-in.
- `media/gaairobotrender.png` — rendered preview, used in the main README.

## Workflow

1. Each part (chassis plates, motor mounts, suspension links, sensor housings) modeled as a separate Fusion 360 component — parametric, so individual parts can be revised without rebuilding the assembly.
2. Key dimensions (motor bolt pattern, wheel/encoder shaft diameter, LiPo footprint, mounting holes) matched to datasheet or caliper measurements, checked against real hardware before fabrication.
3. Rendered with Fusion's built-in ray-traced render workspace — materials/appearances per component, scene lighting, separate from the working design view.
4. Exported as STEP: standard mechanical CAD interchange format, viewable without a Fusion 360 license.

## Why STEP

| Format | Use case |
|---|---|
| STEP (used here) | Full parametric-equivalent geometry, editable in any CAD tool |
| STL | Fine for printing a single part, loses assembly structure |
| Fusion native (.f3d/.f3z) | Only opens in Fusion 360 |

## Notes

- Model to real datasheet dimensions before ordering parts — retrofitting a model to hardware you already bought is more work than modeling first.
