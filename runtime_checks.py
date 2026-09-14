import json, random, os, sys
from lib.GazoToolsState import get_app_state
from GazoToolsLogic import load_config, save_config
from lib.GazoToolsVectorInterpreter import get_interpreter

print('=== Runtime checks start ===')
# load config
cfg = load_config()
print('Loaded config last_folder:', cfg.get('last_folder'))

# get app state and show vector_display
app_state = get_app_state()
print('AppState vector_display (before):', getattr(app_state, 'vector_display', None))

# modify and save config: toggle a setting then save and reload
vd = cfg.get('vector_display', {})
vd['interpretation_mode'] = 'labels'
vd['show_color_features'] = not vd.get('show_color_features', True)
cfg['vector_display'] = vd
# Save via save_config (use current last_folder/geometries/settings merging)
settings_to_save = cfg.get('settings', {})
settings_to_save['vector_display'] = vd
try:
    save_config(cfg.get('last_folder', os.getcwd()), cfg.get('geometries', {}), settings_to_save)
    print('Saved config with updated vector_display')
except Exception as e:
    print('Error saving config:', e)

# reload
cfg2 = load_config()
print('Reloaded vector_display show_color_features:', cfg2.get('settings', {}).get('vector_display', {}).get('show_color_features'))

# Interpreter check
interpreter = get_interpreter({'vector_display': cfg2.get('settings', {}).get('vector_display', {})})
vec = [random.gauss(0, 0.2) for _ in range(1024)]
res = interpreter.interpret_vector(vec)
print('Interpretation mode:', res.get('mode'))
print('Top dims count:', len(res.get('dimensions', [])))
print('Sample output:\n', interpreter.format_interpretation_text(res))

print('=== Runtime checks end ===')
