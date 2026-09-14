# Error Log (errarlog)

## 2026-01-04: Smart Move Window Disappearing
- **Error**: Dialog closes before all files are moved.
- **Cause**: Race condition. The "Target Image" (current view) was moved first. This triggered the parent window to destroy itself (as the file is gone), which cascaded to destroy the child dialog (`SimilarityMoveDialog`) immediately.
- **Fix**: Reordered the file list in `on_execute`. Moved the target image to the *end* of the list.
- **Prevention**: When performing batch operations that include the active/viewed item, always process the active item last or detach the UI dependency before processing.

## 2026-01-04: Last Folder Not Saved
- **Error**: Application restarts in a default or old folder, ignoring the last visited location.
- **Cause**: State Management Bypass. Navigation actions (Help button, Double click) called `refresh_ui` directly, bypassing `AppState.set_current_folder`. Thus, `AppState` held stale data which was saved on exit.
- **Fix**: Refactored all navigation triggers to call `app_state.set_current_folder(path)`. This ensures `AppState` is the Single Source of Truth, which then triggers the UI update via callback.
- **Prevention**: Enforce "Unidirectional Data Flow". UI should trigger State changes -> State changes trigger UI updates. Never update UI directly for state-dependent data.

## 2026-01-04: AttributeError in Image Size Settings
- **Error**: `AttributeError: 'AppState' object has no attribute 'set_image_size_limits'`
- **Cause**: Implementation Gap. The `GazoToolsApp` called a method `set_image_size_limits` on `app_state`, but this method was missing from the `AppState` class definition in `GazoToolsState.py`. Likely missed during the transition from global to state-based management.
- **Fix**: Implemented the missing `set_image_size_limits` method in `AppState` class.
- **Prevention**: Verify all method calls against the class definition. Use linting tools to catch undefined attributes.

## 2026-01-04: Settings Not Saved on Exit
- **Error**: Application state (Current Folder, Window Geometry) lost after restart.
- **Cause**: Missing Exit Handler. The application relied on standard window closing, which does not trigger any autosave logic. `save_config` was only called in specific dialogs, not on main app exit.
- **Fix**: Added `on_closing` function bound to `WM_DELETE_WINDOW` protocol. This function captures current window geometries and calls `save_config` via `app_state`.
- **Prevention**: In GUI apps, always explicitly handle the main window's close event to perform cleanup and state persistence.

## 2026-01-04: Smart Move Low Threshold Ineffective
- **Error**: Lowering similarity threshold in Smart Move did not increase the number of candidate images.
- **Cause**: Incomplete Data. The previous logic only compared images that were *already* in the vector database (`vectors.pkl`). Images not yet processed by the background thread were completely skipped, regardless of similarity.
- **Fix**: Updated `SimilarityMoveDialog` to calculate vectors on-the-fly for any image missing from the database, and save the updated database afterwards.
- **Prevention**: When relying on cached derived data (like vectors), always handle the "cache miss" case by computing on demand or alerting the user.

## 2026-01-04: AI Model Dimension Mismatch (Careless Deletion)
- **Error**: Vector Interpreter expects 1024 dims, but AI model outputs 576 dims.
- **Cause**: "Careless Code Deletion". When optimizing MobileNetV3, the entire `classifier` layer was replaced with `Identity()`, inadvertently removing the projection layer (576->1024).
- **Lesson**: When removing code (especially model layers or logic chains), **verify the output shape/type** to ensure it matches downstream expectations.
- **Action**: Always double-check `errarlog.md` and verify impacts before deleting code.

## 2026-01-04: Configuration Sync Failure (Initialization Miss)
- **Error**: "Interpretation Error" in Vector Display.
- **Cause**: Added a new setting `show_internal_values` to `config_defaults.py` but forgot to add it to `GazoToolsState.py` initialization. The Interpreter tried to access this key from `app_state` (via config) and likely failed or returned unexpected structure.
- **Fix**: Added default value to `GazoToolsState.py` and wrapped config access in `VectorInterpreter` with try-except block.
- **Lesson**: When adding new settings, remember there are **two** places to update: `config_defaults.py` (file default) and `GazoToolsState.py` (in-memory default).

## 2026-01-04: AttributeError (vectors_cache)
- **Error**: `AttributeError: 'GazoPicture' object has no attribute 'vectors_cache'`
- **Cause**: The `vectors_cache` attribute was defined in `HakoData` but I tried to access it from `GazoPicture` (self) in the vector interpretation logic without ensuring it existed in `GazoPicture`.
- **Fix**: Initialized `self.vectors_cache = load_vectors()` in `GazoPicture.__init__`.
- **Lesson**: Ensure that any shared state or data caches are properly initialized in all classes that use them, or pass them appropriately.

## 2026-01-04: AttributeError (_image_hash)
- **Error**: `AttributeError: 'Toplevel' object has no attribute '_image_hash'`
- **Cause**: In `GazoPicture.Drawing`, the vector interpretation logic was called before the `_image_hash` attribute was assigned to the `Toplevel` window.
- **Fix**: Moved the assignment of `_image_hash` (and `_image_path`) to the beginning of the window setup process, before the vector display logic is executed.
- **Lesson**: Be careful with the order of operations when adding new UI elements that depend on attributes assigned later in the function.
"じっこうちゅう～だよ"

## 2026-01-07: Vector Interpretation Failure (Missing Import)
- **Error**: `NameError: name 'get_interpreter' is not defined` in `GazoToolsLogic.py`.
- **Cause**: Refactoring Oversight. During the refactoring of `GazoToolsLogic.py` imports, the `get_interpreter` function from `lib/GazoToolsVectorInterpreter` was accidentally removed from the import list.
- **Fix**: Added `from lib.GazoToolsVectorInterpreter import get_interpreter` to `GazoToolsLogic.py`.
- **Lesson**: When cleaning up imports, carefully check usage of each imported name, or use an IDE/Linter that highlights undefined variables *before* running.
"ぶんせきちゅう～むずかし～よ～なのじゃ"

