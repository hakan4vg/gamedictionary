# Game Dictionary

## Overview

Game Dictionary is a Python application that allows users to capture a screenshot, perform OCR (Optical Character Recognition) on the captured image, and display the definition of the detected word in a custom overlay window. This tool is particularly useful for gamers who want to quickly look up the meaning of words they encounter in games.

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
    - Download Tesseract OCR from here.
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


## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have any suggestions or improvements.