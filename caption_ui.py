import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Optional

class FloatingCaptionUI:
    """
    Floating, semi-transparent, draggable caption window for live translations
    """
    
    def __init__(self, font_size: int = 14, opacity: float = 0.8):
        self.font_size = font_size
        self.opacity = opacity
        
        # Window properties
        self.window = None
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Content
        self.japanese_text = ""
        self.chinese_text = ""
        
        # Auto-hide functionality
        self.last_update_time = time.time()
        self.auto_hide_delay = 5.0  # Hide after 5 seconds of no updates
        self.is_hidden = False
        
        # Threading for UI updates
        self.update_queue = []
        self.queue_lock = threading.Lock()
        
        self._create_window()
        self._start_auto_hide_timer()
    
    def _create_window(self):
        """Create the floating caption window"""
        self.window = tk.Tk()
        
        # Window configuration
        self.window.title("LiveCaption")
        self.window.overrideredirect(True)  # Remove window decorations
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', self.opacity)  # Semi-transparent
        
        # Set initial size and position
        window_width = 600
        window_height = 120
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Position at bottom center of screen
        x = (screen_width - window_width) // 2
        y = screen_height - window_height - 100
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Configure background
        self.window.configure(bg='black')
        
        # Create main frame with padding
        self.main_frame = tk.Frame(
            self.window,
            bg='black',
            padx=15,
            pady=10
        )
        self.main_frame.pack(fill='both', expand=True)
        
        # Japanese text label
        self.japanese_label = tk.Label(
            self.main_frame,
            text="Japanese text will appear here...",
            font=('Arial', self.font_size, 'normal'),
            fg='white',
            bg='black',
            wraplength=550,
            justify='left',
            anchor='w'
        )
        self.japanese_label.pack(fill='x', pady=(0, 5))
        
        # Chinese text label (slightly larger and different color)
        self.chinese_label = tk.Label(
            self.main_frame,
            text="Chinese translation will appear here...",
            font=('Arial', self.font_size + 2, 'bold'),
            fg='#00ff88',  # Light green for Chinese text
            bg='black',
            wraplength=550,
            justify='left',
            anchor='w'
        )
        self.chinese_label.pack(fill='x')
        
        # Bind mouse events for dragging
        self._bind_drag_events(self.window)
        self._bind_drag_events(self.main_frame)
        self._bind_drag_events(self.japanese_label)
        self._bind_drag_events(self.chinese_label)
        
        # Right-click context menu
        self._create_context_menu()
        
        # Bind right-click to all components
        self._bind_context_menu(self.window)
        self._bind_context_menu(self.main_frame)
        self._bind_context_menu(self.japanese_label)
        self._bind_context_menu(self.chinese_label)
    
    def _bind_drag_events(self, widget):
        """Bind mouse events for dragging functionality"""
        widget.bind('<Button-1>', self._start_drag)
        widget.bind('<B1-Motion>', self._on_drag)
        widget.bind('<ButtonRelease-1>', self._stop_drag)
    
    def _bind_context_menu(self, widget):
        """Bind right-click context menu"""
        widget.bind('<Button-3>', self._show_context_menu)
    
    def _start_drag(self, event):
        """Start dragging the window"""
        self.is_dragging = True
        self.drag_start_x = event.x_root - self.window.winfo_x()
        self.drag_start_y = event.y_root - self.window.winfo_y()
    
    def _on_drag(self, event):
        """Handle window dragging"""
        if self.is_dragging:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.window.geometry(f"+{x}+{y}")
    
    def _stop_drag(self, event):
        """Stop dragging the window"""
        self.is_dragging = False
    
    def _create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        
        # Hide/Show option
        self.context_menu.add_command(
            label="Hide Captions",
            command=self._toggle_visibility
        )
        
        self.context_menu.add_separator()
        
        # Font size options
        font_menu = tk.Menu(self.context_menu, tearoff=0)
        for size in [10, 12, 14, 16, 18, 20, 24]:
            font_menu.add_command(
                label=f"{size}px",
                command=lambda s=size: self._change_font_size(s)
            )
        self.context_menu.add_cascade(label="Font Size", menu=font_menu)
        
        # Opacity options
        opacity_menu = tk.Menu(self.context_menu, tearoff=0)
        for opacity in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            opacity_menu.add_command(
                label=f"{int(opacity*100)}%",
                command=lambda o=opacity: self._change_opacity(o)
            )
        self.context_menu.add_cascade(label="Transparency", menu=opacity_menu)
        
        self.context_menu.add_separator()
        
        # Quit option
        self.context_menu.add_command(
            label="Quit LiveCaption",
            command=self._quit_application
        )
    
    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            # Update hide/show menu text
            if self.is_hidden:
                self.context_menu.entryconfig(0, label="Show Captions")
            else:
                self.context_menu.entryconfig(0, label="Hide Captions")
            
            self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Context menu error: {e}")
    
    def _toggle_visibility(self):
        """Toggle caption visibility"""
        if self.is_hidden:
            self.window.deiconify()
            self.is_hidden = False
        else:
            self.window.withdraw()
            self.is_hidden = True
    
    def _change_font_size(self, new_size: int):
        """Change font size"""
        self.font_size = new_size
        self.japanese_label.configure(font=('Arial', self.font_size, 'normal'))
        self.chinese_label.configure(font=('Arial', self.font_size + 2, 'bold'))
        print(f"Font size changed to {new_size}px")
    
    def _change_opacity(self, new_opacity: float):
        """Change window opacity"""
        self.opacity = new_opacity
        self.window.attributes('-alpha', self.opacity)
        print(f"Opacity changed to {int(new_opacity*100)}%")
    
    def _quit_application(self):
        """Quit the application"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit LiveCaption?"):
            self.window.quit()
            self.window.destroy()
    
    def _start_auto_hide_timer(self):
        """Start the auto-hide timer"""
        def check_auto_hide():
            while True:
                try:
                    current_time = time.time()
                    if (current_time - self.last_update_time > self.auto_hide_delay 
                        and not self.is_hidden):
                        # Auto-hide if no updates for a while
                        self.window.after(0, lambda: self.window.withdraw())
                        self.is_hidden = True
                    
                    time.sleep(1.0)
                except:
                    break
        
        timer_thread = threading.Thread(target=check_auto_hide, daemon=True)
        timer_thread.start()
    
    def update_caption(self, japanese: Optional[str] = None, chinese: Optional[str] = None):
        """Update caption text (thread-safe)"""
        with self.queue_lock:
            if japanese is not None:
                self.japanese_text = japanese
            if chinese is not None:
                self.chinese_text = chinese
            
            # Schedule UI update in main thread
            self.window.after(0, self._update_ui)
            
            # Update last update time and show window if hidden
            self.last_update_time = time.time()
            if self.is_hidden:
                self.window.after(0, lambda: self.window.deiconify())
                self.is_hidden = False
    
    def _update_ui(self):
        """Update UI elements (must be called from main thread)"""
        try:
            with self.queue_lock:
                # Update Japanese text
                if self.japanese_text:
                    self.japanese_label.configure(text=self.japanese_text)
                
                # Update Chinese text
                if self.chinese_text:
                    self.chinese_label.configure(text=self.chinese_text)
                
                # Auto-resize window to fit content
                self.window.update_idletasks()
                
        except Exception as e:
            print(f"UI update error: {e}")
    
    def run(self):
        """Run the UI main loop"""
        try:
            print("Starting caption UI...")
            self.window.mainloop()
        except Exception as e:
            print(f"UI error: {e}")
        finally:
            self.destroy()
    
    def destroy(self):
        """Clean up and destroy the window"""
        try:
            if self.window:
                self.window.quit()
                self.window.destroy()
        except:
            pass

# Test function
if __name__ == "__main__":
    def test_ui():
        ui = FloatingCaptionUI(font_size=16, opacity=0.8)
        
        # Test with sample text
        ui.update_caption(
            japanese="こんにちは、元気ですか？",
            chinese="你好，你好吗？"
        )
        
        # Add more test updates after a delay
        def add_test_updates():
            time.sleep(2)
            ui.update_caption(
                japanese="今日はいい天気ですね",
                chinese="今天天气真好呢"
            )
            
            time.sleep(3)
            ui.update_caption(
                japanese="ありがとうございます",
                chinese="谢谢您"
            )
        
        test_thread = threading.Thread(target=add_test_updates, daemon=True)
        test_thread.start()
        
        ui.run()
    
    test_ui()
