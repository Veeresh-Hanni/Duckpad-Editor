import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog, 
    QAction, QMessageBox, QFontDialog, QStatusBar, QWidget,
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox
)
from PyQt5.QtGui import QFont, QColor, QPainter, QKeySequence,QIcon, QTextDocument, QTextCursor
from PyQt5.QtCore import Qt, QRect, QSize, QTimer

DEVELOPER_NAME = "Veeresh Hanni"
APP_NAME = "DuckPad Editor"
APP_VERSION = "1.0.0"
MAX_RECENT_FILES = 5


class LineNumberArea(QWidget):
    """Sidebar widget to display line numbers."""
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Text editor with custom line numbers and mouse wheel zoom."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks //= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def wheelEvent(self, event):
        """Ctrl + Wheel Zoom."""
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn(1)
            else:
                self.zoomOut(1)
            event.accept()
        else:
            super().wheelEvent(event)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        
        is_dark = getattr(self, "is_dark_mode", False)
        bg_color = QColor(40, 44, 52) if is_dark else QColor(240, 240, 240)
        text_color = QColor(120, 120, 120) if is_dark else QColor(150, 150, 150)
        
        painter.fillRect(event.rect(), bg_color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(text_color)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, top, self.line_number_area.width() - 5, 
                    self.fontMetrics().height(), Qt.AlignRight, number
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class FindReplaceDialog(QDialog):
    """Find and Replace modal dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = parent.text_edit
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Find and Replace")
        self.setFixedSize(350, 150)

        layout = QVBoxLayout()

        # Find input
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        # Replace input
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        # Options
        self.match_case = QCheckBox("Match Case")
        layout.addWidget(self.match_case)

        # Buttons
        btn_layout = QHBoxLayout()
        find_btn = QPushButton("Find Next")
        find_btn.clicked.connect(self.find_next)
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.replace)
        replace_all_btn = QPushButton("Replace All")
        replace_all_btn.clicked.connect(self.replace_all)

        btn_layout.addWidget(find_btn)
        btn_layout.addWidget(replace_btn)
        btn_layout.addWidget(replace_all_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def get_flags(self):
        flags = QTextDocument.FindFlags()
        if self.match_case.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return
        found = self.editor.find(text, self.get_flags())
        if not found:
            # Wrap around to start
            self.editor.moveCursor(QTextCursor.Start)
            found = self.editor.find(text, self.get_flags())
            if not found:
                QMessageBox.information(self, "Find", f"Cannot find '{text}'")

    def replace(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not text:
            return
        
        self.editor.moveCursor(QTextCursor.Start)
        count = 0
        while self.editor.find(text, self.get_flags()):
            cursor = self.editor.textCursor()
            cursor.insertText(replace_text)
            count += 1
            
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrence(s).")


class DuckPad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.is_dark_mode = False
        self.default_font_size = 11
        self.recent_files = []
        self.setWindowIcon(QIcon("duckpad.png"))
        self.init_ui()
        self.setup_autosave()

    def init_ui(self):
        self.update_title()
        self.setGeometry(100, 100, 950, 650)

        # Main editor component
        self.text_edit = CodeEditor(self)
        self.setCentralWidget(self.text_edit)

        # Font configuration
        font = QFont("Consolas", self.default_font_size)
        self.text_edit.setFont(font)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.text_edit.textChanged.connect(self.update_status)
        self.text_edit.cursorPositionChanged.connect(self.update_status)

        self.create_actions()
        self.create_menus()
        
        self.apply_theme()
        self.update_status()

    def update_title(self):
        filename = os.path.basename(self.current_file) if self.current_file else "Untitled"
        self.setWindowTitle(f"{filename} - {APP_NAME} | Dev: {DEVELOPER_NAME}")

    def create_actions(self):
        # File Actions
        self.new_action = QAction("&New", self, shortcut="Ctrl+N", triggered=self.new_file)
        self.open_action = QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open_file)
        self.save_action = QAction("&Save", self, shortcut="Ctrl+S", triggered=self.save_file)
        self.save_as_action = QAction("Save &As...", self, shortcut="Ctrl+Shift+S", triggered=self.save_file_as)
        self.exit_action = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)

        # Edit Actions
        self.undo_action = QAction("&Undo", self, shortcut="Ctrl+Z", triggered=self.text_edit.undo)
        self.redo_action = QAction("&Redo", self, shortcut="Ctrl+Y", triggered=self.text_edit.redo)
        self.cut_action = QAction("Cu&t", self, shortcut="Ctrl+X", triggered=self.text_edit.cut)
        self.copy_action = QAction("&Copy", self, shortcut="Ctrl+C", triggered=self.text_edit.copy)
        self.paste_action = QAction("&Paste", self, shortcut="Ctrl+V", triggered=self.text_edit.paste)
        self.find_action = QAction("&Find and Replace...", self, shortcut="Ctrl+F", triggered=self.show_find_dialog)

        # View & Format Actions
        self.font_action = QAction("&Font...", self, triggered=self.change_font)
        self.word_wrap_action = QAction("Word &Wrap", self, checkable=True)
        self.word_wrap_action.setChecked(True)
        self.word_wrap_action.triggered.connect(self.toggle_word_wrap)

        self.zoom_in_action = QAction("Zoom &In", self, shortcut=QKeySequence.ZoomIn, triggered=lambda: self.text_edit.zoomIn(1))
        self.zoom_out_action = QAction("Zoom &Out", self, shortcut=QKeySequence.ZoomOut, triggered=lambda: self.text_edit.zoomOut(1))
        self.reset_zoom_action = QAction("&Reset Zoom", self, shortcut="Ctrl+0", triggered=self.reset_zoom)

        self.dark_mode_action = QAction("Toggle Dark Mode", self, checkable=True, triggered=self.toggle_dark_mode)

        # Help Actions
        self.about_action = QAction(f"About {APP_NAME}", self, triggered=self.show_about_dialog)

    def create_menus(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addActions([self.new_action, self.open_action, self.save_action, self.save_as_action])
        
        self.recent_menu = file_menu.addMenu("Recent Files")
        self.update_recent_files_menu()

        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addActions([self.undo_action, self.redo_action])
        edit_menu.addSeparator()
        edit_menu.addActions([self.cut_action, self.copy_action, self.paste_action])
        edit_menu.addSeparator()
        edit_menu.addAction(self.find_action)

        # Format Menu
        format_menu = menu_bar.addMenu("F&ormat")
        format_menu.addAction(self.font_action)
        format_menu.addAction(self.word_wrap_action)

        # View Menu
        view_menu = menu_bar.addMenu("&View")
        view_menu.addActions([self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action])
        view_menu.addSeparator()
        view_menu.addAction(self.dark_mode_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def setup_autosave(self):
        """Auto-saves the file every 30 seconds if a file is active."""
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.auto_save_file)
        self.autosave_timer.start(30000)

    def auto_save_file(self):
        if self.current_file and self.text_edit.document().isModified():
            self.save_file()
            self.status_bar.showMessage("Auto-saved successfully", 3000)

    # File Operations
    def new_file(self):
        if self.maybe_save():
            self.text_edit.clear()
            self.current_file = None
            self.update_title()

    def open_file(self):
        if self.maybe_save():
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
            if file_path:
                self.load_file(file_path)

    def load_file(self, file_path):
        content = None
        # Try UTF-8 first (with BOM handling), then fall back to common encodings
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {e}")
                return

        if content is None:
            QMessageBox.critical(self, "Error", "Could not decode this file with any supported encoding.")
            return

        self.text_edit.setPlainText(content)
        self.current_file = file_path
        self.update_title()
        self.add_recent_file(file_path)
        self.text_edit.document().setModified(False)


    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.text_edit.toPlainText())
                self.text_edit.document().setModified(False)
                self.status_bar.showMessage("File Saved", 2000)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")
                return False
        else:
            return self.save_file_as()

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.current_file = file_path
            self.update_title()
            self.add_recent_file(file_path)
            return self.save_file()
        return False

    def maybe_save(self):
        if not self.text_edit.document().isModified():
            return True
        ret = QMessageBox.warning(
            self, APP_NAME,
            "The document has been modified.\nDo you want to save your changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        if ret == QMessageBox.Save:
            return self.save_file()
        elif ret == QMessageBox.Cancel:
            return False
        return True

    def add_recent_file(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        if len(self.recent_files) > MAX_RECENT_FILES:
            self.recent_files.pop()
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        self.recent_menu.clear()
        for path in self.recent_files:
            action = QAction(os.path.basename(path), self)
            action.setData(path)
            action.triggered.connect(lambda checked, p=path: self.load_file(p))
            self.recent_menu.addAction(action)

    # Actions & Dialogs
    def show_find_dialog(self):
        dialog = FindReplaceDialog(self)
        dialog.exec_()

    def change_font(self):
        font, ok = QFontDialog.getFont(self.text_edit.font(), self)
        if ok:
            self.text_edit.setFont(font)

    def toggle_word_wrap(self):
        mode = QPlainTextEdit.WidgetWidth if self.word_wrap_action.isChecked() else QPlainTextEdit.NoWrap
        self.text_edit.setLineWrapMode(mode)

    def reset_zoom(self):
        font = self.text_edit.font()
        font.setPointSize(self.default_font_size)
        self.text_edit.setFont(font)

    def toggle_dark_mode(self):
        self.is_dark_mode = self.dark_mode_action.isChecked()
        self.apply_theme()

    def apply_theme(self):
        self.text_edit.is_dark_mode = self.is_dark_mode
        if self.is_dark_mode:
            dark_stylesheet = """
                QMainWindow, QMenuBar, QMenu, QStatusBar, QDialog {
                    background-color: #21252b;
                    color: #abb2bf;
                }
                QPlainTextEdit {
                    background-color: #282c34;
                    color: #abb2bf;
                    selection-background-color: #3e4451;
                    border: none;
                }
                QMenuBar::item:selected, QMenu::item:selected {
                    background-color: #3e4451;
                }
                QLineEdit {
                    background-color: #282c34;
                    color: #abb2bf;
                    border: 1px solid #3e4451;
                }
                QPushButton {
                    background-color: #3e4451;
                    color: #abb2bf;
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #4b5263;
                }
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet("")

        self.text_edit.line_number_area.update()

    def show_about_dialog(self):
        about_text = f"""
        <h2>{APP_NAME} v{APP_VERSION}</h2>
        <p>A full-featured cross-platform text editor built with PyQt5.</p>
        <hr>
        <p><b>Developer:</b> {DEVELOPER_NAME}</p>
        <p><b>Copyright:</b> © {DEVELOPER_NAME}. All Rights Reserved.</p>
        """
        QMessageBox.about(self, f"About {APP_NAME}", about_text)

    def update_status(self):
        text = self.text_edit.toPlainText()
        chars = len(text)
        words = len(text.split())
        lines = self.text_edit.blockCount()

        cursor = self.text_edit.textCursor()
        line_num = cursor.blockNumber() + 1
        col_num = cursor.columnNumber() + 1

        self.status_bar.showMessage(
            f"Line: {line_num}, Col: {col_num}  |  Total Lines: {lines}  |  Words: {words}  |  Chars: {chars}"
        )

    def closeEvent(self, event):
        if self.maybe_save():
            QApplication.quit()
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DuckPad()
    editor.show()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path):
            editor.load_file(file_path)

    sys.exit(app.exec_())