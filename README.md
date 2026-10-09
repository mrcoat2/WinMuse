# WinMuse

Install:
Run the provided executable
[Download the Latest Release](https://github.com)
or run from source
`py -m pip install -r requirements.txt`
`py app.py`

Build Windows EXE:
`py -m pip install pyinstaller`
`pyinstaller --noconsole --onefile --name SheetMusicReader app.py`

Controls:
- F11: fullscreen
- Escape: leave fullscreen
- Left/Right/Space: page navigation
- R: rotate
- Navigation bar:
    - Navigate mode: tap left/right side to turn pages
    - Pen / Highlighter: draw with mouse, stylus, or touchscreen, you must click navigate mode again to go back to tap to turn
    - Export PDF: creates a PDF containing the annotated pages

Still a work in progress, please report bugs

I created this app after realizing there is not a great open source way to view sheet music on a windows, and there is still not a great way. But I hope this taught me something.
 
Works the best with windows tablet mode, rotated to be the shape of a piece of paper.