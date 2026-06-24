# Perfiles de rehabilitación

Esta carpeta solo debe contener perfiles ficticios utilizados en demostraciones y pruebas automatizadas.

- `paciente_demo.json` no representa a una persona real.
- No guardar aquí cédulas, teléfonos, direcciones, correos ni información clínica identificable.
- Los perfiles reales deben permanecer fuera de GitHub y almacenarse únicamente según las políticas institucionales y la supervisión profesional aplicable.

El sistema es una herramienta de apoyo y no reemplaza la evaluación de un fisioterapeuta.

El formato vigente usa `schema_version: 2`. Cada ejercicio define `rango_inicio`, `rango_objetivo`, `lado`, `histeresis_grados`, `permanencia_ms`, `ciclo_minimo_ms`, `excursion_minima_grados` y `repeticiones_objetivo`. `excursion_minima_grados` evita contar movimientos demasiado cortos desde la referencia inicial calibrada. Los perfiles antiguos con `angulo_minimo`/`angulo_maximo` se aceptan solo para migración en memoria; al guardar se escribe siempre v2.
