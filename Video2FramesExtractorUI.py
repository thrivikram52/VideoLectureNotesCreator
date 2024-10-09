import sys
import cv2
import numpy as np
import os
from skimage.metrics import structural_similarity as ssim
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QToolTip, QMessageBox, QComboBox, QProgressBar, QTextEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

# Constants and default values
DEFAULT_OUTPUT_FOLDER = 'scenes'
DEFAULT_SSIM_THRESHOLD = 0.6
DEFAULT_FRAME_SKIP = 30
DEFAULT_MIN_SCENE_DURATION = 1

class WorkerThread(QThread):
    progress_update = pyqtSignal(int, int)
    log_update = pyqtSignal(str)

    def __init__(self, video_source, output_folder, ssim_threshold, frame_skip, min_scene_duration):
        super().__init__()
        self.video_source = video_source
        self.output_folder = output_folder
        self.ssim_threshold = ssim_threshold
        self.frame_skip = frame_skip
        self.min_scene_duration = min_scene_duration

    def run(self):
        if self.video_source.startswith('http'):
            self.download_youtube_video()
        self.scene_detection()

    def download_youtube_video(self):
        yt = YouTube(self.video_source)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        total_size = stream.filesize
        self.log_update.emit(f"Total video size: {total_size / (1024 * 1024):.2f} MB")
        
        def on_progress(stream, chunk, bytes_remaining):
            progress = (total_size - bytes_remaining) / total_size
            self.progress_update.emit(int(progress * 100), 100)
        
        yt.register_on_progress_callback(on_progress)
        self.video_source = os.path.join(os.getcwd(), 'downloaded_video.mp4')
        stream.download(filename=self.video_source)
        self.log_update.emit(f"Video downloaded to: {self.video_source}")

    def scene_detection(self):
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        cap = cv2.VideoCapture(self.video_source)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        last_saved_frame = None
        scene_number = 0
        processed_frames = 0
        last_save_time = 0

        if not cap.isOpened():
            self.log_update.emit("Error: Could not open video.")
            return

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            processed_frames += 1
            self.progress_update.emit(processed_frames, frame_count)

            if processed_frames % self.frame_skip != 0:
                continue

            current_time = processed_frames / fps

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if last_saved_frame is not None:
                ssim_score, _ = ssim(last_saved_frame, gray_frame, full=True)

                if ssim_score < self.ssim_threshold and (current_time - last_save_time) >= self.min_scene_duration:
                    scene_number += 1
                    output_filename = f'{self.output_folder}/scene_{scene_number}.png'
                    cv2.imwrite(output_filename, frame)
                    last_saved_frame = gray_frame
                    last_save_time = current_time
                    self.log_update.emit(f"New scene detected: {output_filename}, SSIM={ssim_score:.2f}")
            else:
                # Save the first frame
                scene_number += 1
                output_filename = f'{self.output_folder}/scene_{scene_number}.png'
                cv2.imwrite(output_filename, frame)
                last_saved_frame = gray_frame
                last_save_time = current_time
                self.log_update.emit(f"First scene saved: {output_filename}")

        cap.release()
        cv2.destroyAllWindows()

        self.log_update.emit(f'Total unique scenes detected: {scene_number}')

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # File Upload
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Input Video:")
        self.file_path = QLineEdit()
        self.file_button = QPushButton("Browse")
        self.file_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.file_button)
        layout.addLayout(file_layout)

        # Output Folder
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Output Folder:")
        self.folder_path = QLineEdit()
        self.folder_button = QPushButton("Browse")
        self.folder_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(self.folder_button)
        layout.addLayout(folder_layout)

        # SSIM Threshold
        ssim_layout = QHBoxLayout()
        ssim_layout.addWidget(QLabel("SSIM Threshold:"))
        self.ssim_threshold = QLineEdit("0.8")  # Set default value to 0.65
        ssim_layout.addWidget(self.ssim_threshold)
        layout.addLayout(ssim_layout)

        # Frame Skip
        frame_skip_layout = QHBoxLayout()
        frame_skip_layout.addWidget(QLabel("Frame Skip:"))
        self.frame_skip = QLineEdit("30")
        frame_skip_layout.addWidget(self.frame_skip)
        layout.addLayout(frame_skip_layout)

        # Min Scene Duration
        min_scene_duration_layout = QHBoxLayout()
        min_scene_duration_layout.addWidget(QLabel("Min Scene Duration (s):"))
        self.min_scene_duration = QLineEdit("1")  # Set default value to 1
        min_scene_duration_layout.addWidget(self.min_scene_duration)
        layout.addLayout(min_scene_duration_layout)

        # Start Processing Button
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        # Progress Bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Status Area
        self.status_area = QTextEdit()
        self.status_area.setReadOnly(True)
        self.status_area.setMinimumHeight(100)
        layout.addWidget(self.status_area)

        self.setLayout(layout)
        self.setWindowTitle('Video to PDF Converter')
        self.setGeometry(300, 300, 500, 400)

    def add_default_field(self, layout, label, default_value):
        field_layout = QHBoxLayout()
        label_widget = QLabel(label)
        value_widget = QLineEdit(default_value)
        field_layout.addWidget(label_widget)
        field_layout.addWidget(value_widget)
        layout.addLayout(field_layout)
        return value_widget

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_name:
            self.file_path.setText(file_name)

    def browse_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder_name:
            self.folder_path.setText(folder_name)

    def start_processing(self):
        if not self.file_path.text() or not self.folder_path.text():
            QMessageBox.warning(self, "Input Error", "Please select both input file and output folder.")
            return

        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_area.clear()

        self.processing_thread = ProcessingThread(
            self.file_path.text(),
            self.folder_path.text(),
            self.ssim_threshold.text(),
            self.frame_skip.text(),
            self.min_scene_duration.text()
        )
        self.processing_thread.update_status.connect(self.update_status)
        self.processing_thread.progress_update.connect(self.update_progress)
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.start()

    def update_status(self, message):
        self.status_area.append(message)
        self.status_area.verticalScrollBar().setValue(self.status_area.verticalScrollBar().maximum())

    def update_progress(self, current, total):
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)

    def on_processing_finished(self):
        self.start_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.update_status("Processing completed!")

class ProcessingThread(QThread):
    progress_update = pyqtSignal(int, int)
    update_status = pyqtSignal(str)  # Add this line

    def __init__(self, video_source, output_folder, ssim_threshold, frame_skip, min_scene_duration):
        super().__init__()
        self.video_source = video_source
        self.output_folder = output_folder
        self.ssim_threshold = float(ssim_threshold)  # Convert to float
        self.frame_skip = int(frame_skip)  # Convert to int
        self.min_scene_duration = float(min_scene_duration)  # Convert to float

    def run(self):
        if self.video_source.startswith('http'):
            self.download_youtube_video()
        self.scene_detection()

    def download_youtube_video(self):
        yt = YouTube(self.video_source)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        total_size = stream.filesize
        self.update_status.emit(f"Total video size: {total_size / (1024 * 1024):.2f} MB")
        
        def on_progress(stream, chunk, bytes_remaining):
            progress = (total_size - bytes_remaining) / total_size
            self.progress_update.emit(int(progress * 100), 100)
        
        yt.register_on_progress_callback(on_progress)
        self.video_source = os.path.join(os.getcwd(), 'downloaded_video.mp4')
        stream.download(filename=self.video_source)
        self.update_status.emit(f"Video downloaded to: {self.video_source}")

    def scene_detection(self):
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        cap = cv2.VideoCapture(self.video_source)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        last_saved_frame = None
        scene_number = 0
        processed_frames = 0
        last_save_time = 0

        if not cap.isOpened():
            self.update_status.emit("Error: Could not open video.")
            return

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            processed_frames += 1
            self.progress_update.emit(processed_frames, frame_count)

            if processed_frames % self.frame_skip != 0:
                continue

            current_time = processed_frames / fps

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if last_saved_frame is not None:
                ssim_score, _ = ssim(last_saved_frame, gray_frame, full=True)

                if ssim_score < self.ssim_threshold and (current_time - last_save_time) >= self.min_scene_duration:
                    scene_number += 1
                    output_filename = f'{self.output_folder}/scene_{scene_number}.png'
                    cv2.imwrite(output_filename, frame)
                    last_saved_frame = gray_frame
                    last_save_time = current_time
                    self.update_status.emit(f"New scene detected: {output_filename}, SSIM={ssim_score:.2f}")
            else:
                # Save the first frame
                scene_number += 1
                output_filename = f'{self.output_folder}/scene_{scene_number}.png'
                cv2.imwrite(output_filename, frame)
                last_saved_frame = gray_frame
                last_save_time = current_time
                self.update_status.emit(f"First scene saved: {output_filename}")

        cap.release()
        cv2.destroyAllWindows()

        self.update_status.emit(f'Total unique scenes detected: {scene_number}')

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())