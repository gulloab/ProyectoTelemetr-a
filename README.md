# Panel de Telemetría F1: Verstappen vs Pérez

Este proyecto es una aplicación de escritorio desarrollada en Python que extrae, visualiza y analiza datos de telemetría de Fórmula 1 en tiempo real. Utilizando la API de OpenF1, el sistema establece un duelo de métricas entre los pilotos Max Verstappen (1) y Sergio Pérez (11) a través de una arquitectura concurrente de productor-consumidor.

## Arquitectura del Sistema

El programa está diseñado para procesar datos de forma fluida sin bloquear la interfaz de usuario:

*   **Arquitectura de Doble Bus (Colas):** Utiliza colas independientes (`queue.Queue`) para gestionar la telemetría entrante de cada piloto por separado.
*   **Multithreading (Hilos):** Los datos son solicitados a la API de `openf1.org` mediante hilos dedicados (productores). Esto permite que el ciclo de actualización de la interfaz gráfica y los gráficos (consumidor) se mantenga rápido y reactivo.
*   **Interfaz Gráfica (GUI):** Construida con **PyQt6**, proporcionando controles para la selección de carreras y paneles de lectura de telemetría en vivo.
*   **Gráficos de Alto Rendimiento:** Utiliza **pyqtgraph** para el ploteo en tiempo real de múltiples curvas con muy baja latencia.

## Funcionalidades Principales

*   **Selección de Sesiones:** Permite elegir entre varias carreras de la temporada 2024 (Bahréin, Arabia Saudita, Australia).
*   **Análisis de Correlación (RPM vs Velocidad):** Gráfico en vivo que contrasta las revoluciones del motor con la velocidad actual de cada coche.
*   **Entradas de Pedales (Acelerador y Freno):** Gráfico que muestra las gráficas de presión de freno y porcentaje de aceleración simultáneamente.
*   **Panel de Dominio de Velocidad:** Un calculador automático que lleva la cuenta de cuántas veces un piloto supera en velocidad al otro (Ticks de ventaja).
*   **Registro de Datos (CSV):** Exporta automáticamente la comparativa de velocidades a un archivo `comparativa_velocidad.csv` con marcas de tiempo del sistema y de los servidores de F1.

## Requisitos Previos

Para ejecutar este proyecto, necesitas tener Python 3 instalado y las siguientes bibliotecas de terceros:

```bash
pip install PyQt6 pyqtgraph requests
```

## Ejecución y Uso

1. Inicia la aplicación ejecutando el script principal:
   ```bash
   python Motor-Telemetria_F1.py
   ```
2. En la interfaz principal, utiliza el menú desplegable para **Seleccionar Carrera**.
3. Haz clic en **"Iniciar Duelo (Verstappen vs Pérez)"**. El sistema comenzará a extraer paquetes de telemetría de la API y a dibujar las gráficas.
4. Puedes pausar la extracción de datos sin perder la información ya graficada utilizando el botón **"Detener Telemetría"**.
5. Al finalizar, revisa tu directorio local para encontrar el archivo `comparativa_velocidad.csv` con el registro de análisis.

## Estructura del CSV Generado

El archivo de exportación se guarda en el mismo directorio de ejecución y contiene las siguientes columnas:
* `Timestamp_Sistema`: Hora local en la que se procesó el dato.
* `Timestamp_F1`: Marca de tiempo reportada por la API de Fórmula 1.
* `Session_Key`: Identificador único de la carrera seleccionada.
* `Velocidad_VER` / `Velocidad_PER`: Velocidad registrada de cada piloto.
* `Lider_Velocidad`: Etiqueta que indica quién iba más rápido en esa fracción de segundo (VER, PER o EMPATE).
