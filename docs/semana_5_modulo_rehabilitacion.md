# Semana 5 - Módulo de rehabilitación fisioterapéutica

> Actualización 2026: los perfiles vigentes usan `schema_version: 2`, rangos separados de inicio/objetivo y ciclos completos. La interfaz permite editar paciente, rangos, lado y repeticiones antes de iniciar. La rotación de muñeca es relativa a una calibración neutral.

## Objetivo

Implementar el Módulo 2 de la guía PUCE - Fe y Alegría con perfiles JSON ficticios, seis ejercicios terapéuticos, rangos configurables y reporte CSV por sesión.

FreeMoCap se mantiene como proyecto base. La interfaz en vivo usa MediaPipe Pose como complemento para obtener articulaciones desde una cámara sin modificar el núcleo original de FreeMoCap.

## Relación con el Módulo 2 de la guía

La diferencia principal frente al módulo de pesas es que los rangos no están fijados en el código. Cada perfil define el ángulo mínimo, ángulo máximo y repeticiones objetivo de los ejercicios prescritos para una demostración o prueba supervisada.

El sistema no diagnostica lesiones ni reemplaza la evaluación profesional. Los resultados indican únicamente si el ángulo observado está dentro o fuera del rango configurado.

## Perfiles JSON

El perfil ficticio incluido se encuentra en:

```text
profiles/paciente_demo.json
```

Contiene:

- nombre ficticio;
- código de prueba;
- descripción de caso ficticio;
- observaciones sin datos reales;
- rangos y repeticiones objetivo por ejercicio.

Las funciones de `puce_mocap/rehab_profiles.py` permiten cargar, guardar, validar y crear perfiles demo. Si falta un campo obligatorio o un rango no es válido, se genera un `ValueError` claro.

## Privacidad

- No guardar cédulas, teléfonos, direcciones, correos ni nombres reales en GitHub.
- No subir perfiles reales, videos de pacientes o reportes identificables.
- `profiles/*.json` está ignorado por Git, excepto `profiles/paciente_demo.json`.
- Las pruebas y evidencias deben usar personas voluntarias o datos ficticios según la supervisión institucional aplicable.

## Ejercicios implementados

1. Flexión de codo.
2. Abducción de hombro.
3. Rotación de muñeca aproximada con puntos visibles de la mano.
4. Extensión de rodilla.
5. Dorsiflexión de tobillo.
6. Elevación de pierna recta con comprobación básica de extensión de rodilla.

Todos los cálculos reutilizan `puce_mocap.angle_utils.calcular_angulo` o `calcular_angulo_vectores`.

## Encuadre mínimo

No todos los ejercicios requieren el cuerpo entero ni estar de pie. MediaPipe debe detectar con suficiente confianza únicamente estas articulaciones del lado configurado:

| Ejercicio | Articulaciones requeridas | Puede realizarse sentado |
|---|---|---|
| Flexión de codo | Hombro, codo y muñeca | Sí |
| Abducción de hombro | Cadera, hombro y codo | Sí |
| Rotación de muñeca | Codo, muñeca, índice y meñique | Sí |
| Extensión de rodilla | Cadera, rodilla y tobillo | Sí |
| Dorsiflexión de tobillo | Rodilla, tobillo y punta del pie | Sí |
| Elevación de pierna recta | Cadera, rodilla y tobillo | Depende de la posición indicada por el fisioterapeuta |

Al pulsar `Iniciar ejercicio`, el sistema calibra automáticamente como referencia la primera postura válida, estable y situada fuera del rango objetivo. Debe mantenerse aproximadamente `200 ms`. El retorno de cada repetición se compara con esta referencia medida, no con la coincidencia exacta del rango inicial teórico.

El rango inicial del perfil se conserva como guía y para compatibilidad con perfiles anteriores. Si la persona ya está dentro del rango objetivo al iniciar, la interfaz solicita adoptar primero una postura cómoda de reposo fuera de ese rango. No es necesario alcanzar exactamente valores rígidos como `160°–180°`.

Los fotogramas aislados, las articulaciones fuera del encuadre y las detecciones de baja confianza no calibran el inicio ni completan una repetición.

La opción `Extremidad evaluada` no indica cómo debe orientarse la persona. Sus valores son:

- `Automático`: utiliza la extremidad requerida con mejor visibilidad y conserva la selección mientras ambas tengan una confianza similar.
- `Derecho`: analiza únicamente la extremidad derecha de la persona.
- `Izquierdo`: analiza únicamente la extremidad izquierda de la persona.

Orientación recomendada:

- Vista frontal: flexión de codo, abducción de hombro y rotación de muñeca.
- Vista lateral u oblicua: extensión de rodilla, dorsiflexión de tobillo y elevación de pierna recta.

La previsualización puede estar espejada como un espejo, pero `derecho` e `izquierdo` siempre se refieren al cuerpo de la persona observada.

## Estados visuales

- Verde: `DENTRO_DEL_RANGO`.
- Amarillo: `FUERA_DEL_RANGO`.
- Rojo: `POSTURA_INCOMPLETA`.

Una postura incompleta indica las articulaciones concretas que deben permanecer visibles y no se cuenta como fotograma válido.

## Interfaz en vivo

Comando final:

```powershell
python -m puce_mocap.modulo_rehabilitacion_app
```

Controles principales:

- `Iniciar cámara` abre únicamente la cámara detectada que seleccione el usuario.
- `Iniciar ejercicio` habilita el registro y el conteo.
- Los formularios permiten editar datos del paciente, rangos de inicio/objetivo, lado y repeticiones.
- `Calibrar muñeca` aparece para la rotación de muñeca.
- `Cargar perfil` y `Guardar perfil` administran archivos JSON fuera del repositorio.

La pantalla muestra identidad PUCE + Fe y Alegría, cámara con esqueleto, perfil ficticio, ejercicio actual, ángulo, rango objetivo, estado, repeticiones, porcentaje dentro del rango, ángulo máximo y frames válidos.

El módulo también se abre seleccionando su tarjeta con el mouse desde:

```powershell
python -m puce_mocap.main_menu
```

El reporte conserva el historial de sesiones en el mismo CSV y, cuando existe una sesión anterior comparable del mismo ejercicio, informa de manera neutral el aumento, disminución o ausencia de cambio en el ángulo máximo alcanzado.

## Demo sin cámara

```powershell
python examples\semana_5_rehab_demo.py
```

La demo presenta un caso dentro del rango, otro fuera del rango, postura incompleta, resumen de sesión y generación de CSV.

## Pruebas

```powershell
python -m pytest
```

Las pruebas cubren perfiles, campos obligatorios, evaluación de flexión de codo, postura incompleta, acumulación de sesión y exportación del resumen.

## Evidencias esperadas

- Perfil ficticio abierto en un editor.
- Demo de consola con los tres estados.
- Interfaz en vivo con logos y esqueleto.
- Captura verde dentro del rango.
- Captura amarilla fuera del rango.
- Captura roja con postura incompleta.
- Métricas de sesión visibles.
- CSV generado y abierto sin datos reales.
- `pytest` aprobado.

## Limitaciones

- Las métricas de una cámara son aproximadas y dependen de iluminación, encuadre y visibilidad.
- La rotación de muñeca se aproxima con landmarks de Pose y no sustituye una medición clínica específica.
- Los rangos del perfil demo son únicamente ejemplos ficticios.
- La comparación incluida usa únicamente el ángulo máximo de la sesión anterior del mismo ejercicio; no interpreta progreso clínico.

## Seguridad y alcance

Este módulo es una herramienta académica y comunitaria de apoyo. Toda interpretación y ajuste de rangos debe realizarse bajo supervisión de un fisioterapeuta.
