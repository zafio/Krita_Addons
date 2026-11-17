# Quick Toggle Layer for Krita (5.x+)

A Krita Python extension that lets you pin and toggle visibility of up to **3 independent Special Layers** (e.g., Reference sketch, Lineart, Anatomy / Color Guide) on-the-fly using dedicated keyboard shortcuts — without interrupting your workflow or switching away from your active layer.

---

## 🚀 Features

- **3 Independent Quick Slots**:
  - **Slot 1**: Set with `Shift+1` & toggle with `1`
  - **Slot 2**: Set with `Shift+2` & toggle with `2`
  - **Slot 3**: Set with `Shift+3` & toggle with `3`
- **Dynamic Pinning**: Select any layer and press the **Set** hotkey to register it to that slot.
- **Instant Toggle**: Hit the corresponding **Toggle** key from anywhere to show/hide that layer instantly.
- **Auto-Fallback**: If a slot hasn't been manually pinned yet, it will automatically search for layers named `[1]`/`#1`, `[2]`/`#2`, or `[3]`/`#3`.
- **Status Bar Feedback**: Displays unobtrusive feedback in Krita's status bar (*e.g., `Quick Toggle [Slot 1]: 'Sketch' is now Hidden`*).

---

## 📦 Updating / Installing

1. Copy the updated [`quick_toggle_layer`](file:///C:/Users/JU/.gemini/antigravity/scratch/krita_quick_toggle_layer/quick_toggle_layer) folder into your Krita `pykrita` directory:
   ```text
   %APPDATA%\krita\pykrita\
   ```
2. *(Optional)* Copy [`quick_toggle_layer.action`](file:///C:/Users/JU/.gemini/antigravity/scratch/krita_quick_toggle_layer/quick_toggle_layer/quick_toggle_layer.action) into the `actions` folder if you want the action catalog updated.
3. Restart Krita.

---

## ⚙️ Configuring Your Shortcuts in Krita

1. Open Krita and go to **Settings > Configure Shortcuts...**
2. In the search box, type `Quick Toggle`.
3. Assign your shortcuts:
   - **`Quick Toggle: Toggle Layer 1`** $\rightarrow$ `1`
   - **`Quick Toggle: Set Current Layer as Slot 1`** $\rightarrow$ `Shift+1`
   - **`Quick Toggle: Toggle Layer 2`** $\rightarrow$ `2`
   - **`Quick Toggle: Set Current Layer as Slot 2`** $\rightarrow$ `Shift+2`
   - **`Quick Toggle: Toggle Layer 3`** $\rightarrow$ `3`
   - **`Quick Toggle: Set Current Layer as Slot 3`** $\rightarrow$ `Shift+3`
4. Click **OK**.
