import time
from PySide6.QtCore import QEvent, Qt, QPointF
from PySide6.QtGui import QPixmap, QTransform, QPainter, QPen, QColor, QShowEvent
from PySide6.QtWidgets import QLabel

class PageCanvas(QLabel):
    def __init__(self, main):
        super().__init__()
        self.main = main

        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background:#202020;")
        self.setMinimumSize(500, 500)

        self.base = QPixmap()
        self.image = QPixmap()

        self.mode = "navigate"
        self.color = QColor("red")
        self.last = None
        self.drawing = False

        self.click_start = 0

        # -------------------------
        # Zoom / pan state
        # -------------------------
        self.zoom = 1.0
        self.offset = QPointF(0, 0)

        self.grabGesture(Qt.PinchGesture)

    # =========================================================
    # Gesture handling
    # =========================================================

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.gesture_event(event)

        return super().event(event)

    def gesture_event(self, event):
        pinch = event.gesture(Qt.PinchGesture)

        if pinch:
            center = pinch.centerPoint()

            if pinch.state() == Qt.GestureStarted:
                print("Pinch started")

            elif pinch.state() == Qt.GestureUpdated:
                self.zoom_at(
                    center,
                    pinch.scaleFactor()
                )

            elif pinch.state() == Qt.GestureFinished:
                print("Pinch finished")

            event.accept(pinch)
            return True

        return False

    # =========================================================
    # Image / zoom
    # =========================================================

    def set_image(self, pix):
        self.base = pix
        self.image = pix.copy()

        self.zoom = 1.0

        # Center image
        self.offset = QPointF(
            (self.width() - self.image.width()) / 2,
            (self.height() - self.image.height()) / 2
        )

        self.refresh()

    def zoom_at(self, center, factor):
        print(f"Zooming at {center}, factor: {factor}")
        if self.image.isNull():
            return

        old_zoom = self.zoom

        # Calculate new zoom
        new_zoom = old_zoom * factor

        # Clamp zoom
        new_zoom = max(0.1, min(new_zoom, 5.0))

        if new_zoom == old_zoom:
            return

        # -------------------------------------------------
        # Find which point in the original image is
        # currently underneath the pinch center.
        # -------------------------------------------------

        image_x = (center.x() - self.offset.x()) / old_zoom
        image_y = (center.y() - self.offset.y()) / old_zoom

        # Apply zoom
        self.zoom = new_zoom

        # -------------------------------------------------
        # Move the image so that the SAME image point
        # remains underneath the pinch center.
        # -------------------------------------------------

        self.offset = QPointF(
            center.x() - image_x * new_zoom,
            center.y() - image_y * new_zoom
        )

        self.refresh()

    def refresh(self):
        if self.image.isNull():
            self.clear()
            self.setText("Open a PDF or add sheet music photos")
            return

        self.update()

    # =========================================================
    # Painting
    # =========================================================

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.SmoothPixmapTransform
        )

        # Scale the image according to zoom
        size = self.image.size() * self.zoom

        scaled = self.image.scaled(
            size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        painter.drawPixmap(
            self.offset,
            scaled
        )

        painter.end()

    # =========================================================
    # Resize
    # =========================================================

    def resizeEvent(self, e):
        super().resizeEvent(e)

        if self.image.isNull():
            return

        # Only automatically center when we're at the
        # initial zoom level.
        if self.zoom == 1.0:
            self.offset = QPointF(
                (self.width() - self.image.width()) / 2,
                (self.height() - self.image.height()) / 2
            )

        self.update()

    # =========================================================
    # Mouse / drawing
    # =========================================================

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return

        if self.mode == "navigate":
            self.click_start = time.perf_counter()
            """if e.position().x() >= self.width() / 2: # Moved to mouseReleaseEvent
                self.main.next_page()
            else:
                self.main.previous_page()"""

        else:
            self.drawing = True
            self.last = e.position()

    def mouseMoveEvent(self, e):
        if not self.drawing or self.last is None:
            return

        if self.image.isNull():
            return

        # Convert widget coordinates -> image coordinates
        p1 = self.widget_to_image(self.last)
        p2 = self.widget_to_image(e.position())

        # Ignore points outside the image
        if p1 is None or p2 is None:
            self.last = e.position()
            return

        painter = QPainter(self.image)

        pen = QPen(self.color)

        """pen.setWidth( # Makes the pen way too big
            max(16, self.width() * 4)
            if self.mode == "highlighter"
            else self.width()
        )"""
        pen.setWidth(4)

        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        if self.mode == "highlighter":
            c = QColor(self.color)
            c.setAlpha(90)
            pen.setColor(c)

        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()

        self.last = e.position()

        self.refresh()

    def mouseReleaseEvent(self, e):
        if time.perf_counter() - self.click_start < 0.1:  # Only turn page for short click
            if e.position().x() >= self.width() / 2:
                self.main.next_page()
            else:
                self.main.previous_page()
            
        if e.button() == Qt.LeftButton:
            self.drawing = False
            self.last = None
            self.main.save_annotation()

    # =========================================================
    # Coordinate conversion
    # =========================================================

    def widget_to_image(self, pos):
        if self.image.isNull():
            return None

        # Widget -> zoomed image coordinates
        x = (pos.x() - self.offset.x()) / self.zoom
        y = (pos.y() - self.offset.y()) / self.zoom

        # Make sure we're inside the image
        if (
            x < 0
            or y < 0
            or x >= self.image.width()
            or y >= self.image.height()
        ):
            return None

        return QPointF(x, y)
