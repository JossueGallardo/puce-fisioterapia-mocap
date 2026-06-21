# Menú principal Qt integrado

## Ejecución

```powershell
python -m puce_mocap.main_menu
# o, después de instalar el proyecto
puce-mocap
```

## Arquitectura vigente

El menú, Pesas, Rehabilitación y Análisis de marcha son páginas de una única `QMainWindow` de PySide6. Los controles son widgets Qt interactivos, funcionan con mouse y teclado y se adaptan al escalado de Windows.

La captura OpenCV y la inferencia MediaPipe se ejecutan en un `QThread`. El modelo se prepara en segundo plano al abrir la aplicación, pero la cámara solo se abre cuando el usuario pulsa `Iniciar cámara`. Entrar a un módulo no inicia el registro ni contabiliza repeticiones.

El selector de cámara usa los dispositivos de vídeo enumerados por Qt; no muestra índices ficticios del 0 al 10. También permite elegir entre `640 × 480` y `1280 × 720`.

FreeMoCap original permanece aislado y se abre mediante `QProcess`. La ejecución de pytest también es asíncrona y no congela la ventana.

## Fuentes de datos

- **Cámara:** MediaPipe Pose en vivo, con coordenadas world y filtro de visibilidad 0.5.
- **Sesión FreeMoCap:** carpeta que contenga `output_data/*_body_3d_xyz.npy`.
- Al importar se solicita la unidad de calibración; si se desconoce se usa `sin_especificar`.
- La reproducción incluye pausa y deslizador por fotograma.

## Flujo de trabajo

1. Abrir el módulo requerido.
2. Revisar el paciente y los rangos configurados.
3. Pulsar `Iniciar cámara` o importar una sesión FreeMoCap.
4. Pulsar `Iniciar ejercicio` o `Iniciar sesión` para comenzar el registro.
5. Finalizar y guardar el reporte.

## Cierre seguro

Al volver al menú o cerrar la aplicación se guardan las sesiones con datos, se detiene el worker, se libera la cámara y se terminan procesos secundarios. Los reportes y perfiles reales se guardan en el directorio local de la aplicación, fuera de Git.
