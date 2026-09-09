# Better Camera Navigation

Better Camera Navigation is a Blender add-on that replaces the default viewport navigation workflow with a faster, game-like camera system inspired by Mine-imator-style controls.

It is designed for users who prefer **freelook + WASD movement**, while still keeping orbit, pan, zoom, and Blender's native middle-mouse pan available.

## Features

- RMB freelook that rotates from the current viewpoint instead of orbiting around Blender's pivot.
- LMB orbit around the current pivot.
- Shift + LMB grab-style pan.
- Native Blender MMB pan.
- WASD movement relative to the current view direction.
- Q / E vertical movement.
- Space speed boost and Shift slow movement.
- Mouse-wheel zoom.
- Optional direct control of the active Blender camera while in Camera View.
- Horizontal and vertical mouse inversion options.
- Adjustable movement, look, and pan sensitivity.
- Quick toggle with `Ctrl + F`.
- Blender's native `Ctrl + F` Face menu remains available in Mesh Edit Mode.

## Requirements

- Blender **3.6 or newer**.

## Installation

### Recommended: install a release ZIP

1. Download `better_camera_navigation_v1_0.zip` from the repository's **Releases** page.
2. Open Blender.
3. Go to **Edit > Preferences > Add-ons**.
4. Choose **Install from Disk** and select the ZIP.
5. Enable **Better Camera Navigation**.
6. Open a 3D Viewport and press `N`.
7. Open the **Better Camera** tab and click **Enable Navigation**.

If an older version is already installed, disabling/removing it before installing the new version is recommended.

### Install from source

Copy the `better_camera_navigation` folder into your Blender add-ons directory, then enable **Better Camera Navigation** from Blender Preferences.

## Controls

| Input | Action |
| --- | --- |
| RMB + drag | Freelook / rotate in place |
| LMB + drag | Orbit around the current pivot |
| Shift + LMB + drag | Pan / grab view |
| MMB + drag | Blender native pan |
| Mouse wheel | Zoom |
| W / A / S / D | Move relative to view |
| Q / E | Move down / up |
| Space | Move faster |
| Shift | Move slower |
| Ctrl + F | Toggle Better Camera Navigation |
| Esc | Disable navigation |

> In **Mesh Edit Mode**, the add-on does not capture `Ctrl + F`, so Blender's native Face menu keeps working.

## Settings

Open **3D Viewport > N Panel > Better Camera** to configure:

- Move Speed
- Space Multiplier
- Shift Multiplier
- Move Camera in Camera View
- Look Sensitivity
- Pan Sensitivity
- Invert Horizontal
- Invert Vertical

## Camera View

When **Move Camera in Camera View** is enabled and the viewport is in Camera View (`Numpad 0`), Better Camera Navigation moves and rotates the active scene camera directly.

Outside Camera View, the add-on controls the normal 3D viewport instead.

## Source Structure

```text
Better-Camera-Navigation/
├── better_camera_navigation/
│   ├── __init__.py
│   └── nav_math.py
├── .gitignore
├── LICENSE
└── README.md
```

`__init__.py` contains the Blender operators, panel, settings, keymap, camera/view manipulation, and add-on registration.

`nav_math.py` contains the reusable navigation math and input helpers.

Some internal identifiers still use the original `mineimator_*` naming to preserve compatibility with the existing v1.0 source. The public add-on name shown in Blender is **Better Camera Navigation**.

## Version 1.0.0

- Better Camera Navigation branding.
- RMB freelook.
- LMB orbit.
- Shift + LMB pan.
- Native MMB pan.
- WASD + Q/E movement.
- Space fast movement and Shift slow movement.
- Camera View control.
- Configurable movement and mouse sensitivity.
- `Ctrl + F` navigation toggle.
- Mesh Edit Mode compatibility for Blender's native `Ctrl + F` Face menu.

## License

This project is licensed under the [MIT License](LICENSE).
