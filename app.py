import os
import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, Slot
from PySide6.QtGui import QAction, QImage, QPixmap, QTransform, QPainter, QPen, QColor, QShowEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsTransform, QGraphicsRotation, QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QFileDialog, QMessageBox, QLabel, QListWidget, QListWidgetItem, QSplitter, QToolBar, QComboBox, QColorDialog
from PySide6.QtMultimedia import QCamera, QImageCapture, QMediaCaptureSession
from PySide6.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PIL import Image
import fitz

class PageCanvas(QLabel):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background:#202020;")
        self.setMinimumSize(500,500)
        self.base = QPixmap()
        self.image = QPixmap()
        self.mode = "navigate"
        self.color = QColor("red")
        self.last = None
        self.drawing = False

    def set_image(self, pix):
        self.base = pix
        self.image = pix.copy()
        self.refresh()

    def refresh(self):
        if self.image.isNull():
            self.setText("Open a PDF or add sheet music photos")
        else:
            self.setPixmap(self.image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.refresh()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton: return
        if self.mode == "navigate":
            print(e.position().x())
            print(self.width())
            if e.position().x() >= self.width()/2: self.main.next_page()
            else: self.main.previous_page()
        else:
            self.drawing = True
            self.last = e.position()

    def mouseMoveEvent(self, e):
        if not self.drawing or self.last is None or self.image.isNull(): return
        shown = self.pixmap()
        if shown.isNull(): return
        ox = (self.width()-shown.width())/2
        oy = (self.height()-shown.height())/2
        x, y = e.position().x()-ox, e.position().y()-oy
        lx, ly = self.last.x()-ox, self.last.y()-oy
        if not (0 <= x <= shown.width() and 0 <= y <= shown.height()):
            self.last = e.position(); return
        sx, sy = self.image.width()/shown.width(), self.image.height()/shown.height()
        p1, p2 = QPointF(lx*sx,ly*sy), QPointF(x*sx,y*sy)
        painter = QPainter(self.image)
        pen = QPen(self.color)
        pen.setWidth(max(16,self.width()*4) if self.mode=="highlighter" else self.width())
        pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        if self.mode=="highlighter":
            c = QColor(self.color); c.setAlpha(90); pen.setColor(c)
        painter.setPen(pen); painter.drawLine(p1,p2); painter.end()
        self.last=e.position(); self.refresh()

    def mouseReleaseEvent(self,e):
        if e.button()==Qt.LeftButton:
            self.drawing=False; self.last=None; self.main.save_annotation()

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Camera App")
        self.resize(517, 704)

        # 0. Setup scene view
        self.layout = QVBoxLayout(self)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)


        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)

        self.video_item.setTransformOriginPoint(self.video_item.boundingRect().center())
        self.video_item.setRotation(90)

        # 1. Setup Multimedia Core Classes
        self.camera = QCamera()
        self.image_capture = QImageCapture()
        self.capture_session = QMediaCaptureSession()
        
        # Connect everything to the central session
        self.capture_session.setCamera(self.camera)
        self.capture_session.setImageCapture(self.image_capture)

        # 2. Setup GUI Layout and Video Preview Widget
        self.capture_session.setVideoOutput(self.video_item)

        self.capture_button = QPushButton("Take Picture")
        self.capture_button.clicked.connect(self.take_picture)

        # Arrange Layout
        self.layout.addWidget(self.capture_button)

        self.layout.addWidget(self.view)

        self.setLayout(self.layout)
        """container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)"""

        # 3. Connect Signals & Start Camera
        self.image_capture.imageSaved.connect(self.on_image_saved)
        self.camera.start()
        self.fit_screen()

    def resizeEvent(self, event):
        """Ensure the rotated video scales correctly when window resizes."""
        super().resizeEvent(event)
        self.fit_screen()

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.fit_screen()
        # Place your code here when the widget opens/shows

    def fit_screen(self):
        print(f"Width: {self.width()}, Height: {self.height()}")
        # Update the transform origin point on window resize
        self.video_item.setTransformOriginPoint(self.video_item.boundingRect().center())
        # Make the video item fit the viewport size while maintaining aspect ratio
        self.view.fitInView(self.video_item, Qt.KeepAspectRatio)

    @Slot()
    def take_picture(self):
        # Generate a unique file name using the current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(os.getcwd(), f"captured_{timestamp}.jpg")
        
        # Disable button to prevent spamming while saving
        self.capture_button.setEnabled(False)
        
        # Trigger the image capture
        self.image_capture.captureToFile(filename)

    @Slot(int, str)
    def on_image_saved(self, id, path):
        # Re-enable the button and alert user
        self.capture_button.setEnabled(True)
        QMessageBox.information(self, "Success", f"Picture saved to:\n{path}")
    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sheet Music Reader")
        self.resize(1250,800)
        self.pages=[]; self.current=0; self.orientation="Auto"; self.fullscreen=False
        self.cam_window = None

        self.canvas=PageCanvas(self)
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
        act("Open PDF",self.open_pdf,"Ctrl+O")
        act("Add Photos",self.add_photos)
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

    def add_photos(self):
        fs,_=QFileDialog.getOpenFileNames(self,"Add Sheet Music Photos","","Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        for f in fs:
            img=QImage(f)
            if not img.isNull():
                self.pages.append({"name":Path(f).name,"image":img,"pixmap":None,"rotation":0})
                self.list.addItem(QListWidgetItem(Path(f).name))
        if self.pages: self.list.setCurrentRow(0)

    def open_cam_window(self):
            # Only create the window if it doesn't exist yet
            if self.cam_window is None:
                self.cam_window = CameraApp()
            
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
                self.pages.append({"name":f"{Path(f).stem} — Page {i+1}","image":img,"pixmap":None,"rotation":0})
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
        if not self.pages:return
        f,_=QFileDialog.getSaveFileName(self,"Export Annotated PDF","sheet_music_annotated.pdf","PDF Files (*.pdf)")
        if not f:return
        try:
            self.save_annotation(); ims=[]
            for p in self.pages:
                pm=p["pixmap"] or self.base_pixmap(p)
                q=pm.toImage().convertToFormat(QImage.Format_RGB888)
                ptr=q.constBits(); ptr.setsize(q.sizeInBytes())
                ims.append(Image.frombuffer("RGB",(q.width(),q.height()),bytes(ptr),"raw","RGB",q.bytesPerLine(),1).copy())
            ims[0].save(f,"PDF",resolution=150,save_all=True,append_images=ims[1:])
            QMessageBox.information(self,"Exported",f"Saved:\n{f}")
        except Exception as e: QMessageBox.critical(self,"Export error",str(e))

def main():
    app=QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec())
if __name__=="__main__":main()
