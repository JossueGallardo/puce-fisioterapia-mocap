# Semana 3 - Módulo de ejercicios con pesas

> Actualización 2026: la interfaz final usa PySide6 y el conteo exige el ciclo completo inicio-objetivo-inicio. La cámara y el contador requieren inicio explícito. Los rangos y los datos del paciente son editables antes de comenzar. Las secciones OpenCV posteriores describen prototipos históricos, no la GUI vigente.

## Objetivo

Completar el Módulo 1 con una base funcional para analizar ejercicios con pesas, tanto con datos simulados como con un prototipo real en vivo usando cámara, esqueleto superpuesto y retroalimentación visual.

FreeMoCap sigue siendo el proyecto base. Para el prototipo de pose en vivo se usa MediaPipe Pose como complemento ligero, porque permite detectar articulaciones directamente desde la cámara sin modificar el núcleo de FreeMoCap.

## Contexto institucional

- Institución: Pontificia Universidad Católica del Ecuador
- Programa: Vinculación con la Comunidad
- Contraparte: Fe y Alegría Ecuador
- Año: 2026
- Proyecto base: FreeMoCap - Free Motion Capture for Everyone
- Repositorio original: https://github.com/freemocap/freemocap
- Licencia original: AGPLv3

## Qué hace el módulo

- Captura vídeo desde una cámara detectada por el sistema.
- Detecta pose humana en vivo con MediaPipe Pose.
- Dibuja el esqueleto sobre la imagen con OpenCV.
- Convierte landmarks a un diccionario compatible con `exercise_rules.py`.
- Calcula ángulos articulares con `puce_mocap.angle_utils`.
- Muestra indicador verde/rojo, estado, retroalimentación, repeticiones y porcentaje correcto.
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

### Interfaz final en vivo con pose y evaluacion

Archivo principal de Semana 3 / Modulo 1:

```text
puce_mocap/modulo_pesas_app.py
```

Comando final:

```powershell
python -m puce_mocap.modulo_pesas_app
```

También puede abrirse con el mouse desde el menú gráfico integrado:

```powershell
python -m puce_mocap.main_menu
```

Al salir del módulo con `q` o cerrar su ventana, el menú principal vuelve a mostrarse automáticamente.

Esta es la interfaz final de Semana 3 / Modulo 1. Abre la camara 0, detecta el cuerpo con MediaPipe Pose, dibuja el esqueleto sobre la camara, evalua el ejercicio seleccionado y genera `reports/semana_3_live_pose_report.csv` al salir. La pantalla se reorganizo como dashboard profesional en modo oscuro con header institucional, logos PUCE y Fe y Alegria, panel grande de camara, panel central de estado, panel derecho de ejercicios, tarjetas de metricas, leyenda y sesion en curso.

El archivo antiguo queda solo como wrapper de compatibilidad:

```text
examples/semana_3_live_pose_exercise_demo.py
```

Teclas:

- `1`: Sentadilla.
- `2`: Press de hombro.
- `3`: Peso muerto.
- `r`: Reiniciar sesion y contador.
- `q`: Salir y generar reporte CSV.

Si no se detecta postura completa, el sistema muestra:

```text
Alejate de la camara hasta que se vean cabeza, cadera, rodillas, tobillos y pies.
```

Los frames incompletos no se registran como frames correctos ni se usan para el porcentaje correcto de la sesion.

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

## Troubleshooting MediaPipe en Windows

Para Windows se recomienda trabajar desde una ruta corta, sin acentos ni espacios:

```powershell
D:\mocap\puce-fisioterapia-mocap
```

Si MediaPipe falla con `FileNotFoundError: pose_landmark_cpu.binarypb` aunque el archivo exista, mover o copiar el proyecto a una ruta corta como la anterior, o usar una unidad virtual apuntando a esa carpeta limpia.

Antecedente: este problema se observo al trabajar desde la ruta anterior `D:\Respaldo\Jossue Puce\Septimo Semestre\PRÁC.DE SERVICIO COMUNITARIO\puce-fisioterapia-mocap`. Esa ruta no debe usarse como ruta principal.

Si aparecen rutas antiguas dentro de logs o archivos de `venv\Lib\site-packages`, no se corrigen modificando el codigo del proyecto. Eso normalmente indica que el entorno virtual fue copiado desde la ruta anterior; la solucion limpia es recrear el `venv` dentro de `D:\mocap\puce-fisioterapia-mocap`.

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

Interfaz final del Modulo 1:

```powershell
python -m puce_mocap.modulo_pesas_app
```

Wrapper antiguo compatible:

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
- Captura de la interfaz final con header, logos, panel de camara y esqueleto superpuesto.
- Captura `VERDE / CORRECTO`.
- Captura `ROJO / CORREGIR_POSTURA`.
- Captura del contador de repeticiones.
- Captura del porcentaje correcto de sesion.
- Captura del panel de ejercicios con Sentadilla, Press hombro, Peso muerto, Reiniciar y Salir.
- Captura del panel inferior con leyenda y sesion en curso.
- Archivo `reports/semana_3_live_pose_report.csv` generado.
- Nota de que FreeMoCap sigue abriendo correctamente y no se modifico su logica interna.

## Limitaciones actuales

- La interfaz final usa MediaPipe Pose como complemento funcional de camara en vivo, sin modificar el nucleo de FreeMoCap.
- La reconstruccion 3D completa y profunda con FreeMoCap queda pendiente.
- El contador de repeticiones es basico: cuenta transiciones de `CORREGIR_POSTURA` a `CORRECTO`.
- La compensacion lumbar del press de hombro se marca como validacion futura si no existen puntos completos del tronco.
- La deteccion de colapso de rodillas en peso muerto requiere vista frontal y puntos izquierdo/derecho confiables.
- El adaptador FreeMoCap trabaja con diccionarios 3D ya cargados; la lectura automatica de sesiones exportadas se implementara despues de confirmar el formato real de salida.

## Seguridad y alcance

Este modulo no reemplaza la evaluacion profesional de un fisioterapeuta. No emite diagnosticos medicos y no debe usarse con datos reales de pacientes sin supervision autorizada.
