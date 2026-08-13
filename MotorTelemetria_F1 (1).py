import sys
import time
import threading
import queue
import requests
import csv
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import QTimer
import pyqtgraph as pg


API_BASE_URL = "https://api.openf1.org/v1"
DATA_QUEUE_MAX = 20000
POLLING_INTERVAL = 1.0  
MAX_POINTS = 200        


queue_p1 = queue.Queue(maxsize=DATA_QUEUE_MAX)
queue_p2 = queue.Queue(maxsize=DATA_QUEUE_MAX)



def consultar_api_productor(endpoint: str, params: dict, stop_event: threading.Event, driver_num: int, target_queue: queue.Queue, initial_delay: float):
    url = f"{API_BASE_URL}/{endpoint}"
    last_date = None
    
    
    if initial_delay > 0:
        stop_event.wait(initial_delay)
        
    print(f"[*] Hilo iniciado - Buscando telemetría de piloto: {driver_num}...")
    
    while not stop_event.is_set():
        try:
            current_params = params.copy()
            if last_date:
                current_params['date>'] = last_date
                
            response = requests.get(url, params=current_params, timeout=5)
            response.raise_for_status()
            data_chunk = response.json()
            
            if data_chunk and isinstance(data_chunk, list):
                print(f"[API] Hilo Piloto {driver_num} -> Aportando {len(data_chunk)} registros a su bus.")
                
                for pkt in data_chunk:
                    try:
                        target_queue.put(pkt, timeout=1)
                    except queue.Full:
                        pass
                
                if 'date' in data_chunk[-1]:
                    last_date = data_chunk[-1]['date']
            
            
            stop_event.wait(POLLING_INTERVAL)
            
        except Exception as e:
            print(f"[!] Error en Hilo {driver_num}: {e}")
            stop_event.wait(2)


class TelemetryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Análisis - Arquitectura de Doble Bus + Pedales + CSV")
        self.resize(1100, 850)
        
        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)
        self.setCentralWidget(central)

        #seleccionar carrera
        control_layout = QHBoxLayout()
        layout.addLayout(control_layout)
        
        lbl_carrera = QLabel("Seleccionar Carrera:")
        lbl_carrera.setStyleSheet("font-weight: bold; font-size: 14px;")
        control_layout.addWidget(lbl_carrera)
        
        self.combo_sesion = QComboBox()
        
        self.combo_sesion.addItem("Bahrain 2024 (Race)", 9472)
        self.combo_sesion.addItem("Saudi Arabia 2024 (Race)", 9480)
        self.combo_sesion.addItem("Australia 2024 (Race)", 9488)
        control_layout.addWidget(self.combo_sesion)

        self.info_label = QLabel("Motor inactivo. Seleccione carrera y presione Iniciar.")
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        control_layout.addWidget(self.info_label)

        
        self.panel_layout = QHBoxLayout()
        layout.addLayout(self.panel_layout)
        
        self.lbl_ver = QLabel("VER - RPM: 0 | Vel: 0 km/h | Thr: 0% | Brk: 0%")
        self.lbl_ver.setStyleSheet("color: #0088FF; font-weight: bold; font-size: 16px; background-color: #111; padding: 5px;")
        
        self.lbl_per = QLabel("PER - RPM: 0 | Vel: 0 km/h | Thr: 0% | Brk: 0%")
        self.lbl_per.setStyleSheet("color: #FFFF00; font-weight: bold; font-size: 16px; background-color: #111; padding: 5px;")
        
        self.panel_layout.addWidget(self.lbl_ver)
        self.panel_layout.addWidget(self.lbl_per)

        #vivo y csv
        self.lbl_comparativa = QLabel("Análisis de Ventaja (Km/h): Esperando datos...")
        self.lbl_comparativa.setStyleSheet("color: #00FFCC; font-weight: bold; font-size: 15px; background-color: #222; padding: 5px; border: 1px solid #444;")
        layout.addWidget(self.lbl_comparativa)
        
        self.ver_faster_ticks = 0
        self.per_faster_ticks = 0
        self.csv_filename = "comparativa_velocidad.csv"
        
        #creacion csv
        with open(self.csv_filename, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp_Sistema', 'Timestamp_F1', 'Session_Key', 'Velocidad_VER', 'Velocidad_PER', 'Lider_Velocidad'])

        #botones
        self.btn_start = QPushButton("Iniciar Duelo (Verstappen vs Pérez)")
        self.btn_stop = QPushButton("Detener Telemetría (Pausa y Conservar Datos)")
        self.btn_stop.setEnabled(False)
        self.btn_start.setStyleSheet("background-color: #28a745; color: white; padding: 8px; font-weight: bold;")
        self.btn_stop.setStyleSheet("background-color: #dc3545; color: white; padding: 8px; font-weight: bold;")
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)

        #graficos
        pg.setConfigOption('background', '#111111') 
        pg.setConfigOption('foreground', '#FFFFFF') 
        
        self.win = pg.GraphicsLayoutWidget()
        layout.addWidget(self.win)
        
        
        self.plot_rpm_spd = self.win.addPlot(title="Correlación: RPM vs Velocidad")
        self.plot_rpm_spd.setLabel('left', 'Velocidad (km/h)', color='white', size='12pt')
        self.plot_rpm_spd.setLabel('bottom', 'Motor (RPM)', color='white', size='12pt')
        self.plot_rpm_spd.addLegend(offset=(10, 10)) 
        self.plot_rpm_spd.showGrid(x=True, y=True, alpha=0.3)
        
        self.curve_p1 = self.plot_rpm_spd.plot([], [], name="VER (1)", pen=pg.mkPen('#0088FF', width=3), symbol='o', symbolSize=4, symbolBrush='#0088FF')
        self.curve_p2 = self.plot_rpm_spd.plot([], [], name="PER (11)", pen=pg.mkPen('#FFFF00', width=3), symbol='t', symbolSize=4, symbolBrush='#FFFF00')

        self.win.nextRow() # Salto de línea

        
        self.plot_pedals = self.win.addPlot(title="Inputs: Acelerador vs Freno")
        self.plot_pedals.setLabel('left', 'Input (%)', color='white', size='12pt')
        self.plot_pedals.addLegend(offset=(10, 10))
        self.plot_pedals.showGrid(x=True, y=True, alpha=0.3)
        
        self.curve_thr_p1 = self.plot_pedals.plot([], [], name="VER Thr", pen=pg.mkPen('#00FF00', width=2))
        self.curve_brk_p1 = self.plot_pedals.plot([], [], name="VER Brk", pen=pg.mkPen('#FF0000', width=2))
        self.curve_thr_p2 = self.plot_pedals.plot([], [], name="PER Thr", pen=pg.mkPen('#AADD00', width=2, style=pg.QtCore.Qt.PenStyle.DashLine))
        self.curve_brk_p2 = self.plot_pedals.plot([], [], name="PER Brk", pen=pg.mkPen('#DD5555', width=2, style=pg.QtCore.Qt.PenStyle.DashLine))

       
        self.data_p1 = {'rpm': [], 'speed': [], 'throttle': [], 'brake': []}
        self.data_p2 = {'rpm': [], 'speed': [], 'throttle': [], 'brake': []}

       
        self.last_date_p1 = None
        self.last_date_p2 = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.consume_proc_queues)
        self.timer.start(100)  

        self.btn_start.clicked.connect(self.start_producers)
        self.btn_stop.clicked.connect(self.stop_producers)

        self.stop_event = threading.Event()
        self.api_threads = []

    def start_producers(self):
        """Inicia los hilos y asegura que el temporizador esté activo."""
        self.stop_event.clear()
        
        
        selected_session = self.combo_sesion.currentData()
        
        
        self.combo_sesion.setEnabled(False)
        
        endpoints = [
            {"path": "car_data", "params": {"session_key": selected_session, "driver_number": 1, "date>": getattr(self, 'last_date_p1', None)}, "driver": 1, "queue": queue_p1, "delay": 0.0},
            {"path": "car_data", "params": {"session_key": selected_session, "driver_number": 11, "date>": getattr(self, 'last_date_p2', None)}, "driver": 11, "queue": queue_p2, "delay": 0.5}
        ]
        
        for ep in endpoints:
            t = threading.Thread(
                target=consultar_api_productor, 
                args=(ep["path"], ep["params"], self.stop_event, ep["driver"], ep["queue"], ep["delay"]), 
                daemon=True
            )
            t.start()
            self.api_threads.append(t)
            
        self.timer.start(100) # Reloj visual
        self.info_label.setText(f"Sistema activo: Extrayendo telemetría de Sesión {selected_session}...")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def stop_producers(self):
        """Detiene los hilos y congela la interfaz visual sin borrar datos."""
        self.stop_event.set()
        self.timer.stop()
        self.api_threads.clear()
        
        self.info_label.setText("Sistema en PAUSA. Datos conservados.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        # por si se quiere cambiar la carrera post pausa.
        self.combo_sesion.setEnabled(True) 

    def consume_proc_queues(self):
    
        if self.btn_start.isEnabled():
            return
            
        updated_p1 = False
        updated_p2 = False
        
        l_rpm_1, l_spd_1, l_thr_1, l_brk_1 = 0, 0, 0, 0
        l_rpm_2, l_spd_2, l_thr_2, l_brk_2 = 0, 0, 0, 0
        
       
        batch_p1 = []
        while not queue_p1.empty() and len(batch_p1) < 3:
            try: pkt = queue_p1.get_nowait()
            except queue.Empty: break
                
            date_str = pkt.get('date')
            if date_str:
                self.last_date_p1 = date_str
                
            rpm, speed = pkt.get('rpm'), pkt.get('speed')
            thr, brk = pkt.get('throttle'), pkt.get('brake')
            
            if rpm is not None and speed is not None and thr is not None and brk is not None:
                if float(rpm) > 0 and float(speed) > 0:
                    batch_p1.append(pkt)
                    
        for pkt in batch_p1:
            rpm, speed = float(pkt['rpm']), float(pkt['speed'])
            thr, brk = float(pkt['throttle']), float(pkt['brake'])
            
            self.data_p1['rpm'].append(rpm)
            self.data_p1['speed'].append(speed)
            self.data_p1['throttle'].append(thr)
            self.data_p1['brake'].append(brk)
            
            l_rpm_1, l_spd_1, l_thr_1, l_brk_1 = rpm, speed, thr, brk
            updated_p1 = True

        
        batch_p2 = []
        while not queue_p2.empty() and len(batch_p2) < 3:
            try: pkt = queue_p2.get_nowait()
            except queue.Empty: break
                
            date_str = pkt.get('date')
            if date_str:
                self.last_date_p2 = date_str
                
            rpm, speed = pkt.get('rpm'), pkt.get('speed')
            thr, brk = pkt.get('throttle'), pkt.get('brake')
            
            if rpm is not None and speed is not None and thr is not None and brk is not None:
                if float(rpm) > 0 and float(speed) > 0:
                    batch_p2.append(pkt)
                    
        for pkt in batch_p2:
            rpm, speed = float(pkt['rpm']), float(pkt['speed'])
            thr, brk = float(pkt['throttle']), float(pkt['brake'])
            
            self.data_p2['rpm'].append(rpm)
            self.data_p2['speed'].append(speed)
            self.data_p2['throttle'].append(thr)
            self.data_p2['brake'].append(brk)
            
            l_rpm_2, l_spd_2, l_thr_2, l_brk_2 = rpm, speed, thr, brk
            updated_p2 = True
        
        
        if updated_p1:
            self.lbl_ver.setText(f"VER - RPM: {int(l_rpm_1)} | Vel: {int(l_spd_1)} km/h | Thr: {int(l_thr_1)}% | Brk: {int(l_brk_1)}%")
            self.data_p1['rpm'] = self.data_p1['rpm'][-MAX_POINTS:]
            self.data_p1['speed'] = self.data_p1['speed'][-MAX_POINTS:]
            self.data_p1['throttle'] = self.data_p1['throttle'][-MAX_POINTS:]
            self.data_p1['brake'] = self.data_p1['brake'][-MAX_POINTS:]
            
            self.curve_p1.setData(self.data_p1['rpm'], self.data_p1['speed'])
            self.curve_thr_p1.setData(self.data_p1['throttle'])
            self.curve_brk_p1.setData(self.data_p1['brake'])
            
        if updated_p2:
            self.lbl_per.setText(f"PER - RPM: {int(l_rpm_2)} | Vel: {int(l_spd_2)} km/h | Thr: {int(l_thr_2)}% | Brk: {int(l_brk_2)}%")
            self.data_p2['rpm'] = self.data_p2['rpm'][-MAX_POINTS:]
            self.data_p2['speed'] = self.data_p2['speed'][-MAX_POINTS:]
            self.data_p2['throttle'] = self.data_p2['throttle'][-MAX_POINTS:]
            self.data_p2['brake'] = self.data_p2['brake'][-MAX_POINTS:]
            
            self.curve_p2.setData(self.data_p2['rpm'], self.data_p2['speed'])
            self.curve_thr_p2.setData(self.data_p2['throttle'])
            self.curve_brk_p2.setData(self.data_p2['brake'])

        
        if updated_p1 or updated_p2:
            current_spd_1 = self.data_p1['speed'][-1] if len(self.data_p1['speed']) > 0 else 0
            current_spd_2 = self.data_p2['speed'][-1] if len(self.data_p2['speed']) > 0 else 0
            
            if current_spd_1 > 0 and current_spd_2 > 0:
                lider = "EMPATE"
                if current_spd_1 > current_spd_2:
                    self.ver_faster_ticks += 1
                    lider = "VER"
                elif current_spd_2 > current_spd_1:
                    self.per_faster_ticks += 1
                    lider = "PER"
                
                self.lbl_comparativa.setText(f" Dominio de Velocidad (Km/h) -> VERSTAPPEN: {self.ver_faster_ticks} veces | PÉREZ: {self.per_faster_ticks} veces")
                
                with open(self.csv_filename, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    sys_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    f1_time = getattr(self, 'last_date_p1', 'N/A') 
                    # Añadimos la session key al log
                    session = self.combo_sesion.currentData()
                    writer.writerow([sys_time, f1_time, session, current_spd_1, current_spd_2, lider])

def main():
    app = QApplication(sys.argv)
    win = TelemetryWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()