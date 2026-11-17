# Cursor Resize & Opacity (Krita plugin)

Author: Zafio

Hold **Alt** over the canvas and move the cursor (no mouse/pen button pressed):

| Movement   | Changes          | Range      |
|------------|------------------|------------|
| Left/right | Brush size       | 1 – 1000 px |
| Up/down    | Painting opacity | 1 – 100 %  |

The first few pixels of movement pick the axis; it stays locked until Alt is released, so resizing never nudges opacity and vice versa. A floating message on the canvas shows the current value.

## Precision at small values

- **Size 1–20 px:** 8 screen pixels per 1 px of brush size (about 150 px of travel for the whole 1–20 range).
- **Above 20 px:** grows exponentially with no jump in speed at the joint (20→100 px ≈ 260 px of travel, 100→1000 px ≈ 370 px).
- **Opacity 1–20 %:** 5 px per percent; above 20 %: 2.5 px per percent.

Pushing past a limit and coming back responds immediately. All of this can be tuned at the top of `cursor_resize_opacity/cursor_resize_opacity.py`.

## Install

**Easiest:** in Krita, *Tools > Scripts > Import Python Plugin from File…* and pick `cursor_resize_opacity.zip`, then restart Krita and enable it in *Settings > Configure Krita > Python Plugin Manager*.

**Windows script:** run `install.ps1`, restart Krita, enable *Cursor Resize & Opacity* in the Python Plugin Manager, restart again.

**Manual:** copy `cursor_resize_opacity.desktop` and the `cursor_resize_opacity/` folder into Krita's `pykrita` folder (*Settings > Manage Resources > Open Resource Folder*).

## Notes

- Alt is ignored while typing in a text field, while a button is held, over dockers, or when Ctrl/Shift are also held. Alt+key shortcuts still work as before.
- Turn it on/off with *Tools > Scripts > Cursor Resize & Opacity (Alt + drag)* (remembered between sessions).
- Works with Krita 5.x (PyQt5) and is written to also load on Qt6 builds.
- Inspired by the cursor trackers in [Shortcut Composer](https://github.com/wojtryb/Shortcut-Composer).
