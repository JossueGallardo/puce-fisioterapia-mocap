import pytest

from puce_mocap.movement import AngleRange, MovementDefinition, MovementPhase, RepetitionTracker


def definition(**overrides):
    values = {
        "start_range": AngleRange(160, 180),
        "target_range": AngleRange(70, 100),
        "dwell_seconds": 0.2,
        "min_cycle_seconds": 0.6,
        "ema_alpha": 1.0,
    }
    values.update(overrides)
    return MovementDefinition(**values)


def feed(tracker, samples):
    return [tracker.update(angle, timestamp, valid=valid, form_ok=form_ok) for timestamp, angle, valid, form_ok in samples]


def test_cuenta_unicamente_inicio_objetivo_inicio_confirmados():
    tracker = RepetitionTracker(definition())
    updates = feed(
        tracker,
        [
            (0.0, 170, True, None),
            (0.2, 170, True, None),
            (0.4, 90, True, True),
            (0.6, 90, True, True),
            (0.8, 170, True, None),
            (1.0, 170, True, None),
        ],
    )

    assert tracker.repetitions == 1
    assert updates[-1].repetition_completed
    assert updates[-1].phase == MovementPhase.INICIO


def test_oscilar_en_el_umbral_no_cuenta_repeticiones():
    tracker = RepetitionTracker(definition())
    feed(
        tracker,
        [
            (0.0, 170, True, None),
            (0.2, 170, True, None),
            (0.3, 99, True, True),
            (0.35, 103, True, None),
            (0.4, 98, True, True),
            (0.45, 104, True, None),
        ],
    )

    assert tracker.repetitions == 0


def test_empezar_en_objetivo_no_cuenta_hasta_ciclo_posterior():
    tracker = RepetitionTracker(definition(dwell_seconds=0.0))
    for timestamp, angle in [(0.0, 90), (0.4, 170), (0.8, 90), (1.2, 170)]:
        tracker.update(angle, timestamp, form_ok=True)

    assert tracker.repetitions == 1


def test_forma_incorrecta_impide_confirmar_objetivo():
    tracker = RepetitionTracker(definition(dwell_seconds=0.0))
    tracker.update(170, 0.0)
    tracker.update(90, 0.4, form_ok=False)
    tracker.update(170, 0.8)

    assert tracker.repetitions == 0


def test_perdida_prolongada_reinicia_ciclo_sin_borrar_conteo():
    tracker = RepetitionTracker(definition(dwell_seconds=0.0, invalid_reset_seconds=1.0))
    tracker.update(170, 0.0)
    tracker.update(90, 0.4, form_ok=True)
    tracker.update(None, 1.5, valid=False)
    tracker.update(170, 1.6)

    assert tracker.repetitions == 0
    assert tracker.state == MovementPhase.BUSCANDO_OBJETIVO


def test_inicio_requiere_permanencia_tras_deteccion_tardia():
    tracker = RepetitionTracker(definition())
    tracker.update(None, 0.0, valid=False)
    tracker.update(None, 0.5, valid=False)

    first = tracker.update(170, 1.0, valid=True)
    confirmed = tracker.update(170, 1.2, valid=True)

    assert first.state == MovementPhase.ESPERANDO_INICIO
    assert confirmed.state == MovementPhase.BUSCANDO_OBJETIVO
    assert confirmed.repetitions == 0


def test_retorno_requiere_permanencia_para_evitar_cierre_falso():
    tracker = RepetitionTracker(
        MovementDefinition(
            start_range=AngleRange(0, 20),
            target_range=AngleRange(45, 100),
            dwell_seconds=0.2,
            min_cycle_seconds=0.6,
            ema_alpha=0.35,
        )
    )
    tracker.update(10, 0.0)
    tracker.update(10, 0.2)
    tracker.update(70, 0.4)
    tracker.update(80, 0.6)
    tracker.update(80, 0.8)

    transient = tracker.update(10, 1.0)
    completed = tracker.update(10, 1.2)

    assert not transient.repetition_completed
    assert completed.repetition_completed
    assert tracker.repetitions == 1


def test_perdida_de_deteccion_descarta_retorno_transitorio():
    tracker = RepetitionTracker(definition())
    feed(
        tracker,
        [
            (0.0, 170, True, None),
            (0.2, 170, True, None),
            (0.4, 90, True, True),
            (0.6, 90, True, True),
            (0.8, 170, True, None),
            (0.9, None, False, None),
            (1.0, 170, True, None),
            (1.1, 120, True, None),
        ],
    )

    assert tracker.state == MovementPhase.REGRESANDO_INICIO
    assert tracker.repetitions == 0


def test_armado_explicito_tras_calibracion_inicial():
    tracker = RepetitionTracker(definition())

    update = tracker.arm_from_start(170.0, 0.5)

    assert update.state == MovementPhase.BUSCANDO_OBJETIVO
    assert update.phase == MovementPhase.INICIO
    assert tracker.filtered_angle == 170.0


def test_rechaza_rangos_solapados():
    with pytest.raises(ValueError, match="solaparse"):
        MovementDefinition(AngleRange(80, 120), AngleRange(100, 160))
