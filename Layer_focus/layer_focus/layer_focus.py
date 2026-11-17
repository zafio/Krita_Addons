"""
Layer Focus - Krita 5.x (PyQt5)

1. Draws a lighter-hue outline around every selected row in the Layers docker
   (brighter/thicker for the active layer).
2. When the selection changes from somewhere other than a click in the list
   (canvas Alt+click, shortcuts, Page Up/Down...), smoothly scrolls the
   Layers docker so the active layer sits in the vertical centre.

Nothing is stored in the document; everything is a transparent overlay on the
docker's QTreeView, so Krita's own delegate is left untouched.
"""
from krita import Krita, Extension
from PyQt5.QtCore import (Qt, QObject, QEvent, QTimer, QRectF, QModelIndex,
                          QPropertyAnimation, QEasingCurve)
from PyQt5.QtGui import QColor, QPainter, QPalette, QPen
from PyQt5.QtWidgets import (QWidget, QTreeView, QStyle, QStyleOptionViewItem,
                             QAbstractItemDelegate)

try:
    from PyQt5 import sip
except ImportError:  # very old bundles
    import sip

# ---- tweak these -----------------------------------------------------------
OUTLINE_COLOR = QColor(176, 186, 138)   # lighter version of the theme's olive (hue ~73 deg)
ACTIVE_COLOR = QColor(214, 224, 170)    # active layer, a step brighter
OUTLINE_WIDTH = 1.5
ACTIVE_WIDTH = 2.0
CENTER_ON_SELECT = True                 # scroll active layer to the middle
CENTER_AFTER_LIST_CLICK = False         # also re-centre when you clicked inside the list
TRANSPARENT_SELECTION = True            # no fill behind selected layers; the outlines show the selection
# Only used when TRANSPARENT_SELECTION = False:
SELECTED_TEXT_COLOR = QColor(34, 34, 34)  # layer name colour on selected rows; None = leave to theme
SELECTED_BG_COLOR = QColor(142, 150, 110)  # background of selected-but-not-active layers (theme's is 118,126,89); None = leave to theme
ANIM_MS = 160
POLL_MS = 150
# ---------------------------------------------------------------------------


class _Overlay(QWidget):
    """Transparent, click-through widget that paints the outlines."""

    def __init__(self, view):
        super().__init__(view)  # sibling of the viewport, so viewport scrolling doesn't move it
        self.view = view
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.sync_geometry()
        self.show()
        self.raise_()

    def sync_geometry(self):
        self.setGeometry(self.view.viewport().geometry())

    def signature(self):
        sm = self.view.selectionModel()
        if sm is None:
            return None
        rects = []
        for idx in sm.selectedIndexes():
            r = self.view.visualRect(idx)
            rects.append((r.x(), r.y(), r.width(), r.height()))
        cur = self.view.visualRect(sm.currentIndex())
        return (tuple(rects), (cur.x(), cur.y(), cur.width(), cur.height()))

    def paintEvent(self, _event):
        sm = self.view.selectionModel()
        if sm is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.NoBrush)
        current = sm.currentIndex()
        for idx in sm.selectedIndexes():
            if idx.column() != 0:
                continue
            r = self.view.visualRect(idx)
            if not r.isValid() or r.isEmpty():
                continue
            active = (idx == current)
            pen = QPen(ACTIVE_COLOR if active else OUTLINE_COLOR)
            pen.setWidthF(ACTIVE_WIDTH if active else OUTLINE_WIDTH)
            p.setPen(pen)
            p.drawRoundedRect(QRectF(r).adjusted(1, 1, -1, -1), 3, 3)
        p.end()


class _SelectedTextDelegate(QAbstractItemDelegate):
    """Passes everything to Krita's own delegate; only swaps the Text colour
    in the palette for selected rows before Krita paints them."""

    _GROUPS = (QPalette.Active, QPalette.Inactive, QPalette.Disabled)

    def __init__(self, orig, view):
        super().__init__(view)
        self.orig = orig
        # The view stops listening to the old delegate once replaced, so relay
        # its signals (rename editor commit/close, row size changes).
        orig.commitData.connect(self.commitData)
        orig.closeEditor.connect(self.closeEditor)
        orig.sizeHintChanged.connect(self.sizeHintChanged)

    def paint(self, painter, option, index):
        if int(option.state) & int(QStyle.State_Selected):
            opt = QStyleOptionViewItem(option)
            pal = QPalette(opt.palette)
            for g in self._GROUPS:
                if TRANSPARENT_SELECTION:
                    # keep the theme's normal (light) text so it stays readable
                    pal.setColor(g, QPalette.Highlight, QColor(0, 0, 0, 0))
                    continue
                if SELECTED_TEXT_COLOR is not None:
                    pal.setColor(g, QPalette.Text, SELECTED_TEXT_COLOR)
                if SELECTED_BG_COLOR is not None and not self._is_active(index):
                    pal.setColor(g, QPalette.Highlight, SELECTED_BG_COLOR)
            opt.palette = pal
            self.orig.paint(painter, opt, index)
        else:
            self.orig.paint(painter, option, index)

    @staticmethod
    def _is_active(index):
        # KisNodeModel::ActiveRole (Qt::UserRole + 1) is only true on column 0
        return bool(index.sibling(index.row(), 0).data(Qt.UserRole + 1))

    def sizeHint(self, option, index):
        return self.orig.sizeHint(option, index)

    def editorEvent(self, event, model, option, index):
        return self.orig.editorEvent(event, model, option, index)

    def helpEvent(self, event, view, option, index):
        return self.orig.helpEvent(event, view, option, index)

    def createEditor(self, parent, option, index):
        return self.orig.createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        self.orig.setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        self.orig.setModelData(editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        self.orig.updateEditorGeometry(editor, option, index)

    def destroyEditor(self, editor, index):
        self.orig.destroyEditor(editor, index)


class _Decorator(QObject):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.overlay = _Overlay(view)
        self.sm = None
        self.mouse_down = False
        self.anim = None
        self._last_sig = None
        view.viewport().installEventFilter(self)
        self.rehook()

    # Krita swaps the view's selection model when you switch documents
    def rehook(self):
        sm = self.view.selectionModel()
        if sm is self.sm:
            return
        self.sm = sm
        if sm is not None:
            sm.selectionChanged.connect(self._on_changed)
            sm.currentChanged.connect(self._on_changed)

    # Krita's NodeDelegate draws the layer name with QPalette::Text for every
    # row, selected or not, so the theme can't target it. Wrap the delegate.
    def _apply_text_color(self):
        if not TRANSPARENT_SELECTION and SELECTED_TEXT_COLOR is None and SELECTED_BG_COLOR is None:
            return
        current = self.view.itemDelegate()
        if current is None or isinstance(current, _SelectedTextDelegate):
            return
        self.proxy = _SelectedTextDelegate(current, self.view)
        self.view.setItemDelegate(self.proxy)
        self.view.viewport().update()

    def tick(self):
        self.rehook()
        self._apply_text_color()
        self.overlay.sync_geometry()
        sig = self.overlay.signature()
        if sig != self._last_sig:
            self._last_sig = sig
            self.overlay.update()

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.MouseButtonPress:
            self.mouse_down = True
        elif t == QEvent.MouseButtonRelease:
            QTimer.singleShot(60, self._release)
        elif t in (QEvent.Resize, QEvent.Move):
            self.overlay.sync_geometry()
        return False

    def _release(self):
        self.mouse_down = False

    def _on_changed(self, *_args):
        self.overlay.update()
        if CENTER_ON_SELECT and (CENTER_AFTER_LIST_CLICK or not self.mouse_down):
            QTimer.singleShot(0, self._center)

    def _center(self):
        if self.sm is None or sip.isdeleted(self.sm):
            return
        idx = self.sm.currentIndex()
        if not idx.isValid():
            return
        rect = self.view.visualRect(idx)
        if not rect.isValid() or rect.isEmpty():  # inside a collapsed group
            return
        bar = self.view.verticalScrollBar()
        target = bar.value() + rect.center().y() - self.view.viewport().height() // 2
        target = max(bar.minimum(), min(bar.maximum(), target))
        if target == bar.value():
            return
        if self.anim is not None:
            self.anim.stop()
        self.anim = QPropertyAnimation(bar, b"value", self)
        self.anim.setDuration(ANIM_MS)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.setStartValue(bar.value())
        self.anim.setEndValue(target)
        self.anim.start()


class LayerFocusExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.decorator = None
        self.timer = None

    def setup(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(POLL_MS)

    def createActions(self, window):
        pass

    def _find_view(self):
        app = Krita.instance()
        box = next((d for d in app.dockers() if d.objectName() == "KisLayerBox"), None)
        if box is None:
            return None
        return box.findChild(QTreeView, "listLayers") or box.findChild(QTreeView)

    def _tick(self):
        if self.decorator is not None and sip.isdeleted(self.decorator.view):
            self.decorator = None
        if self.decorator is None:
            view = self._find_view()
            if view is not None:
                self.decorator = _Decorator(view)
        if self.decorator is not None:
            self.decorator.tick()


Krita.instance().addExtension(LayerFocusExtension(Krita.instance()))
