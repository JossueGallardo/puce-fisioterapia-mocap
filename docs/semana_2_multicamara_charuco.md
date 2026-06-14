# Semana 2 - Multicámara y calibración ChArUco

## Objetivo

Preparar la configuración multicámara para pruebas de marcha en caminadora y documentar el uso de calibración ChArUco sin modificar el núcleo original de FreeMoCap.

## Configuracion recomendada

Usar al menos 2 camaras y, si es posible, 3 camaras:

| Camara | Posicion | Objetivo |
|---|---|---|
| Camara 1 obligatoria | Lateral derecha, a 2 o 3 metros de la caminadora | Capturar flexion de rodilla, cadera, tobillo e inclinacion del tronco |
| Camara 2 obligatoria | Frontal, a 2 o 3 metros frente a la caminadora | Capturar simetria izquierda/derecha, hombros y desplazamientos laterales |
| Camara 3 recomendada | Lateral izquierda o diagonal posterior | Reducir oclusiones y mejorar triangulacion 3D |

## Distancia y altura

- Distancia sugerida: 2 a 3 metros desde la caminadora.
- Altura lateral sugerida: cerca de la altura de la cadera o ligeramente por encima.
- Altura frontal sugerida: entre pecho y hombros.
- Evitar contraluz y sombras fuertes.
- Mantener todas las camaras estables usando tripodes o soportes firmes.

## Calibracion con tablero ChArUco

FreeMoCap utiliza calibracion para estimar la posicion relativa de cada camara. Para la Semana 2 se recomienda usar un tablero ChArUco:

1. Imprimir el tablero ChArUco en papel rigido o pegarlo sobre una superficie plana.
2. Verificar que el tablero no este doblado.
3. Mostrar el tablero frente a todas las camaras.
4. Moverlo lentamente por distintas zonas del volumen de captura durante 30 a 60 segundos.
5. Guardar el archivo de calibracion generado por FreeMoCap.

No mover las camaras despues de calibrar. Si una camara cambia de posicion, altura, inclinacion o zoom, se debe repetir la calibracion.

## Carpeta sugerida para sesiones

Guardar las pruebas locales fuera de Git:

```text
sesiones/prueba_caminadora/
```

La carpeta `sesiones/` queda preparada en el repositorio, pero su contenido real debe permanecer ignorado por Git para evitar subir videos, reportes o datos sensibles.

## Comandos sugeridos en Windows

Crear y activar entorno:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
```

Ejecutar FreeMoCap:

```powershell
python -m freemocap
```

Algunas versiones o herramientas auxiliares pueden ofrecer comandos para listar camaras. Si estan disponibles en el entorno instalado, se pueden probar:

```powershell
python -m freemocap --list-cameras
```

Si el comando no existe en la version instalada, listar y seleccionar camaras desde la interfaz grafica de FreeMoCap.

## Prueba multicamara

1. Conectar las 2 o 3 camaras antes de abrir FreeMoCap.
2. Verificar que Windows reconozca cada camara.
3. Abrir FreeMoCap.
4. Seleccionar las camaras disponibles desde la interfaz.
5. Calibrar con el tablero ChArUco.
6. Grabar una prueba corta en `sesiones/prueba_caminadora/`.
7. Revisar que las vistas de camara no esten invertidas, oscuras o desenfocadas.

## Recomendaciones para Windows

- Usar puertos USB distintos cuando haya varias camaras USB.
- Evitar hubs USB de baja calidad.
- Cerrar Zoom, Teams, OBS u otras aplicaciones que bloqueen la camara.
- Configurar permisos de camara en Windows.
- Mantener el cargador conectado en laptops.
- Usar una carpeta de ruta corta si aparecen problemas con rutas largas.

## Problema comun: OpenCV sin modulo aruco

La calibracion con tablero ChArUco necesita el modulo `cv2.aruco`, que normalmente viene en `opencv-contrib-python`. Si aparece un error como `AttributeError: module 'cv2' has no attribute 'aruco'`, verificar primero el entorno activo:

```powershell
python -c "import cv2; print(getattr(cv2, '__version__', 'SIN_VERSION')); print(hasattr(cv2, 'aruco'))"
```

Si el resultado final es `False`, puede haber una instalacion de `opencv-python` basica reemplazando a `opencv-contrib-python`. En ese caso, dentro del entorno virtual del proyecto, se puede reinstalar OpenCV contrib:

```powershell
python -m pip uninstall opencv-python opencv-python-headless opencv-contrib-python -y
python -m pip install opencv-contrib-python
```

Hacer este cambio solo dentro del `venv` del proyecto y volver a probar FreeMoCap despues. El `pyproject.toml` del fork ya declara `opencv-contrib-python`, pero una instalacion previa de OpenCV puede dejar el entorno en conflicto.

## Evidencia esperada para la entrega

- Foto o captura del montaje con camara lateral derecha y camara frontal.
- Captura de FreeMoCap detectando las camaras.
- Captura o nota del proceso de calibracion ChArUco.
- Registro de la carpeta local de prueba, sin subir videos al repositorio.
- Observaciones sobre iluminacion, distancia y estabilidad de camaras.

## Limite de alcance

Semana 2 deja implementado y probado el cálculo de ángulos 2D/3D, además de la guía multicámara y ChArUco. El análisis automático de marcha ya fue implementado posteriormente en Semana 4; la calibración física con 2 o 3 cámaras continúa siendo una validación manual del entorno real.
