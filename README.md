# Sheet Music Reader v2

Adds PDF opening, fullscreen performance mode, and on-page annotations.

Install:
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
- Navigate mode: tap left/right side to turn pages
- Pen / Highlighter: draw with mouse, stylus, or touchscreen
- Export PDF: creates a PDF containing the annotated pages

Note: annotations are currently rasterized into the exported PDF, which makes the implementation reliable but means they aren't editable PDF annotation objects.
