# Game Dictionary

## Overview

Game Dictionary is a Python application that allows users to capture a screenshot, perform OCR (Optical Character Recognition) on the captured image, and display the definition of the clicked word in a custom overlay window. This tool is particularly useful for gamers who want to quickly look up the meaning of words they encounter in games.

## Features

- Capture screenshots using a global keyboard shortcut.
- Perform OCR on the captured screenshot to detect words.
- Fetch word definitions from an online dictionary API.
- Display word definitions in a custom overlay window with a modern UI.
- System tray icon for easy access to preferences and exit options.

## Requirements

- Python 3.7+
- The following Python packages:
  - `tkinter`
  - `Pillow`
  - `pytesseract`
  - `pystray`
  - `pynput`
  - `requests`
  - `customtkinter`

## Installation

1. Clone the repository or download the source code.
2. Install the required Python packages using pip:
   ```sh
   pip install tkinter Pillow pytesseract pystray pynput requests customtkinter
3. Ensure you have Tesseract OCR installed and set the correct path in the code:
    - Download Tesseract OCR from https://github.com/tesseract-ocr/tesseract.
    - Update the TESSERACT_PATH and TESSDATA_PATH variables in main.py to point to your Tesseract installation.

## Usage
1. Run the application:
    - python main.py
2. The application will start and a system tray icon will appear.
3. Use the default keyboard shortcut Ctrl+Alt+S to capture a screenshot.
4. Click on a word in the screenshot to see its definition in the overlay window.
5. To change the keyboard shortcut, right-click the system tray icon and select "Preferences".

## Customization
- You can change the default keyboard shortcut by modifying the SHORTCUT variable in main.py.
- The appearance of the overlay window can be customized by modifying the 
ModernDictionaryOverlay class in main.py.

##TODO

- I will definitely try to improve the OCR accuracy and speed
- There are some crashes every few clicks, currently working on this issue
- It can't detect small or crammed fonts, will try to improve that
- Currently, I can't implement a better OCR system with systemically guessing words from the dictionary since I'm using dictionaryapi.dev and every query is an API call, will experiment with a local dictionary but I don't really know how it would affect performance and memory usage.
- Preferences window sometimes freeze, will work on that later down the line.
- Will improve dictionary overlay with multiple dictionary choices (hopefully) and translations down the line.
- It only works when a game is in borderless windowed mode, I'll try to make it work in exclusive fullscreen as well, there are overlays that work in those situations but I don't really know how.
- I want to add an effect to highlight all words during the OCR process to give a better feedback to the user, might be very performance intensive, will try that later.


## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have any suggestions or improvements.
