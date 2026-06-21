# Semana 4 - Módulo de caminadora y análisis de marcha

> Actualización 2026: la asimetría se calcula entre ciclos completos y la longitud de paso conserva la unidad de la fuente. Antes de dos ciclos por lado estas métricas se muestran como N/D.

## Objetivo

Implementar una primera version funcional del Modulo 3: analisis de marcha en caminadora con metricas en pantalla, semaforo de alertas y reporte CSV.

FreeMoCap sigue siendo el proyecto base para captura de movimiento. Esta version live usa MediaPipe Pose con una camara como complemento incremental, igual que el Modulo 1, sin modificar el nucleo original de FreeMoCap. La integracion profunda con datos 3D multicamara de FreeMoCap queda preparada mediante `puce_mocap/freemocap_adapter.py`.

## Contexto institucional

- Institucion: Pontificia Universidad Catolica del Ecuador
- Programa: Vinculacion con la Comunidad
- Contraparte: Fe y Alegria Ecuador
- Anio: 2026
- Proyecto base: FreeMoCap - Free Motion Capture for Everyone
- Repositorio original: https://github.com/freemocap/freemocap
- Sitio oficial: https://freemocap.org
- Licencia original: AGPLv3

## Relacion con la guia del estudiante

La guia define el Modulo 3 como analisis de marcha en caminadora, idealmente con 2 o 3 camaras calibradas. Esta Semana 4 implementa la base tecnica del modulo:

- calculo de inclinacion del tronco,
- angulo de rodilla derecha,
- angulo de rodilla izquierda,
- asimetria entre rodillas,
- longitud de paso,
- semaforo de alertas,
- interfaz en tiempo real,
- reporte CSV de sesion.

## Configuracion recomendada de camaras

Para el analisis completo se recomienda usar FreeMoCap con varias camaras:

| Camara | Posicion | Objetivo |
|---|---|---|
| Camara 1 obligatoria | Lateral derecha, a 2 o 3 metros de la caminadora | Capturar inclinacion del tronco, flexion de rodilla, cadera y tobillo |
| Camara 2 obligatoria | Frontal, a 2 o 3 metros frente a la caminadora | Observar simetria izquierda/derecha y desplazamientos laterales |
| Camara 3 recomendada | Lateral izquierda o diagonal posterior | Reducir oclusiones y mejorar triangulacion 3D |

## Importancia de ChArUco

La calibracion ChArUco permite que FreeMoCap estime la posicion relativa de cada camara y reconstruya un esqueleto 3D mas confiable. Para pruebas reales de caminadora:

1. Colocar las camaras en tripodes o soportes firmes.
2. No moverlas despues de calibrar.
3. Mover el tablero ChArUco por el volumen de captura durante 30 a 60 segundos.
4. Guardar la calibracion localmente.
5. Repetir la calibracion si cambia la posicion de alguna camara.

## Modulos implementados

### Analizador de marcha

Archivo:

```text
puce_mocap/gait_analyzer.py
```

Funcion principal:

```python
analizar_marcha(esqueleto_3d)
```

Recibe un diccionario con coordenadas 2D o 3D y retorna `GaitAnalysisResult`.

### Sesion

Archivo:

```text
puce_mocap/gait_session.py
```

Acumula frames validos, conteos verde/amarillo/rojo, promedios y duracion.

### Reporte

Archivo:

```text
puce_mocap/gait_report.py
```

Genera:

```text
reports/semana_4_gait_report.csv
```

### Interfaz live

Archivo:

```text
puce_mocap/modulo_caminadora_app.py
```

Comando final:

```powershell
python -m puce_mocap.modulo_caminadora_app
```

El módulo también puede abrirse desde `python -m puce_mocap.main_menu`. Al cerrarlo con `q` o cerrar su ventana, se regresa al menú gráfico.

## Metricas implementadas

- `inclinacion_tronco`
- `angulo_rodilla_derecha`
- `angulo_rodilla_izquierda`
- `asimetria_rodillas`
- `longitud_paso`
- `oscilacion_lateral_cadera`

## Reglas iniciales del semaforo

### Inclinacion del tronco

- Menor o igual a 5 grados: `VERDE / NORMAL`.
- Mayor a 5 y menor o igual a 15 grados: `AMARILLO / ATENCION`.
- Mayor a 15 grados: `ROJO / REVISAR_CON_FISIOTERAPEUTA`.

### Asimetria de rodillas

- Diferencia menor o igual a 10 grados: normal.
- Diferencia mayor a 10 grados: atencion.

### Longitud de paso

- Se calcula como distancia entre tobillos.
- Si no hay datos suficientes, se muestra `N/D` y no se rompe la ejecucion.

## Interfaz

La interfaz de Semana 4 mantiene coherencia visual con el Modulo 1:

- header con logos PUCE y Fe y Alegria,
- camara en vivo con esqueleto superpuesto,
- badge `EN VIVO`,
- panel central de metricas,
- semaforo de alerta,
- panel de controles,
- grafica simple de ciclo de marcha,
- panel inferior de sesion.

Controles por teclado:

- `i`: iniciar sesion.
- `t`: terminar sesion y generar reporte CSV.
- `r`: reiniciar.
- `q`: salir.
- `1`: vista lateral / analisis lateral.
- `2`: vista frontal / analisis frontal.

Si se usa una sola camara, la interfaz muestra:

```text
Modo una camara: metricas aproximadas. Para analisis completo usar 2-3 camaras calibradas.
```

## Comandos

Ejecutar pruebas:

```powershell
python -m pytest
```

Demo de consola con datos simulados:

```powershell
python examples\semana_4_gait_analyzer_demo.py
```

Interfaz final del Modulo 3 / Semana 4:

```powershell
python -m puce_mocap.modulo_caminadora_app
```

Wrapper de compatibilidad:

```powershell
python examples\semana_4_modulo_caminadora_demo.py
```

## Evidencias esperadas

- Captura de `python -m pytest` con pruebas aprobadas.
- Captura del demo de consola mostrando caso normal, asimetria e inclinacion elevada.
- Captura de la interfaz live con camara y esqueleto.
- Captura de `VERDE / NORMAL`.
- Captura de `AMARILLO / ATENCION`.
- Captura de `ROJO / REVISAR`.
- Captura de la grafica simple de ciclo de marcha.
- Archivo `reports/semana_4_gait_report.csv` generado al terminar sesion.
- Nota de que FreeMoCap sigue intacto y no se modifico su nucleo.

## Limitaciones actuales

- El prototipo live usa MediaPipe Pose con una camara como complemento.
- Las metricas con una camara son aproximadas.
- El analisis multicamara completo requiere prueba real con 2 o 3 camaras.
- La calibracion ChArUco real debe hacerse en el entorno fisico.
- La integracion profunda con sesiones 3D exportadas por FreeMoCap queda preparada para una mejora posterior.

## Seguridad y alcance

Este modulo no reemplaza la evaluacion profesional de un fisioterapeuta. No emite diagnosticos medicos, no detecta enfermedades y no debe usarse con datos reales de pacientes sin supervision autorizada.
