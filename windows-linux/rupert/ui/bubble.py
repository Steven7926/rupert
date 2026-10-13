from __future__ import annotations

import html
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QTextEdit, QToolButton, QWidget

from rupert.ui.common import THEMES, WINDOW_FLAGS, color, mono_font

if TYPE_CHECKING:
    from rupert.ui.controller import Controller


class GrowInput(QTextEdit):

    returnPressed = Signal()
    heightChanged = Signal()
    MAX_LINES = 5

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.document().setDocumentMargin(1)
        self.setTabChangesFocus(True)
        self._height = 0
        self.textChanged.connect(self._grow)

    def text(self) -> str:
        return self.toPlainText()

    def line_height(self) -> int:
        return QFontMetrics(self.font()).lineSpacing()

    def wanted_height(self) -> int:
        doc = self.document().clone()
        doc.setTextWidth(max(10, self.viewport().width()))
        lh = self.line_height()
        return max(lh + 4, min(int(doc.size().height()) + 2, lh * self.MAX_LINES + 4))

    def _grow(self) -> None:
        h = self.wanted_height()
        if h != self._height:
            self._height = h
            over = self.document().size().height() > h
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if over else Qt.ScrollBarAlwaysOff)
            self.heightChanged.emit()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._grow()

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if e.modifiers() & Qt.ShiftModifier:
                self.insertPlainText("\n")
            else:
                self.returnPressed.emit()
            return
        if e.key() == Qt.Key_Escape:
            e.ignore()
            return
        super().keyPressEvent(e)


class Bubble(QWidget):
    WIDTH, TAIL = 300, 10
    EDGE = 14
    GAP = 10
    WELL_PAD = 3
    PROMPT_ROOM = 18

    def __init__(self, ctl: Controller):
        super().__init__(None, WINDOW_FLAGS)
        self.ctl = ctl
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.tail_down = True
        self.tail_x = 250.0
        self.theme = THEMES["light"]
        self.raw: tuple[str, str | None] = ("", None)
        self.cmd_line = 0
        self.copied = False
        self.input = GrowInput(self)
        self.input.setFont(mono_font())
        self.input.heightChanged.connect(self.grew)
        self.answer = QLabel(self)
        self.answer.setFont(mono_font())
        self.answer.setWordWrap(True)
        self.answer.setTextFormat(Qt.RichText)
        self.answer.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.clip = QToolButton(self)
        self.clip.setAutoRaise(True)
        self.clip.setCursor(Qt.PointingHandCursor)
        self.clip.setToolTip("Copy command")
        self.clip.setFixedSize(20, 20)
        self.clip.setIconSize(QSize(14, 14))
        self.clip.hide()
        self.apply_theme("light")

    def apply_theme(self, name: str) -> None:
        t = self.theme = THEMES[name]
        self.input.setStyleSheet(
            f"background: transparent; color: {t['text']}; selection-background-color: {t['chip']};"
            f" selection-color: {t['chip_text']};")
        pal = self.input.palette()
        pal.setColor(QPalette.PlaceholderText, color(t["muted"]))
        self.input.setPalette(pal)
        self.answer.setStyleSheet(f"color: {t['text']}; background: transparent;")
        self.clip.setStyleSheet(
            f"QToolButton {{ border: none; border-radius: 5px; background: transparent; }}"
            f" QToolButton:hover {{ background: {t['button']}; }}")
        self.show_copied(self.copied)
        self.set_answer(*self.raw)

    def show_copied(self, done: bool) -> None:
        self.copied = done
        pm = QPixmap(28, 28)
        pm.setDevicePixelRatio(2)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color(self.theme["accent"]), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        if done:
            p.drawPolyline([QPointF(2.5, 7.5), QPointF(5.5, 10.5), QPointF(11.5, 3.5)])
        else:
            p.drawRoundedRect(QRectF(2.5, 2.5, 9, 10.5), 1.8, 1.8)
            p.setBrush(color(self.theme["paper"]))
            p.drawRoundedRect(QRectF(4.8, 1, 4.4, 3), 1, 1)
            p.drawLine(QPointF(4.8, 7), QPointF(9.2, 7))
            p.drawLine(QPointF(4.8, 9.6), QPointF(8, 9.6))
        p.end()
        self.clip.setIcon(QIcon(pm))

    def set_answer(self, text: str, command: str | None = None) -> None:
        self.raw = (text, command)
        self.cmd_line = 0
        lines = text.split("\n")
        if command and len(lines) > 1:
            lines = lines[1:] + lines[:1]
            self.cmd_line = len(lines) - 1
        escaped = [html.escape(line) for line in lines]
        if command:
            c = html.escape(command)
            gap = "&nbsp;" * 4
            escaped[self.cmd_line] = escaped[self.cmd_line].replace(
                c, f'<span style="background:{self.theme["chip"]}; color:{self.theme["chip_text"]};'
                   f' font-weight:bold">&nbsp;{c}&nbsp;</span>{gap}', 1)
        self.answer.setText("<br>".join(escaped) if text else "")
        self.relayout()

    @property
    def content_width(self) -> int:
        return self.WIDTH - 2 * self.EDGE

    def relayout(self) -> None:
        edge, inner = self.EDGE, self.content_width
        cmd = self.raw[1] if not self.clip.isHidden() else None
        clip_x = None
        answer_w = inner
        if cmd:
            bold = QFont(mono_font())
            bold.setBold(True)
            chip_w = QFontMetrics(bold).horizontalAdvance(f" {cmd} ")
            if chip_w + 24 <= inner:
                clip_x = edge + chip_w + 3
            else:
                answer_w = inner - 22
                clip_x = edge + answer_w + 2
        answer_h = 0
        if self.answer.text():
            self.answer.setFixedWidth(answer_w)
            answer_h = max(self.answer.heightForWidth(answer_w), self.answer.sizeHint().height())
        input_h = self.input.wanted_height()
        well_h = input_h + 2 * self.WELL_PAD
        answer_block = answer_h + self.GAP if answer_h else 0
        self.setFixedSize(self.WIDTH, edge + answer_block + well_h + edge + self.TAIL)
        top = 0 if self.tail_down else self.TAIL
        self.answer.setGeometry(edge, top + edge, answer_w, answer_h)
        self.input.setGeometry(edge + self.PROMPT_ROOM, top + edge + answer_block + self.WELL_PAD,
                               inner - self.PROMPT_ROOM - 4, input_h)
        if clip_x is not None:
            fm = QFontMetrics(mono_font())
            y = top + edge + self.cmd_line * fm.lineSpacing() + (fm.height() - 20) / 2
            self.clip.move(int(clip_x), int(y))
        self.answer.setVisible(answer_h > 0)
        self.update()

    def grew(self) -> None:
        self.relayout()
        self.ctl.position_bubble()

    def set_tail(self, down: bool, x: float) -> None:
        if down != self.tail_down:
            self.tail_down = down
            self.relayout()
        self.tail_x = x
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self.theme
        top = 0 if self.tail_down else self.TAIL
        body = QRectF(1.5, top + 1.5, self.WIDTH - 3, self.height() - self.TAIL - 3)
        shape = QPainterPath()
        shape.addRoundedRect(body, 10, 10)
        tx = min(max(self.tail_x, 22), self.WIDTH - 22)
        edge = body.bottom() if self.tail_down else body.top()
        tip = edge + self.TAIL - 1.5 if self.tail_down else edge - self.TAIL + 1.5
        inset = -1 if self.tail_down else 1
        tail = QPainterPath()
        tail.moveTo(tx - 9, edge + inset)
        tail.lineTo(tx, tip)
        tail.lineTo(tx + 9, edge + inset)
        tail.closeSubpath()
        shape = shape.united(tail)
        p.fillPath(shape, color(t["paper"]))
        pen = QPen(color(t["border"]), 3)
        pen.setJoinStyle(Qt.RoundJoin)
        p.strokePath(shape, pen)
        g = self.input.geometry()
        well = QRectF(self.EDGE, g.y() - self.WELL_PAD, self.content_width, g.height() + 2 * self.WELL_PAD)
        p.setBrush(color(t["field"]))
        p.setPen(QPen(color(t["accent"] if self.input.hasFocus() else t["field_edge"]), 1.5))
        p.drawRoundedRect(well, 7, 7)
        p.setPen(color(t["accent"]))
        prompt_font = QFont(mono_font())
        prompt_font.setBold(True)
        p.setFont(prompt_font)
        lh = self.input.line_height() + 4
        p.drawText(QRectF(self.EDGE + 4, g.y(), 14, lh), Qt.AlignVCenter | Qt.AlignLeft, "›")

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Escape:
            self.ctl.close_bubble()
        else:
            super().keyPressEvent(e)

    def changeEvent(self, e) -> None:
        if e.type() == QEvent.ActivationChange and self.isVisible() and not self.isActiveWindow():
            QTimer.singleShot(0, self.ctl.close_if_inactive)
        super().changeEvent(e)
