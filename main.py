import tkinter as tk
from tkinter import simpledialog, Text, Scrollbar
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
listener = None
# Process selection
def capture_screen():
    global listener
    screen = ImageGrab.grab()
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.grab_set()  # Steal focus
    root.focus_force()
    root.lift()  # Bring the window to the front

    # Static screen capture as background
    screen_photo = ImageTk.PhotoImage(screen)
    canvas = tk.Canvas(root, bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.create_image(0, 0, anchor=tk.NW, image=screen_photo)

    def on_click(event):
        x, y = event.x, event.y
        root.quit()
        root.destroy()
        process_selection(x, y)
        restart_listener()  # Restart listener after selection

    def on_escape(event):
        global listener
        root.quit()
        root.destroy()
        restart_listener()  # Restart listener after Escape

    canvas.bind("<Button-1>", on_click)
    root.bind("<Escape>", on_escape)
    root.mainloop()

def process_selection(x, y):
    screen = ImageGrab.grab()
    ocr_data = pytesseract.image_to_data(screen, output_type=Output.DICT)
    for i, word in enumerate(ocr_data["text"]):
        if word.strip() and ocr_data["conf"][i] > 60:  # Filter low-confidence
            if (ocr_data["left"][i] <= x <= ocr_data["left"][i] + ocr_data["width"][i] and
                    ocr_data["top"][i] <= y <= ocr_data["top"][i] + ocr_data["height"][i]):
                data = fetch_definition(word)
                show_definition(word, x, y, data)
                return
    show_definition("No word detected.", x, y, data)

# Display word definition
class ModernDictionaryOverlay(ctk.CTkFrame):
    def __init__(self, x: int, y: int, word: str, data: Dict[str, Any]):
        # Create the main window
        self.root = ctk.CTk()
        self.root.geometry(f"+{x}+{y}")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.95)
        
        
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.root.grab_set()  # Steal focus
                
        # Initialize the frame
        super().__init__(master=self.root, 
                        fg_color="#1E1E1E",  # Dark background
                        corner_radius=15)     # Rounded corners
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
            fg_color="transparent",
            corner_radius=0,
            height=200  # Initial height, will be adjusted
        )
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Add content
        self._add_content(data)
        
        # Calculate and set proper window size
        self._adjust_window_size()
        
        # Add keyboard bindings
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<FocusOut>", lambda e: self.root.destroy())
        
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
            


    def _adjust_window_size(self):
        # Get required height for content
        content_height = sum(child.winfo_reqheight() for child in self.content_frame.winfo_children())
        
        # Set maximum height to 400 pixels or content height, whichever is smaller
        max_height = min(content_height + 60, 400)  # 60 pixels for padding and title
        
        # Update window size
        self.content_frame.configure(height=max_height - 60)
        self.root.geometry(f"500x{max_height}")
        
    def show(self):
        self.root.mainloop()

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
