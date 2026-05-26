from __future__ import annotations

import time

import cv2


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No se pudo abrir la camara 0. Conecta una camara y vuelve a intentar.")
        return

    frame_count = 0
    print("Demo visual iniciado. Presiona 'q' para salir.")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("No se pudo leer un frame de la camara.")
            break

        frame_count += 1
        estado_correcto = (frame_count // 90) % 2 == 0
        estado = "CORRECTO" if estado_correcto else "CORREGIR POSTURA"
        color_nombre = "VERDE" if estado_correcto else "ROJO"
        color = (0, 180, 0) if estado_correcto else (0, 0, 220)

        cv2.rectangle(frame, (0, 0), (frame.shape[1], 120), (20, 20, 20), -1)
        cv2.putText(frame, "PUCE MoCap - Modulo de Pesas", (30, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, "Basado en FreeMoCap", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (210, 210, 210), 2)
        cv2.putText(frame, f"{color_nombre} / {estado}", (30, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

        cv2.imshow("PUCE MoCap - Semana 3", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        time.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

