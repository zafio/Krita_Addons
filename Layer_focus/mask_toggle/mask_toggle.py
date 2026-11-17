"""
Mask Toggle - Krita plugin

One shortcut (default "<") toggles between a layer and its transparency mask:

  * On a layer  -> selects its transparency mask, remembers the current
                   foreground/background colors and resets them to black/white.
  * On a mask   -> selects the parent layer and restores the remembered colors.
"""

from krita import Extension, Krita

ACTION_ID = "mask_toggle_switch"
MASK_TYPE = "transparencymask"


class MaskToggleExtension(Extension):

    def __init__(self, parent):
        super().__init__(parent)
        self._saved_fg = None
        self._saved_bg = None
        # parent layer uniqueId -> uniqueId of the mask last used on it
        self._last_mask = {}

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction(
            ACTION_ID, "Toggle Transparency Mask", "tools/scripts")
        # Text and default shortcut come from actions/mask_toggle.action, which also
        # makes the action appear in Settings > Configure Krita > Keyboard Shortcuts.
        action.triggered.connect(self.toggle)

    # ------------------------------------------------------------------ helpers

    def _message(self, view, text):
        try:
            view.showFloatingMessage(text, Krita.instance().icon("transparencyMask"), 1500, 1)
        except Exception:
            pass

    def _find_mask(self, layer):
        masks = [n for n in layer.childNodes() if n.type() == MASK_TYPE]
        if not masks:
            return None
        last_id = self._last_mask.get(layer.uniqueId())
        for m in masks:
            if last_id is not None and m.uniqueId() == last_id:
                return m
        # topmost mask in the stack (childNodes() is bottom-to-top)
        return masks[-1]

    def _save_colors(self, view):
        self._saved_fg = view.foregroundColor()
        self._saved_bg = view.backgroundColor()

    def _reset_colors(self, view):
        reset = Krita.instance().action("reset_fg_bg")
        if reset is not None:
            reset.trigger()
        else:
            from krita import ManagedColor
            from PyQt5.QtGui import QColor
            view.setForeGroundColor(ManagedColor.fromQColor(QColor(0, 0, 0), view.canvas()))
            view.setBackGroundColor(ManagedColor.fromQColor(QColor(255, 255, 255), view.canvas()))

    def _restore_colors(self, view):
        if self._saved_fg is not None:
            view.setForeGroundColor(self._saved_fg)
        if self._saved_bg is not None:
            view.setBackGroundColor(self._saved_bg)
        self._saved_fg = None
        self._saved_bg = None

    # ------------------------------------------------------------------- action

    def toggle(self):
        app = Krita.instance()
        doc = app.activeDocument()
        window = app.activeWindow()
        view = window.activeView() if window else None
        if doc is None or view is None:
            return

        node = doc.activeNode()
        if node is None:
            return

        if node.type() == MASK_TYPE:
            # Mask -> back to parent layer, restore colors
            parent = node.parentNode()
            if parent is None:
                return
            self._last_mask[parent.uniqueId()] = node.uniqueId()
            doc.setActiveNode(parent)
            self._restore_colors(view)
            self._message(view, "Layer: " + parent.name())
            return

        # Layer -> its transparency mask, black/white colors
        mask = self._find_mask(node)
        if mask is None:
            self._message(view, "No transparency mask on \"" + node.name() + "\"")
            return

        # Only save if we don't already hold colors from an unfinished toggle
        if self._saved_fg is None:
            self._save_colors(view)
        self._last_mask[node.uniqueId()] = mask.uniqueId()
        doc.setActiveNode(mask)
        self._reset_colors(view)
        self._message(view, "Mask: " + mask.name())
