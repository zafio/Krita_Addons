# Cursor Resize & Opacity - Krita 5.x plugin
# Author: Zafio
#
# Hold Alt, press the right mouse button over the canvas and drag:
#   - horizontally -> brush size (right = bigger, minimum 1 px)
#   - vertically   -> painting opacity (up = more opaque)
# The first movement past a small deadzone picks the axis; it stays locked
# until the right button is released. Small values are precise (see curves.py).
#
# Idea based on the cursor trackers of Shortcut Composer by Wojciech Trybus
# (https://github.com/wojtryb/Shortcut-Composer). Qt shortcuts can't bind a
# mouse button, so Alt + RMB is caught with an application-wide event filter.

from krita import Extension, Krita

try:
    from PyQt5.QtCore import QObject, QEvent, QTimer, Qt
    from PyQt5.QtGui import QCursor, QIcon
    from PyQt5.QtWidgets import QApplication
except ImportError:  # Krita 6 (Qt6)
    from PyQt6.QtCore import QObject, QEvent, QTimer, Qt
    from PyQt6.QtGui import QCursor, QIcon
    from PyQt6.QtWidgets import QApplication

from .curves import SizeCurve, OpacityCurve


# --------------------------------------------------------------------------
# Settings (edit here to tune the feel)
# --------------------------------------------------------------------------
DEADZONE_PX = 6              # movement needed before the axis is picked
TICK_MS = 16                 # cursor polling interval (~60 fps)

SIZE_PRECISE_UNTIL = 20      # px; below this every size step is slow/precise
SIZE_PX_PER_UNIT = 8         # screen px per 1 px of brush size in that range
SIZE_MAX = 1000              # px; upper limit reached by dragging

OPACITY_MIN = 1              # %
OPACITY_PRECISE_UNTIL = 20   # %; below this every percent is slow/precise
OPACITY_PRECISE_PX = 5       # screen px per 1 % below OPACITY_PRECISE_UNTIL
OPACITY_PX = 2.5             # screen px per 1 % above it

SHOW_MESSAGE = True          # floating "Size: 12 px" / "Opacity: 40 %" text
ONLY_OVER_CANVAS = True      # only start when the press is on the canvas

SETTINGS_GROUP = "cursor_resize_opacity"
ACTION_TOGGLE = "cursor_resize_opacity_toggle"

CANVAS_CLASSES = ("KisOpenGLCanvas2", "KisQPainterCanvas", "KisCanvasWidgetBase")

ALT = Qt.KeyboardModifier.AltModifier
OTHER_MODS = (Qt.KeyboardModifier.ControlModifier
              | Qt.KeyboardModifier.ShiftModifier
              | Qt.KeyboardModifier.MetaModifier)


class _Tracker(QObject):
    """Application event filter + timer that runs the Alt drag."""

    IDLE, WAITING, SIZE, OPACITY = range(4)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = True
        self.state = self.IDLE
        self.view = None
        self.last_pos = None
        self.origin = None
        self.travel = 0.0
        self.curve = None
        self.last_applied = None
        self.from_mouse = True
        self.swallow_context_menu = False

        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._tick)

    # -- event filter -------------------------------------------------------
    # Alt + right mouse button (mouse or pen side button) starts the drag;
    # releasing the right button ends it. While dragging, the right-button
    # press/move/release are consumed so Krita doesn't also open the pop-up
    # palette or start a stroke. Everything else passes through untouched.
    PRESS = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick,
             QEvent.Type.TabletPress)
    MOVE = (QEvent.Type.MouseMove, QEvent.Type.TabletMove)
    RELEASE = (QEvent.Type.MouseButtonRelease, QEvent.Type.TabletRelease)

    def eventFilter(self, obj, event):
        try:
            etype = event.type()

            if self.state == self.IDLE:
                if etype == QEvent.Type.ContextMenu and self.swallow_context_menu:
                    # Windows sends a context menu after the RMB release.
                    self.swallow_context_menu = False
                    return True
                if etype in self.PRESS and \
                        event.button() == Qt.MouseButton.RightButton:
                    return self._try_start(event)
                return False

            # -- dragging --
            if etype in (QEvent.Type.ApplicationDeactivate,
                         QEvent.Type.WindowDeactivate):
                self._stop()
                return False
            # Some tablet drivers report the side-button release as NoButton.
            if etype in self.RELEASE and (
                    event.button() == Qt.MouseButton.RightButton or
                    (not self.from_mouse and
                     etype == QEvent.Type.TabletRelease)):
                self._stop()
                self.swallow_context_menu = True
                QTimer.singleShot(300, self._clear_context_swallow)
                return True
            if etype in self.PRESS or etype in self.MOVE or \
                    etype in self.RELEASE or etype == QEvent.Type.ContextMenu:
                return True
            if etype == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._stop()
                return True
        except Exception:
            self._stop()
        return False

    def _clear_context_swallow(self):
        self.swallow_context_menu = False

    # -- start / stop ---------------------------------------------------------
    def _try_start(self, event):
        """Return True (consume the press) if the drag started."""
        if not self.enabled:
            return False
        mods = QApplication.queryKeyboardModifiers()
        if not (mods & ALT) or (mods & OTHER_MODS):
            return False

        window = Krita.instance().activeWindow()
        if window is None or window.activeView() is None:
            return False
        if window.activeView().document() is None:
            return False
        if ONLY_OVER_CANVAS and not self._cursor_over_canvas():
            return False

        self.view = window.activeView()
        self.from_mouse = event.type() != QEvent.Type.TabletPress
        self.origin = QCursor.pos()
        self.last_pos = self.origin
        self.last_applied = None
        self.state = self.WAITING
        self.timer.start()
        return True

    def _stop(self):
        self.timer.stop()
        self.state = self.IDLE
        self.view = None
        self.curve = None

    @staticmethod
    def _cursor_over_canvas():
        widget = QApplication.widgetAt(QCursor.pos())
        while widget is not None:
            if widget.metaObject().className() in CANVAS_CLASSES:
                return True
            widget = widget.parentWidget()
        return False

    # -- main loop ------------------------------------------------------------
    def _tick(self):
        try:
            # Missed mouse release (e.g. released outside the window).
            if self.from_mouse and not (
                    QApplication.mouseButtons() & Qt.MouseButton.RightButton):
                self._stop()
                return

            pos = QCursor.pos()

            if self.state == self.WAITING:
                dx = pos.x() - self.origin.x()
                dy = pos.y() - self.origin.y()
                if max(abs(dx), abs(dy)) <= DEADZONE_PX:
                    return
                if abs(dx) >= abs(dy):
                    self._begin_size()
                else:
                    self._begin_opacity()
                # Measure from here, the deadzone movement is not applied.
                self.last_pos = pos
                return

            if self.state == self.SIZE:
                delta = pos.x() - self.last_pos.x()
            else:
                delta = self.last_pos.y() - pos.y()  # screen y grows downward
            self.last_pos = pos
            if delta == 0:
                return

            # Accumulate and clamp: pushing past a limit and coming back
            # responds immediately, no dead travel to undo.
            self.travel = min(max(self.travel + delta, self.curve.min_travel),
                              self.curve.max_travel)
            self._apply()
        except Exception:
            self._stop()

    def _begin_size(self):
        current = float(self.view.brushSize())
        self.curve = SizeCurve(
            precise_until=SIZE_PRECISE_UNTIL,
            px_per_unit=SIZE_PX_PER_UNIT,
            # Never pull a bigger existing brush down to SIZE_MAX.
            max_size=max(SIZE_MAX, current),
        )
        self.travel = self.curve.travel_for(current)
        self.state = self.SIZE

    def _begin_opacity(self):
        current = float(self.view.paintingOpacity()) * 100.0
        self.curve = OpacityCurve(
            min_opacity=OPACITY_MIN,
            precise_until=OPACITY_PRECISE_UNTIL,
            precise_px_per_unit=OPACITY_PRECISE_PX,
            px_per_unit=OPACITY_PX,
        )
        self.travel = self.curve.travel_for(current)
        self.state = self.OPACITY

    def _apply(self):
        value = self.curve.snap(self.curve.value_at(self.travel))
        if value == self.last_applied:
            return
        self.last_applied = value
        if self.state == self.SIZE:
            self.view.setBrushSize(float(value))
            self._message("Size: %d px" % value)
        else:
            self.view.setPaintingOpacity(value / 100.0)
            self._message("Opacity: %d %%" % value)

    def _message(self, text):
        if not SHOW_MESSAGE:
            return
        try:
            # priority 0 = high, so it replaces itself instantly
            self.view.showFloatingMessage(text, QIcon(), 700, 0)
        except Exception:
            pass


class CursorResizeOpacityExtension(Extension):

    def __init__(self, parent):
        super().__init__(parent)
        self.tracker = None

    def setup(self):
        self.tracker = _Tracker()
        enabled = Krita.instance().readSetting(SETTINGS_GROUP, "enabled", "true")
        self.tracker.enabled = (enabled != "false")
        QApplication.instance().installEventFilter(self.tracker)

    def createActions(self, window):
        action = window.createAction(
            ACTION_TOGGLE,
            "Cursor Resize & Opacity (Alt + RMB drag)",
            "tools/scripts",
        )
        action.setCheckable(True)
        action.setChecked(self.tracker.enabled if self.tracker else True)
        action.toggled.connect(self._set_enabled)

    def _set_enabled(self, enabled):
        if self.tracker is None:
            return
        self.tracker.enabled = bool(enabled)
        if not enabled:
            self.tracker._stop()
        Krita.instance().writeSetting(
            SETTINGS_GROUP, "enabled", "true" if enabled else "false")
