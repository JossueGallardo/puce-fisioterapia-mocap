# Semana 6 - Pruebas integrales y ajustes

## Objetivo

Dejar preparado un protocolo repetible para comprobar que los tres módulos, el menú, FreeMoCap y los reportes funcionan juntos sin usar datos reales ni presentar conclusiones clínicas.

## Checklist técnico

- [ ] `python -m freemocap` abre correctamente.
- [ ] `python -m puce_mocap.modulo_pesas_app` abre y cierra con `q`.
- [ ] `python -m puce_mocap.modulo_rehabilitacion_app` abre con el perfil demo.
- [ ] `python -m puce_mocap.modulo_caminadora_app` abre y cierra con `q`.
- [ ] `python -m puce_mocap.main_menu` abre la interfaz gráfica, permite seleccionar con mouse y recupera el control al cerrar cada módulo.
- [ ] `python -m pytest` termina sin fallos.
- [ ] Los tres reportes CSV se generan en `reports/`.
- [ ] Los logos PUCE y Fe y Alegría cargan en los dashboards.
- [ ] `cv2.aruco` está disponible.
- [ ] MediaPipe encuentra `pose_landmark_cpu.binarypb`.
- [ ] No existen videos, perfiles reales ni datos identificables preparados para commit.

## Smoke check sin cámara

```powershell
python examples\semana_6_smoke_check.py
```

Este comando comprueba imports, carpetas, logos, OpenCV, ArUco y MediaPipe. No abre cámara ni ejecuta la GUI de FreeMoCap.

## Protocolo de cinco sesiones ficticias

Usar códigos `TEST-001` a `TEST-005`. No registrar nombres reales, cédulas, teléfonos, direcciones ni antecedentes clínicos.

| Sesión | Módulo | Escenario ficticio | Comprobación |
|---|---|---|---|
| 1 | Pesas | Sentadilla simulada | Verde/rojo, repeticiones, porcentaje y CSV |
| 2 | Pesas | Press o peso muerto simulado | Cambio de ejercicio y retroalimentación |
| 3 | Rehabilitación | Perfil `PAC-001` | Dentro/fuera de rango, postura incompleta y CSV |
| 4 | Caminadora | Marcha voluntaria de prueba | Métricas, semáforo, sesión y CSV |
| 5 | Menú gráfico integrado | Recorrido por los tres módulos | Selección por mouse, retorno al menú y manejo de cierres |

Para cada sesión registrar únicamente fecha, código ficticio, módulo, comando, resultado técnico, error observado y ajuste propuesto.

## Registro de feedback profesional

El fisioterapeuta puede revisar claridad de mensajes, legibilidad, ergonomía, orden de métricas y utilidad del reporte. No se deben guardar diagnósticos ni información identificable en el repositorio.

Preguntas sugeridas:

1. ¿Los mensajes son comprensibles y no alarmistas?
2. ¿El rango objetivo se distingue con facilidad?
3. ¿Las métricas necesarias están visibles durante la sesión?
4. ¿Qué ajuste de interfaz mejoraría la supervisión?
5. ¿Qué limitación debe mostrarse con mayor claridad?

## Tabla de errores y correcciones

| Fecha | Código ficticio | Módulo | Error observado | Pasos para reproducir | Corrección aplicada | Estado |
|---|---|---|---|---|---|---|
| AAAA-MM-DD | TEST-000 | Ejemplo | Descripción técnica | Pasos sin datos personales | Cambio realizado | Pendiente/Resuelto |

## Seguridad y privacidad

- Realizar pruebas físicas en un espacio despejado y con supervisión autorizada.
- Detener la prueba ante incomodidad; el software no decide si una persona debe continuar.
- No usar textos como diagnóstico, enfermedad detectada, lesión detectada o riesgo grave.
- Mantener videos, reportes reales y perfiles reales fuera de GitHub.
- Usar `D:\mocap\puce-fisioterapia-mocap` como ruta de trabajo recomendada en Windows.

## Limitaciones

- Las pruebas automáticas no validan cámara, iluminación ni precisión clínica.
- MediaPipe con una cámara entrega aproximaciones visuales.
- La validación multicámara ChArUco requiere el montaje físico.
- Cinco sesiones ficticias validan el flujo técnico, no la eficacia clínica.

## Evidencias esperadas

- Captura de pytest aprobado.
- Salida completa del smoke check.
- Menú principal gráfico, selección por mouse y retorno desde cada módulo.
- Dashboard de cada módulo con logos cargados.
- Un CSV ficticio por módulo.
- Checklist firmado o revisado por el responsable del proyecto.
- Tabla de errores actualizada con resultados reales de las pruebas técnicas.

## Estado actual de Semana 6

La estructura técnica está preparada: pruebas automáticas, smoke check, menú gráfico, reportes y protocolo de cinco sesiones ficticias. Semana 6 se considera completamente validada únicamente después de ejecutar las pruebas físicas supervisadas, registrar el feedback y completar la tabla de errores sin incluir datos sensibles.
