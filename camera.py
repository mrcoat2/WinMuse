import sys
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtMultimedia import QMediaCaptureSession, QCamera, QVideoSink, QVideoFrame

class VideoTransformWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Video Transform Example")
        self.resize(800, 600)

        # UI Layout setup
        self.display_label = QLabel("Initializing camera...")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.display_label)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 1. Initialize Multimedia Components
        self.capture_session = QMediaCaptureSession()
        self.camera = QCamera()
        self.video_sink = QVideoSink()

        # 2. Connect Session Pipelines
        self.capture_session.setCamera(self.camera)
        self.capture_session.setVideoOutput(self.video_sink)

        # 3. Handle Frame Pipeline Interrupts
        self.video_sink.videoFrameChanged.connect(self.process_video_frame)

        # 4. Fire up the Hardware Pipeline
        self.camera.start()

    @Slot(QVideoFrame)
    def process_video_frame(self, frame: QVideoFrame):
        # Prevent processing logic if frame data is empty
        if not frame.isValid():
            return

        # Clone and Map the data pointer safely out of GPU/Hardware space
        clone_frame = QVideoFrame(frame)
        if not clone_frame.map(QVideoFrame.MapMode.ReadOnly):
            return

        try:
            # Convert frame straight to QImage pointer map
            image = clone_frame.toImage()
            if image.isNull():
                return

            # Format to 32-bit RGB if necessary
            image = image.convertToFormat(QImage.Format.Format_RGB32)
            
            # --- TRANSFORM VIA NUMPY AREA BEGIN ---
            # Extract underlying memory array safely without duplicating data pointers
            width, height = image.width(), image.height()
            ptr = image.bits()
            
            # Create a view array (Shape: Height, Width, RGBA Channels)
            arr = np.array(ptr).reshape((height, width, 4))

            # Sample Transformation: Invert image colors (excluding Alpha channel)
            arr[:, :, :3] = 255 - arr[:, :, :3]
            # --- TRANSFORM AREA END ---

            # Reconstruct the modified NumPy array back into standard Qt visual assets
            transformed_image = QImage(arr.data, width, height, image.bytesPerLine(), QImage.Format.Format_RGB32)
            pixmap = QPixmap.fromImage(transformed_image)
            
            # Update UI on Main GUI Thread loop safely
            self.display_label.setPixmap(pixmap.scaled(
                self.display_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))

        finally:
            # Crucial: Unmap native buffer memory allocation immediately
            clone_frame.unmap()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoTransformWindow()
    window.show()
    sys.exit(app.exec())
