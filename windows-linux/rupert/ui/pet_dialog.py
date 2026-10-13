from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from rupert.paths import HOME
from rupert.pets import BREEDS, breed_template, paint_breed, personalities_for, personality
from rupert.sprites import normalize_sprite
from rupert.ui.common import sprite_pixmap

IMAGE_FILTER = "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif)"
MAX_NAME = 24


class PetDialog(QDialog):
    def __init__(self, existing: dict[str, Any] | None = None):
        super().__init__(None)
        self.existing = existing or {}
        self.photo = ""
        self.setWindowTitle(f"Edit {existing['name']}" if existing else "New pet")
        self.setMinimumWidth(420)
        self._build()
        e = self.existing
        if e.get("kind") == "breed":
            self.use_breed.setChecked(True)
            self.breed.setCurrentIndex(max(0, self.breed.findData(e.get("breed"))))
        elif e:
            self.use_photo.setChecked(True)
        else:
            self.use_breed.setChecked(True)
        self._fill_colors(e.get("color"))
        self._fill_personalities(e.get("personality") if e.get("kind") == "breed" else e.get("preset", ""))
        self.use_photo.toggled.connect(lambda _: (self._fill_personalities(), self.refresh()))
        self.breed.currentIndexChanged.connect(
            lambda _: (self._fill_colors(), self._fill_personalities(), self.refresh()))
        self.color.currentIndexChanged.connect(lambda _: self.refresh())
        self.pers.currentIndexChanged.connect(lambda _: self.refresh())
        self.name.textChanged.connect(lambda _: self.refresh())
        self.refresh()

    def _build(self) -> None:
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(110)
        self.preview.setStyleSheet("QLabel { background: #2e2e34; border-radius: 8px; color: #b8b8c0; }")
        form = self.form = QFormLayout()
        self.name = QLineEdit(self.existing.get("name", ""))
        self.name.setPlaceholderText("e.g. Biscuit")
        self.name.setMaxLength(MAX_NAME)
        form.addRow("Name", self.name)
        self.use_photo = QRadioButton("Upload a photo")
        self.use_breed = QRadioButton("Pick a breed and color")
        look = QHBoxLayout()
        look.addWidget(self.use_photo)
        look.addWidget(self.use_breed)
        form.addRow("Look", look)
        self.photo_btn = QPushButton("Choose photo…")
        self.photo_btn.clicked.connect(self._choose_photo)
        self.photo_label = QLabel("")
        self.photo_label.setStyleSheet("color: gray")
        photo_row = QHBoxLayout()
        photo_row.setContentsMargins(0, 0, 0, 0)
        photo_row.addWidget(self.photo_btn)
        photo_row.addWidget(self.photo_label, 1)
        self.photo_row = QWidget()
        self.photo_row.setLayout(photo_row)
        form.addRow("Photo", self.photo_row)
        self.breed = QComboBox()
        for b in BREEDS:
            self.breed.addItem(b["name"], b["id"])
        self.color = QComboBox()
        form.addRow("Breed", self.breed)
        form.addRow("Color", self.color)
        self.pers = QComboBox()
        form.addRow("Personality", self.pers)
        self.blurb = QLabel()
        self.blurb.setWordWrap(True)
        self.blurb.setStyleSheet("color: gray")
        form.addRow("", self.blurb)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok = buttons.button(QDialogButtonBox.Ok)
        self.ok.setText("Save" if self.existing else "Add pet")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box = QVBoxLayout(self)
        box.addWidget(self.preview)
        box.addLayout(form)
        box.addWidget(buttons)

    def _template(self) -> dict[str, Any]:
        return breed_template(self.breed.currentData())

    def _fill_colors(self, keep: str | None = None) -> None:
        keep = keep or self.color.currentData()
        self.color.blockSignals(True)
        self.color.clear()
        for c in self._template()["colors"]:
            self.color.addItem(c["name"], c["id"])
        self.color.setCurrentIndex(max(0, self.color.findData(keep)))
        self.color.blockSignals(False)

    def _fill_personalities(self, keep: str | None = None) -> None:
        photo = self.use_photo.isChecked()
        keep = self.pers.currentData() if keep is None else keep
        t = self._template()
        self.pers.blockSignals(True)
        self.pers.clear()
        if photo:
            self.pers.addItem("Guess from the photo", "")
        for p in personalities_for("" if photo else t["animal"]):
            self.pers.addItem(p["name"], p["id"])
        i = self.pers.findData(keep)
        if i < 0:
            i = 0 if photo else max(0, self.pers.findData(t["default"]))
        self.pers.setCurrentIndex(i)
        self.pers.blockSignals(False)

    def _choose_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Photo of your pet", str(HOME), IMAGE_FILTER)
        if path:
            self.photo = path
            self.photo_label.setText(os.path.basename(path))
            self.refresh()

    def _preview_sprite(self, photo: bool, keeps_drawing: bool) -> dict[str, Any] | None:
        try:
            if not photo:
                return normalize_sprite(paint_breed(self.breed.currentData(), self.color.currentData()))
            if keeps_drawing:
                return normalize_sprite(self.existing["sprite"])
        except ValueError:
            pass
        return None

    def refresh(self) -> None:
        photo = self.use_photo.isChecked()
        for w, show in ((self.photo_row, photo), (self.breed, not photo), (self.color, not photo)):
            self.form.setRowVisible(w, show)
        keeps_drawing = photo and not self.photo and "sprite" in self.existing
        if photo and not self.photo:
            self.photo_label.setText("keeps the current drawing" if keeps_drawing else "")
        p = personality(self.pers.currentData())
        self.blurb.setText(p["text"] if p else "The AI picks a personality from the photo.")
        sprite = self._preview_sprite(photo, keeps_drawing)
        if sprite:
            px = max(2, min(4, int(150 / sprite["w"])))
            lying, walking = sprite_pixmap(sprite, "awake", px), sprite_pixmap(sprite, "walk", px)
            pm = QPixmap(lying.width() + walking.width() + 24, max(lying.height(), walking.height()))
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            painter.drawPixmap(0, pm.height() - lying.height(), lying)
            painter.drawPixmap(lying.width() + 24, pm.height() - walking.height(), walking)
            painter.end()
            self.preview.setPixmap(pm)
        else:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Drawn by AI from your photo")
        self.ok.setEnabled(bool(self.name.text().strip()) and (not photo or bool(self.photo) or keeps_drawing))

    def result_pet(self) -> dict[str, Any]:
        return dict(name=" ".join(self.name.text().split())[:MAX_NAME],
                    photo=self.photo if self.use_photo.isChecked() else "",
                    from_breed=self.use_breed.isChecked(),
                    breed=self.breed.currentData(), color=self.color.currentData(),
                    personality=self.pers.currentData() or "")
