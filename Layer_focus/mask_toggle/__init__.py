from krita import Krita
from .mask_toggle import MaskToggleExtension

Krita.instance().addExtension(MaskToggleExtension(Krita.instance()))
