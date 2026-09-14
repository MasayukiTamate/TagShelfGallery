# Task List

- [x] Refine Smart Move Feature
    - [x] Update `execute_move` in `GazoToolsApp.py` to support bulk moving (add `refresh` parameter)
    - [x] Update `SimilarityMoveDialog` in `GazoToolsLogic.py` to use optimized move and `refresh_callback`
    - [x] Implement persistence for Smart Move threshold (save/load settings)
    - [x] Verify logic correctness
- [x] Smart Move Thumbnail Display
    - [x] Add `smart_move_show_thumbnails` setting to `GazoToolsState.py`
    - [x] Implement `ScrollableFrame` class for optimized list display
    - [x] Implement real-time filtering (Widget Pooling) in `SimilarityMoveDialog`
    - [x] Add thumbnail toggle checkbox
    - [x] Implement background processing for data preparation (threading)
        - [x] Measure and log time every 10 items
- [x] Documentation
    - [x] Update `manual.html` / `manual.md` with Smart Move feature details
- [x] Code Analysis
    - [x] Update `code_analysis.md`
- [x] History
    - [x] Update `hister.md`
- [ ] Code Analysis and Optimization
    - [x] Analyze `GazoToolsApp.py` and `GazoToolsLogic.py`
    - [x] Analyze `lib` directory contents
    - [x] Identify error-prone code and complexity
    - [x] Create `code_analysis.md` with detailed findings
    - [x] Update `hister.md`
    - [x] **Phase 1: Separate UI from Logic**
        - [x] Create `lib/GazoToolsGUI.py`
        - [x] Move `ScrollableFrame`, `RowWidget`, `SimilarityMoveDialog`, `SplashWindow`
        - [x] Update imports in `GazoToolsLogic.py` and `GazoToolsApp.py`
    - [x] **Context Menu Enhancement**
        - [x] Add "Search Similar Images" to right-click menu
        - [x] Bind to `SimilarityMoveDialog`
    - [ ] **Fix Vector Dimension Mismatch**
        - [x] Restore MobileNetV3 1024-dim projection layer in `GazoToolsAI.py`
        - [x] Add versioning/validation to invalid old 576-dim vectors in `GazoToolsLogic.py`
        - [x] Verify `VectorInterpreter` works with 1024 dims
    - [ ] **Vector Display Refinement**
        - [ ] Add `show_internal_values` toggle to `vector_display` config
        - [x] Update `VectorInterpreter` to conditionally hide numeric scores
        - [x] Add menu option in `GazoToolsApp.py`
    - [x] **Splash Screen Optimization**
        - [x] Move Splash initialization to top of `GazoToolsApp.py`
        - [x] Verify timing and visibility
    - [x] **Vector On-demand Calculation**
        - [x] Implement on-the-fly vectorization in `GazoPicture.Drawing`
        - [x] Auto-save newly calculated vectors
        - [x] Add `auto_vectorize` toggle to settings
        - [x] Implement click-to-vectorize manual override

    - [x] **Info Window Enhancement**
        - [x] Add vector interpretation to image info window

- [x] Resolve Merge Conflicts
    - [x] Analyze and fix `GazoToolsApp.py`
    - [x] Analyze and fix `GazoToolsLogic.py`
    - [x] Verify application stability

    - [x] Report progress

- [x] Dedicated Vector Analysis Window
    - [x] Create `VectorWindow` class in `lib/GazoToolsGUI.py`
    - [x] Instantiate `VectorWindow` in `GazoToolsApp.py`
    - [x] Update `GazoToolsLogic.py` to output analysis to `VectorWindow`
    - [x] Verify functionality

- [x] Click-to-Toggle Vector Window
    - [x] Update `GazoToolsLogic.py` to bind click event on image window
    - [x] Implement toggle visibility logic in `GazoToolsLogic.py` (referencing `vector_win`)
    - [x] Verify interaction

- [x] Manual Analysis Button in Vector Window
    - [x] Add "Run Analysis" button to `VectorWindow`
    - [x] Implement `perform_manual_vectorization` in `GazoToolsLogic`
    - [x] Link button to vectorization logic
    - [x] Verify button functionality

- [x] Persist Vector Window State
    - [x] Add defaults to `lib/config_defaults.py`
    - [x] Update `GazoToolsApp.py` to apply saved geometry/visibility on startup
    - [x] Update `GazoToolsApp.py` to save geometry/visibility on exit
    - [x] Verify state restoration
