from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from puce_mocap.angle_utils import calcular_angulo


def main():
    """Ejecuta una demostracion simple del calculo de angulo de rodilla."""
    cadera = [0.0, 1.0, 0.0]
    rodilla = [0.0, 0.0, 0.0]
    tobillo = [1.0, 0.0, 0.0]

    angulo_rodilla = calcular_angulo(cadera, rodilla, tobillo)

    print(f"Angulo de rodilla calculado: {angulo_rodilla:.2f} grados")

    if 70 <= angulo_rodilla <= 100:
        print("CORRECTO - Postura correcta")
    else:
        print("CORREGIR POSTURA - Revisa el rango de la rodilla")


if __name__ == "__main__":
    main()

