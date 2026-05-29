# PUCE MoCap Fisioterapia — Fe y Alegría

Sistema de captura de movimiento para apoyar procesos de rehabilitación fisioterapéutica comunitaria, basado en FreeMoCap.

Este repositorio es un fork y adaptación académica de **FreeMoCap — Free Motion Capture for Everyone**. El objetivo es construir, de forma incremental, herramientas simples para analizar movimiento humano mediante cámaras convencionales, ángulos articulares y reportes básicos de seguimiento.

> Nota etica: este software es una herramienta de apoyo academico/comunitario. No reemplaza la evaluacion de un fisioterapeuta, no emite diagnosticos medicos y no debe usarse para guardar datos reales de pacientes en GitHub.

## Créditos y Origen

- Proyecto base: **FreeMoCap — Free Motion Capture for Everyone**
- Repositorio original: https://github.com/freemocap/freemocap
- Sitio oficial: https://freemocap.org
- Autores: Jon Matthis y equipo FreeMoCap
- Licencia original: **AGPLv3**

Este fork mantiene la licencia AGPLv3 y conserva la trazabilidad hacia el proyecto original FreeMoCap. No se deben eliminar archivos legales, creditos, codigo de conducta ni referencias al proyecto base.

## Identificación Institucional

- Institución: Pontificia Universidad Católica del Ecuador
- Programa: Vinculación con la Comunidad
- Contraparte: Fe y Alegría Ecuador
- Año: 2026
- Estudiante desarrollador: Jossue Hermel Gallardo Toro
- Carrera: Ingeniería en Sistemas de Información
- Tutor: RODRIGUEZ CLAVIJO FRANCISCO

Los logos institucionales reales deben agregarse manualmente en `assets/`:

- `assets/logo_puce.png`
- `assets/logo_fe_alegria.png`

No se incluyen logos descargados de internet en este repositorio.

## Descripción del Sistema

PUCE MoCap Fisioterapia — Fe y Alegría busca adaptar FreeMoCap para apoyar actividades de fisioterapia comunitaria. El sistema se orienta a:

- Capturar movimiento corporal con una o varias camaras.
- Usar coordenadas 3D del esqueleto para calcular angulos articulares.
- Evaluar ejercicios fisicos y terapeuticos con mensajes claros en español.
- Documentar sesiones de prueba sin almacenar datos sensibles en el repositorio.
- Preparar una base tecnica para analisis de marcha en caminadora.

## Objetivo General

Adaptar un sistema de captura de movimiento basado en FreeMoCap para analizar movimientos corporales en ejercicios físicos, rehabilitación fisioterapéutica y marcha en caminadora, con el propósito de apoyar procesos de evaluación y seguimiento comunitario bajo supervisión profesional.

## Objetivos Específicos

- Implementar una base de cálculo de ángulos articulares con NumPy.
- Preparar documentación de instalación y prueba inicial con una cámara.
- Documentar la configuración multicámara y la calibración con tablero ChArUco.
- Mantener separada la personalizacion PUCE del nucleo original de FreeMoCap.
- Preparar el proyecto para modulos posteriores de pesas, rehabilitacion y marcha.

## Modulos del Proyecto

### Modulo 1: Analisis de ejercicios con pesas

Analisis de ejercicios fisicos basicos mediante angulos articulares, indicador correcto/incorrecto y retroalimentacion visual en español. La Semana 3 / Modulo 1 incluye datos simulados, reporte CSV y una interfaz final en vivo tipo dashboard con camara, logos institucionales, esqueleto superpuesto y MediaPipe Pose como complemento.

Comando principal del producto final de Semana 3:

```powershell
python -m puce_mocap.modulo_pesas_app
```

Ejercicios previstos:

- Sentadilla.
- Press de hombro.
- Peso muerto.

### Modulo 2: Rehabilitacion fisioterapeutica

Ejercicios terapeuticos con rangos configurables por paciente mediante perfiles JSON y reportes simples. Se implementara desde la Semana 5.

Ejercicios previstos:

- Flexion de codo.
- Abduccion de hombro.
- Rotacion de muñeca.
- Extension de rodilla.
- Dorsiflexion de tobillo.
- Elevacion de pierna recta.

### Modulo 3: Analisis de marcha en caminadora

Analisis de marcha con 2 o 3 camaras, calibracion ChArUco, metricas de simetria y longitud de paso. La Semana 4 ya incluye un primer modulo funcional con camara en vivo usando MediaPipe Pose como complemento, semaforo de alertas y reporte CSV.

Comando principal del producto de Semana 4:

```powershell
python -m puce_mocap.modulo_caminadora_app
```

Metricas previstas:

- Inclinacion del tronco.
- Angulo de rodilla derecha.
- Angulo de rodilla izquierda.
- Asimetria entre rodillas.
- Longitud de paso.
- Indicador basico de atencion.

## Tecnologias Usadas

- Python 3.10+
- FreeMoCap
- NumPy
- OpenCV
- MediaPipe Pose como complemento para prototipo en vivo
- PySide6
- Git y GitHub
- pytest
- JSON y CSV para etapas posteriores

## Instalacion Base de FreeMoCap

Instalacion desde PyPI:

```powershell
python -m pip install freemocap
freemocap
```

Ejecucion desde codigo fuente:

```powershell
python -m freemocap
```

## Instalacion del Fork

En Windows se recomienda ubicar el proyecto en una ruta corta, sin acentos ni espacios:

```powershell
D:\mocap\puce-fisioterapia-mocap
```

Evitar usar rutas largas o con caracteres especiales como ruta principal de trabajo, porque algunas dependencias de vision por computadora pueden fallar aunque los archivos existan.

Clonar el repositorio:

```powershell
git clone https://github.com/JossueGallardo/puce-fisioterapia-mocap.git
cd puce-fisioterapia-mocap
```

Crear y activar entorno virtual en Windows:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
```

Instalar el proyecto en modo editable:

```powershell
pip install -e .
```

Ejecutar FreeMoCap:

```powershell
python -m freemocap
```

Ejecutar pruebas del modulo PUCE:

```powershell
python -m pytest
```

Ejecutar el ejemplo de calculo de angulos:

```powershell
python examples\semana_2_angle_utils_demo.py
```

Ejecutar el demo de ejercicios con pesas:

```powershell
python examples\semana_3_modulo_pesas_demo.py
```

Ejecutar el demo visual OpenCV del modulo de pesas:

```powershell
python examples\semana_3_overlay_demo.py
```

Ejecutar el producto final del Modulo 1 con dashboard en vivo:

```powershell
python -m puce_mocap.modulo_pesas_app
```

Ejecutar el wrapper antiguo del demo real en vivo con pose:

```powershell
python examples\semana_3_live_pose_exercise_demo.py
```

Ejecutar el demo del adaptador FreeMoCap:

```powershell
python examples\semana_3_freemocap_adapter_demo.py
```

Ejecutar el demo de consola de marcha en caminadora:

```powershell
python examples\semana_4_gait_analyzer_demo.py
```

Ejecutar la interfaz final de caminadora:

```powershell
python -m puce_mocap.modulo_caminadora_app
```

## Estado Actual del Proyecto

Implementado:

- README institucional con creditos a FreeMoCap.
- Carpeta `assets/` preparada para logos reales.
- Documentacion de Semana 1 para instalacion y prueba con una camara.
- Documentacion de Semana 2 para multicamara y calibracion ChArUco.
- Modulo `puce_mocap.angle_utils` con calculo de angulos 2D y 3D.
- Pruebas unitarias con pytest para calculo de angulos.
- Ejemplo ejecutable con puntos simulados de rodilla.
- Base de Semana 3 para ejercicios con pesas: sentadilla, press de hombro y peso muerto.
- Sesion simple con conteo de repeticiones, porcentaje correcto y reporte CSV.
- Demo visual OpenCV con identidad PUCE para el modulo de pesas.
- Interfaz final de Semana 3 / Modulo 1 con dashboard oscuro, camara en vivo, logos, paneles de estado, ejercicios, metricas y reporte CSV.
- Wrapper de compatibilidad para el demo real en vivo de Semana 3.
- Adaptador inicial para conectar diccionarios 3D de FreeMoCap con las reglas del modulo de pesas.
- Base de Semana 4 / Modulo 3 para analisis de marcha en caminadora: metricas, semaforo, sesion, reporte CSV e interfaz live.
- Carpeta `sesiones/` preparada para pruebas locales no versionadas.

Pendiente manual:

- Verificar manualmente que los logos reales de `assets/` carguen correctamente en la interfaz final.
- Instalar dependencias completas de FreeMoCap en el entorno local.
- Probar fisicamente FreeMoCap con una camara.
- Probar configuracion multicamara con tablero ChArUco.

## Cronograma Resumido de 7 Semanas

| Semana | Actividad principal | Entregable |
|---|---|---|
| Semana 1 | Personalizacion inicial, instalacion y prueba con una camara | Repositorio institucional y FreeMoCap probado con una camara |
| Semana 2 | Funcion de angulos, base de esqueleto 3D, multicamara y ChArUco | Angulos validados y guia multicamara |
| Semana 3 | Ejercicios con pesas | Modulo de pesas con indicador correcto/incorrecto |
| Semana 4 | Marcha en caminadora | Metricas de marcha y alertas basicas |
| Semana 5 | Rehabilitacion con perfiles JSON | Rangos terapeuticos configurables y reporte simple |
| Semana 6 | Pruebas integrales | Validacion bajo supervision y ajustes |
| Semana 7 | Documentacion final y demo | Repositorio final y demo lista |

## Documentacion del Proyecto

- [Semana 1 - Prueba con una camara](docs/semana_1_prueba_una_camara.md)
- [Semana 2 - Multicamara y calibracion ChArUco](docs/semana_2_multicamara_charuco.md)
- [Semana 3 - Modulo de ejercicios con pesas](docs/semana_3_modulo_pesas.md)
- [Semana 4 - Modulo de caminadora](docs/semana_4_modulo_caminadora.md)
- [Assets institucionales](assets/README.md)

## Estructura PUCE Agregada

```text
puce-fisioterapia-mocap/
├── assets/
│   ├── .gitkeep
│   └── README.md
├── docs/
│   ├── semana_1_prueba_una_camara.md
│   ├── semana_2_multicamara_charuco.md
│   ├── semana_3_modulo_pesas.md
│   └── semana_4_modulo_caminadora.md
├── examples/
│   ├── semana_2_angle_utils_demo.py
│   ├── semana_3_freemocap_adapter_demo.py
│   ├── semana_3_live_pose_exercise_demo.py
│   ├── semana_3_modulo_pesas_demo.py
│   ├── semana_3_overlay_demo.py
│   ├── semana_4_gait_analyzer_demo.py
│   └── semana_4_modulo_caminadora_demo.py
├── puce_mocap/
│   ├── __init__.py
│   ├── angle_utils.py
│   ├── exercise_report.py
│   ├── exercise_rules.py
│   ├── exercise_session.py
│   ├── freemocap_adapter.py
│   ├── gait_analyzer.py
│   ├── gait_report.py
│   ├── gait_session.py
│   ├── modulo_caminadora_app.py
│   └── modulo_pesas_app.py
├── reports/
│   └── .gitkeep
├── sesiones/
│   └── .gitkeep
└── tests/
    ├── test_angle_utils.py
    ├── test_exercise_rules.py
    ├── test_exercise_session.py
    ├── test_freemocap_adapter.py
    ├── test_gait_analyzer.py
    └── test_gait_session.py
```

## Uso del Modulo de Angulos

```python
from puce_mocap.angle_utils import calcular_angulo

cadera = [0.0, 1.0, 0.0]
rodilla = [0.0, 0.0, 0.0]
tobillo = [1.0, 0.0, 0.0]

angulo_rodilla = calcular_angulo(cadera, rodilla, tobillo)
print(angulo_rodilla)
```

## Privacidad y Seguridad

- No subir videos de pacientes al repositorio.
- No subir reportes reales.
- No subir perfiles reales con nombres, cedulas, telefonos o direcciones.
- Usar datos ficticios en ejemplos y pruebas.
- Toda interpretacion clinica debe quedar bajo supervision de un fisioterapeuta.

## Licencia

Este proyecto mantiene la licencia original **GNU Affero General Public License v3.0 (AGPLv3)** de FreeMoCap.

Ver el archivo [LICENSE](LICENSE).
