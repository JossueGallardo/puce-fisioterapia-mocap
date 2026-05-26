# Semana 3 - Modulo de ejercicios con pesas

## Objetivo

Implementar una base clara y testeable para analizar ejercicios con pesas usando coordenadas 3D simuladas o provenientes gradualmente de FreeMoCap.

Esta semana no modifica el nucleo original de FreeMoCap. La logica institucional se mantiene separada en `puce_mocap/` y reutiliza `puce_mocap.angle_utils` para no duplicar formulas de angulos.

## Contexto institucional

- Institucion: Pontificia Universidad Catolica del Ecuador
- Programa: Vinculacion con la Comunidad
- Contraparte: Fe y Alegria Ecuador
- Año: 2026
- Proyecto base: FreeMoCap - Free Motion Capture for Everyone
- Repositorio original: https://github.com/freemocap/freemocap
- Licencia original: AGPLv3

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

## Archivos principales

- `puce_mocap/exercise_rules.py`: reglas puras de evaluacion.
- `puce_mocap/exercise_session.py`: contador simple de frames correctos, porcentaje y repeticiones.
- `puce_mocap/exercise_report.py`: reporte CSV simple.
- `examples/semana_3_modulo_pesas_demo.py`: demo de consola con esqueletos simulados.
- `examples/semana_3_overlay_demo.py`: demo visual OpenCV con identidad PUCE.
- `tests/test_exercise_rules.py`: pruebas de reglas.
- `tests/test_exercise_session.py`: pruebas de sesion y reporte.

## Comandos

Activar entorno virtual:

```powershell
venv\Scripts\activate
```

Ejecutar pruebas:

```powershell
python -m pytest
```

Ejecutar demo de consola:

```powershell
python examples\semana_3_modulo_pesas_demo.py
```

Ejecutar demo visual OpenCV:

```powershell
python examples\semana_3_overlay_demo.py
```

Cerrar el demo visual con la tecla `q`.

## Evidencias esperadas

- Captura de `python -m pytest` con pruebas aprobadas.
- Captura del demo de consola mostrando estado, angulos y retroalimentacion.
- Archivo `reports/semana_3_demo_report.csv` generado con datos simulados.
- Captura del demo visual OpenCV con el texto `PUCE MoCap - Modulo de Pesas` y `Basado en FreeMoCap`.
- Nota de que FreeMoCap sigue abriendo correctamente y no se modifico su logica interna.

## Limitaciones actuales

- Los esqueletos del demo son simulados.
- El contador de repeticiones es basico: cuenta transiciones de `CORREGIR_POSTURA` a `CORRECTO`.
- La compensacion lumbar del press de hombro se marca como validacion futura si no existen puntos completos del tronco.
- La deteccion de colapso de rodillas en peso muerto requiere vista frontal y puntos izquierdo/derecho confiables.
- La integracion real con datos 3D exportados o capturados por FreeMoCap se hara de forma gradual.

## Seguridad y alcance

Este modulo no reemplaza la evaluacion profesional de un fisioterapeuta. No emite diagnosticos medicos y no debe usarse con datos reales de pacientes sin supervision autorizada.

