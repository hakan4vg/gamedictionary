import tkinter as tk
from tkinter import simpledialog
from PIL import ImageGrab, Image, ImageTk
import pytesseract
import pystray
from pystray import MenuItem as item
from pynput import keyboard
import requests
import os
import json
from pytesseract import Output
import customtkinter as ctk
from typing import Dict, Any
import textwrap
import re
import asyncio
import threading

BASE_DIR = os.path.dirname(__file__)
TESSERACT_PATH = os.path.join(BASE_DIR, "bin", "tesseract.exe")
TESSDATA_PATH = os.path.join(BASE_DIR, "bin", "tessdata")

# Global variables
SHORTCUT = '<ctrl>+<alt>+s'
API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
CACHE_FILE = "dictionary_cache.json"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
os.environ["TESSDATA_PREFIX"] = TESSDATA_PATH

cache = {}
screenshot_window = None
current_overlay = None
is_active = False
is_root_destroyed = False

# Load or initialize cache
def load_cache():
    global cache
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

load_cache()

# Fetch word definition
def fetch_definition(word):
    word = word.lower()
    if word in cache:
        return cache[word]

    response = requests.get(f"{API_URL}{word}")
    if response.status_code == 200:
        data = response.json()
        cache[word] = data
        save_cache()
        return data
    else:
        return {"error": f"Word '{word}' not found."}

class ScreenshotWindow:
    def __init__(self):
        global is_active, is_root_destroyed
        is_root_destroyed = False
        is_active = True  # Mark the window as active
        
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes('-topmost', True)
        
        # Take screenshot
        self.screen = ImageGrab.grab()
        self.screen_photo = ImageTk.PhotoImage(self.screen)
        
        # Create canvas
        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screen_photo)
        
        # Create loading indicator (centered at the top)
        self.loading_label = tk.Label(self.root, text="Processing OCR...", font=("Helvetica", 20), fg="white", bg="black")
        self.loading_label.place(relx=0.5, rely=0.05, anchor="center")
        
        # Disable clicks while processing
        self.root.config(cursor="wait")
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Escape>", self.on_escape)
        
        self.ocr_done = asyncio.Event()  # Event to signal OCR completion
        self.processing_ocr = False  # Flag to track if OCR is in progress

    async def process_ocr(self):
        self.processing_ocr = True
        # Simulate OCR processing delay
        screen = ImageGrab.grab()
        self.ocr_data = pytesseract.image_to_data(screen, output_type=Output.DICT)
        
        # After OCR processing completes
        self.processing_ocr = False
        self.ocr_done.set()  # Signal that OCR processing is finished
        self.loading_label.destroy()
        self.root.config(cursor="")  # Reset cursor to default (allow clicks)
        await asyncio.sleep(1)  # Delay to show the "OCR Done!" message briefly

    def on_click(self, event):
        if self.processing_ocr:
            # Wait for OCR to finish before proceeding
            self.ocr_done.clear()
            asyncio.ensure_future(self.wait_for_ocr(event.x, event.y))
        else:
            self.handle_click(event.x, event.y)

    async def wait_for_ocr(self, x, y):
        await self.ocr_done.wait()
        self.handle_click(x, y)

    def handle_click(self, x, y):
        global current_overlay
        # Close previous overlay if exists
        try:
            if current_overlay and current_overlay.root.winfo_exists():
                current_overlay.root.destroy()
                current_overlay = None
        except tk.TclError:
            current_overlay = None
        
        # Loop through OCR data to find the word clicked
        for i, word in enumerate(self.ocr_data["text"]):
            if word.strip() and self.ocr_data["conf"][i] > 60:  # Filter low-confidence words
                # Check if the click is within the word's bounding box
                if (self.ocr_data["left"][i] <= x <= self.ocr_data["left"][i] + self.ocr_data["width"][i] and
                        self.ocr_data["top"][i] <= y <= self.ocr_data["top"][i] + self.ocr_data["height"][i]):
                    # If the cleaned word is not empty, fetch definition
                    if word:
                        data = fetch_definition(word)
                        current_overlay = ModernDictionaryOverlay(x, y, word, data)
                        current_overlay.show()
                        return
                    
        # If no word detected, show an overlay indicating so
        current_overlay = ModernDictionaryOverlay(x, y, "No word detected.", {"error": "No word detected at this position"})
        current_overlay.show()

    def on_escape(self, event):
        global current_overlay, screenshot_window, is_active, is_root_destroyed

        if not is_active or is_root_destroyed:  # Prevent multiple calls after the window is destroyed
            return

        # Ensure that the overlay exists and is valid before attempting to destroy it
        if current_overlay and current_overlay.root:
            try:
                if current_overlay.root.winfo_exists():
                    current_overlay.root.destroy()
                    current_overlay = None
            except tk.TclError:
                current_overlay = None

        # Mark the root as destroyed
        is_root_destroyed = True
        is_active = False  # Mark as inactive

        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass  # Ignore the error if root is already destroyed

        screenshot_window = None
        restart_listener()

class ModernDictionaryOverlay(ctk.CTkFrame):
    def __init__(self, x: int, y: int, word: str, data: Dict[str, Any]):
        # Create the main window
        self.root = ctk.CTk()
        self.root.attributes("-alpha", 0.0)
        self.root.overrideredirect(True)
        #self.root.attributes("-alpha", 0.95)
    
        self.root.attributes('-topmost', True)
        
        # Initialize the frame
        super().__init__(master=self.root, 
                        fg_color="#1E1E1E",
                        border_color="1E1E1E",
                        border_width=0,
                        corner_radius=15)
        self.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        
        # Add word title
        self.title = ctk.CTkLabel(
            self,
            text=word.capitalize(),
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        # Create scrollable frame for content
        self.content_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#1E1E1E", 
            corner_radius=15, 
            border_color="#1E1E1E", 
            border_width=0,  
            height=200
        )
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Add content
        self._add_content(data)
        
        # Set initial size and update to get actual dimensions
        self.root.geometry("500x1")  # Set width only
        self.root.update()
        
        # Calculate and set proper window size
        self._adjust_window_size()
        self.root.update()  # Update again to ensure size is applied
        
        # Now position the window based on its actual size
        self._position_window(x, y)
        
        # Add keyboard bindings
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<FocusOut>", lambda e: self.root.destroy())
        
        # Final focus
        self.root.focus_force()
        self.root.grab_set()

        self.root.attributes("-alpha", 0.95)
        
    def _position_window(self, x: int, y: int):
        # Get screen and window dimensions
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Determine which quadrant the click is in
        is_left = x < screen_width / 2
        is_top = y < screen_height / 2
        
        # Calculate position based on quadrant
        if is_left and is_top:  # Top Left -> Bottom Right
            new_x = x
            new_y = y
        elif not is_left and is_top:  # Top Right -> Bottom Left
            new_x = x - window_width
            new_y = y
        elif is_left and not is_top:  # Bottom Left -> Top Right
            new_x = x
            new_y = y - window_height
        else:  # Bottom Right -> Top Left
            new_x = x - window_width
            new_y = y - window_height
        
        # Ensure window stays within screen bounds
        new_x = max(0, min(new_x, screen_width - window_width))
        new_y = max(0, min(new_y, screen_height - window_height))
        
        self.root.geometry(f"+{new_x}+{new_y}")

    def _adjust_window_size(self):
        # Get required height for content
        content_height = sum(child.winfo_reqheight() for child in self.content_frame.winfo_children())
        
        # Add padding for title and margins
        total_height = content_height + 60  # 60 pixels for padding and title
        
        # Set maximum height to 400 pixels
        max_height = min(total_height, 400)
        
        # Update window size
        self.content_frame.configure(height=max_height - 60)
        self.root.geometry(f"500x{max_height}")
           
    def get_screen_width(self):
        return self.root.winfo_screenwidth()

    def get_screen_height(self):
        return self.root.winfo_screenheight()
        
    def _show_window(self):
        self.root.deiconify()  # Show the window
        self.root.lift()  # Raise window to top
        self.root.focus_force()  # Force focus
        
        # On Windows, we need these additional calls
        self.root.attributes('-topmost', True)
        self.root.update()

    def _on_escape(self, event):
        self.root.quit()
        self.root.destroy()

    def _on_focus_out(self, event):
        # Only destroy if we actually lost focus to another window
        if not self.root.focus_get():
            self.root.quit()
            self.root.destroy()
        
    def _add_content(self, data: Dict[str, Any]):
        if "error" in data:
            label = ctk.CTkLabel(
                self.content_frame,
                text=data["error"],
                font=ctk.CTkFont(family="Inter", size=12),
                text_color="#FF6B6B",  # Error in red
                wraplength=300
            )
            label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            return

        row = 0
        for meaning in data[0].get("meanings", []):
            # Part of speech
            pos_label = ctk.CTkLabel(
                self.content_frame,
                text=meaning['partOfSpeech'],
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                text_color="#4D96FF"  # Light blue for part of speech
            )
            pos_label.grid(row=row, column=0, padx=5, pady=(5, 2), sticky="w")
            row += 1
            
            # Add synonyms if available
            if meaning.get("synonyms"):
                syn_text = "Synonyms: " + ", ".join(meaning["synonyms"][:5])
                syn_label = ctk.CTkLabel(
                    self.content_frame,
                    text=syn_text,
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color="#6C757D",
                    wraplength=300
                )
                syn_label.grid(row=row, column=0, padx=(15, 5), pady=(2, 5), sticky="w")
                row += 1
            
            # Definitions
            for definition in meaning.get("definitions", []):
                def_text = textwrap.fill(definition['definition'], width=75)
                def_label = ctk.CTkLabel(
                    self.content_frame,
                    text=f"• {def_text}",
                    font=ctk.CTkFont(family="Inter", size=11),
                    text_color="#CCCCCC",  # Light gray for definitions
                    wraplength=450,
                    justify="left"
                )
                def_label.grid(row=row, column=0, padx=(15, 5), pady=2, sticky="w")
                row += 1
                
                # Example if available
                if 'example' in definition:
                    example_text = textwrap.fill(f"\"{definition['example']}\"", width=70)
                    example_label = ctk.CTkLabel(
                        self.content_frame,
                        text=example_text,
                        font=ctk.CTkFont(family="Inter", size=10, slant="italic"),
                        text_color="#888888",  # Darker gray for examples
                        wraplength=320
                    )
                    example_label.grid(row=row, column=0, padx=(25, 5), pady=(0, 2), sticky="w")
                    row += 1


        
    def show(self):
        self.root.mainloop()

# Capture screen asynchronously
def capture_screen():
    global screenshot_window
    if screenshot_window is None:
        screenshot_window = ScreenshotWindow()
        # Start OCR processing in background thread
        threading.Thread(target=asyncio.run, args=(screenshot_window.process_ocr(),)).start()
        screenshot_window.root.mainloop()

def show_definition(word: str, x: int, y: int, data: Dict[str, Any]):
    overlay = ModernDictionaryOverlay(x, y, word, data)
    overlay.show()   

# System tray setup
def setup_tray_icon():
    def on_exit():
        tray.stop()

    menu = (
        item("Preferences", preferences),
        item("Exit", on_exit)
    )

    icon_image = Image.open("icon.png")
    tray = pystray.Icon("WordPicker", icon=icon_image, menu=menu)
    tray.run()

# Preferences
def preferences():
    global SHORTCUT, listener
    root = tk.Tk()
    root.withdraw()
    
    listener.stop()
    
    new_shortcut = simpledialog.askstring("Preferences", "Enter a new shortcut (e.g., ctrl+alt+x):")
    if new_shortcut:
        SHORTCUT = new_shortcut
        setup_shortcut()
        
    root.destroy()

# Key listener
def on_activate():
    capture_screen()
    
listener = None

def restart_listener():
    global listener
    if listener and listener.is_alive():
        listener.stop()  # Stop the listener if it's running
    setup_shortcut()  # Restart the listener

def setup_shortcut():
    global listener
    listener = keyboard.GlobalHotKeys({SHORTCUT: on_activate})
    listener.start()

# Main function
def main():
    setup_shortcut()
    setup_tray_icon()

if __name__ == "__main__":
    main()