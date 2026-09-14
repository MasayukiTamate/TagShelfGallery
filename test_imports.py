import importlib
import sys
try:
    importlib.import_module('lib.GazoToolsVectorInterpreter')
    importlib.import_module('lib.GazoToolsState')
    importlib.import_module('GazoToolsLogic')
    print('imports OK')
except Exception as e:
    print('IMPORT ERROR:', e)
    raise
