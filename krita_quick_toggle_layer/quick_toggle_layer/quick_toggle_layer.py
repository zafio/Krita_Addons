# Quick Toggle Layer - Refactored for Krita 5.x
# Full support for Layers and Groups (Folders) with multi-slot toggling

import os
from krita import Extension, Krita
from PyQt5.QtGui import QIcon

class QuickToggleLayerExtension(Extension):
    def __init__(self, parent):
        super(QuickToggleLayerExtension, self).__init__(parent)
        self.slots = {
            1: {"node": None, "uuid": None, "name": None, "type": None},
            2: {"node": None, "uuid": None, "name": None, "type": None},
            3: {"node": None, "uuid": None, "name": None, "type": None},
        }

    def setup(self):
        pass

    def createActions(self, window):
        menu_loc = "tools/scripts"

        # Slot 1 Actions
        act_toggle_1 = window.createAction("quick_toggle_layer_1", "Quick Toggle: Toggle Layer/Group 1", menu_loc)
        act_toggle_1.setEnabled(True)
        act_toggle_1.triggered.connect(self.toggle_slot_1)
        act_set_1 = window.createAction("quick_set_layer_1", "Quick Toggle: Set Current Layer/Group as Slot 1", menu_loc)
        act_set_1.setEnabled(True)
        act_set_1.triggered.connect(self.set_slot_1)

        # Slot 2 Actions
        act_toggle_2 = window.createAction("quick_toggle_layer_2", "Quick Toggle: Toggle Layer/Group 2", menu_loc)
        act_toggle_2.setEnabled(True)
        act_toggle_2.triggered.connect(self.toggle_slot_2)
        act_set_2 = window.createAction("quick_set_layer_2", "Quick Toggle: Set Current Layer/Group as Slot 2", menu_loc)
        act_set_2.setEnabled(True)
        act_set_2.triggered.connect(self.set_slot_2)

        # Slot 3 Actions
        act_toggle_3 = window.createAction("quick_toggle_layer_3", "Quick Toggle: Toggle Layer/Group 3", menu_loc)
        act_toggle_3.setEnabled(True)
        act_toggle_3.triggered.connect(self.toggle_slot_3)
        act_set_3 = window.createAction("quick_set_layer_3", "Quick Toggle: Set Current Layer/Group as Slot 3", menu_loc)
        act_set_3.setEnabled(True)
        act_set_3.triggered.connect(self.set_slot_3)

    # Action slot handlers
    def toggle_slot_1(self, *args):
        self._toggle_slot(1)

    def set_slot_1(self, *args):
        self._set_active_as_slot(1)

    def toggle_slot_2(self, *args):
        self._toggle_slot(2)

    def set_slot_2(self, *args):
        self._set_active_as_slot(2)

    def toggle_slot_3(self, *args):
        self._toggle_slot(3)

    def set_slot_3(self, *args):
        self._set_active_as_slot(3)

    def _get_all_nodes(self, parent_node):
        """Recursively collect all nodes including paint layers, group layers, and nested groups."""
        nodes = []
        if not parent_node:
            return nodes
        for child in parent_node.childNodes():
            nodes.append(child)
            if child.childNodes():
                nodes.extend(self._get_all_nodes(child))
        return nodes

    def _get_uuid_str(self, node):
        """Safely extract UUID as clean string."""
        if hasattr(node, "uniqueId"):
            try:
                uid = node.uniqueId()
                if uid is not None:
                    if hasattr(uid, "toString"):
                        return str(uid.toString()).strip("{}")
                    return str(uid).strip("{}")
            except Exception:
                pass
        return None

    def _set_active_as_slot(self, slot_num):
        doc = Krita.instance().activeDocument()
        if not doc:
            self._notify("No active document found.")
            return

        active_node = doc.activeNode()
        if not active_node:
            self._notify("No layer or group is currently selected.")
            return

        node_name = active_node.name()
        node_type = active_node.type() # e.g. "grouplayer", "paintlayer"
        uuid_str = self._get_uuid_str(active_node)
        is_group = (node_type == "grouplayer")
        kind_label = "Group" if is_group else "Layer"

        self.slots[slot_num] = {
            "node": active_node,
            "uuid": uuid_str,
            "name": node_name,
            "type": node_type
        }

        self._notify(f"Slot {slot_num} [Assigned]: {kind_label} '{node_name}'")

    def _find_target_node(self, doc, slot_num):
        slot_info = self.slots.get(slot_num, {})
        saved_uuid = slot_info.get("uuid")
        saved_name = slot_info.get("name")
        saved_node = slot_info.get("node")

        all_nodes = self._get_all_nodes(doc.rootNode())

        # 1. Match by UUID string
        if saved_uuid:
            for node in all_nodes:
                if self._get_uuid_str(node) == saved_uuid:
                    return node

        # 2. Match by direct node instance
        if saved_node:
            for node in all_nodes:
                try:
                    if node == saved_node:
                        return node
                except Exception:
                    pass

        # 3. Match by exact name
        if saved_name:
            for node in all_nodes:
                if node.name().strip().lower() == saved_name.strip().lower():
                    return node

        # 4. Fallback search by tag names
        fallback_tags = [
            f"[{slot_num}]", f"#{slot_num}", f"Slot {slot_num}", f"Slot{slot_num}",
            f"Group {slot_num}", f"Group{slot_num}", f"Group #{slot_num}"
        ]
        if slot_num == 1:
            fallback_tags.extend(["[Special]", "#special", "[Toggle]", "#ref", "Reference", "Ref"])

        for tag in fallback_tags:
            for node in all_nodes:
                if node.name().strip().lower() == tag.lower():
                    return node

        return None

    def _toggle_slot(self, slot_num):
        doc = Krita.instance().activeDocument()
        if not doc:
            return

        target_node = self._find_target_node(doc, slot_num)

        if not target_node:
            self._notify(f"Slot {slot_num} is empty. Select a layer/group & press Set Slot {slot_num}")
            return

        is_currently_visible = target_node.visible()
        new_visibility = not is_currently_visible

        # Set visibility on the target (works on both GroupLayer and PaintLayer)
        target_node.setVisible(new_visibility)

        # If turning visibility ON, ensure all parent groups up to root are also visible
        if new_visibility:
            parent = target_node.parentNode()
            while parent and parent != doc.rootNode():
                if not parent.visible():
                    parent.setVisible(True)
                parent = parent.parentNode()

        # Update Krita projection and canvas
        doc.refreshProjection()
        try:
            doc.waitForDone()
        except Exception:
            pass

        is_group = (target_node.type() == "grouplayer")
        kind_label = "Group" if is_group else "Layer"
        state_label = "VISIBLE" if new_visibility else "HIDDEN"

        self._notify(f"Slot {slot_num} [{kind_label} '{target_node.name()}']: {state_label}")

    def _notify(self, message):
        """Display notification on canvas HUD or status bar."""
        app = Krita.instance()
        try:
            window = app.activeWindow()
            if window:
                view = window.activeView()
                if view and hasattr(view, "showFloatingMessage"):
                    view.showFloatingMessage(message, QIcon(), 1600, 1)
                    return
                if hasattr(window, "qwindow") and window.qwindow():
                    qwin = window.qwindow()
                    if hasattr(qwin, "statusBar") and qwin.statusBar():
                        qwin.statusBar().showMessage(f"Quick Toggle: {message}", 2500)
                        return
        except Exception:
            pass
        print(f"[QuickToggle] {message}")
