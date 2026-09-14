'''
Created: 2026-01-04
Function: AppState and UI Callback Mechanism Test
'''
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.GazoToolsLogger import setup_logging, get_logger
from lib.GazoToolsState import get_app_state

setup_logging(debug_mode=True)
logger = get_logger(__name__)

def test_app_state_singleton():
    """Verify AppState singleton pattern"""
    print("\n=== AppState Singleton Test ===")
    state1 = get_app_state()
    state2 = get_app_state()
    
    assert state1 is state2, "Singleton pattern not working"
    print("[PASS] AppState returns the same instance\n")

def test_callback_system():
    """Verify callback mechanism"""
    print("=== Callback System Test ===")
    app_state = get_app_state()
    app_state.clear()
    
    events = []
    
    def on_state_changed(event_name, data):
        events.append((event_name, data))
        print(f"  Event received: {event_name}")
    
    app_state.register_callback(on_state_changed)
    
    print("  Triggering folder change...")
    app_state.set_current_folder(os.getcwd())
    
    print("  Registering move destination...")
    app_state.set_move_destination(0, os.path.expanduser("~"))
    
    print("  Enabling screensaver...")
    app_state.set_ss_mode(True)
    
    assert len(events) >= 3, "Callbacks not called correctly"
    print(f"[PASS] {len(events)} events processed correctly\n")

def test_state_persistence():
    """Test state save/restore"""
    print("=== State Persistence Test ===")
    app_state = get_app_state()
    app_state.clear()
    
    print("  Setting state...")
    app_state.set_current_folder(os.path.expanduser("~"))
    app_state.set_move_destination(0, os.path.expanduser("~"))
    app_state.set_ss_mode(True)
    app_state.set_ss_interval(10)
    
    print("  Converting to dict...")
    state_dict = app_state.to_dict()
    
    assert state_dict["last_folder"] == os.path.expanduser("~")
    assert state_dict["settings"]["ss_mode"] == True
    assert state_dict["settings"]["ss_interval"] == 10
    
    print("  Restoring state...")
    new_state = get_app_state()
    new_state.clear()
    new_state.from_dict(state_dict)
    
    assert new_state.ss_mode == True
    assert new_state.ss_interval == 10
    
    print("[PASS] State save/restore working correctly\n")

def test_move_destinations():
    """Test move destination management"""
    print("=== Move Destination Test ===")
    app_state = get_app_state()
    app_state.reset_move_destinations()
    
    print("  Registering destinations...")
    app_state.set_move_destination(0, os.path.expanduser("~"))
    app_state.set_move_destination(1, os.path.dirname(os.path.abspath(__file__)))
    
    assert app_state.move_dest_list[0] == os.path.expanduser("~")
    assert app_state.move_dest_list[1] == os.path.dirname(os.path.abspath(__file__))
    
    print("  Rotating index...")
    app_state.set_move_reg_idx(0)
    app_state.rotate_move_reg_idx()
    assert app_state.move_reg_idx == 1
    
    print("  Resetting...")
    app_state.reset_move_destinations()
    assert all(p == "" for p in app_state.move_dest_list)
    assert app_state.move_reg_idx == 0
    
    print("[PASS] Move destination management working\n")

def test_window_count_change():
    """Test move destination window count change"""
    print("=== Window Count Change Test ===")
    app_state = get_app_state()
    
    print("  Initial count: 2")
    assert app_state.move_dest_count == 2
    
    print("  Changing to 6...")
    app_state.set_move_dest_count(6)
    assert app_state.move_dest_count == 6
    
    print("  Changing to 12...")
    app_state.set_move_dest_count(12)
    assert app_state.move_dest_count == 12
    
    print("  Testing invalid value (5)...")
    result = app_state.set_move_dest_count(5)
    assert result == False
    assert app_state.move_dest_count == 12
    
    print("[PASS] Window count change working\n")

def main():
    print("=" * 60)
    print("GazoTools UI Improvement - AppState Test")
    print("=" * 60)
    
    try:
        test_app_state_singleton()
        test_callback_system()
        test_state_persistence()
        test_move_destinations()
        test_window_count_change()
        
        print("=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n[FAILED] Test failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Test execution error: {e}", exc_info=True)
        print(f"\n[ERROR] Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
