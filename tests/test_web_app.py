import numpy as np
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from puce_mocap.rehab_analyzer import RehabAnalysisResult
from puce_mocap.skeleton_frame import SkeletonFrame
from puce_mocap.web.app import create_app
from puce_mocap.web.camera_service import BrowserPoseFrame
from puce_mocap.web.controller import PuceWebController


def sentadilla_correcta():
    return {
        "right_shoulder": [0.0, 2.0, 0.0],
        "right_hip": [0.0, 1.0, 0.0],
        "right_knee": [0.0, 0.0, 0.0],
        "right_ankle": [1.0, 0.0, 0.0],
        "right_foot": [1.0, 1.0, 0.0],
    }


def codo_90():
    return {
        "right_shoulder": [1.0, 0.0, 0.0],
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [0.0, 1.0, 0.0],
    }


def marcha_normal():
    return {
        "nose": [0.0, 2.4, 0.0],
        "left_shoulder": [-0.2, 2.0, 0.0],
        "right_shoulder": [0.2, 2.0, 0.0],
        "left_hip": [-0.2, 1.0, 0.0],
        "right_hip": [0.2, 1.0, 0.0],
        "left_knee": [-0.2, 0.5, 0.0],
        "right_knee": [0.2, 0.5, 0.0],
        "left_ankle": [-0.2, 0.0, 0.0],
        "right_ankle": [0.2, 0.0, 0.0],
    }


class FakePoseProcessor:
    def close(self):
        return None

    def process_jpeg(self, image_bytes):
        assert image_bytes == b"jpeg-de-prueba"
        landmarks = [{"x": 0.5, "y": 0.5, "visibility": 1.0} for _ in range(33)]
        return BrowserPoseFrame(
            SkeletonFrame(sentadilla_correcta(), timestamp=0.0, source="navegador_prueba"),
            landmarks,
            12.5,
        )


def test_web_app_factory_expone_inicio_y_estado():
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 200
        info_response = client.get("/api/app-info")
        info = info_response.json()
        state = client.get("/api/state").json()

    assert info["local_only"] is False
    assert info["deployment"]["browser_camera"] is True
    assert info["deployment"]["server_filesystem_paths"] is False
    assert next(item for item in info["rehab_exercises"] if item["key"] == "flexion_codo")["orientation"] == "frontal"
    assert any(module["key"] == "weights" for module in info["modules"])
    assert state["module"] == "weights"
    assert state["source"]["mode"] == "none"
    assert info_response.headers["cache-control"] == "no-store"
    assert "camera=(self)" in info_response.headers["permissions-policy"]


def test_web_controller_pesas_registra_y_exporta_reporte(monkeypatch, tmp_path):
    monkeypatch.setenv("PUCE_MOCAP_DATA_DIR", str(tmp_path))
    controller = PuceWebController()

    controller.start_weights({})
    controller.process_skeleton(SkeletonFrame(sentadilla_correcta(), timestamp=0.0, source="prueba"))
    state = controller.snapshot()
    controller.save_weights()
    saved = controller.snapshot()["last_report"]

    assert state["weights"]["recording"] is True
    assert state["metrics"][0]["value"] == "90.0°"
    assert saved == {"available": True, "filename": "pesas_v2.csv"}
    assert tmp_path.joinpath("reports", "pesas_v2.csv").is_file()
    controller.close()


def test_web_controller_rehabilitacion_y_marcha_exportan(monkeypatch, tmp_path):
    monkeypatch.setenv("PUCE_MOCAP_DATA_DIR", str(tmp_path))
    controller = PuceWebController()

    controller.set_module("rehab")
    controller.configure_rehab({"exercise": "flexion_codo"})
    controller.start_rehab({})
    controller.process_skeleton(SkeletonFrame(codo_90(), timestamp=0.0, source="prueba"))
    controller.save_rehab()

    controller.set_module("gait")
    controller.start_gait()
    controller.process_skeleton(SkeletonFrame(marcha_normal(), timestamp=0.0, source="prueba"))
    controller.stop_gait()

    assert tmp_path.joinpath("reports", "rehabilitacion_v3.csv").is_file()
    assert tmp_path.joinpath("reports", "marcha_v2.csv").is_file()
    controller.close()


def test_web_endpoint_carga_archivo_freemocap_desde_el_navegador(tmp_path):
    recording = tmp_path / "recording"
    output = recording / "output_data"
    output.mkdir(parents=True)
    data = np.full((1, 33, 3), np.nan)
    points = {
        0: [0.0, 2.4, 0.0],
        11: [-0.2, 2.0, 0.0],
        12: [0.2, 2.0, 0.0],
        23: [-0.2, 1.0, 0.0],
        24: [0.2, 1.0, 0.0],
        25: [-0.2, 0.5, 0.0],
        26: [0.2, 0.5, 0.0],
        27: [-0.2, 0.0, 0.0],
        28: [0.2, 0.0, 0.0],
    }
    for index, point in points.items():
        data[0, index] = point
    np.save(output / "mediapipe_body_3d_xyz.npy", data)

    with TestClient(create_app()) as client:
        assert client.post("/api/module", json={"module": "gait"}).status_code == 200
        response = client.post(
            "/api/source/freemocap/upload?filename=mediapipe_body_3d_xyz.npy&unit=m",
            content=(output / "mediapipe_body_3d_xyz.npy").read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
        )
        state = response.json()["state"]

    assert response.status_code == 200
    assert state["source"]["mode"] == "freemocap"
    assert state["source"]["freemocap"]["frame_count"] == 1
    assert state["source"]["freemocap"]["filename"] == "mediapipe_body_3d_xyz.npy"
    assert "path" not in state["source"]["freemocap"]
    assert state["visualization"]["detected"] is True
    assert state["metrics"][0]["value"] == "180.0°"


def test_web_endpoint_procesa_camara_del_navegador():
    controller = PuceWebController(pose_processor=FakePoseProcessor())
    with TestClient(create_app(controller)) as client:
        started = client.post(
            "/api/source/camera/start",
            json={"device_label": "Cámara integrada", "width": 640, "height": 360},
        )
        response = client.post(
            "/api/source/camera/frame",
            content=b"jpeg-de-prueba",
            headers={"Content-Type": "image/jpeg"},
        )
        state = response.json()["state"]

    assert started.status_code == 200
    assert response.status_code == 200
    assert response.json()["visualization"]["processing_ms"] == 12.5
    assert state["source"]["mode"] == "browser_camera"
    assert state["source"]["camera"]["label"] == "Cámara integrada"
    assert state["metrics"][0]["value"] == "90.0°"


def test_web_perfil_y_reporte_se_descargan_sin_rutas_del_servidor(monkeypatch, tmp_path):
    monkeypatch.setenv("PUCE_MOCAP_DATA_DIR", str(tmp_path))
    controller = PuceWebController()
    controller.start_weights({})
    controller.process_skeleton(SkeletonFrame(sentadilla_correcta(), timestamp=0.0, source="prueba"))
    controller.save_weights()

    profile = controller.rehab_profile_json()
    with TestClient(create_app(controller)) as client:
        uploaded = client.post(
            "/api/rehab/profile/upload",
            content=profile,
            headers={"Content-Type": "application/json"},
        )
        downloaded_profile = client.get("/api/rehab/profile/download")
        downloaded_report = client.get("/api/reports/latest")

    assert uploaded.status_code == 200
    assert downloaded_profile.status_code == 200
    assert downloaded_profile.headers["content-disposition"].endswith('"perfil_rehabilitacion.json"')
    assert downloaded_report.status_code == 200
    assert "attachment; filename=\"pesas_v2.csv\"" in downloaded_report.headers["content-disposition"]


def test_web_rehabilitacion_explica_inicio_y_no_exige_cuerpo_entero():
    controller = PuceWebController()
    confidence = {
        "right_shoulder": 0.95,
        "right_elbow": 0.95,
        "right_wrist": 0.95,
    }
    controller.set_module("rehab")
    controller.start_rehab({})
    controller.process_skeleton(
        SkeletonFrame(codo_90(), confidence=confidence, timestamp=0.0, source="prueba")
    )

    assert "Ángulo actual: 90.0°" in controller.snapshot()["status"]
    assert "fuera del objetivo 30°–130°" in controller.snapshot()["status"]

    controller.process_skeleton(SkeletonFrame({}, confidence=confidence, timestamp=0.1, source="prueba"))
    status = controller.snapshot()["status"]

    assert "hombro, codo y muñeca" in status
    assert "Puede realizarse sentado" in status
    controller.close()


def test_web_rehabilitacion_cambia_a_izquierda_y_auto_elige_mejor_visible():
    controller = PuceWebController()
    controller.set_module("rehab")
    base_config = {
        "rango_inicio": {"minimo": 160, "maximo": 180},
        "rango_objetivo": {"minimo": 30, "maximo": 130},
        "repeticiones_objetivo": 10,
    }
    controller.configure_rehab(
        {
            "exercise": "flexion_codo",
            "config": {**base_config, "lado": "left"},
        }
    )

    assert controller.snapshot()["rehab"]["profile"]["ejercicios"]["flexion_codo"]["lado"] == "left"

    controller.configure_rehab(
        {
            "exercise": "flexion_codo",
            "config": {**base_config, "lado": "auto"},
        }
    )
    controller.process_skeleton(
        SkeletonFrame(
            {
                "right_shoulder": [-1.0, 0.0, 0.0],
                "right_elbow": [0.0, 0.0, 0.0],
                "right_wrist": [1.0, 0.0, 0.0],
                "left_shoulder": [1.0, 0.0, 0.0],
                "left_elbow": [0.0, 0.0, 0.0],
                "left_wrist": [0.0, 1.0, 0.0],
            },
            confidence={
                "right_shoulder": 0.70,
                "right_elbow": 0.70,
                "right_wrist": 0.70,
                "left_shoulder": 0.96,
                "left_elbow": 0.96,
                "left_wrist": 0.96,
            },
            timestamp=0.0,
            source="prueba",
        )
    )

    assert controller.snapshot()["rehab"]["evaluated_side"] == "left"
    controller.close()


def test_intento_invalido_no_bloquea_cambio_de_extremidad():
    controller = PuceWebController()
    controller.set_module("rehab")
    controller.start_rehab({})
    controller.process_skeleton(SkeletonFrame({}, timestamp=0.0, source="prueba"))
    controller.pause_rehab()
    controller.configure_rehab(
        {
            "exercise": "flexion_codo",
            "config": {
                "rango_inicio": {"minimo": 160, "maximo": 180},
                "rango_objetivo": {"minimo": 30, "maximo": 130},
                "repeticiones_objetivo": 10,
                "lado": "left",
            },
        }
    )

    assert controller.snapshot()["rehab"]["profile"]["ejercicios"]["flexion_codo"]["lado"] == "left"
    controller.close()


def test_web_calibra_referencia_inicial_sin_exigir_rango_teorico(monkeypatch):
    controller = PuceWebController()
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
    monkeypatch.setattr(
        "puce_mocap.web.controller.evaluar_ejercicio_rehabilitacion",
        lambda *_args: result,
    )
    controller.set_module("rehab")
    controller.start_rehab({})

    for timestamp in (0.0, 0.1, 0.2):
        controller.process_skeleton(SkeletonFrame(points={}, timestamp=timestamp, source="prueba"))

    state = controller.snapshot()
    assert state["rehab"]["start_reference"] == 145.0
    assert state["metrics"][1]["value"] == "Buscando objetivo"
    assert "Inicio calibrado en 145.0°" in state["status"]
    controller.close()
