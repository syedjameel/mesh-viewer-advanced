from imgui_bundle import imgui, hello_imgui, ImVec2, ImVec4, icons_fontawesome_6

class ProgressOverlay:
    """
    A modal overlay that displays progress information for background tasks.
    """
    def __init__(self):
        self.visible = False
        self.title = "Processing..."
        self.message = ""
        self.progress = 0.0
        self.cancelable = False
        self.on_cancel = None
        self.cancel_requested = False
        self.active_task_id = None
        
    def show(self, title: str, message: str = "", progress: float = 0.0, cancelable: bool = False, on_cancel=None, task_id=None):
        """Show the progress overlay with the specified parameters."""
        self.visible = True
        self.title = title
        self.message = message
        self.progress = progress
        self.cancelable = cancelable
        self.on_cancel = on_cancel
        self.cancel_requested = False
        self.active_task_id = task_id
        
    def hide(self):
        """Hide the progress overlay."""
        self.visible = False
        
    def update(self, progress: float, message: str = None):
        """Update the progress and optionally the message."""
        self.progress = progress
        if message is not None:
            self.message = message
    
    def render(self):
        """Render the progress overlay if visible."""
        if not self.visible:
            return
            
        # Center the modal on screen
        viewport_size = imgui.get_main_viewport().size
        center_x = viewport_size.x * 0.5
        center_y = viewport_size.y * 0.5
        
        # Set window position and size
        window_width = min(300, viewport_size.x * 0.8)
        window_height = 0  # Auto size height
        
        imgui.set_next_window_pos(ImVec2(center_x - window_width * 0.5, center_y - 60), 
                                 imgui.Cond_.appearing)
        imgui.set_next_window_size(ImVec2(window_width, window_height), imgui.Cond_.appearing)
        
        # Modal flags
        flags = (imgui.WindowFlags_.no_title_bar | 
                 #imgui.WindowFlags_.always_auto_resize | 
                 imgui.WindowFlags_.no_resize | 
                 imgui.WindowFlags_.no_move |
                 imgui.WindowFlags_.no_saved_settings |
                 imgui.WindowFlags_.no_nav |
                 imgui.WindowFlags_.no_decoration)
        
        # Begin modal popup
        if imgui.begin_popup_modal("##ProgressOverlay", None, flags)[0]:
            # Title
            imgui.text(self.title)
            imgui.separator()
            
            # Progress bar
            imgui.progress_bar(self.progress, ImVec2(-1, 0), f"{int(self.progress * 100)}%")
            
            # Message
            if self.message:
                imgui.text_wrapped(self.message)
                
            imgui.spacing()
            
            # Cancel button
            if self.cancelable and self.on_cancel:
                if imgui.button(f"{icons_fontawesome_6.ICON_FA_XMARK} Cancel", ImVec2(-1, 0)):
                    # Don't call the cancel function directly from the UI thread
                    # Just set a flag that we'll check in the next frame
                    self.cancel_requested = True
                    
            imgui.end_popup()
        else:
            # Open the popup if it's not already open
            imgui.open_popup("##ProgressOverlay")