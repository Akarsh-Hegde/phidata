import pkgutil
import importlib
import inspect
import sys
from phi.tools import Toolkit
import phi.tools

def load_selected_tools(tool_names):
    """
    Dynamically import only the tools specified in the tool_names set.

    Args:
        tool_names (set): Set of tool class names to load.

    Returns:
        dict: A dictionary mapping {ClassName: ClassObject}.
    """
    tool_classes = {}
    loaded_modules = set()

    for module_info in pkgutil.iter_modules(phi.tools.__path__):
        module_name = module_info.name
        full_module_name = f"phi.tools.{module_name}"
        
        try:
            module = importlib.import_module(full_module_name)
            loaded_modules.add(full_module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name in tool_names and issubclass(obj, Toolkit) and obj is not Toolkit:
                    if name in tool_classes:
                        # Warning: Duplicate tool class '{name}' found in '{full_module_name}'.
                        pass
                    tool_classes[name] = obj
        except ImportError as e:
            # Skipping module '{full_module_name}' due to ImportError.
            pass
        except Exception as e:
            # Skipping module '{full_module_name}' due to unexpected error.
            pass

    # Identify missing tools
    missing_tools = tool_names - set(tool_classes.keys())
    if missing_tools:
        # Error: The following tools were not found in phi.tools modules.
        sys.exit(1)

    return tool_classes
