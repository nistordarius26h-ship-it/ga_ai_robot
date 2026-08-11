# 3D Modeling & Rendering

The chassis and mechanical layout were designed in **Autodesk Fusion 360**.

## Files

- `media/gaairobot3dmodel.step` — full assembly, exported in the neutral **STEP (.step)** format so it can be opened in any CAD package (Fusion 360, SolidWorks, FreeCAD, etc.) without vendor lock-in.
- `media/gaairobotrender.png` — rendered preview of the assembly, used in the main README.

## Workflow

1. **Component modeling.** Each physical part of the robot (chassis plates, motor mounts, suspension links, sensor housings) modeled as a separate Fusion 360 component, so the design stays parametric and individual parts can be revised without rebuilding the whole assembly.
2. **Assembly & joints.** Components brought together in a Fusion 360 assembly using joints (rigid, revolute) rather than static positioning, which matters specifically for the **active mechanical suspension** — revolute joints let the suspension geometry be checked for range of motion and clearance directly in CAD before anything is cut or printed.
3. **Fit-checking against real hardware.** Key dimensions (motor mounting bolt pattern, wheel/encoder shaft diameter, LiPo pack footprint, PCB/perfboard mounting holes) modeled to match datasheet or caliper-measured dimensions of the actual components, so the design isn't purely aesthetic — it double-checks that everything physically fits before fabrication.
4. **Rendering.** Fusion 360's built-in rendering workspace (ray-traced render engine) used to produce the presentation image in `media/gaairobotrender.png` — applying materials/appearances to each component (metal, plastic, rubber) and setting up scene lighting for a clean presentation shot, separate from the working design view.
5. **Export.** Final assembly exported as **STEP** rather than a Fusion-native format for two reasons: it's the standard interchange format for mechanical CAD, and it keeps the model viewable/reusable even without a Fusion 360 license (useful for sharing the design publicly on GitHub).

## Why STEP over other export formats

| Format | Use case |
|---|---|
| **STEP** (used here) | Full parametric-equivalent geometry, editable in any CAD tool, ideal for sharing a complete assembly |
| STL | Good for 3D printing a single part, but loses assembly structure and exact parametric surfaces |
| Fusion 360 native (.f3d/.f3z) | Only opens in Fusion 360, not suitable for public sharing |

## Tips from this build

- Model to real datasheet dimensions early — retrofitting a model to match hardware you already bought is far more painful than modeling from the datasheet before ordering.
- Keep suspension and other moving assemblies as actual joints in the CAD, not fixed geometry — it's the only way to visually verify range-of-motion and collision clearance before machining.
- Export a STEP checkpoint whenever a design milestone is reached (not just at the very end) — it's a lightweight, tool-agnostic backup of your assembly history.
