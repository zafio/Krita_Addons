from .quick_toggle_layer import QuickToggleLayerExtension
from krita import Krita

# Register the extension in Krita
app = Krita.instance()
extension = QuickToggleLayerExtension(parent=app)
app.addExtension(extension)
