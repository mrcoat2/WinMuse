import numpy as np
import cv2
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap, QTransform, QShowEvent
from PySide6.QtWidgets import QSlider, QStackedLayout, QGraphicsScene, QGraphicsView, QWidget, QPushButton, QVBoxLayout, QMessageBox, QLabel
from PySide6.QtMultimedia import QCamera, QImageCapture, QMediaCaptureSession
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem


def qimage_to_cv2(image: QImage):
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)

    width = image.width()
    height = image.height()

    ptr = image.bits()
    arr = np.frombuffer(ptr, dtype=np.uint8)

    arr = arr.reshape((height, width, 4))

    # Convert RGBA → BGR for OpenCV
    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

def cv2_to_qimage(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    height, width, channels = image.shape
    bytes_per_line = channels * width

    return QImage(
        image.data,
        width,
        height,
        bytes_per_line,
        QImage.Format.Format_RGB888
    ).copy()

class CameraApp(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.setWindowTitle("PySide6 Camera App")
        self.resize(919, 1244)

        # 0. Setup scene view
        self.main_layout = QVBoxLayout(self)
        self.content_stack = QStackedLayout()

        self.main_layout.addLayout(self.content_stack)

        self.camera_widget = QWidget()
        self.camera_layout = QVBoxLayout(self.camera_widget)
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
        self.capture_button.clicked.connect(self.image_capture.capture)
        self.image_capture.imageCaptured.connect(self.take_picture)

        # Arrange Layout
        self.camera_layout.addWidget(self.capture_button)
        self.camera_layout.addWidget(self.view)

        # Setup the captured content layout
        self.capture_widget = QWidget()
        self.capture_layout = QVBoxLayout(self.capture_widget)

        # Image capture layout
        self.back_button = QPushButton("Discard")
        self.back_button.clicked.connect(self.back_to_cam_butt_click)
        self.capture_layout.addWidget(self.back_button)

        self.keep_photo_butt = QPushButton("Keep Photo")
        self.keep_photo_butt.clicked.connect(self.keep_photo)
        self.capture_layout.addWidget(self.keep_photo_butt)

        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(-100)
        self.contrast_slider.setMaximum(100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.valueChanged.connect(self.contrast_value_changed)
        self.capture_layout.addWidget(self.contrast_slider)

        self.image_label = QLabel('No image captured yet')
        self.working_image = None
        self.image_label.setScaledContents(True)
        self.capture_layout.addWidget(self.image_label)
        
        # Add the widgets to stack
        self.content_stack.addWidget(self.camera_widget)
        self.content_stack.addWidget(self.capture_widget)

        # 3. Connect Signals & Start Camera
        self.image_capture.imageSaved.connect(self.on_image_saved)
        self.camera.start()

    def contrast_value_changed(self, value):
        print(f"Contrast value changed to: {value}")
        contrast_factor = value / 100.0 + 1.0
        """
        Adjusts contrast. 
        contrast_factor: 1.0 is original, < 1.0 is lower, > 1.0 is higher.
        
        pixmap = self.image_label.pixmap()
        # 1. Convert QPixmap to QImage (Format_ARGB32 ensures 4 channels)
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        """
        image = self.working_image.copy()
        width, height = image.width(), image.height()
        
        # 2. Access the raw pixel data buffer
        ptr = image.bits()
        # Create a NumPy array sharing the memory buffer
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))
        
        # 3. Extract RGB channels (leave Alpha untouched)
        rgb = arr[:, :, :3].astype(np.float32)
        
        # 4. Apply contrast formula: (Pixel - Midpoint) * Factor + Midpoint
        # 127.5 is the middle gray point of an 8-bit image channel
        rgb = (rgb - 127.5) * contrast_factor + 127.5
        
        # 5. Clip values to valid 0-255 range and cast back to uint8
        arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)

        # 6. Convert back to QPixmap
        pixmap = QPixmap.fromImage(image)
        transform = QTransform().rotate(90)
        pixmap = pixmap.scaled(
                        self.image_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
        
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)

    @Slot()
    def keep_photo(self, event):
        self.parent.add_photo(self.image_label.pixmap().toImage())
        self.back_to_cam()

    def back_to_cam(self):
        self.content_stack.setCurrentIndex(0)
        self.camera.start()
    
    @Slot()
    def back_to_cam_butt_click(self, event):
        self.back_to_cam()
    
    def resizeEvent(self, event):
        """Ensure the rotated video scales correctly when window resizes."""
        super().resizeEvent(event)
        self.fit_screen()

    def closeEvent(self, event):
        self.camera.stop()
        super().closeEvent(event)

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
    def take_picture(self, request_id, image):
        """# Generate a unique file name using the current timestamp # Save Image code
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(os.getcwd(), f"captured_{timestamp}.jpg")
        
        # Disable button to prevent spamming while saving
        self.capture_button.setEnabled(False)
        
        # Trigger the image capture
        self.image_capture.captureToFile(filename)"""
        self.camera.stop()
        self.working_image = image

        cv_image = qimage_to_cv2(image)

        """ This code makes the image not look good
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Reduce camera noise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive black/white threshold
        bw = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            12
        )

        # Clean small artifacts
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel)

        # Slightly close gaps in letters/lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)

        new_image = cv2_to_qimage(bw)"""

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        gray = cv2.fastNlMeansDenoising( # Remove tiny noise
            gray,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21
        )

        # Increase separation between paper and ink
        gray = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        ).apply(gray)

        bw = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            10
        )

        new_image = cv2_to_qimage(bw)
        pixmap = QPixmap.fromImage(new_image)
        transform = QTransform().rotate(90)
        pixmap = pixmap.scaled(
                        self.image_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
        
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        self.image_label.setPixmap(rotated_pixmap)
        print("took picture")
        self.content_stack.setCurrentIndex(1)

    @Slot(int, str)
    def on_image_saved(self, id, path):
        # Re-enable the button and alert user
        self.capture_button.setEnabled(True)
        QMessageBox.information(self, "Success", f"Picture saved to:\n{path}")
    