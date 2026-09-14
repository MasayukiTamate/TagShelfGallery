
import sys
import os
sys.path.append(os.getcwd())

try:
    print("Importing GazoToolsUI...")
    import lib.GazoToolsUI
    print("GazoToolsUI imported successfully.")

    print("Importing GazoToolsLogic...")
    import GazoToolsLogic
    print("GazoToolsLogic imported successfully.")

except Exception as e:
    print(f"FAILED: {e}")
    raise
