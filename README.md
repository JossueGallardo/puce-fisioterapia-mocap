<p align="center">
  <img src="https://github.com/freemocap/freemocap/assets/15314521/da1af7fe-f808-43dc-8f59-c579715d6593" height="160" alt="FreeMoCap Logo">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="https://www.puce.edu.ec/wp-content/uploads/2020/09/logo3.png" height="120" alt="PUCE Logo">
</p>

<h2 align="center">PUCE MoCap Fisioterapia</h2>

<h4 align="center">
Sistema de captura de movimiento para apoyar procesos de rehabilitación fisioterapéutica comunitaria, basado en FreeMoCap.
</h4>

---

## Descripción del proyecto

Este proyecto consiste en la adaptación de **FreeMoCap** para crear un sistema de captura y análisis de movimiento orientado a fisioterapia comunitaria.

El sistema busca apoyar la evaluación de ejercicios físicos, movimientos terapéuticos y análisis de marcha mediante cámaras convencionales, cálculo de ángulos articulares y generación de reportes básicos para seguimiento fisioterapéutico.

El proyecto se desarrolla como parte del programa de **Vinculación con la Comunidad** de la **Pontificia Universidad Católica del Ecuador**, en colaboración con **Fe y Alegría Ecuador**.

---

## Créditos y origen del proyecto

Este repositorio es un fork y adaptación del proyecto original:

**FreeMoCap — Free Motion Capture for Everyone**  
Repositorio original: https://github.com/freemocap/freemocap  
Sitio web: https://freemocap.org  

FreeMoCap fue desarrollado por **Jon Matthis** y el equipo **FreeMoCap**.

La licencia original del proyecto es **AGPLv3**, la cual se mantiene en este fork.

---

## Identificación institucional

- Institución: Pontificia Universidad Católica del Ecuador
- Programa: Vinculación con la Comunidad
- Contraparte: Fe y Alegría Ecuador
- Año: 2026

---

## Estudiante desarrollador

- Nombre: Jossue Hermel Gallardo Toro
- Carrera: Ingeniería en Sistemas de Información
- Tutor: RODRIGUEZ CLAVIJO FRANCISCO

---

## Logo institucional

El proyecto utiliza el logo institucional de la Pontificia Universidad Católica del Ecuador desde el sitio oficial de la PUCE.

<p align="center">
  <img src="https://www.puce.edu.ec/wp-content/uploads/2020/09/logo3.png" height="120" alt="PUCE Logo">
</p>

---

## Objetivo general

Adaptar un sistema de captura de movimiento basado en FreeMoCap para analizar movimientos corporales en ejercicios físicos, rehabilitación fisioterapéutica y marcha en caminadora, con el propósito de apoyar procesos de evaluación y seguimiento en comunidades con recursos limitados.

---

## Objetivos específicos

- Implementar un módulo inicial de análisis de ejercicios físicos mediante cálculo de ángulos articulares.
- Adaptar el sistema a ejercicios de rehabilitación fisioterapéutica con rangos configurables por paciente.
- Desarrollar un módulo de análisis de marcha en caminadora utilizando captura de movimiento.
- Generar reportes básicos de sesión que permitan visualizar el desempeño y progreso del paciente.
- Personalizar el sistema con identidad institucional de la Pontificia Universidad Católica del Ecuador.

---

## Módulos del proyecto

### Módulo 1: Sistema de análisis de ejercicios con pesas

Este módulo permite analizar ejercicios físicos básicos mediante captura de movimiento y cálculo de ángulos articulares.

Ejercicios considerados:

- Sentadilla
- Press de hombro
- Peso muerto

Funciones principales:

- Captura del movimiento con cámara.
- Extracción del esqueleto 3D.
- Cálculo de ángulos articulares.
- Indicador visual de postura correcta o incorrecta.
- Texto de retroalimentación para el usuario.
- Contador de repeticiones.
- Porcentaje de la sesión en posición correcta.

---

### Módulo 2: Adaptación a rehabilitación fisioterapéutica

Este módulo adapta el sistema a ejercicios de fisioterapia, donde los rangos de movimiento dependen del paciente, la lesión y la indicación del fisioterapeuta.

Ejercicios considerados:

- Flexión de codo
- Abducción de hombro
- Rotación de muñeca
- Extensión de rodilla
- Dorsiflexión de tobillo
- Elevación de pierna recta

Funciones principales:

- Creación de perfiles de pacientes en formato JSON.
- Configuración de ángulos mínimos y máximos por ejercicio.
- Registro del ángulo máximo alcanzado.
- Comparación con sesiones anteriores.
- Reporte simple en PDF o CSV.

Ejemplo de perfil de paciente:

```python
perfil_paciente = {
    "nombre": "Juan Perez",
    "lesion": "Fractura de radio distal",
    "ejercicios": {
        "flexion_codo": {
            "angulo_minimo": 30,
            "angulo_maximo": 120,
            "repeticiones_objetivo": 10
        }
    }
}
```

---

### Módulo 3: Análisis de marcha en caminadora

Este módulo permite analizar la marcha de una persona utilizando varias cámaras y métricas de movimiento.

Métricas consideradas:

- Inclinación del tronco.
- Ángulo de rodillas.
- Simetría entre pierna izquierda y derecha.
- Longitud del paso.
- Variabilidad del paso.
- Indicadores básicos de riesgo de caída.

Funciones principales:

- Captura con 2 o 3 cámaras.
- Calibración con tablero ChArUco.
- Visualización del esqueleto en tiempo real.
- Panel de métricas de marcha.
- Semáforo de alertas.
- Reporte final de sesión.

---

## Tecnologías utilizadas

- Python 3.10+
- FreeMoCap
- NumPy
- OpenCV
- Matplotlib
- JSON
- Git
- GitHub

---

## Instalación base de FreeMoCap

Para instalar FreeMoCap se puede utilizar el siguiente comando:

```bash
pip install freemocap
```

Para ejecutar la interfaz gráfica:

```bash
freemocap
```

También se puede ejecutar desde el código fuente:

```bash
python -m freemocap
```

---

## Instalación del proyecto desde este repositorio

Clonar el repositorio:

```bash
git clone https://github.com/JossueGallardo/puce-fisioterapia-mocap.git
```

Ingresar a la carpeta del proyecto:

```bash
cd puce-fisioterapia-mocap
```

Crear un entorno virtual:

```bash
python -m venv venv
```

Activar el entorno virtual en Linux o macOS:

```bash
source venv/bin/activate
```

Activar el entorno virtual en Windows:

```bash
venv\Scripts\activate
```

Instalar dependencias del proyecto:

```bash
pip install -e .
```

Ejecutar FreeMoCap desde el código fuente:

```bash
python -m freemocap
```

---

## Personalización del repositorio

Este fork será personalizado con:

- README institucional.
- Logo de la Pontificia Universidad Católica del Ecuador.
- Créditos al proyecto original FreeMoCap.
- Pantalla de inicio con identidad PUCE.
- Código para análisis de ángulos articulares.
- Módulo de ejercicios con pesas.
- Módulo de rehabilitación fisioterapéutica.
- Módulo de análisis de marcha en caminadora.
- Reportes básicos por sesión.

---

## Estructura esperada del proyecto

```text
puce-fisioterapia-mocap/
│
├── freemocap/
│
├── README.md
├── LICENSE
└── ...
```

---

## Ejemplo de cálculo de ángulo

El sistema utilizará coordenadas 3D de las articulaciones para calcular ángulos corporales.

```python
import numpy as np

def calcular_angulo(punto_a, punto_b, punto_c):
    """
    Calcula el ángulo en el punto B formado por los puntos A-B-C.
    Cada punto debe tener coordenadas [x, y, z].
    """
    vector_ba = np.array(punto_a) - np.array(punto_b)
    vector_bc = np.array(punto_c) - np.array(punto_b)

    coseno = np.dot(vector_ba, vector_bc) / (
        np.linalg.norm(vector_ba) * np.linalg.norm(vector_bc)
    )

    angulo = np.degrees(np.arccos(np.clip(coseno, -1.0, 1.0)))

    return angulo
```

Ejemplo aplicado a una sentadilla:

```python
angulo_rodilla = calcular_angulo(cadera, rodilla, tobillo)

if 70 <= angulo_rodilla <= 100:
    estado = "CORRECTO"
else:
    estado = "CORREGIR POSTURA"
```

---

## Cronograma general

| Semana | Actividad principal | Entregable |
|---|---|---|
| Semana 1 | Instalación de FreeMoCap, prueba con una cámara y personalización del repositorio | Repositorio personalizado y sistema corriendo con una cámara |
| Semana 2 | Configuración de 2 a 3 cámaras, calibración y función de cálculo de ángulos | Sistema multicámara calibrado y función de ángulos validada |
| Semana 3 | Desarrollo del módulo de ejercicios con pesas | Módulo de pesas completo con identidad PUCE |
| Semana 4 | Desarrollo del módulo de análisis de marcha en caminadora | Módulo de caminadora funcionando con métricas en pantalla |
| Semana 5 | Adaptación a fisioterapia con perfiles y reportes | Módulo de fisioterapia completo |
| Semana 6 | Pruebas integrales y ajustes | Sistema validado en entorno real |
| Semana 7 | Documentación final y preparación de demo | Repositorio final y demo lista |

---

## Estado del proyecto

Actualmente el proyecto se encuentra en fase inicial de personalización del fork y preparación del entorno de desarrollo.

---

## Licencia

Este proyecto mantiene la licencia original **AGPLv3** de FreeMoCap.

Ver archivo `LICENSE` para más información.

---

## Referencias

- FreeMoCap: https://github.com/freemocap/freemocap
- Sitio oficial de FreeMoCap: https://freemocap.org
- MediaPipe: https://github.com/google-ai-edge/mediapipe
- OpenPose: https://github.com/CMU-Perceptual-Computing-Lab/openpose
- EasyMocap: https://github.com/zju3dv/EasyMocap
- Open Mocap Blender: https://github.com/Larenju-Rai/open-mocap-blender
