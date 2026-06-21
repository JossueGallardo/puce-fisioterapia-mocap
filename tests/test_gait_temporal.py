import pytest

from puce_mocap.gait_temporal import GaitCycleAnalyzer


def test_simetria_y_paso_requieren_ciclos_completos():
    analyzer = GaitCycleAnalyzer(alpha=1.0, min_interval=0.4, min_excursion=10.0)
    right = [170, 140, 100, 140, 170, 140, 100, 140, 170, 140, 100, 140, 170, 140, 100, 140, 170]
    left = [100, 140, 170, 140, 100, 140, 170, 140, 100, 140, 170, 140, 100, 140, 170, 140, 100]
    metricas = None
    for index, (right_angle, left_angle) in enumerate(zip(right, left)):
        metricas = analyzer.update(right_angle, left_angle, 0.5, index * 0.2, length_unit="m")

    assert metricas is not None
    assert metricas.completed_cycles >= 4
    assert metricas.asymmetry == pytest.approx(0.0)
    assert metricas.step_length == pytest.approx(0.5)
    assert metricas.length_unit == "m"


def test_vista_frontal_no_inventa_ciclos_laterales():
    analyzer = GaitCycleAnalyzer(alpha=1.0)
    for index, angle in enumerate([170, 120, 170, 120, 170]):
        metricas = analyzer.update(angle, angle, 0.4, index * 0.5, view="frontal")

    assert metricas.completed_cycles == 0
    assert metricas.asymmetry is None
    assert metricas.step_length is None
