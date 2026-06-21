import numpy as np
import pytest

from puce_mocap.freemocap_session import FreeMoCapSessionProvider


def test_carga_sesion_freemocap_sin_importar_skellytracker(tmp_path):
    output = tmp_path / "output_data"
    timestamps = tmp_path / "synchronized_videos" / "timestamps"
    output.mkdir()
    timestamps.mkdir(parents=True)
    data = np.arange(2 * 33 * 3, dtype=float).reshape(2, 33, 3)
    np.save(output / "mediapipe_body_3d_xyz.npy", data)
    np.save(timestamps / "cam0.npy", np.array([0.0, 0.033]))

    provider = FreeMoCapSessionProvider(tmp_path, length_unit="mm")
    frame = provider.get_frame(1)

    assert provider.frame_count == 2
    assert frame.points["right_knee"] == pytest.approx(data[1, 26].tolist())
    assert frame.timestamp == pytest.approx(0.033)
    assert frame.source == "freemocap_session"
    assert frame.length_unit == "mm"


def test_rechaza_forma_incompatible(tmp_path):
    output = tmp_path / "output_data"
    output.mkdir()
    np.save(output / "mediapipe_body_3d_xyz.npy", np.zeros((2, 32, 3)))

    with pytest.raises(ValueError, match="frames, 33, 3"):
        FreeMoCapSessionProvider(tmp_path)
