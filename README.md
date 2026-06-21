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

Los logos institucionales usados por las interfaces están disponibles en `assets/`:

- `assets/logo_puce.png`
- `assets/logo_fe_alegria.png`

Las interfaces de Pesas, Rehabilitación, Caminadora y el menú principal cargan estos archivos sin modificar el núcleo de FreeMoCap.

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
- Integrar los módulos de pesas, rehabilitación y marcha desde un menú principal.

## Módulos del Proyecto

### Módulo 1: Análisis de ejercicios con pesas

Análisis mediante ciclos completos `inicio -> objetivo -> inicio`, control de forma independiente y retroalimentación visual en español. La interfaz Qt admite mouse, escalado HiDPI, cámara MediaPipe y sesiones 3D procesadas por FreeMoCap. La cámara y el registro se inician de forma explícita; entrar al módulo no contabiliza datos.

Comando principal del producto final de Semana 3:

```powershell
python -m puce_mocap.modulo_pesas_app
```

Ejercicios implementados:

- Sentadilla.
- Press de hombro.
- Peso muerto.

### Módulo 2: Rehabilitación fisioterapéutica

Ejercicios terapéuticos con perfiles JSON v2, rangos separados de inicio/objetivo, sesión acumulada y reporte CSV. La interfaz permite editar datos del paciente, lado, repeticiones y rangos antes de comenzar. Los perfiles v1 se migran en memoria y la rotación de muñeca requiere calibración neutral.

Comando principal del producto de Semana 5:

```powershell
python -m puce_mocap.modulo_rehabilitacion_app
```

Ejercicios implementados:

- Flexion de codo.
- Abduccion de hombro.
- Rotacion de muñeca.
- Extension de rodilla.
- Dorsiflexion de tobillo.
- Elevacion de pierna recta.

### Módulo 3: Análisis de marcha en caminadora

Análisis temporal de marcha con ángulos suavizados, ciclos por pierna, simetría entre picos y longitud de paso estimada. La cámara MediaPipe sirve como prototipo en vivo y las grabaciones multicámara se importan desde salidas procesadas por FreeMoCap.

Comando principal del producto de Semana 4:

```powershell
python -m puce_mocap.modulo_caminadora_app
```

Metricas implementadas:

- Inclinacion del tronco.
- Ángulo de rodilla derecha.
- Ángulo de rodilla izquierda.
- Asimetria entre ciclos completos de ambas rodillas.
- Longitud de paso estimada, conservando la unidad de la fuente.
- Indicador basico de atencion.

## Tecnologias Usadas

- Python 3.10+
- FreeMoCap
- NumPy
- OpenCV para captura y conversion de imagen, no como framework GUI
- MediaPipe Pose como complemento para el prototipo en vivo
- PySide6 para interfaz, controles, mouse y escalado HiDPI
- Git y GitHub
- pytest
- JSON y CSV para perfiles ficticios y reportes

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
pip install -e ".[puce]"
```

Ejecutar FreeMoCap:

```powershell
python -m freemocap
```

Ejecutar pruebas del modulo PUCE:

```powershell
python -m pytest
```

Ejecutar el sistema integrado desde el menú principal gráfico:

```powershell
python -m puce_mocap.main_menu
# equivalente tras instalar:
puce-mocap
```

La ventana Qt mantiene los tres modulos como paginas de un mismo proceso, con botones reales, atajos y diseño adaptable. MediaPipe se carga en un worker y FreeMoCap original se abre de forma asincrona en un proceso separado.

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

Ejecutar el producto final del Módulo 1 con dashboard en vivo:

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

Ejecutar la demo de rehabilitacion sin camara:

```powershell
python examples\semana_5_rehab_demo.py
```

Ejecutar la interfaz final de rehabilitacion:

```powershell
python -m puce_mocap.modulo_rehabilitacion_app
```

Ejecutar las verificaciones integrales sin camara:

```powershell
python examples\semana_6_smoke_check.py
```

## Estado Actual del Proyecto

Implementado:

- README institucional con creditos a FreeMoCap.
- Carpeta `assets/` preparada para logos reales.
- Documentacion de Semana 1 para instalacion y prueba con una camara.
- Documentacion de Semana 2 para multicamara y calibracion ChArUco.
- Módulo `puce_mocap.angle_utils` con cálculo de ángulos 2D y 3D.
- Pruebas unitarias con pytest para calculo de angulos.
- Ejemplo ejecutable con puntos simulados de rodilla.
- Base de Semana 3 para ejercicios con pesas: sentadilla, press de hombro y peso muerto.
- Motor temporal con EMA, histeresis y conteo de ciclos completos.
- Interfaz PySide6 con identidad PUCE, mouse, HiDPI y worker de camara.
- Importacion de `output_data/*_body_3d_xyz.npy` generado por FreeMoCap.
- Wrapper de compatibilidad para el demo real en vivo de Semana 3.
- Adaptador inicial para conectar diccionarios 3D de FreeMoCap con las reglas del modulo de pesas.
- Análisis temporal de marcha con ciclos, buffers acotados, unidades y reportes v2.
- Perfiles de rehabilitacion v2, migracion v1 y calibracion relativa de muñeca.
- Menú principal gráfico integrado, coherente con los dashboards, para abrir los tres módulos PUCE y FreeMoCap original.
- Semana 6 preparada con smoke check, pruebas de importación, menú gráfico y protocolo de cinco sesiones ficticias.
- Carpeta `sesiones/` preparada para pruebas locales no versionadas.

Pendiente manual:

- Probar manualmente las tres interfaces con camara en el entorno fisico.
- Probar configuracion multicamara con tablero ChArUco.
- Ejecutar y documentar las cinco sesiones ficticias del protocolo de Semana 6.
- Validar con el fisioterapeuta todos los rangos provisionales antes de uso clinico.

## Datos locales y reportes

Los CSV v2 se guardan en el directorio local de datos de la aplicacion, no dentro de la instalacion. En pruebas o despliegues puede definirse `PUCE_MOCAP_DATA_DIR`. Los reportes incluyen nombre y lesion por decision del proyecto, por lo que deben tratarse como datos sensibles y nunca subirse a Git.

## Estado por Semana

| Semana | Actividad principal | Entregable | Estado actual |
|---|---|---|---|
| Semana 1 | Personalización inicial, instalación y prueba con una cámara | Repositorio institucional y FreeMoCap probado con una cámara | Implementada; conservar evidencia física |
| Semana 2 | Ángulos 2D/3D, multicámara y ChArUco | Ángulos validados y guía multicámara | Implementada; calibración física pendiente |
| Semana 3 | Ejercicios con pesas | Dashboard con cámara, reglas, métricas y CSV | Implementada |
| Semana 4 | Marcha en caminadora | Métricas de marcha, alertas y CSV | Implementada con una cámara; multicámara pendiente |
| Semana 5 | Rehabilitación con perfiles JSON | Seis ejercicios, rangos, historial y CSV | Implementada |
| Semana 6 | Pruebas integrales | Smoke check, menú gráfico y protocolo de cinco sesiones | Preparada; sesiones físicas pendientes |
| Semana 7 | Documentación final y demo | Repositorio final y casa abierta | No implementada todavía |

## Documentacion del Proyecto
- [Menú principal integrado](docs/menu_principal.md)
- [Semana 1 - Prueba con una camara](docs/semana_1_prueba_una_camara.md)
- [Semana 2 - Multicamara y calibracion ChArUco](docs/semana_2_multicamara_charuco.md)
- [Semana 3 - Módulo de ejercicios con pesas](docs/semana_3_modulo_pesas.md)
- [Semana 4 - Módulo de caminadora](docs/semana_4_modulo_caminadora.md)
- [Semana 5 - Módulo de rehabilitación](docs/semana_5_modulo_rehabilitacion.md)
- [Semana 6 - Pruebas integrales](docs/semana_6_pruebas_integrales.md)
- [Assets institucionales](assets/README.md)

## Estructura PUCE Agregada

```text
puce-fisioterapia-mocap/
├── assets/
│   ├── logo_puce.png
│   ├── logo_fe_alegria.png
│   └── README.md
├── docs/
│   ├── semana_1_prueba_una_camara.md
│   ├── semana_2_multicamara_charuco.md
│   ├── semana_3_modulo_pesas.md
│   ├── semana_4_modulo_caminadora.md
│   ├── semana_5_modulo_rehabilitacion.md
│   ├── semana_6_pruebas_integrales.md
│   └── menu_principal.md
├── examples/
│   ├── semana_2_angle_utils_demo.py
│   ├── semana_3_freemocap_adapter_demo.py
│   ├── semana_3_live_pose_exercise_demo.py
│   ├── semana_3_modulo_pesas_demo.py
│   ├── semana_3_overlay_demo.py
│   ├── semana_4_gait_analyzer_demo.py
│   ├── semana_4_modulo_caminadora_demo.py
│   ├── semana_5_rehab_demo.py
│   ├── semana_6_smoke_check.py
│   └── menu_principal_demo.py
├── profiles/
│   ├── paciente_demo.json
│   └── README.md
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
│   ├── main_menu.py
│   ├── modulo_caminadora_app.py
│   ├── modulo_pesas_app.py
│   ├── modulo_rehabilitacion_app.py
│   ├── rehab_analyzer.py
│   ├── rehab_profiles.py
│   ├── rehab_report.py
│   └── rehab_session.py
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
    ├── test_gait_session.py
    ├── test_main_menu.py
    ├── test_rehab_analyzer.py
    ├── test_rehab_profiles.py
    ├── test_rehab_session.py
    └── test_smoke_imports.py
```

## Uso del Módulo de Ángulos

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
