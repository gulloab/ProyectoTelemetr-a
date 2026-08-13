# Real-Time F1 Telemetry - Driver Comparison

A Python desktop application built with **PyQt6** and **PyQtGraph** for real-time visualization and comparative analysis of Formula 1 telemetry data using the public **OpenF1 API**.

## Features

* **Multithreaded Architecture (Producer-Consumer):** Background API queries ensure smooth UI rendering without freezing or blocking the user interface.
* **Dual-Bus Processing:** Independent data queues (`queue.Queue`) and channels for each driver.
* **Real-Time Dynamic Visualization:**
  * **Engine RPM vs. Speed (km/h)** correlation plot.
  * Driver inputs plot comparing **Throttle vs. Brake** percentages.
* **CSV Data Logging:** Automatic point-by-point recording of speeds, session keys, and timestamped speed-leader metrics saved directly to `comparativa_velocidad.csv`.
* **Session Control:** Interactive Grand Prix selection with real-time telemetry streaming start/pause controls.

## Requirements and Installation

To run this project, install the required dependencies:

```bash
pip install PyQt6 pyqtgraph requests
