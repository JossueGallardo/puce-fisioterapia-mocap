# Semana 1 - Personalización inicial y prueba con una cámara

## Objetivo

Preparar el fork institucional PUCE MoCap Fisioterapia — Fe y Alegría, instalar FreeMoCap en Windows y verificar una primera prueba con una cámara.

## Contexto institucional

- Institución: Pontificia Universidad Católica del Ecuador
- Programa: Vinculación con la Comunidad
- Contraparte: Fe y Alegría Ecuador
- Año: 2026
- Estudiante desarrollador: Jossue Hermel Gallardo Toro
- Carrera: Ingeniería en Sistemas de Información
- Tutor: RODRIGUEZ CLAVIJO FRANCISCO
- Proyecto base: FreeMoCap — Free Motion Capture for Everyone
- Repositorio original: https://github.com/freemocap/freemocap
- Sitio oficial: https://freemocap.org
- Licencia original: AGPLv3

## Requisitos previos

- Windows 10 u 11.
- Python 3.10, 3.11 o 3.12.
- Git instalado.
- Una camara web USB o camara integrada.
- Buena iluminacion frontal.
- Espacio libre para mover brazos y piernas sin obstaculos.

## Crear el entorno virtual

En Windows se recomienda trabajar desde una ruta corta, sin acentos ni
espacios, para evitar fallos de dependencias de vision por computadora:

```powershell
cd D:\mocap\puce-fisioterapia-mocap
python -m venv venv
```

Activar el entorno virtual:

```powershell
venv\Scripts\activate
```

Actualizar pip:

```powershell
python -m pip install --upgrade pip
```

## Instalar dependencias

Instalar el fork en modo editable:

```powershell
pip install -e .
```

Si solo se desea instalar FreeMoCap desde PyPI para una prueba rapida:

```powershell
pip install freemocap
```

## Ejecutar FreeMoCap

Desde el entorno virtual activo:

```powershell
python -m freemocap
```

Tambien se puede ejecutar el comando instalado:

```powershell
freemocap
```

## Prueba con una camara

1. Conectar la camara antes de abrir FreeMoCap.
2. Abrir FreeMoCap con `python -m freemocap`.
3. Verificar que la camara aparezca en la interfaz.
4. Crear o seleccionar una sesion de prueba.
5. Realizar una grabacion corta de 10 a 20 segundos.
6. Revisar que el video se guarde y que el procesamiento no muestre errores obvios.

Usar movimientos simples:

- Levantar un brazo.
- Flexionar levemente las rodillas.
- Caminar uno o dos pasos frente a la camara si el espacio lo permite.

## Comandos recomendados

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
python -m freemocap
```

Para ejecutar las pruebas del proyecto:

```powershell
python -m pytest
```

## Problemas comunes

- **La camara no aparece:** cerrar otras aplicaciones que usen la camara, desconectar y reconectar el dispositivo, reiniciar FreeMoCap.
- **Permisos de camara bloqueados:** revisar Configuracion de Windows > Privacidad y seguridad > Camara.
- **Pantalla negra:** mejorar iluminacion, cambiar puerto USB o probar otra camara.
- **Instalacion lenta:** FreeMoCap usa dependencias pesadas de vision por computadora; esperar a que finalice la instalacion.
- **Error con Python:** verificar que la version sea compatible con el rango indicado por el proyecto.

## Evidencia esperada para la entrega

- Captura de pantalla del repositorio con README institucional.
- Captura de la estructura `assets/`, `docs/`, `puce_mocap/`, `tests/` y `examples/`.
- Captura de FreeMoCap abierto.
- Captura o nota de una grabacion corta realizada con una camara.
- Registro de cualquier problema encontrado y como se resolvio.

## Estado final de Semana 1

La personalización institucional, los créditos, los assets y la guía de instalación están implementados. Los logos `assets/logo_puce.png` y `assets/logo_fe_alegria.png` son utilizados por las interfaces gráficas del proyecto. La evidencia física de FreeMoCap con una cámara debe conservarse como parte de la entrega, sin subir videos de pacientes.

## Advertencia de uso

Esta prueba no genera diagnostico medico. Solo valida la instalacion, la captura basica y la preparacion inicial del repositorio para el proyecto comunitario.
