import importlib.util
import os
import sys
from typing import List, Tuple, Type
from processing_base import BaseProcessingModule

def discover_modules(folder: str, mode: str) -> List[Tuple[str, type, list]]:
    """
    Discover and import all modules in the given folder that define a class inheriting from BaseProcessingModule.
    Only include modules whose MODE matches the given mode ('pre' or 'post').
    Returns a list of (module_name, class, PARAMETERS).
    """
    modules = []
    for fname in os.listdir(folder):
        if fname.endswith('.py') and not fname.startswith('__'):
            mod_path = os.path.join(folder, fname)
            mod_name = os.path.splitext(fname)[0]
            spec = importlib.util.spec_from_file_location(mod_name, mod_path)
            if spec is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            try:
                spec.loader.exec_module(mod)
            except Exception as e:
                print(f"Error loading module {mod_name}: {e}")
                continue
            # Check for MODE
            mod_mode = getattr(mod, 'MODE', None)
            if mod_mode is None:
                continue
            if isinstance(mod_mode, str):
                allowed = [mod_mode]
            else:
                allowed = list(mod_mode)
            if mode not in allowed and mode != 'all':
                continue
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if isinstance(obj, type) and issubclass(obj, BaseProcessingModule) and obj is not BaseProcessingModule:
                    # Maybe we should have the default come from the object instead of the module
                    parameters = getattr(obj, 'PARAMETERS', getattr(mod, 'PARAMETERS', []))
                    # parameters = getattr(mod, 'PARAMETERS', getattr(obj, 'PARAMETERS', [])) inconsistent with future plotmodules
                    name = getattr(obj, 'name', mod_name) # Can customize name, maybe add description?
                    modules.append((name, obj, parameters))
    return modules 