from krita import Krita
from .cursor_resize_opacity import CursorResizeOpacityExtension

app = Krita.instance()
app.addExtension(CursorResizeOpacityExtension(app))
