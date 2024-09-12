import sys
import subprocess
import os
import logging
import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                               QLabel, QFileDialog, QGridLayout,QHBoxLayout, QListWidget, QSplitter, QListWidgetItem,
                               QFrame)
from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QBrush, QCursor

# Add version information
__version__ = "1.0.0"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DragDropLabel(QWidget):
    files_dropped = Signal(list)  # Change to emit a list of files
    cleared = Signal(str)  # New signal to emit the cleared file name
    clicked = Signal()  # New signal for click events

    def __init__(self, text, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        layout.addWidget(self.label, 0, 0, 1, 2)
        
        self.remove_btn = QPushButton("✖")  # Unicode "Heavy Multiplication X" symbol
        self.remove_btn.setFixedSize(30, 30)
        self.remove_btn.clicked.connect(self.clear)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: red;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                color: darkred;
            }
        """)
        layout.addWidget(self.remove_btn, 0, 1, Qt.AlignRight | Qt.AlignTop)
        
        self.setAcceptDrops(True)
        self.setFixedWidth(300)  # Limit the width of the label
        self.setStyleSheet("""
            QWidget {
                border: 2px dashed #aaa;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
            QLabel {
                background-color: transparent;
            }
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))  # Set cursor to pointing hand

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def setText(self, text):
        if len(text) > 30:
            text = text[:27] + "..."
        self.label.setText(text)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and event.mimeData().urls()[0].toLocalFile().endswith('.pdf'):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        file_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile().endswith('.pdf')]
        if file_paths:
            self.setText(os.path.basename(file_paths[0]))
            self.files_dropped.emit(file_paths)  # Emit all dropped files

    def clear(self):
        old_text = self.label.text()
        self.label.setText("Drag and drop PDF file here")
        self.cleared.emit(old_text)  # Emit the old file name
        self.files_dropped.emit([])

class PDFListWidget(QListWidget):
    def __init__(self, output_dir, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.setAlternatingRowColors(True)
        self.setStyleSheet("QListWidget::item { height: 30px; }")
        self.itemDoubleClicked.connect(self.open_file)

    def open_file(self, item):
        file_path = os.path.join(self.output_dir, item.text())
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(('open', file_path))
            else:
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            print(f"Error opening file: {e}")

class DiffPDFApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PDF Diff GUI v{__version__}")  # Update the window title
        self.setGeometry(100, 100, 800, 600)
        self.file1 = None
        self.file2 = None
        self.output_dir = os.path.abspath('.')  # Current directory
        self.selected_files = set()
        self.initUI()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create a splitter for resizable sidebar
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Sidebar (PDF file list)
        self.file_list = PDFListWidget(self.output_dir, self)
        self.file_list.itemClicked.connect(self.add_file_from_sidebar)
        splitter.addWidget(self.file_list)

        # Main content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        splitter.addWidget(content_widget)

        # Create drag-drop labels
        self.file1_label = DragDropLabel("Click here or drag and drop PDF file")
        self.file2_label = DragDropLabel("Click here or drag and drop PDF file")
        self.file1_label.files_dropped.connect(self.update_files)
        self.file2_label.files_dropped.connect(self.update_files)
        self.file1_label.cleared.connect(self.handle_label_cleared)
        self.file2_label.cleared.connect(self.handle_label_cleared)
        self.file1_label.clicked.connect(lambda: self.add_pdf_file(self.file1_label))
        self.file2_label.clicked.connect(lambda: self.add_pdf_file(self.file2_label))

        # Create a single bounding frame for the PDF adding area
        pdf_frame = QFrame()
        pdf_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        pdf_frame.setLineWidth(2)

        # Create layout for the frame
        frame_layout = QGridLayout(pdf_frame)
        frame_layout.addWidget(self.file1_label, 0, 0)
        frame_layout.addWidget(self.file2_label, 0, 1)

        # Add the frame to the content layout
        content_layout.addWidget(pdf_frame)

        # Buttons to run diff and view diff
        button_layout = QHBoxLayout()
        diff_btn = QPushButton("Generate Comparison PDF")
        diff_btn.clicked.connect(self.run_diff)
        view_diff_btn = QPushButton("View Differences")
        view_diff_btn.clicked.connect(self.view_diff)
        button_layout.addWidget(diff_btn)
        button_layout.addWidget(view_diff_btn)

        content_layout.addLayout(button_layout)

        # Set initial splitter sizes
        splitter.setSizes([200, 600])  # Adjust these values as needed

        # Status bar
        self.statusBar().showMessage('Ready')

        # Populate the file list
        self.update_file_list()

        self.diff_exe_path = self.get_diff_exe_path()

    def get_diff_exe_path(self):
        if sys.platform == "win32":
            return os.path.join(os.path.dirname(__file__), "diff-pdf-win", "diff-pdf.exe")
        elif sys.platform == "darwin":  # macOS
            return "diff-pdf"  # Assuming it's installed and in PATH
        else:  # Linux and other Unix-like systems
            return "diff-pdf"  # Assuming it's installed and in PATH

    def add_file_from_sidebar(self, item):
        if item.text() in self.selected_files:
            return

        file_path = os.path.join(self.output_dir, item.text())
        abs_path = os.path.abspath(file_path)
        if not self.file1:
            self.update_file(self.file1_label, abs_path)
        elif not self.file2:
            self.update_file(self.file2_label, abs_path)
        else:
            self.statusBar().showMessage('Two files are already selected. Please remove one before adding a new file.')

    def update_files(self, file_paths):
        for file_path in file_paths:
            abs_path = os.path.abspath(file_path)
            if not self.file1:
                self.update_file(self.file1_label, abs_path)
            elif not self.file2:
                self.update_file(self.file2_label, abs_path)
            else:
                self.statusBar().showMessage('Two files are already selected. Cannot add more.')
                break

    def update_file(self, label, file_path):
        if file_path:
            file_name = os.path.basename(file_path)
            label.setText(file_name)
            if label == self.file1_label:
                self.file1 = file_path
            else:
                self.file2 = file_path
            self.selected_files.add(file_name)
            self.statusBar().showMessage(f'File selected: {file_path}')
            self.disable_file_in_list(file_name)
        else:
            if label == self.file1_label:
                if self.file1:
                    self.selected_files.discard(os.path.basename(self.file1))
                self.file1 = None
            else:
                if self.file2:
                    self.selected_files.discard(os.path.basename(self.file2))
                self.file2 = None
            label.setText("Drag and drop PDF file here")
            self.statusBar().showMessage('File removed')
            self.enable_file_in_list(label.text())
        self.update_file_list()

    def handle_label_cleared(self, file_name):
        if file_name != "Drag and drop PDF file here":
            self.enable_file_in_list(file_name)
            if file_name in self.selected_files:
                self.selected_files.remove(file_name)
            self.update_file_list()

    def disable_file_in_list(self, file_name):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.text() == file_name:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                break

    def enable_file_in_list(self, file_name):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.text() == file_name:
                item.setFlags(item.flags() | Qt.ItemIsEnabled)
                break
        if file_name in self.selected_files:
            self.selected_files.remove(file_name)

    def update_file_list(self):
        self.file_list.clear()
        pdf_files = [f for f in os.listdir(self.output_dir) if f.lower().endswith('.pdf')]
        for file in pdf_files:
            item = QListWidgetItem(file)
            if file in self.selected_files:
                item.setForeground(QBrush(QColor("#888888")))
            self.file_list.addItem(item)

    def run_diff(self):
        if self.file1 and self.file2:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file1_name = os.path.splitext(os.path.basename(self.file1))[0]
            file2_name = os.path.splitext(os.path.basename(self.file2))[0]
            output_file = os.path.join(self.output_dir, f"diff_{file1_name}_vs_{file2_name}_{timestamp}.pdf")

            cmd = [self.diff_exe_path, f"--output-diff={output_file}", self.file1, self.file2]
            self.statusBar().showMessage('Comparing PDFs...')
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if os.path.exists(output_file):
                    self.statusBar().showMessage(f'Comparison completed. Output saved to {output_file}')
                    logging.info(f"Diff completed successfully. Output saved to {output_file}")
                    logging.debug(f"Command output: {result.stdout}")
                    if result.returncode != 0:
                        logging.info(f"diff-pdf exited with code {result.returncode}, which may indicate differences were found.")
                    
                    # Update the file list
                    self.update_file_list()
                    
                    # Open the folder containing the diff file in Explorer
                    try:
                        os.startfile(self.output_dir)
                        logging.info(f"Opened folder containing diff file: {self.output_dir}")
                    except Exception as e:
                        logging.error(f"Error opening folder: {e}")
                        self.statusBar().showMessage(f'Unable to open folder containing diff file: {e}')
                else:
                    raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            except subprocess.CalledProcessError as e:
                error_msg = f'Error comparing: {e}'
                self.statusBar().showMessage(error_msg)
                logging.error(f"Error running diff: {e}")
                logging.error(f"Error output: {e.stderr}")
        else:
            msg = 'Please select two PDF files first'
            self.statusBar().showMessage(msg)
            logging.warning(msg)

    def view_diff(self):
        if self.file1 and self.file2:
            cmd = [self.diff_exe_path, "--view", self.file1, self.file2]
            self.statusBar().showMessage('Opening diff viewer...')
            try:
                subprocess.Popen(cmd)
                logging.info(f"Opened diff viewer for {self.file1} and {self.file2}")
            except Exception as e:
                error_msg = f'Error opening diff viewer: {e}'
                self.statusBar().showMessage(error_msg)
                logging.error(f"Error opening diff viewer: {e}")
        else:
            msg = 'Please select two PDF files first'
            self.statusBar().showMessage(msg)
            logging.warning(msg)

    def add_pdf_file(self, label):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select PDF file", "", "PDF Files (*.pdf)")
        if file_path:
            self.update_file(label, file_path)

if __name__ == "__main__":
    import qdarktheme
    from PySide6.QtGui import QIcon
    app = QApplication(sys.argv)
    try:
        qdarktheme.setup_theme("light")
    except Exception as e:
        print(e)
    ex = DiffPDFApp()
    icon_path = os.path.join(os.path.dirname(__file__),'resources', "icon.ico")
    ex.setWindowIcon(QIcon(icon_path))
    ex.show()
    sys.exit(app.exec())