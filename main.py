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
    root.attributes("-alpha", 0.5)
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
                show_definition(word, x, y)
                return
    show_definition("No word detected.", x, y)

# Display word definition
def show_definition(word, x, y):
    data = fetch_definition(word)
    
    # Create a borderless window with curved edges
    popup = tk.Tk()
    popup.geometry(f"400x300+{x}+{y}")
    popup.overrideredirect(True)  # Borderless window
    popup.grab_set()
    popup.focus_force()

    # Make the background black and slightly transparent
    popup.config(bg="#000000")
    popup.attributes("-alpha", 0.8)  # Adjust transparency

    # Title label with modern font and smaller size
    title_label = tk.Label(popup, text=f"Word: {word}", font=("Segoe UI", 14, "bold"), fg="white", bg="#000000", wraplength=380)
    title_label.pack(pady=10)

    # Frame for the dictionary meanings
    frame = tk.Frame(popup, bg="#000000")
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    y_offset = 10  # Starting Y position for text
    total_height = 0  # To calculate total height of the content

    # Add a label for each meaning
    if "error" in data:
        error_label = tk.Label(frame, text=data["error"], font=("Segoe UI", 12), fg="white", bg="#000000", wraplength=380)
        error_label.pack(anchor="w", pady=(y_offset, 0))
        total_height += 30  # Adding height for the error label
    else:
        for meaning in data[0].get("meanings", []):
            part_of_speech_label = tk.Label(frame, text=f"Type: {meaning['partOfSpeech']}", font=("Segoe UI", 12, "bold"), fg="white", bg="#000000", wraplength=380)
            part_of_speech_label.pack(anchor="w", pady=(y_offset, 0))
            y_offset += 20  # Increase space after part of speech
            total_height += 30  # Adding height for the part of speech label
            
            for definition in meaning.get("definitions", []):
                definition_label = tk.Label(frame, text=f"- {definition['definition']}", font=("Segoe UI", 12), fg="white", bg="#000000", wraplength=380)
                definition_label.pack(anchor="w", pady=(y_offset, 0))
                y_offset += 20  # Increase space after each definition
                total_height += 30  # Adding height for the definition label

            total_height += 20  # Additional space between different meanings

    # Resize the window based on content height (total height)
    popup.geometry(f"400x{total_height + 50}+{x}+{y}")  # Adjust window height

    # Bind the escape key to close the window
    popup.bind("<Escape>", lambda e: popup.destroy())
    popup.focus_force()
    popup.mainloop()



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
