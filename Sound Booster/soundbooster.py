import sys
import os
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QVBoxLayout, QWidget, QMessageBox, QSlider, QAction
from PyQt5.QtCore import Qt, QUrl
from pydub import AudioSegment
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from pydub.exceptions import CouldntDecodeError
from pydub.playback import play
from pydub.utils import db_to_float, stereo_to_ms
from pydub.effects import normalize, compress_dynamic_range









class AudioProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.processed_audio = None  # Store processed audio data
        self.dropped_file_path = None  # Store the path of the dropped file
        self.audio_paused = False  # Flag to track whether audio is paused
        self.media_player = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        self.media_player.setPlaylist(self.playlist)

    def initUI(self):
        self.setWindowTitle('Audio Processor')
        self.setGeometry(100, 100, 400, 300)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()

        self.label = QLabel('Drag and drop an audio file here:')
        self.label.setStyleSheet("color: #ddd;")  # Light gray color
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.rms_slider = QSlider(Qt.Horizontal)
        self.rms_slider.setMinimum(2000)  # High boost
        self.rms_slider.setMaximum(12000)  # Less boost
        self.rms_slider.setValue(2000)     # Default value on the right
        layout.addWidget(self.rms_slider)

        self.rms_value_label = QLabel('Current RMS Value: 2000')
        self.rms_value_label.setStyleSheet("color: #ddd;")  # Light gray color
        layout.addWidget(self.rms_value_label)

        self.rms_slider.setStyleSheet("""
            QSlider::handle:horizontal {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop: 0 #e74c3c, stop: 1 #3498db);
                border: 1px solid #ccc;
                width: 20px;
                margin: -5px 0;
                border-radius: 6px;
            }

            QSlider::groove:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop: 0 #e74c3c, stop: 1 #3498db);
                border: 1px solid #ccc;
                height: 10px;
                margin: 0px;
                border-radius: 5px;
            }
        """)
    


        self.process_button = QPushButton('Process Audio')
        self.process_button.setStyleSheet("background-color: #1abc9c; color: black;")
        layout.addWidget(self.process_button)
        self.process_button.setEnabled(False)

        


        self.save_button = QPushButton('Save Processed Audio')
        self.save_button.setStyleSheet("background-color: #1abc9c; color: black;")
        layout.addWidget(self.save_button)
        self.save_button.hide()

        self.central_widget.setLayout(layout)

        # Set the background color of the central widget to dark grey
        self.central_widget.setStyleSheet("background-color: #333;")

        # Enable drag-and-drop support
        self.setAcceptDrops(True)

        self.process_button.clicked.connect(self.process_audio)
        self.save_button.clicked.connect(self.save_processed_audio)

        # Connect slider valueChanged event to update RMS value label
        self.rms_slider.valueChanged.connect(self.update_rms_value_label)

        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(self.restart_program)

       
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction(restart_action)

    def update_rms_value_label(self):
        current_rms_value = self.rms_slider.value()
        self.rms_value_label.setText(f'Current RMS Value: {current_rms_value}')
        self.rms_value_label.setStyleSheet("color: #ddd;")  # Light gray color
        

    

    def restart_program(self):

        # Close the current QMainWindow
        self.close()

        # Close the current QApplication instance
        app = QApplication.instance()
        app.quit()

        # Start a new instance of the application
        new_app = QApplication(sys.argv)
        new_mainWindow = AudioProcessorApp()
        new_mainWindow.show()
        sys.exit(new_app.exec_())
                
            
    def process_audio(self):

        if self.dropped_file_path is None:
            return

        target_rms_level = self.rms_slider.value()
        stereo_widening_factor = 0.8  # Increase the stereo widening factor


        try:
            if self.dropped_file_path.lower().endswith('.mp3'):
                # Convert MP3 to WAV format
                audio = AudioSegment.from_mp3(self.dropped_file_path)
            else:
                audio = AudioSegment.from_file(self.dropped_file_path)
                audio = audio.set_sample_width(2)
                audio = audio.set_frame_rate(48000)
                audio = normalize(audio)

            current_rms_level = audio.rms
            gain_adjustment_db = 20 * (np.log10(target_rms_level) - np.log10(current_rms_level))
            #print(gain_adjustment_db)
            
           
            # Apply dynamic range compression to limit gain adjustment
            max_gain_db = 10  # Maximum gain reduction to prevent distortion
            if gain_adjustment_db > max_gain_db:
                gain_adjustment_db = max_gain_db

            adjusted_audio = audio - gain_adjustment_db
            print(adjusted_audio.dBFS)

            # Apply stereo widening to both sides
            left_channel = adjusted_audio.pan(-stereo_widening_factor)
            right_channel = adjusted_audio.pan(stereo_widening_factor)
            delayed_right_channel = right_channel.set_frame_rate(right_channel.frame_rate + 8000)

            # Combine the left and right channels
            widened_audio = left_channel.overlay(delayed_right_channel)
            # Analyze the audio for bass-heavy sections (e.g., using spectral analysis)
            bass_threshold = -2  # Adjust the threshold as needed
            bass_sections = []
 
            # Dummy logic: Here, we'll consider bass-heavy sections to be where the energy is higher than the threshold
            for i in range(0, len(widened_audio), 5000):  # Adjust the window size as needed
                segment = widened_audio[i:i + 5000]
                segment_data = np.array(segment.get_array_of_samples())
                energy = np.sum(segment_data ** 2) / len(segment_data)

                if energy > bass_threshold:
                    bass_sections.append(segment)

            # Apply parametric equalizer to reduce gain of excessive bass frequencies
            for bass_section in bass_sections:
                # Adjust the parameters of the equalizer as needed
                bass_section = bass_section.low_pass_filter(350)  # Lower frequencies
                bass_section = bass_section.high_pass_filter(40)  # Higher frequencies
                bass_section = bass_section - 5  # Reduce gain by 10 dB

            # Combine all sections to create the final audio
            bass_dip_audio = sum(bass_sections)

            audio_data = np.array(bass_dip_audio.get_array_of_samples())
            

            # Check for clipping (values exceeding the [-32768, 32767] range)
            max_sample_value = 32767
            if np.any(np.abs(audio_data) > max_sample_value):
                print("Clipping detected")

                # Identify the clipping points (samples exceeding the allowed range)
                clipping_indices = np.where(np.abs(audio_data) > max_sample_value)[0]

                # Adjust the clipped samples (for example, you can clip values to the max allowed)
                audio_data[clipping_indices] = np.sign(audio_data[clipping_indices]) * max_sample_value

                # Create a new PyDub audio segment from the adjusted NumPy array
                adjusted_audio = AudioSegment(
                    audio_data.tobytes(),
                    frame_rate=audio.frame_rate,
                    sample_width=audio.sample_width,
                    channels=audio.channels
                )
            
            self.processed_audio = adjusted_audio
            


            # Update UI
            self.label.setText('Audio Processed. Preview or Save.')
            self.save_button.show()
          

        except CouldntDecodeError:
            QMessageBox.critical(self, 'Error', 'Failed to decode the audio file. Please make sure it is a valid audio format.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred: {str(e)}')


    def save_processed_audio(self):
        if self.processed_audio is not None:
            output_path, _ = QFileDialog.getSaveFileName(self, 'Save Processed Audio', '', 'Audio Files (*.wav)')
            if output_path:
                self.processed_audio.export(output_path, format="wav")
                QMessageBox.information(self, 'Success', 'Processed audio saved successfully.')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            file_path = event.mimeData().urls()[0].toLocalFile()
            if os.path.isfile(file_path) and (file_path.lower().endswith('.wav') or file_path.lower().endswith('.mp3')):
                event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            file_path = event.mimeData().urls()[0].toLocalFile()
            if os.path.isfile(file_path) and (file_path.lower().endswith('.wav') or file_path.lower().endswith('.mp3')):
                self.label.setText(f'Dropped File: {os.path.basename(file_path)}')

                # Store the path of the dropped file
                self.dropped_file_path = file_path

                self.process_button.setEnabled(True)
                self.processed_audio = None
                self.save_button.hide()
               

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = AudioProcessorApp()
    mainWindow.show()
    sys.exit(app.exec_())
