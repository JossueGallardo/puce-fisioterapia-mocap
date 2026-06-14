# Menú principal gráfico integrado

## Objetivo

Centralizar el acceso a los tres módulos PUCE, FreeMoCap original y las verificaciones técnicas mediante una interfaz OpenCV coherente con los dashboards del proyecto.

## Comando recomendado

```powershell
python -m puce_mocap.main_menu
```

No es necesario escribir opciones en la consola. La selección principal se realiza con el mouse sobre tarjetas gráficas.

## Opciones gráficas

- **Módulo 1 - Ejercicios con pesas:** abre sentadilla, press de hombro y peso muerto.
- **Módulo 2 - Rehabilitación:** abre perfiles ficticios, rangos configurables y seis ejercicios terapéuticos.
- **Módulo 3 - Caminadora:** abre métricas de marcha y semáforo de alertas.
- **FreeMoCap original:** ejecuta `python -m freemocap` sin alterar su núcleo.
- **Verificar entorno:** muestra visualmente OpenCV, `cv2.aruco`, MediaPipe y `pose_landmark_cpu.binarypb`; incluye un botón para ejecutar pytest.
- **Salir del sistema:** cierra el menú de forma segura.

## Funcionamiento

El menú utiliza `subprocess.run` y `sys.executable`. Al abrir un módulo:

1. La ventana del menú se oculta.
2. El módulo seleccionado se ejecuta como proceso independiente.
3. Al presionar `q` o cerrar la ventana del módulo, su proceso termina.
4. El menú gráfico reaparece automáticamente y queda listo para otra selección.

Si un módulo termina con error, el menú vuelve a mostrarse e informa el código de salida en su barra de estado. Un fallo aislado no cierra todo el sistema.

## Interacción alternativa

El mouse es el control principal. También se mantienen teclas y flechas como respaldo de accesibilidad:

- `1` a `6`: activar la opción correspondiente.
- Flechas: cambiar la selección.
- `Enter`: abrir la tarjeta seleccionada.
- `Esc` o `q`: salir o volver desde la verificación.

## Wrapper opcional

```powershell
python examples\menu_principal_demo.py
```

## Evidencias esperadas

- Pantalla gráfica con logos PUCE y Fe y Alegría.
- Las seis tarjetas visibles sin superposición.
- Selección de cada módulo con el mouse.
- Menú oculto mientras un módulo está abierto.
- Regreso automático al cerrar Pesas, Rehabilitación o Caminadora.
- Vista gráfica de verificación con OpenCV, ArUco, MediaPipe y pytest.
- Créditos visibles a FreeMoCap, Jon Matthis y equipo FreeMoCap, con licencia AGPLv3.
