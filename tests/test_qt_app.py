import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton

from puce_mocap.exercise_rules import ExerciseFeedback
from puce_mocap.rehab_analyzer import RehabAnalysisResult
from puce_mocap.qt_app import GaitPage, MenuPage, RehabPage, WeightsPage
from puce_mocap.skeleton_frame import SkeletonFrame


def app():
    return QApplication.instance() or QApplication([])


def test_menu_emite_navegacion_con_click_de_mouse():
    app()
    page = MenuPage()
    selected = []
    page.open_requested.connect(selected.append)
    button = next(button for button in page.findChildren(QPushButton) if "Ejercicios con pesas" in button.text())

    QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    assert selected == ["pesas"]


def test_paginas_de_analisis_tienen_controles_qt_reales():
    app()
    for page in (WeightsPage(), RehabPage(), GaitPage()):
        buttons = page.findChildren(QPushButton)
        assert any("Volver" in button.text() for button in buttons)
        assert any("Importar sesión FreeMoCap" in button.text() for button in buttons)
        assert page.video.minimumWidth() >= 640


def test_entrar_a_una_pagina_no_abre_la_camara_automaticamente():
    app()
    page = WeightsPage()
    requests = []
    page.camera_requested.connect(requests.append)

    page.activate()

    assert requests == []
    assert not page.camera_active


def test_selector_de_camara_usa_dispositivos_detectados_y_no_indices_fijos():
    app()
    page = WeightsPage()

    assert isinstance(page.camera_index, QComboBox)
    assert page.camera_index.count() >= 1
    assert page.camera_index.itemData(0) == 0


def test_pesas_no_registra_hasta_iniciar(monkeypatch):
    app()
    page = WeightsPage()
    feedback = ExerciseFeedback(
        ejercicio="Sentadilla",
        estado="CORRECTO",
        color="verde",
        angulos={"angulo_rodilla": 170.0},
        mensajes=["Vista previa."],
        frame_valido=True,
        forma_correcta=True,
        angulo_principal="angulo_rodilla",
    )
    monkeypatch.setattr("puce_mocap.qt_app.evaluar_sentadilla", lambda _points: feedback)
    frame = SkeletonFrame(points={}, timestamp=0.0, source="prueba")

    page.process_skeleton(frame)
    assert page.sessions["Sentadilla"].total_frames == 0

    page.toggle_recording()
    page.process_skeleton(frame)
    assert page.sessions["Sentadilla"].total_frames == 1


def test_rehabilitacion_aplica_datos_del_paciente_y_rangos():
    app()
    page = RehabPage()
    page.patient_name.setText("Paciente ficticio editado")
    page.patient_code.setText("PAC-EDIT")
    page.patient_injury.setText("Seguimiento ficticio")
    page.patient_notes.setText("Sin datos reales")
    page.rehab_target_min.setValue(40.0)
    page.rehab_target_max.setValue(120.0)

    assert page.apply_profile_changes()
    assert page.profile["nombre"] == "Paciente ficticio editado"
    assert page.profile["codigo_paciente"] == "PAC-EDIT"
    assert page.profile["ejercicios"][page.exercise]["rango_objetivo"] == {
        "minimo": 40.0,
        "maximo": 120.0,
    }
    assert page.sessions[page.exercise].codigo_paciente == "PAC-EDIT"


def test_rehabilitacion_qt_permita_automatico_e_izquierdo():
    app()
    page = RehabPage()

    assert page.rehab_side.findData("auto") >= 0
    page.rehab_side.setCurrentIndex(page.rehab_side.findData("left"))

    assert page.apply_profile_changes()
    assert page.profile["ejercicios"][page.exercise]["lado"] == "left"


def test_rehabilitacion_no_registra_hasta_iniciar(monkeypatch):
    app()
    page = RehabPage()
    result = RehabAnalysisResult(
        ejercicio="flexion_codo",
        estado="DENTRO_DEL_RANGO",
        color="verde",
        angulo_actual=90.0,
        angulo_minimo=30.0,
        angulo_maximo=130.0,
        dentro_rango=True,
        mensajes=["Dentro del rango terapéutico."],
        forma_correcta=True,
    )
    monkeypatch.setattr("puce_mocap.qt_app.evaluar_ejercicio_rehabilitacion", lambda *_args: result)
    frame = SkeletonFrame(points={}, timestamp=0.0, source="prueba")

    page.process_skeleton(frame)
    assert page.sessions[page.exercise].total_frames == 0

    page.toggle_recording()
    page.process_skeleton(frame)
    assert page.sessions[page.exercise].total_frames == 1


def test_rehabilitacion_qt_explica_rango_inicial_y_articulaciones_visibles():
    app()
    page = RehabPage()
    confidence = {
        "right_shoulder": 0.95,
        "right_elbow": 0.95,
        "right_wrist": 0.95,
    }
    page.toggle_recording()
    page.process_skeleton(
        SkeletonFrame(
            points={
                "right_shoulder": [1.0, 0.0, 0.0],
                "right_elbow": [0.0, 0.0, 0.0],
                "right_wrist": [0.0, 1.0, 0.0],
            },
            confidence=confidence,
            timestamp=0.0,
            source="prueba",
        )
    )

    assert "Ángulo actual: 90.0°" in page.status.text()
    assert "fuera del objetivo 30°–130°" in page.status.text()

    page.process_skeleton(SkeletonFrame(points={}, confidence=confidence, timestamp=0.1, source="prueba"))

    assert "hombro, codo y muñeca" in page.status.text()
    assert "Puede realizarse sentado" in page.status.text()


def test_rehabilitacion_qt_calibra_una_referencia_inicial_comoda(monkeypatch):
    app()
    page = RehabPage()
    result = RehabAnalysisResult(
        ejercicio="flexion_codo",
        estado="FUERA_DEL_RANGO",
        color="amarillo",
        angulo_actual=145.0,
        angulo_minimo=30.0,
        angulo_maximo=130.0,
        dentro_rango=False,
        mensajes=["Postura de reposo."],
        lado_evaluado="right",
    )
    monkeypatch.setattr("puce_mocap.qt_app.evaluar_ejercicio_rehabilitacion", lambda *_args: result)
    page.toggle_recording()

    for timestamp in (0.0, 0.1, 0.2):
        page.process_skeleton(SkeletonFrame(points={}, timestamp=timestamp, source="prueba"))

    session = page.sessions[page.exercise]
    assert session.angulo_referencia_inicio == 145.0
    assert session.fase_actual == "buscando_objetivo"
    assert "Inicio calibrado en 145.0°" in page.status.text()
