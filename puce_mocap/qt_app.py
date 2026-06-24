"""Interfaz Qt unificada para los módulos PUCE de fisioterapia."""

from __future__ import annotations

from pathlib import Path
import sys
import time
from uuid import uuid4

import numpy as np
from PySide6.QtCore import QProcess, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QImage, QKeySequence, QPixmap, QRegion, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from puce_mocap.camera_worker import CameraPoseWorker, LivePoseResult
from puce_mocap.app_paths import profiles_dir
from puce_mocap.exercise_rules import (
    ESTADO_POSTURA_INCOMPLETA,
    ExerciseFeedback,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)
from puce_mocap.exercise_session import DEFINICIONES_MOVIMIENTO, ExerciseSession
from puce_mocap.freemocap_session import FreeMoCapSessionProvider
from puce_mocap.gait_analyzer import analizar_marcha
from puce_mocap.gait_session import GaitSession
from puce_mocap.gait_temporal import GaitCycleAnalyzer
from puce_mocap.rehab_analyzer import (
    ORIENTACION_RECOMENDADA,
    WristRotationCalibrator,
    evaluar_ejercicio_rehabilitacion,
    resolver_lado_ejercicio,
)
from puce_mocap.movement import AngleRange, MovementDefinition
from puce_mocap.rehab_profiles import (
    cargar_perfil_paciente,
    crear_perfil_demo,
    guardar_perfil_paciente,
    normalizar_perfil_paciente,
)
from puce_mocap.rehab_session import RehabSession
from puce_mocap.reports_v2 import export_gait_session, export_rehab_sessions, export_weight_sessions
from puce_mocap.resources import resource_file
from puce_mocap.skeleton_frame import SkeletonFrame


REPO_ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = "Herramienta de apoyo. No sustituye la evaluación de un fisioterapeuta."
WEIGHT_EXERCISES = ("Sentadilla", "Press de hombro", "Peso muerto")
REHAB_LABELS = {
    "flexion_codo": "Flexión de codo",
    "abduccion_hombro": "Abducción de hombro",
    "rotacion_muneca": "Rotación de muñeca",
    "extension_rodilla": "Extensión de rodilla",
    "dorsiflexion_tobillo": "Dorsiflexión de tobillo",
    "elevacion_pierna_recta": "Elevación de pierna recta",
}
PHASE_LABELS = {
    "calibrando_inicio": "Calibrando inicio",
    "esperando_inicio": "Esperando postura inicial",
    "buscando_objetivo": "Buscando objetivo",
    "regresando_inicio": "Regresando al inicio",
    "inicio": "Posición inicial",
    "objetivo": "Posición objetivo",
    "transicion": "En transición",
    "no_detectado": "No detectado",
}


def _card(title: str) -> tuple[QGroupBox, QVBoxLayout]:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    return box, layout


def _metric(label: str) -> tuple[QWidget, QLabel]:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    title = QLabel(label)
    title.setProperty("muted", True)
    value = QLabel("N/D")
    value.setProperty("metric", True)
    layout.addWidget(title)
    layout.addWidget(value)
    return widget, value


def _angle_spin(value: float = 0.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(-180.0, 180.0)
    spin.setDecimals(1)
    spin.setSingleStep(1.0)
    spin.setSuffix("°")
    spin.setValue(value)
    return spin


def _detected_cameras() -> list[tuple[str, int]]:
    """Enumera dispositivos de vídeo sin probar diez índices de OpenCV."""
    try:
        from PySide6.QtMultimedia import QMediaDevices

        devices = QMediaDevices.videoInputs()
        if devices:
            return [(device.description() or f"Cámara {index + 1}", index) for index, device in enumerate(devices)]
    except (ImportError, RuntimeError):
        pass
    return [("Cámara predeterminada", 0)]


def _phase_text(phase: str) -> str:
    return PHASE_LABELS.get(phase, phase.replace("_", " ").capitalize())


class MenuPage(QWidget):
    open_requested = Signal(str)
    verify_requested = Signal()
    freemocap_requested = Signal()
    exit_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("menuPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 28, 42, 24)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(245)
        hero.setMaximumHeight(300)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 22, 28, 22)
        heading = QVBoxLayout()
        eyebrow = QLabel("VINCULACIÓN CON LA COMUNIDAD · 2026")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Análisis de movimiento\npara fisioterapia")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Herramientas de apoyo para ejercicios, rehabilitación y marcha, "
            "bajo supervisión profesional."
        )
        subtitle.setWordWrap(True)
        heading.addWidget(eyebrow)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        heading.addStretch()
        hero_layout.addLayout(heading, 5)

        identity = QFrame()
        identity.setObjectName("identityPanel")
        identity_layout = QVBoxLayout(identity)
        identity_layout.setContentsMargins(18, 14, 18, 14)
        puce_logo = QLabel("PUCE")
        puce_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(resource_file("assets", "logo_puce.png")))
        if not pixmap.isNull():
            visible_bounds = QRegion(pixmap.mask()).boundingRect()
            if visible_bounds.isValid():
                pixmap = pixmap.copy(visible_bounds)
            puce_logo.setPixmap(
                pixmap.scaled(430, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        identity_layout.addWidget(puce_logo, 1)
        partner_row = QHBoxLayout()
        partner_text = QLabel("En colaboración con")
        partner_text.setObjectName("identityCaption")
        fe_logo = QLabel("Fe y Alegría Ecuador")
        fe_pixmap = QPixmap(str(resource_file("assets", "logo_fe_alegria.png")))
        if not fe_pixmap.isNull():
            fe_logo.setPixmap(
                fe_pixmap.scaled(112, 86, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        partner_row.addWidget(partner_text)
        partner_row.addStretch()
        partner_row.addWidget(fe_logo)
        identity_layout.addLayout(partner_row)
        hero_layout.addWidget(identity, 4)
        layout.addWidget(hero)

        section = QLabel("Seleccione un módulo")
        section.setObjectName("sectionTitle")
        section.setFixedHeight(28)
        layout.addWidget(section)
        module_container = QWidget()
        module_container.setFixedHeight(116)
        grid = QGridLayout(module_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        options = [
            ("pesas", "01", "Ejercicios con pesas", "Sentadilla, press de hombro y peso muerto."),
            ("rehab", "02", "Rehabilitación", "Perfiles, rangos terapéuticos y seguimiento."),
            ("gait", "03", "Análisis de marcha", "Ciclos, simetría y longitud de paso estimada."),
        ]
        for index, (key, number, text, detail) in enumerate(options):
            button = QPushButton(f"{number}   {text}\n       {detail}")
            button.setObjectName("moduleCard")
            button.setProperty("module", key)
            button.setFixedHeight(112)
            button.clicked.connect(lambda _checked=False, page=key: self.open_requested.emit(page))
            grid.addWidget(button, 0, index)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addWidget(module_container)

        tools = QHBoxLayout()
        freemocap = QPushButton("Abrir FreeMoCap original")
        freemocap.setObjectName("secondaryAction")
        freemocap.clicked.connect(self.freemocap_requested)
        verify = QPushButton("Verificar entorno")
        verify.setObjectName("secondaryAction")
        verify.clicked.connect(self.verify_requested)
        close = QPushButton("Salir")
        close.setObjectName("quietAction")
        close.clicked.connect(self.exit_requested)
        tools.addWidget(freemocap)
        tools.addWidget(verify)
        tools.addStretch()
        tools.addWidget(close)
        layout.addLayout(tools)

        self.status = QLabel("Sistema listo. Seleccione un módulo.")
        self.status.setObjectName("menuStatus")
        self.status.setWordWrap(True)
        self.status.setMaximumHeight(58)
        layout.addWidget(self.status)
        footer = QLabel(
            "Pontificia Universidad Católica del Ecuador · Fe y Alegría Ecuador · "
            "Proyecto base FreeMoCap · AGPLv3 · Año 2026\n" + DISCLAIMER
        )
        footer.setProperty("muted", True)
        layout.addWidget(footer)
        layout.addStretch()


class AnalysisPage(QWidget):
    back_requested = Signal()
    camera_requested = Signal(bool)

    def __init__(self, title: str):
        super().__init__()
        self.provider: FreeMoCapSessionProvider | None = None
        self.source_mode = "camera"
        self.camera_active = False
        self.play_index = 0
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._next_frame)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 18)
        root.setSpacing(14)
        header_frame = QFrame()
        header_frame.setObjectName("analysisHeader")
        header = QHBoxLayout(header_frame)
        back = QPushButton("←  Volver al menú")
        back.setObjectName("backButton")
        back.clicked.connect(self._go_back)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        header.addWidget(back)
        header.addWidget(heading, 1)
        root.addWidget(header_frame)

        source_frame = QFrame()
        source_frame.setObjectName("sourceBar")
        source = QHBoxLayout(source_frame)
        source.setContentsMargins(14, 10, 14, 10)
        self.camera_index = QComboBox()
        self.refresh_cameras()
        self.resolution = QComboBox()
        self.resolution.addItem("640 × 480 (rápida)", (640, 480))
        self.resolution.addItem("1280 × 720", (1280, 720))
        self.camera_button = QPushButton("Iniciar cámara")
        self.camera_button.setObjectName("primaryAction")
        self.camera_button.clicked.connect(self.use_camera)
        refresh_button = QPushButton("Actualizar")
        refresh_button.setToolTip("Volver a detectar las cámaras conectadas")
        refresh_button.clicked.connect(self.refresh_cameras)
        import_button = QPushButton("Importar sesión FreeMoCap")
        import_button.clicked.connect(self.import_session)
        self.play_button = QPushButton("Reproducir")
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setEnabled(False)
        source.addWidget(QLabel("Cámara"))
        source.addWidget(self.camera_index)
        source.addWidget(self.resolution)
        source.addWidget(refresh_button)
        source.addWidget(self.camera_button)
        source.addWidget(import_button)
        source.addWidget(self.play_button)
        root.addWidget(source_frame)

        content = QHBoxLayout()
        self.video = QLabel("Cámara inactiva\nSeleccione una fuente para comenzar")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(640, 430)
        self.video.setObjectName("video")
        content.addWidget(self.video, 3)
        control_widget = QWidget()
        self.controls = QVBoxLayout(control_widget)
        self.controls.setContentsMargins(0, 0, 4, 0)
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setFrameShape(QFrame.Shape.NoFrame)
        control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        control_scroll.setWidget(control_widget)
        content.addWidget(control_scroll, 2)
        root.addLayout(content, 1)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._seek_frame)
        root.addWidget(self.slider)
        self.status = QLabel(DISCLAIMER)
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def activate(self) -> None:
        self.status.setText("Seleccione una cámara o importe una sesión. " + DISCLAIMER)

    def deactivate(self) -> None:
        self.camera_requested.emit(False)
        self.camera_active = False
        self.camera_button.setText("Iniciar cámara")
        self.play_timer.stop()

    def _go_back(self) -> None:
        self.finalize()
        self.back_requested.emit()

    def finalize(self) -> Path | None:
        return None

    def use_camera(self) -> None:
        if self.camera_active:
            self.camera_active = False
            self.camera_requested.emit(False)
            self.camera_button.setText("Iniciar cámara")
            self.video.clear()
            self.video.setText("Cámara detenida")
            self.status.setText("Cámara detenida. " + DISCLAIMER)
            return
        self.source_mode = "camera"
        self.provider = None
        self.play_timer.stop()
        self.play_button.setEnabled(False)
        self.slider.setEnabled(False)
        self.camera_active = True
        self.camera_requested.emit(True)
        self.camera_button.setText("Detener cámara")
        self.status.setText("Abriendo la cámara seleccionada...")

    def refresh_cameras(self) -> None:
        current = self.camera_index.currentData() if hasattr(self, "camera_index") else 0
        if not hasattr(self, "camera_index"):
            return
        self.camera_index.clear()
        for label, index in _detected_cameras():
            self.camera_index.addItem(label, index)
        selected = self.camera_index.findData(current)
        self.camera_index.setCurrentIndex(max(0, selected))

    def import_session(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccione una grabación de FreeMoCap")
        if not folder:
            return
        unit, accepted = QInputDialog.getItem(
            self, "Unidad de calibración", "Unidad espacial:", ["sin_especificar", "mm", "cm", "m"], 0, False
        )
        if not accepted:
            return
        try:
            self.provider = FreeMoCapSessionProvider(folder, unit)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Sesión no válida", str(exc))
            return
        self.source_mode = "freemocap"
        self.camera_active = False
        self.camera_button.setText("Iniciar cámara")
        self.camera_requested.emit(False)
        self.play_index = 0
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, self.provider.frame_count - 1))
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.slider.setEnabled(True)
        self.play_button.setEnabled(True)
        self.status.setText(f"Sesión FreeMoCap cargada: {self.provider.frame_count} fotogramas; unidad {unit}.")
        self._show_provider_frame(0)

    def toggle_playback(self) -> None:
        if self.provider is None:
            return
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setText("Reproducir")
        else:
            self.play_timer.start(10)
            self.play_button.setText("Pausar")

    def _next_frame(self) -> None:
        if self.provider is None:
            return
        if self.play_index >= self.provider.frame_count:
            self.play_timer.stop()
            self.play_button.setText("Reproducir")
            return
        self._show_provider_frame(self.play_index)
        self.slider.blockSignals(True)
        self.slider.setValue(self.play_index)
        self.slider.blockSignals(False)
        self.play_index += 1

    def _seek_frame(self, index: int) -> None:
        if self.provider is not None and not self.play_timer.isActive():
            self.play_index = index
            self._show_provider_frame(index)

    def _show_provider_frame(self, index: int) -> None:
        assert self.provider is not None
        frame = self.provider.get_frame(index)
        self.video.setText(f"Sesión FreeMoCap\nFotograma {index + 1} / {self.provider.frame_count}\n{frame.length_unit}")
        self.process_skeleton(frame)

    def on_live_result(self, result: LivePoseResult) -> None:
        if self.source_mode != "camera":
            return
        image = np.asarray(result.image_rgb)
        height, width, channels = image.shape
        qimage = QImage(image.data, width, height, channels * width, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.video.setPixmap(pixmap)
        self.process_skeleton(result.skeleton)

    def process_skeleton(self, frame: SkeletonFrame) -> None:
        raise NotImplementedError


class WeightsPage(AnalysisPage):
    def __init__(self):
        super().__init__("Módulo 1 · Ejercicios con pesas")
        self.session_id = uuid4().hex
        self.definitions = {name: definition for name, (_angle, definition) in DEFINICIONES_MOVIMIENTO.items()}
        self.sessions = {
            name: ExerciseSession(name, session_id=self.session_id, definicion=self.definitions[name])
            for name in WEIGHT_EXERCISES
        }
        self.dirty = False
        self.recording = False
        selector_box, selector_layout = _card("Ejercicio")
        self.selector = QComboBox()
        self.selector.addItems(WEIGHT_EXERCISES)
        self.selector.currentTextChanged.connect(self._exercise_changed)
        selector_layout.addWidget(self.selector)
        self.view_hint = QLabel("Vista lateral recomendada para sentadilla y peso muerto.")
        self.view_hint.setProperty("muted", True)
        self.view_hint.setWordWrap(True)
        selector_layout.addWidget(self.view_hint)
        self.controls.addWidget(selector_box)

        patient_box, patient_layout = _card("Datos del paciente para el reporte")
        patient_grid = QGridLayout()
        self.weight_patient_name = QLineEdit("Paciente de prueba")
        self.weight_patient_code = QLineEdit("PAC-001")
        self.weight_patient_condition = QLineEdit("Seguimiento general ficticio")
        self.weight_patient_notes = QLineEdit("Sin datos reales")
        patient_grid.addWidget(QLabel("Nombre"), 0, 0)
        patient_grid.addWidget(QLabel("Código"), 0, 1)
        patient_grid.addWidget(self.weight_patient_name, 1, 0)
        patient_grid.addWidget(self.weight_patient_code, 1, 1)
        patient_grid.addWidget(QLabel("Condición / lesión"), 2, 0)
        patient_grid.addWidget(QLabel("Observaciones"), 2, 1)
        patient_grid.addWidget(self.weight_patient_condition, 3, 0)
        patient_grid.addWidget(self.weight_patient_notes, 3, 1)
        patient_layout.addLayout(patient_grid)
        self.controls.addWidget(patient_box)

        ranges_box, ranges_layout = _card("Rangos configurables")
        ranges_form = QGridLayout()
        self.start_min = _angle_spin()
        self.start_max = _angle_spin()
        self.target_min = _angle_spin()
        self.target_max = _angle_spin()
        ranges_form.addWidget(QLabel("Inicio mínimo"), 0, 0)
        ranges_form.addWidget(self.start_min, 0, 1)
        ranges_form.addWidget(QLabel("Inicio máximo"), 0, 2)
        ranges_form.addWidget(self.start_max, 0, 3)
        ranges_form.addWidget(QLabel("Objetivo mínimo"), 1, 0)
        ranges_form.addWidget(self.target_min, 1, 1)
        ranges_form.addWidget(QLabel("Objetivo máximo"), 1, 2)
        ranges_form.addWidget(self.target_max, 1, 3)
        ranges_layout.addLayout(ranges_form)
        apply_ranges = QPushButton("Aplicar rangos a este ejercicio")
        apply_ranges.clicked.connect(self.apply_ranges)
        ranges_layout.addWidget(apply_ranges)
        self.controls.addWidget(ranges_box)

        metrics = QGridLayout()
        for index, name in enumerate(("Ángulo", "Fase", "Repeticiones", "Postura")):
            widget, label = _metric(name)
            setattr(self, f"metric_{index}", label)
            metrics.addWidget(widget, index // 2, index % 2)
        self.controls.addLayout(metrics)
        self.start_button = QPushButton("Iniciar ejercicio")
        self.start_button.setObjectName("primaryAction")
        self.start_button.clicked.connect(self.toggle_recording)
        self.controls.addWidget(self.start_button)
        reset = QPushButton("Reiniciar ejercicio")
        reset.clicked.connect(self.reset_current)
        self.controls.addWidget(reset)
        save = QPushButton("Finalizar y guardar reporte")
        save.clicked.connect(self.save_and_restart)
        self.controls.addWidget(save)
        self.controls.addStretch()
        QShortcut(QKeySequence("R"), self, activated=self.reset_current)
        self._load_range_editors()

    @property
    def exercise(self) -> str:
        return self.selector.currentText()

    def _exercise_changed(self) -> None:
        self.recording = False
        self.start_button.setText("Iniciar ejercicio")
        self._load_range_editors()
        self.metric_2.setText(str(self.sessions[self.exercise].repeticiones))
        self.metric_1.setText("En espera")
        self.status.setText("Revise los rangos y pulse «Iniciar ejercicio».")

    def _load_range_editors(self) -> None:
        definition = self.definitions[self.exercise]
        self.start_min.setValue(definition.start_range.minimo)
        self.start_max.setValue(definition.start_range.maximo)
        self.target_min.setValue(definition.target_range.minimo)
        self.target_max.setValue(definition.target_range.maximo)

    def apply_ranges(self) -> bool:
        try:
            definition = MovementDefinition(
                start_range=AngleRange(self.start_min.value(), self.start_max.value()),
                target_range=AngleRange(self.target_min.value(), self.target_max.value()),
            )
        except ValueError as exc:
            self.status.setText(f"No se aplicaron los rangos: {exc}")
            return False
        if definition != self.definitions[self.exercise]:
            self.definitions[self.exercise] = definition
            self.sessions[self.exercise].configurar_movimiento(definition)
            self.recording = False
            self.start_button.setText("Iniciar ejercicio")
            self.metric_2.setText("0")
            self.status.setText("Rangos aplicados. Pulse «Iniciar ejercicio» cuando el paciente esté preparado.")
        return True

    def toggle_recording(self) -> None:
        if self.recording:
            self.recording = False
            self.start_button.setText("Continuar ejercicio")
            self.status.setText("Ejercicio en pausa. No se contabilizarán repeticiones.")
            return
        if not all(
            field.text().strip()
            for field in (self.weight_patient_name, self.weight_patient_code, self.weight_patient_condition)
        ):
            self.status.setText("Complete nombre, código y condición del paciente antes de iniciar.")
            return
        if not self.apply_ranges():
            return
        self.recording = True
        self.start_button.setText("Pausar ejercicio")
        self.metric_1.setText("Calibrando inicio")
        self.status.setText("Mantenga una postura inicial cómoda y estable durante un momento.")

    def reset_current(self) -> None:
        self.sessions[self.exercise].reiniciar()
        self.recording = False
        self.start_button.setText("Iniciar ejercicio")
        self.metric_1.setText("En espera")
        self.metric_2.setText("0")
        self.status.setText("Ejercicio reiniciado. Pulse «Iniciar ejercicio» para comenzar.")

    def finalize(self) -> Path | None:
        if not self.dirty:
            return None
        patient = {
            "codigo_paciente": self.weight_patient_code.text().strip(),
            "nombre_paciente": self.weight_patient_name.text().strip(),
            "lesion": self.weight_patient_condition.text().strip(),
            "observaciones_paciente": self.weight_patient_notes.text().strip(),
        }
        path = export_weight_sessions(
            ({**session.exportar_resumen(), **patient} for session in self.sessions.values())
        )
        self.dirty = False
        return path

    def save_and_restart(self) -> None:
        self.recording = False
        self.start_button.setText("Iniciar ejercicio")
        path = self.finalize()
        if path is not None:
            self.status.setText(f"Reporte guardado en {path}.")
        self.session_id = uuid4().hex
        self.sessions = {
            name: ExerciseSession(name, session_id=self.session_id, definicion=self.definitions[name])
            for name in WEIGHT_EXERCISES
        }

    def process_skeleton(self, frame: SkeletonFrame) -> None:
        try:
            if self.exercise == "Sentadilla":
                feedback = evaluar_sentadilla(frame.points)
            elif self.exercise == "Press de hombro":
                feedback = evaluar_press_hombro(frame.points)
            else:
                feedback = evaluar_peso_muerto(frame.points, vista="lateral")
        except ValueError:
            feedback = ExerciseFeedback(
                self.exercise, ESTADO_POSTURA_INCOMPLETA, "rojo", mensajes=["No se detecta postura completa."],
                frame_valido=False,
            )
        session = self.sessions[self.exercise]
        session.fuente_datos = frame.source
        if self.recording:
            feedback = session.registrar_feedback(feedback, frame.timestamp)
            self.dirty = True
        angle_name = feedback.angulo_principal
        angle = feedback.angulos.get(angle_name) if angle_name else None
        self.metric_0.setText("N/D" if angle is None else f"{angle:.1f}°")
        self.metric_1.setText(_phase_text(feedback.fase) if self.recording else "En espera")
        self.metric_2.setText(str(session.repeticiones))
        self.metric_3.setText("Correcta" if feedback.forma_correcta else "N/D" if feedback.forma_correcta is None else "Corregir")
        if self.recording:
            self.status.setText(feedback.mensajes[0] if feedback.mensajes else DISCLAIMER)
        elif feedback.mensajes:
            self.status.setText("Vista previa: " + feedback.mensajes[0] + " Pulse «Iniciar ejercicio» para registrar.")


class RehabPage(AnalysisPage):
    def __init__(self):
        super().__init__("Módulo 2 · Rehabilitación")
        profile_path = resource_file("profiles", "paciente_demo.json")
        self.profile = cargar_perfil_paciente(profile_path) if profile_path.is_file() else crear_perfil_demo()
        self.session_id = uuid4().hex
        self.sessions: dict[str, RehabSession] = {}
        self.calibrator = WristRotationCalibrator()
        self.dirty = False
        self.recording = False
        self.latest_points = {}
        self.latest_confidence = {}
        self.rehab_evaluated_side: str | None = None

        patient_box, patient_layout = _card("Datos del paciente para el reporte")
        patient_grid = QGridLayout()
        self.patient_name = QLineEdit()
        self.patient_code = QLineEdit()
        self.patient_injury = QLineEdit()
        self.patient_notes = QLineEdit()
        patient_grid.addWidget(QLabel("Nombre"), 0, 0)
        patient_grid.addWidget(QLabel("Código"), 0, 1)
        patient_grid.addWidget(self.patient_name, 1, 0)
        patient_grid.addWidget(self.patient_code, 1, 1)
        patient_grid.addWidget(QLabel("Condición / lesión"), 2, 0)
        patient_grid.addWidget(QLabel("Observaciones"), 2, 1)
        patient_grid.addWidget(self.patient_injury, 3, 0)
        patient_grid.addWidget(self.patient_notes, 3, 1)
        patient_layout.addLayout(patient_grid)
        profile_actions = QHBoxLayout()
        load_profile = QPushButton("Cargar perfil")
        load_profile.clicked.connect(self.load_profile)
        save_profile = QPushButton("Guardar perfil")
        save_profile.clicked.connect(self.save_profile)
        profile_actions.addWidget(load_profile)
        profile_actions.addWidget(save_profile)
        patient_layout.addLayout(profile_actions)
        self.controls.addWidget(patient_box)

        box, layout = _card("Configuración terapéutica")
        self.selector = QComboBox()
        for key in self.profile["ejercicios"]:
            self.selector.addItem(REHAB_LABELS[key], key)
        self.selector.currentIndexChanged.connect(self._load_exercise_config)
        layout.addWidget(self.selector)
        config_grid = QGridLayout()
        self.rehab_start_min = _angle_spin()
        self.rehab_start_max = _angle_spin()
        self.rehab_target_min = _angle_spin()
        self.rehab_target_max = _angle_spin()
        self.rehab_repetitions = QSpinBox()
        self.rehab_repetitions.setRange(1, 1000)
        self.rehab_side = QComboBox()
        self.rehab_side.addItem("Automático (mejor visible)", "auto")
        self.rehab_side.addItem("Derecho", "right")
        self.rehab_side.addItem("Izquierdo", "left")
        config_grid.addWidget(QLabel("Inicio guía mín."), 0, 0)
        config_grid.addWidget(self.rehab_start_min, 0, 1)
        config_grid.addWidget(QLabel("Inicio guía máx."), 0, 2)
        config_grid.addWidget(self.rehab_start_max, 0, 3)
        config_grid.addWidget(QLabel("Objetivo mín."), 1, 0)
        config_grid.addWidget(self.rehab_target_min, 1, 1)
        config_grid.addWidget(QLabel("Objetivo máx."), 1, 2)
        config_grid.addWidget(self.rehab_target_max, 1, 3)
        config_grid.addWidget(QLabel("Extremidad evaluada"), 2, 0)
        config_grid.addWidget(self.rehab_side, 2, 1)
        config_grid.addWidget(QLabel("Repeticiones"), 2, 2)
        config_grid.addWidget(self.rehab_repetitions, 2, 3)
        layout.addLayout(config_grid)
        layout.addWidget(
            QLabel(
                "Al iniciar, la postura estable actual se calibra como referencia. "
                "El rango de inicio del perfil es orientativo."
            )
        )
        config_actions = QHBoxLayout()
        apply_config = QPushButton("Aplicar configuración")
        apply_config.clicked.connect(self.apply_profile_changes)
        self.calibrate_button = QPushButton("Calibrar muñeca")
        self.calibrate_button.clicked.connect(self.calibrate_wrist)
        config_actions.addWidget(apply_config)
        config_actions.addWidget(self.calibrate_button)
        layout.addLayout(config_actions)
        self.controls.addWidget(box)
        metrics = QGridLayout()
        for index, name in enumerate(("Ángulo", "Fase", "Repeticiones", "Rango terapéutico")):
            widget, label = _metric(name)
            setattr(self, f"metric_{index}", label)
            metrics.addWidget(widget, index // 2, index % 2)
        self.controls.addLayout(metrics)
        self.start_button = QPushButton("Iniciar ejercicio")
        self.start_button.setObjectName("primaryAction")
        self.start_button.clicked.connect(self.toggle_recording)
        self.controls.addWidget(self.start_button)
        reset = QPushButton("Reiniciar ejercicio")
        reset.clicked.connect(self.reset_current)
        self.controls.addWidget(reset)
        save = QPushButton("Finalizar y guardar reporte")
        save.clicked.connect(self.save_and_restart)
        self.controls.addWidget(save)
        self.controls.addStretch()
        self._load_patient_fields()
        self._rebuild_sessions()
        self._load_exercise_config()

    @property
    def exercise(self) -> str:
        return str(self.selector.currentData())

    def _load_patient_fields(self) -> None:
        self.patient_name.setText(self.profile["nombre"])
        self.patient_code.setText(self.profile["codigo_paciente"])
        self.patient_injury.setText(self.profile["lesion"])
        self.patient_notes.setText(self.profile["observaciones"])

    def _load_exercise_config(self) -> None:
        if not self.exercise:
            return
        config = self.profile["ejercicios"][self.exercise]
        self.rehab_evaluated_side = None
        self.rehab_start_min.setValue(float(config["rango_inicio"]["minimo"]))
        self.rehab_start_max.setValue(float(config["rango_inicio"]["maximo"]))
        self.rehab_target_min.setValue(float(config["rango_objetivo"]["minimo"]))
        self.rehab_target_max.setValue(float(config["rango_objetivo"]["maximo"]))
        self.rehab_repetitions.setValue(int(config["repeticiones_objetivo"]))
        self.rehab_side.setCurrentIndex(max(0, self.rehab_side.findData(config.get("lado", "auto"))))
        self.calibrate_button.setVisible(self.exercise == "rotacion_muneca")
        self.recording = False
        self.start_button.setText("Iniciar ejercicio")
        self.metric_1.setText("En espera")
        if self.sessions and self.exercise in self.sessions:
            self.metric_2.setText(str(self.sessions[self.exercise].repeticiones_estimadas))
        if self.exercise == "abduccion_hombro":
            excursion = float(config.get("excursion_minima_grados", 70.0))
            self.status.setText(
                f"Abducción: se exigirán al menos {excursion:.0f}° de recorrido "
                "desde el inicio calibrado para contar."
            )
        else:
            self.status.setText("Revise la configuración y pulse «Iniciar ejercicio».")

    def _rebuild_sessions(self) -> None:
        self.sessions = {
            key: RehabSession(key, self.profile["codigo_paciente"], config, session_id=self.session_id)
            for key, config in self.profile["ejercicios"].items()
        }

    def _profile_from_form(self) -> dict:
        profile = {**self.profile}
        profile["nombre"] = self.patient_name.text().strip()
        profile["codigo_paciente"] = self.patient_code.text().strip()
        profile["lesion"] = self.patient_injury.text().strip()
        profile["observaciones"] = self.patient_notes.text().strip()
        profile["ejercicios"] = {key: dict(value) for key, value in self.profile["ejercicios"].items()}
        config = dict(profile["ejercicios"][self.exercise])
        config["rango_inicio"] = {
            "minimo": self.rehab_start_min.value(),
            "maximo": self.rehab_start_max.value(),
        }
        config["rango_objetivo"] = {
            "minimo": self.rehab_target_min.value(),
            "maximo": self.rehab_target_max.value(),
        }
        config["repeticiones_objetivo"] = self.rehab_repetitions.value()
        config["lado"] = self.rehab_side.currentData()
        profile["ejercicios"][self.exercise] = config
        return normalizar_perfil_paciente(profile)

    def apply_profile_changes(self) -> bool:
        if self.recording:
            self.status.setText("Pause el ejercicio antes de cambiar el perfil o los rangos.")
            self.rehab_side.setCurrentIndex(
                max(0, self.rehab_side.findData(self.profile["ejercicios"][self.exercise].get("lado", "auto")))
            )
            return False
        try:
            updated_profile = self._profile_from_form()
        except ValueError as exc:
            self.status.setText(f"No se aplicó la configuración: {exc}")
            return False
        if updated_profile == self.profile:
            return True
        if self.dirty:
            self.status.setText("Finalice y guarde el reporte antes de cambiar datos de una sesión en curso.")
            self.rehab_side.setCurrentIndex(
                max(0, self.rehab_side.findData(self.profile["ejercicios"][self.exercise].get("lado", "auto")))
            )
            return False
        self.profile = updated_profile
        self.rehab_evaluated_side = None
        self._rebuild_sessions()
        self.metric_2.setText("0")
        self.status.setText("Perfil y rangos aplicados correctamente.")
        return True

    def load_profile(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Cargar perfil de rehabilitación",
            str(profiles_dir()),
            "Perfiles JSON (*.json)",
        )
        if not path:
            return
        try:
            self.profile = cargar_perfil_paciente(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Perfil no válido", str(exc))
            return
        self.session_id = uuid4().hex
        self.dirty = False
        self.recording = False
        self.selector.blockSignals(True)
        self.selector.clear()
        for key in self.profile["ejercicios"]:
            self.selector.addItem(REHAB_LABELS[key], key)
        self.selector.blockSignals(False)
        self._load_patient_fields()
        self.rehab_evaluated_side = None
        self._rebuild_sessions()
        self._load_exercise_config()
        self.status.setText(f"Perfil cargado desde {path}.")

    def save_profile(self) -> None:
        if not self.apply_profile_changes():
            return
        suggested = profiles_dir() / f"{self.profile['codigo_paciente']}.json"
        path, _filter = QFileDialog.getSaveFileName(
            self,
            "Guardar perfil de rehabilitación",
            str(suggested),
            "Perfiles JSON (*.json)",
        )
        if not path:
            return
        try:
            saved = guardar_perfil_paciente(self.profile, path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "No se pudo guardar el perfil", str(exc))
            return
        self.status.setText(f"Perfil guardado en {saved}.")

    def toggle_recording(self) -> None:
        if self.recording:
            self.recording = False
            self.start_button.setText("Continuar ejercicio")
            self.status.setText("Ejercicio en pausa. No se contabilizarán repeticiones.")
            return
        if not self.apply_profile_changes():
            return
        if self.exercise == "rotacion_muneca" and not self.calibrator.calibrado:
            self.status.setText("Calibre primero la posición neutral de la muñeca.")
            return
        self.recording = True
        self.start_button.setText("Pausar ejercicio")
        session = self.sessions[self.exercise]
        if session.angulo_referencia_inicio is None:
            self.metric_1.setText("Calibrando inicio")
            self.status.setText("Mantenga una postura inicial cómoda y estable durante un momento.")
        else:
            self.metric_1.setText(_phase_text(session.fase_actual))
            self.status.setText(f"Continuando con referencia inicial de {session.angulo_referencia_inicio:.1f}°.")

    def reset_current(self) -> None:
        self.sessions[self.exercise].reiniciar()
        self.rehab_evaluated_side = None
        self.recording = False
        self.start_button.setText("Iniciar ejercicio")
        self.metric_1.setText("En espera")
        self.metric_2.setText("0")
        self.status.setText("Ejercicio reiniciado.")

    def calibrate_wrist(self) -> None:
        if not self.apply_profile_changes():
            return
        try:
            configured = self.profile["ejercicios"]["rotacion_muneca"].get("lado", "auto")
            lado = resolver_lado_ejercicio(
                "rotacion_muneca",
                self.latest_points,
                configured,
                self.latest_confidence,
                self.rehab_evaluated_side,
            )
            self.calibrator.calibrar(self.latest_points, lado)
            self.rehab_evaluated_side = lado
            side_text = "derecha" if lado == "right" else "izquierda"
            self.status.setText(f"Calibración neutral de muñeca completada en la extremidad {side_text}.")
        except ValueError as exc:
            self.status.setText(str(exc))

    def finalize(self) -> Path | None:
        if not self.dirty:
            return None
        path = export_rehab_sessions(
            (session.exportar_resumen() for session in self.sessions.values()), self.profile
        )
        self.dirty = False
        return path

    def save_and_restart(self) -> None:
        self.recording = False
        self.start_button.setText("Iniciar ejercicio")
        path = self.finalize()
        if path is not None:
            self.status.setText(f"Reporte guardado en {path}.")
        self.session_id = uuid4().hex
        self.rehab_evaluated_side = None
        self._rebuild_sessions()

    def process_skeleton(self, frame: SkeletonFrame) -> None:
        self.latest_points = frame.points
        self.latest_confidence = frame.confidence
        result = evaluar_ejercicio_rehabilitacion(
            self.exercise,
            frame.points,
            self.profile,
            self.calibrator if self.exercise == "rotacion_muneca" else None,
            frame.confidence,
            self.rehab_evaluated_side,
        )
        if result.frame_valido and result.lado_evaluado is not None:
            self.rehab_evaluated_side = result.lado_evaluado
        session = self.sessions[self.exercise]
        session.fuente_datos = frame.source
        if self.recording:
            result = session.registrar_resultado(result, frame.timestamp)
            if result.frame_valido:
                self.dirty = True
        self.metric_0.setText("N/D" if result.angulo_actual is None else f"{result.angulo_actual:.1f}°")
        self.metric_1.setText(_phase_text(session.fase_actual) if self.recording else "En espera")
        self.metric_2.setText(str(session.repeticiones_estimadas))
        self.metric_3.setText("Sí" if result.dentro_rango else "No")
        side_text = "derecha" if result.lado_evaluado == "right" else "izquierda"
        orientation = ORIENTACION_RECOMENDADA[self.exercise]
        orientation_text = "cámara frontal" if orientation == "frontal" else "cámara lateral u oblicua"
        if self.recording:
            config = self.profile["ejercicios"][self.exercise]
            target = config["rango_objetivo"]
            if not result.frame_valido:
                self.status.setText(result.mensajes[0])
            elif session.angulo_referencia_inicio is None:
                if session.estado_calibracion == "en_objetivo":
                    self.status.setText(
                        f"Ángulo actual: {result.angulo_actual:.1f}°. "
                        f"Adopte una postura de reposo fuera del objetivo "
                        f"{target['minimo']:.0f}°–{target['maximo']:.0f}° y manténgala."
                    )
                elif session.estado_calibracion == "forma_incorrecta":
                    self.status.setText(
                        result.mensajes[-1] if result.mensajes else "Corrija la postura antes de calibrar el inicio."
                    )
                elif session.estado_calibracion == "inestable":
                    self.status.setText(
                        f"Ángulo actual: {result.angulo_actual:.1f}°. "
                        "Mantenga la postura quieta para calibrar el inicio."
                    )
                else:
                    self.status.setText(
                        f"Extremidad {side_text}; {orientation_text}. "
                        f"Mantenga esta postura cómoda y estable. Ángulo actual: {result.angulo_actual:.1f}°."
                    )
            elif session.fase_actual == "esperando_inicio":
                start = session.rango_inicio_calibrado
                assert start is not None
                self.status.setText(
                    f"Inicio calibrado en {session.angulo_referencia_inicio:.1f}°. "
                    f"Regrese a {start.minimo:.0f}°–{start.maximo:.0f}° para rearmar el ciclo."
                )
            elif session.fase_actual == "buscando_objetivo":
                count_target = session.rango_objetivo_repeticion
                self.status.setText(
                    f"Inicio calibrado en {session.angulo_referencia_inicio:.1f}°. "
                    f"Para contar, alcance {count_target.minimo:.0f}°–{count_target.maximo:.0f}°. "
                    f"Rango terapéutico: {target['minimo']:.0f}°–{target['maximo']:.0f}°."
                )
            elif session.fase_actual == "regresando_inicio":
                start = session.rango_inicio_calibrado
                assert start is not None
                self.status.setText(
                    f"Objetivo alcanzado. Regrese cerca de la referencia "
                    f"{session.angulo_referencia_inicio:.1f}° "
                    f"({start.minimo:.0f}°–{start.maximo:.0f}°) para contar."
                )
            else:
                self.status.setText(result.mensajes[0])
        elif result.mensajes:
            self.status.setText("Vista previa: " + result.mensajes[0] + " Pulse «Iniciar ejercicio» para registrar.")


class GaitPage(AnalysisPage):
    def __init__(self):
        super().__init__("Módulo 3 · Análisis de marcha")
        self.session = GaitSession()
        self.temporal = GaitCycleAnalyzer()
        self.recording = False
        self.exported = False
        box, layout = _card("Configuración")
        self.view = QComboBox()
        self.view.addItems(["Lateral", "Frontal"])
        layout.addWidget(self.view)
        actions = QHBoxLayout()
        start = QPushButton("Iniciar sesión")
        start.setObjectName("primaryAction")
        start.clicked.connect(self.start_session)
        stop = QPushButton("Finalizar")
        stop.clicked.connect(self.stop_session)
        reset = QPushButton("Reiniciar")
        reset.clicked.connect(self.reset_session)
        actions.addWidget(start)
        actions.addWidget(stop)
        actions.addWidget(reset)
        layout.addLayout(actions)
        self.controls.addWidget(box)
        metrics = QGridLayout()
        for index, name in enumerate(("Rodilla derecha", "Rodilla izquierda", "Asimetría de ciclos", "Longitud de paso")):
            widget, label = _metric(name)
            setattr(self, f"metric_{index}", label)
            metrics.addWidget(widget, index // 2, index % 2)
        self.controls.addLayout(metrics)
        self.controls.addStretch()

    def start_session(self) -> None:
        if self.exported:
            self.reset_session()
        self.recording = True
        self.status.setText("Sesión iniciada.")

    def stop_session(self) -> None:
        self.recording = False
        path = self.finalize()
        self.status.setText((f"Sesión finalizada. Reporte: {path}. " if path else "Sesión sin datos. ") + DISCLAIMER)

    def reset_session(self) -> None:
        self.session = GaitSession()
        self.temporal.reset()
        self.exported = False
        self.status.setText("Sesión reiniciada.")

    def finalize(self) -> Path | None:
        if self.exported or self.session.frames_validos == 0:
            return None
        path = export_gait_session(self.session.exportar_resumen())
        self.exported = True
        return path

    def process_skeleton(self, frame: SkeletonFrame) -> None:
        initial = analizar_marcha(frame.points, vista=self.view.currentText())
        if not initial.frame_valido:
            result = initial
        else:
            right = float(initial.metricas["angulo_rodilla_derecha"])
            left = float(initial.metricas["angulo_rodilla_izquierda"])
            separation = None
            if "left_ankle" in frame.points and "right_ankle" in frame.points:
                separation = abs(float(frame.points["left_ankle"][0]) - float(frame.points["right_ankle"][0]))
            temporal = self.temporal.update(
                right,
                left,
                separation,
                time.monotonic() if frame.timestamp is None else frame.timestamp,
                view=self.view.currentText(),
                length_unit=frame.length_unit,
            )
            result = analizar_marcha(frame.points, vista=self.view.currentText(), metricas_temporales=temporal)
        self.session.fuente_datos = frame.source
        if self.recording:
            self.session.registrar_resultado(result)
        metrics = result.metricas
        self.metric_0.setText("N/D" if metrics.get("angulo_rodilla_derecha") is None else f"{metrics['angulo_rodilla_derecha']:.1f}°")
        self.metric_1.setText("N/D" if metrics.get("angulo_rodilla_izquierda") is None else f"{metrics['angulo_rodilla_izquierda']:.1f}°")
        self.metric_2.setText("N/D" if metrics.get("asimetria_rodillas") is None else f"{metrics['asimetria_rodillas']:.1f}°")
        length = metrics.get("longitud_paso")
        self.metric_3.setText("N/D" if length is None else f"{length:.3f} {metrics['unidad_longitud']}")
        self.status.setText(result.mensajes[0] if result.mensajes else DISCLAIMER)


class PuceMainWindow(QMainWindow):
    def __init__(self, initial_page: str = "menu"):
        super().__init__()
        self.setWindowTitle("PUCE MoCap Fisioterapia")
        self.resize(1400, 850)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.menu = MenuPage()
        self.pages = {"menu": self.menu, "pesas": WeightsPage(), "rehab": RehabPage(), "gait": GaitPage()}
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.menu.open_requested.connect(self.open_page)
        self.menu.verify_requested.connect(self.run_verification)
        self.menu.freemocap_requested.connect(self.open_freemocap)
        self.menu.exit_requested.connect(self.close)
        for page in self.pages.values():
            if isinstance(page, AnalysisPage):
                page.back_requested.connect(lambda: self.open_page("menu"))
                page.camera_requested.connect(self.set_camera_active)
        self.worker = CameraPoseWorker(self)
        self.worker.status_changed.connect(self._worker_status)
        self.worker.model_ready.connect(self._model_ready)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_camera)
        self.poll_timer.start(33)
        QTimer.singleShot(0, self.worker.start)
        self.processes: list[QProcess] = []
        self.open_page(initial_page if initial_page in self.pages else "menu")

    def open_page(self, name: str) -> None:
        current = self.stack.currentWidget()
        if isinstance(current, AnalysisPage):
            current.deactivate()
        page = self.pages[name]
        self.stack.setCurrentWidget(page)
        if isinstance(page, AnalysisPage):
            page.activate()

    def set_camera_active(self, active: bool) -> None:
        page = self.stack.currentWidget()
        if active and isinstance(page, AnalysisPage):
            width, height = page.resolution.currentData()
            self.worker.configure(int(page.camera_index.currentData()), int(width), int(height))
            self.worker.activate()
        else:
            self.worker.deactivate()

    def _poll_camera(self) -> None:
        result = self.worker.take_latest()
        page = self.stack.currentWidget()
        if result is not None and isinstance(page, AnalysisPage):
            page.on_live_result(result)

    def _worker_status(self, text: str) -> None:
        page = self.stack.currentWidget()
        if isinstance(page, AnalysisPage):
            page.status.setText(text)
        else:
            self.menu.status.setText(text)

    def _model_ready(self) -> None:
        self.menu.status.setText("Modelo de pose listo. La cámara se abrirá únicamente cuando se solicite.")

    def _start_process(self, arguments: list[str], label: str) -> None:
        process = QProcess(self)
        process.setWorkingDirectory(str(REPO_ROOT))
        process.setProgram(sys.executable)
        process.setArguments(arguments)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(
            lambda p=process: self.menu.status.setText(bytes(p.readAllStandardOutput()).decode(errors="replace").strip()[-500:])
        )
        process.finished.connect(lambda code, _status: self.menu.status.setText(f"{label} finalizó con código {code}."))
        self.processes.append(process)
        process.start()
        self.menu.status.setText(f"{label} en ejecución...")

    def run_verification(self) -> None:
        self._start_process(["-m", "pytest", "-q"], "Pruebas automáticas")

    def open_freemocap(self) -> None:
        self._start_process(["-m", "freemocap"], "FreeMoCap")

    def closeEvent(self, event: QCloseEvent) -> None:
        for page in self.pages.values():
            if isinstance(page, AnalysisPage):
                page.finalize()
        self.worker.stop()
        for process in self.processes:
            if process.state() != QProcess.ProcessState.NotRunning:
                process.terminate()
        super().closeEvent(event)


STYLE = """
QWidget {
    background: #071827;
    color: #edf5fb;
    font-family: 'Segoe UI';
    font-size: 14px;
}
QMainWindow, QWidget#menuPage { background: #071827; }
QFrame#hero {
    background: #0b2b49;
    border: 1px solid #1b4b70;
    border-radius: 18px;
}
QFrame#hero QLabel { background: transparent; }
QFrame#identityPanel {
    background: #f8fbfd;
    border: 1px solid #d9e5ec;
    border-radius: 14px;
}
QFrame#identityPanel QLabel { background: transparent; color: #27445d; }
QFrame#analysisHeader, QFrame#sourceBar {
    background: #0b243a;
    border: 1px solid #20445f;
    border-radius: 12px;
}
QLabel#pageTitle {
    font-size: 30px;
    font-weight: 750;
    color: #ffffff;
    padding: 4px 0;
}
QLabel#eyebrow {
    color: #43d3c8;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#sectionTitle { font-size: 18px; font-weight: 700; color: #ffffff; }
QLabel#identityCaption { color: #35516a; font-weight: 600; }
QLabel#menuStatus {
    background: #0b243a;
    border-left: 3px solid #2ec4b6;
    border-radius: 5px;
    color: #c9dbe8;
    padding: 9px 12px;
}
QLabel#video {
    background: #02090f;
    border: 1px solid #284d68;
    border-radius: 14px;
    color: #91a9ba;
    font-size: 16px;
}
QLabel[metric="true"] { font-size: 25px; font-weight: 750; color: #58e1b7; }
QLabel[muted="true"] { color: #9eb6c7; }
QGroupBox {
    background: #0b2134;
    border: 1px solid #294b64;
    border-radius: 11px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 700;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #dcebf4; }
QPushButton {
    background: #17354c;
    border: 1px solid #315a75;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
    font-weight: 600;
}
QPushButton:hover { background: #214a65; border-color: #55c6dd; }
QPushButton:pressed { background: #102c41; }
QPushButton#moduleCard {
    background: #0e2940;
    border: 1px solid #2b5570;
    border-radius: 13px;
    padding: 18px;
    text-align: left;
    font-size: 15px;
}
QPushButton#moduleCard:hover { background: #123958; border-color: #31c6c0; }
QPushButton#primaryAction {
    background: #087f78;
    border-color: #24c9bc;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#primaryAction:hover { background: #0a9a90; }
QPushButton#secondaryAction { background: #102c43; }
QPushButton#quietAction, QPushButton#backButton { background: transparent; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit {
    background: #0a1c2c;
    border: 1px solid #3b6079;
    border-radius: 6px;
    padding: 7px;
    selection-background-color: #087f78;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
    border: 1px solid #34c7bd;
}
QSlider::groove:horizontal { height: 5px; background: #29475b; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; background: #38cfc3; border-radius: 8px; }
"""


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            return


def run(initial_page: str = "menu") -> int:
    enable_windows_dpi_awareness()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PUCE MoCap Fisioterapia")
    app.setOrganizationName("Pontificia Universidad Católica del Ecuador")
    app.setStyleSheet(STYLE)
    window = PuceMainWindow(initial_page)
    window.show()
    return app.exec()
