# Semana 3 - Modulo de ejercicios con pesas

## Objetivo

Completar el Modulo 1 con una base funcional para analizar ejercicios con pesas, tanto con datos simulados como con un prototipo real en vivo usando camara, esqueleto superpuesto y retroalimentacion visual.

FreeMoCap sigue siendo el proyecto base. Para el prototipo de pose en vivo se usa MediaPipe Pose como complemento ligero, porque permite detectar articulaciones directamente desde la camara sin modificar el nucleo de FreeMoCap. La integracion gradual con datos 3D de FreeMoCap queda preparada mediante `puce_mocap/freemocap_adapter.py`.

## Contexto institucional

- Institucion: Pontificia Universidad Catolica del Ecuador
- Programa: Vinculacion con la Comunidad
- Contraparte: Fe y Alegria Ecuador
- Año: 2026
- Proyecto base: FreeMoCap - Free Motion Capture for Everyone
- Repositorio original: https://github.com/freemocap/freemocap
- Licencia original: AGPLv3

## Que hace el modulo

- Captura video desde la camara 0.
- Detecta pose humana en vivo con MediaPipe Pose.
- Dibuja el esqueleto sobre la imagen con OpenCV.
- Convierte landmarks a un diccionario compatible con `exercise_rules.py`.
- Calcula angulos articulares con `puce_mocap.angle_utils`.
- Muestra indicador verde/rojo, estado, retroalimentacion, repeticiones y porcentaje correcto.
- Genera reportes CSV simples en `reports/`.

## Ejercicios implementados

### Sentadilla

Articulaciones usadas:

- Hombro.
- Cadera.
- Rodilla.
- Tobillo.
- Pie o punta del pie si esta disponible.

Reglas iniciales:

- Rodilla entre 70 y 100 grados en el punto bajo.
- Tobillo con avance aproximado menor o igual a 35 grados.
- Cadera mayor o igual a 45 grados para evitar redondeo excesivo.

### Press de hombro

Articulaciones usadas:

- Hombro.
- Codo.
- Muñeca.
- Cadera y tronco si existen puntos suficientes.

Reglas iniciales:

- Codo cercano a 90 grados en la fase inicial.
- Brazo extendido entre 170 y 180 grados en la fase superior.
- La compensacion corporal queda como validacion gradual cuando existan puntos completos de tronco.

### Peso muerto

Articulaciones usadas:

- Hombros.
- Caderas.
- Rodilla.
- Tobillo.
- Puntos izquierdo y derecho si existen para revisar simetria frontal.

Reglas iniciales:

- Desviacion del tronco menor o igual a 20 grados.
- Angulo de rodilla y cadera calculados para seguimiento.
- Posible colapso de rodillas hacia adentro si la distancia entre rodillas es muy baja frente a la distancia entre tobillos.

## Demos disponibles

### Demo de consola con datos simulados

Archivo:

```text
examples/semana_3_modulo_pesas_demo.py
```

Usa esqueletos 3D ficticios para verificar reglas, sesion, porcentaje correcto, repeticiones y reporte CSV. Es util para pruebas repetibles.

### Demo visual basico

Archivo:

```text
examples/semana_3_overlay_demo.py
```

Abre la camara 0 y muestra identidad PUCE con un indicador visual simulado. No estima pose real; sirve como pantalla base.

### Demo real en vivo con pose y evaluacion

Archivo principal de Semana 3:

```text
examples/semana_3_live_pose_exercise_demo.py
```

Abre la camara 0, detecta el cuerpo con MediaPipe Pose, dibuja el esqueleto, evalua el ejercicio seleccionado y genera `reports/semana_3_live_pose_report.csv` al salir.

Teclas:

- `1`: Sentadilla.
- `2`: Press de hombro.
- `3`: Peso muerto.
- `r`: Reiniciar sesion y contador.
- `q`: Salir y generar reporte CSV.

Si no se detecta postura completa, el sistema muestra `No se detecta postura completa` y ese frame no se registra como correcto.

### Adaptador para datos FreeMoCap

Archivos:

```text
puce_mocap/freemocap_adapter.py
examples/semana_3_freemocap_adapter_demo.py
```

El adaptador recibe un diccionario de articulaciones 3D, normaliza nombres comunes al formato usado por `exercise_rules.py` y permite evaluar sentadilla, press de hombro o peso muerto. No depende todavia de una ruta interna fija de FreeMoCap.

## Dependencias

El entorno actual ya tiene:

- Python 3.12.10.
- NumPy 1.26.2.
- OpenCV contrib 4.8.1.
- `cv2.aruco = True`.

Para el demo live se necesita MediaPipe:

```powershell
python -m pip install mediapipe
```

No cambiar NumPy ni OpenCV si ya estan funcionando con FreeMoCap.

## Comandos

Activar entorno virtual:

```powershell
venv\Scripts\activate
```

Ejecutar pruebas:

```powershell
python -m pytest
```

Demo de consola con datos simulados:

```powershell
python examples\semana_3_modulo_pesas_demo.py
```

Demo visual basico:

```powershell
python examples\semana_3_overlay_demo.py
```

Demo real en vivo:

```powershell
python examples\semana_3_live_pose_exercise_demo.py
```

Demo del adaptador FreeMoCap:

```powershell
python examples\semana_3_freemocap_adapter_demo.py
```

## Evidencias esperadas

- Captura de `python -m pytest` con pruebas aprobadas.
- Captura del demo de consola mostrando estado, angulos y retroalimentacion.
- Captura con esqueleto superpuesto en el demo live.
- Captura `VERDE / CORRECTO`.
- Captura `ROJO / CORREGIR_POSTURA`.
- Captura del contador de repeticiones.
- Captura del porcentaje correcto de sesion.
- Archivo `reports/semana_3_live_pose_report.csv` generado.
- Nota de que FreeMoCap sigue abriendo correctamente y no se modifico su logica interna.

## Limitaciones actuales

- El demo live usa MediaPipe Pose como prototipo funcional de camara en vivo.
- La reconstruccion 3D completa y profunda con FreeMoCap queda pendiente.
- El contador de repeticiones es basico: cuenta transiciones de `CORREGIR_POSTURA` a `CORRECTO`.
- La compensacion lumbar del press de hombro se marca como validacion futura si no existen puntos completos del tronco.
- La deteccion de colapso de rodillas en peso muerto requiere vista frontal y puntos izquierdo/derecho confiables.
- El adaptador FreeMoCap trabaja con diccionarios 3D ya cargados; la lectura automatica de sesiones exportadas se implementara despues de confirmar el formato real de salida.

## Seguridad y alcance

Este modulo no reemplaza la evaluacion profesional de un fisioterapeuta. No emite diagnosticos medicos y no debe usarse con datos reales de pacientes sin supervision autorizada.

