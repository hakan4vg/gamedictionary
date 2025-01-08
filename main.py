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
from typing import Dict, Any, Tuple, List
import textwrap
import re
import asyncio
import threading
import math
from nltk.corpus import words
from nltk.corpus import wordnet as wn
import nltk
from nltk import download
download("wordnet")
nltk.download('words')


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
        # Take screenshot and process OCR
        screen = ImageGrab.grab()
        self.ocr_data = pytesseract.image_to_data(screen, output_type=Output.DICT)
        
        # Process OCR data into characters list
        self.characters = []
        for i in range(len(self.ocr_data['text'])):
            if self.ocr_data['text'][i].strip():  # Only process non-empty text
                char = self.ocr_data['text'][i]
                x = self.ocr_data['left'][i]
                y = self.ocr_data['top'][i]
                width = self.ocr_data['width'][i]
                height = self.ocr_data['height'][i]
                conf = self.ocr_data['conf'][i]
                
                # Add each character individually
                for idx, single_char in enumerate(char):
                    # Calculate proportional position for each character
                    char_width = width / len(char)
                    char_x = x + (idx * char_width)
                    self.characters.append((
                        single_char,
                        int(char_x),
                        y,
                        int(char_width),
                        height,
                        conf
                    ))
        
        # After OCR processing completes
        self.processing_ocr = False
        self.ocr_done.set()  # Signal that OCR processing is finished
        self.loading_label.destroy()
        self.root.config(cursor="")  # Reset cursor to default
        await asyncio.sleep(1)  # Brief delay to ensure UI updates the "OCR Done!" message briefly

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

    def find_closest_chars(self, x: int, y: int, radius: int = 50) -> Tuple[Dict, List]:
        """Find closest character and nearby characters within radius."""
        timer = 0;
        
        distances = []
        for char, char_x, char_y, width, height, conf in self.characters:
            center_x = char_x + width / 2
            center_y = char_y + height / 2
            distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            
            if distance <= radius:
                distances.append({
                    'char': char,
                    'distance': distance,
                    'x': char_x,
                    'y': char_y,
                    'width': width,
                    'height': height,
                    'center_x': center_x,
                    'center_y': center_y
                })
        
        if not distances:
            return None, []
            
        distances.sort(key=lambda x: x['distance'])
        
        return distances[0], distances

    def find_possible_words(self, x: int, y: int, radius: int = 50) -> List[str]:
        """Find all possible words containing the character at clicked position."""
        closest_char, nearby_chars = self.find_closest_chars(x, y, radius)
        if not closest_char or not nearby_chars:
            return []

        # Group characters by line (y-position)
        chars_by_y = {}
        base_y = closest_char['y']
        max_y_diff = 5

        for char in nearby_chars:
            y_pos = char['y']
            if abs(y_pos - base_y) <= max_y_diff:
                if y_pos not in chars_by_y:
                    chars_by_y[y_pos] = []
                chars_by_y[y_pos].append(char)

        # Sort each line by x position
        for y_pos in chars_by_y:
            chars_by_y[y_pos].sort(key=lambda x: x['x'])

        # Find the line containing clicked character
        target_line = None
        for y_pos, line_chars in chars_by_y.items():
            if any(char['x'] == closest_char['x'] and char['y'] == closest_char['y'] for char in line_chars):
                target_line = line_chars
                break

        if not target_line:
            return []

        # Convert target line to format compatible with your original code
        char_positions = [(char['char'], char['x'], char['y'], char['width'], char['height']) 
                        for char in target_line]
        
        # Find clicked character index
        clicked_idx = next(i for i, (char, x, y, w, h) in enumerate(char_positions) 
                            if x == closest_char['x'] and y == closest_char['y'])

        # Generate candidates using modified logic
        candidates = []
        max_gap = 20  # Maximum pixel gap between characters to be considered part of the same word
        
        # Continue iterating left and right without breaking early on finding a valid word
        for left in range(clicked_idx, -1, -1):
            if left < clicked_idx and (char_positions[left + 1][1] - 
                (char_positions[left][1] + char_positions[left][3]) > max_gap):
                break

            for right in range(clicked_idx, len(char_positions)):
                if right > 0 and (char_positions[right][1] - 
                    (char_positions[right - 1][1] + char_positions[right - 1][3]) > max_gap):
                    break

                word = ''.join(char for char, *_ in char_positions[left:right + 1])
                # Clean the word
                word = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', word)
                if word and len(word) > 1:  # Only add words with 2 or more characters
                    # Calculate how centered the clicked character is in this word
                    word_center_idx = (right - left) / 2
                    click_offset = abs(clicked_idx - left - word_center_idx)
                    candidates.append((word, click_offset, len(word)))

        # Validate words using dictionary API
        valid_words = []
        seen = set()
        
        for word, offset, length in candidates:
            if word.lower() not in seen:
                word = word.lower()
                if word in cache:
                    valid_words.append((word, offset, length))
                    seen.add(word)
                else:
                    response = nltk.corpus.wordnet.synsets(word)
                    if response:
                        valid_words.append((word, offset, length))
                        seen.add(word)


        # Sort by:
        # 1. How centered the clicked character is (smaller offset is better)
        # 2. Word length (longer is better)
        # 3. Alphabetically
        valid_words.sort(key=lambda x: (-x[2], x[1], x[0]))
        best_word = valid_words[0][0] if valid_words else None
        if best_word:
            cache[best_word] = fetch_definition(best_word) 
            save_cache()
        # Extract just the words from the sorted list
        result = [word for word, _, _ in valid_words]
        print("Found valid words:", result)
        return result

        
    def handle_click(self, x: int, y: int):
        """Process click and show word definition."""
        global current_overlay
        try:
            if current_overlay and current_overlay.root.winfo_exists():
                current_overlay.root.destroy()
                current_overlay = None
        except tk.TclError:
            current_overlay = None

        valid_words = self.find_possible_words(x, y)
        
        if valid_words:
            word = valid_words[0]  # Use first valid word found
            data = cache.get(word.lower(), None)  # Try to get from cache first
            if data is None:
                data = fetch_definition(word)
            current_overlay = ModernDictionaryOverlay(x, y, word, data)
            current_overlay.show()
            return

        current_overlay = ModernDictionaryOverlay(
            x, y, "No valid word detected.", 
            {"error": "No valid word detected at this position"}
        )
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

def get_closest_character(click_x, click_y, character_positions):
    """
    Find the character closest to the click position.
    """
    min_distance = float('inf')
    closest_char = None
    closest_index = -1

    for i, (char, x, y, width, height) in enumerate(character_positions):
        center_x, center_y = x + width / 2, y + height / 2
        distance = math.sqrt((click_x - center_x) ** 2 + (click_y - center_y) ** 2)
        if distance < min_distance:
            min_distance = distance
            closest_char = char
            closest_index = i

    return closest_char, closest_index

def generate_word_candidates(character_positions, start_index):
    """
    Generate all possible word candidates centered on the start index.
    """
    candidates = []
    base_char = character_positions[start_index][0]

    # Expand left and right to form substrings
    for left in range(start_index, -1, -1):
        if not character_positions[left][0].isalnum():
            break

        for right in range(start_index, len(character_positions)):
            if not character_positions[right][0].isalnum():
                break

            word = ''.join([char for char, _, _, _, _ in character_positions[left:right + 1]])
            if base_char in word:
                candidates.append(word)

    return candidates

def validate_words(candidates):
    valid_words = []
    for word in candidates:
        word = word.lower()
        if word in cache:
            valid_words.append(word)
        else:
            response = requests.get(f"{API_URL}{word}")
            if response.status_code == 200:
                cache[word] = response.json()
                valid_words.append(word)
                save_cache()
    return valid_words

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