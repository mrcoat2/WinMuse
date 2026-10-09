import sys
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QColor, QImage, QPixmap, QTransform
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QLabel, QListWidget, QListWidgetItem, QSplitter, QToolBar, QComboBox, QColorDialog
from PIL import Image
import fitz

from camera import CameraApp
from PageCanvas import PageCanvas

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sheet Music Reader")
        self.resize(1250,800)
        self.pages=[]; self.current=0; self.orientation="Auto"; self.fullscreen=False
        self.cam_window = None

        self.canvas=PageCanvas(self)
        self.canvas.color = QColor(0, 0, 0) # Default color black
        self.list=QListWidget(); self.list.setMaximumWidth(240)
        self.list.currentRowChanged.connect(self.select_page)
        split=QSplitter(); split.addWidget(self.list); split.addWidget(self.canvas); split.setStretchFactor(1,1)
        self.setCentralWidget(split)
        self.build_toolbar()
        self.status=QLabel("No pages")
        self.statusBar().addPermanentWidget(self.status)

    def build_toolbar(self):
        tb=QToolBar(); self.addToolBar(tb)
        def act(text,fn,key=None):
            a=QAction(text,self); a.triggered.connect(fn)
            if key: a.setShortcut(key)
            tb.addAction(a)

        act("Toggle Sidebar",self.toggle_sidebar)
        act("Open PDF",self.open_pdf,"Ctrl+O")
        act("Add Photos",self.add_photos_from_file)
        act("Camera",self.open_cam_window)
        act("Export PDF",self.export_pdf,"Ctrl+E")
        tb.addSeparator()
        act("◀ Previous",self.previous_page,"Left")
        act("Next ▶",self.next_page,"Right")
        act("Rotate",self.rotate_page,"R")
        tb.addSeparator()
        act("Pen",lambda:self.set_mode("pen"))
        act("Highlighter",lambda:self.set_mode("highlighter"))
        act("Navigate",lambda:self.set_mode("navigate"))
        act("Color",self.color)
        act("Clear",self.clear)
        tb.addSeparator()
        act("Fullscreen",self.toggle_fullscreen,"F11")
        tb.addWidget(QLabel("  Orientation: "))
        box=QComboBox(); box.addItems(["Auto","Horizontal","Vertical"]); box.currentTextChanged.connect(self.set_orientation); tb.addWidget(box)

    def toggle_sidebar(self):
        self.list.setVisible(not self.list.isVisible())

    def add_photo(self, image):
        self.pages.append({"name":str(self.list.count()),"image":image,"pixmap":None,"rotation":0,"zoom":1.0,"center":QPointF(0,0)})
        self.list.addItem(QListWidgetItem(str(self.list.count())))
        if self.pages: self.list.setCurrentRow(0)

    def add_photos_from_file(self):
        fs,_=QFileDialog.getOpenFileNames(self,"Add Sheet Music Photos","","Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        for f in fs:
            print(f)
            img=QImage(f)
            if not img.isNull():
                self.add_photo(img)
        if self.pages: self.list.setCurrentRow(0)

    def open_cam_window(self):
            # Only create the window if it doesn't exist yet
            if self.cam_window is None:
                self.cam_window = CameraApp(self)
            
            self.cam_window.show()

    def open_pdf(self):
        f,_=QFileDialog.getOpenFileName(self,"Open Sheet Music PDF","","PDF Files (*.pdf)")
        if not f:return
        try:
            doc=fitz.open(f)
            self.pages=[]; self.list.clear()
            for i,page in enumerate(doc):
                p=page.get_pixmap(dpi=160,alpha=False)
                img=QImage(p.samples,p.width,p.height,p.stride,QImage.Format_RGB888).copy()
                self.pages.append({"name":f"{Path(f).stem} — Page {i+1}","image":img,"pixmap":None,"rotation":0,"zoom":1.0,"center":QPointF(0,0)})
                self.list.addItem(self.pages[-1]["name"])
            doc.close(); self.list.setCurrentRow(0)
        except Exception as e: QMessageBox.critical(self,"PDF error",str(e))

    def base_pixmap(self,p):
        img=p["image"]
        if self.orientation=="Horizontal" and img.height()>img.width(): img=img.transformed(QTransform().rotate(90))
        if self.orientation=="Vertical" and img.width()>img.height(): img=img.transformed(QTransform().rotate(90))
        if p["rotation"]: img=img.transformed(QTransform().rotate(p["rotation"]))
        return QPixmap.fromImage(img)

    def select_page(self,i):
        if not 0<=i<len(self.pages): return
        self.current=i
        p=self.pages[i]
        if p["pixmap"] is None: p["pixmap"]=self.base_pixmap(p)
        self.canvas.set_image(p["pixmap"])
        self.canvas.zoom_at(p["center"],p["zoom"])
        self.status.setText(f"Page {i+1} / {len(self.pages)}")

    def save_annotation(self):
        if self.pages: self.pages[self.current]["pixmap"]=self.canvas.image.copy()

    def set_mode(self,m):
        self.save_annotation(); self.canvas.mode=m
        self.status.setText("Navigation mode" if m=="navigate" else f"Annotation: {m}")

    def color(self):
        c=QColorDialog.getColor(self.canvas.color,self,"Annotation color")
        if c.isValid(): self.canvas.color=c

    def clear(self):
        if not self.pages:return
        if QMessageBox.question(self,"Clear","Clear annotations on this page?")==QMessageBox.Yes:
            self.canvas.image=self.canvas.base.copy(); self.canvas.refresh(); self.save_annotation()

    def rotate_page(self):
        if not self.pages:return
        self.save_annotation()
        p=self.pages[self.current]; p["rotation"]=(p["rotation"]+90)%360; p["pixmap"]=self.base_pixmap(p)
        self.canvas.set_image(p["pixmap"])

    def set_orientation(self,v):
        self.save_annotation(); self.orientation=v
        for p in self.pages:p["pixmap"]=None
        if self.pages:self.select_page(self.current)

    def next_page(self):
        if self.current<len(self.pages)-1:self.list.setCurrentRow(self.current+1)
    def previous_page(self):
        if self.current>0:self.list.setCurrentRow(self.current-1)

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()
        self.fullscreen=self.isFullScreen()

    def keyPressEvent(self,e):
        if e.key()==Qt.Key_F11:self.toggle_fullscreen()
        elif e.key() in (Qt.Key_Right,Qt.Key_Down,Qt.Key_Space,Qt.Key_PageDown):self.next_page()
        elif e.key() in (Qt.Key_Left,Qt.Key_Up,Qt.Key_PageUp):self.previous_page()
        elif e.key()==Qt.Key_R:self.rotate_page()
        elif e.key()==Qt.Key_Escape and self.isFullScreen():self.toggle_fullscreen()
        else:super().keyPressEvent(e)

    def export_pdf(self):
        if not self.pages:
            return

        f, _ = QFileDialog.getSaveFileName(
            self,
            "Export Annotated PDF",
            "sheet_music_annotated.pdf",
            "PDF Files (*.pdf)"
        )

        if not f:
            return

        try:
            self.save_annotation()
            ims = []

            for p in self.pages:
                pm = p["pixmap"] or self.base_pixmap(p)

                q = pm.toImage().convertToFormat(QImage.Format_RGB888)

                # PySide6 constBits() returns a memoryview
                ptr = q.constBits()
                data = bytes(ptr)

                ims.append(
                    Image.frombuffer(
                        "RGB",
                        (q.width(), q.height()),
                        data,
                        "raw",
                        "RGB",
                        q.bytesPerLine(),
                        1
                    ).copy()
                )

            ims[0].save(
                f,
                "PDF",
                resolution=150,
                save_all=True,
                append_images=ims[1:]
            )

            QMessageBox.information(self, "Exported", f"Saved:\n{f}")

        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

def main():
    app=QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec())
if __name__=="__main__":main()
