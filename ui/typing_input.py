"""Typing input that distinguishes user edits from display/programmatic changes."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QTextEdit


class TypingInput(QTextEdit):
    # Emitted after an input event, before the main window checks completion.
    user_edited = pyqtSignal(object)
    answer_imported = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editing = False
        self._insertions = []
        self.document().contentsChange.connect(self._capture_insertion)

    def _capture_insertion(self, position, removed, added):
        if not self.editing or not added:
            return
        # Qt offsets count UTF-16 units; Python indexes count Unicode characters.
        raw = self.toPlainText().encode("utf-16-le")
        prefix = raw[:position * 2].decode("utf-16-le")
        inserted = raw[position * 2:(position + added) * 2].decode("utf-16-le")
        if inserted:
            self._insertions.append((len(prefix), inserted))

    def _edit(self, handler, event):
        self.editing = True
        self._insertions = []
        try:
            handler(event)
        finally:
            self.editing = False
        self.user_edited.emit(self._insertions)

    def keyPressEvent(self, event):
        # Undo/redo restore text rather than constitute fresh typing attempts.
        if event.matches(QKeySequence.StandardKey.Undo) or event.matches(QKeySequence.StandardKey.Redo):
            super().keyPressEvent(event)
            return
        self._edit(super().keyPressEvent, event)

    def inputMethodEvent(self, event):
        self._edit(super().inputMethodEvent, event)

    def insertFromMimeData(self, source):
        if source.hasText() and not self.isReadOnly():
            self.answer_imported.emit()
        super().insertFromMimeData(source)

    def dropEvent(self, event):
        if not self.isReadOnly():
            self.answer_imported.emit()
        super().dropEvent(event)
