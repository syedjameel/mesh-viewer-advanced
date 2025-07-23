from typing import List
from imgui_bundle import portable_file_dialogs as pfd

def prompt_load_mesh_paths() -> List[str]:
    """Opens a file dialog to select mesh files and returns their paths."""
    # Create a file open dialog
    open_file_dialog = pfd.open_file(
        "Choose Mesh Files", 
        options=pfd.opt.multiselect
    )
    
    # Block until the dialog is closed
    result = open_file_dialog.result()
    return result