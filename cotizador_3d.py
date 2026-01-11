import sys
import os
import json
from datetime import datetime

# Importaciones de Interfaz Gráfica
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QTabWidget, QRadioButton, QSpinBox, QMessageBox, QCheckBox,
    QTextEdit, QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

# Importaciones Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Intentar importar tema oscuro
try:
    import qdarktheme
    HAS_THEME = True
except ImportError:
    HAS_THEME = False

# --- CONSTANTES ---
CONFIG_FILE = "configuracion.json"
CREDENTIALS_JSON = 'credenciales.json'
SHEET_NAME = 'PythonProyecTabla' # <--- ASEGÚRATE QUE COINCIDA CON TU HOJA

class CotizadorPro(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cotizador 3D Pro - Gestión Unificada")
        self.setGeometry(100, 100, 1000, 700)
        
        if os.path.exists("icono.png"):
            self.setWindowIcon(QIcon("icono.png"))

        # Datos por defecto
        self.default_precio_material = {"PLA": 20000, "PETG": 16450, "ABS": 19000, "TPU": 22700, "Resina": 35000}
        self.default_config = {
            "precio_kwh": 170, "consumo_kw": 0.2, "precio_hora_diseno": 8500,
            "margen_ganancia": 100, "precio_desgaste_hora": 200
        }

        self.loadConfig()
        self.initUI()

    # ================= UI PRINCIPAL =================
    def initUI(self):
        main_layout = QVBoxLayout(self)

        # --- 1. BARRA SUPERIOR (RESPONSABLE) ---
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("👤 Responsable de la sesión:"))
        
        self.combo_responsable = QComboBox()
        self.combo_responsable.addItems(["Nahuel", "Seba", "Otro"]) # Agrega los nombres que quieras
        self.combo_responsable.setFixedWidth(200)
        top_layout.addWidget(self.combo_responsable)
        top_layout.addStretch()
        
        main_layout.addLayout(top_layout)

        # --- 2. TABS PRINCIPALES ---
        self.tabs = QTabWidget()
        self.tab_cotizar = QWidget()
        self.tab_llaveros = QWidget() # <--- NUEVA PESTAÑA
        self.tab_historial = QWidget()
        self.tab_config = QWidget()

        self.tabs.addTab(self.tab_cotizar, "🖨️ Impresión 3D")
        self.tabs.addTab(self.tab_llaveros, "🔑 Venta Directa (Llaveros)")
        self.tabs.addTab(self.tab_historial, "📋 Historial")
        self.tabs.addTab(self.tab_config, "⚙️ Configuración")

        self.initTabCotizar()
        self.initTabLlaveros()
        self.initTabHistorial()
        self.initTabConfig()

        main_layout.addWidget(self.tabs)

    # ================= PESTAÑA 1: IMPRESIÓN 3D =================
    def initTabCotizar(self):
        layout = QVBoxLayout()

        # A. DATOS DEL PROYECTO
        group_cliente = QGroupBox("Datos del Cliente y Modelo")
        layout_cliente = QFormLayout()
        
        self.input_cliente = QLineEdit()
        self.input_cliente.setPlaceholderText("Nombre del cliente...")
        layout_cliente.addRow("Cliente:", self.input_cliente)

        self.input_modelo = QLineEdit()
        self.input_modelo.setPlaceholderText("Nombre de la pieza (STL)...")
        layout_cliente.addRow("Modelo/Pieza:", self.input_modelo)
        
        group_cliente.setLayout(layout_cliente)
        layout.addWidget(group_cliente)

        # B. PARÁMETROS DE IMPRESIÓN
        group_print = QGroupBox("Parámetros Técnicos")
        layout_print = QFormLayout()

        # Material y Color en una fila
        h_mat = QHBoxLayout()
        self.combo_material = QComboBox()
        self.combo_material.addItems(self.precio_material.keys())
        
        self.combo_color = QComboBox()
        self.combo_color.addItems(["Negro", "Blanco", "Gris", "Rojo", "Azul", "Naranja", "Verde", "Multicolor"])
        self.combo_color.setEditable(True)

        h_mat.addWidget(QLabel("Mat:"))
        h_mat.addWidget(self.combo_material)
        h_mat.addWidget(QLabel("Color:"))
        h_mat.addWidget(self.combo_color)
        layout_print.addRow("Material / Color:", h_mat)

        # Peso
        self.input_peso = QLineEdit()
        self.input_peso.setPlaceholderText("Gramos totales (con soportes)")
        layout_print.addRow("Peso Total (g):", self.input_peso)

        # Tiempo (Días, Horas, Minutos)
        h_time = QHBoxLayout()
        self.spin_dias = QSpinBox(); self.spin_dias.setSuffix(" d"); self.spin_dias.setRange(0,30)
        self.spin_horas = QSpinBox(); self.spin_horas.setSuffix(" h"); self.spin_horas.setRange(0,23)
        self.spin_min = QSpinBox(); self.spin_min.setSuffix(" m"); self.spin_min.setRange(0,59)
        
        h_time.addWidget(self.spin_dias)
        h_time.addWidget(self.spin_horas)
        h_time.addWidget(self.spin_min)
        layout_print.addRow("Tiempo Impresión:", h_time)

        # Cantidad
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setRange(1, 10000)
        self.spin_cantidad.setSuffix(" unid.")
        layout_print.addRow("Cantidad:", self.spin_cantidad)

        group_print.setLayout(layout_print)
        layout.addWidget(group_print)

        # C. EXTRAS
        group_extras = QGroupBox("Costos Adicionales")
        layout_extras = QHBoxLayout()

        self.spin_margen_error = QSpinBox()
        self.spin_margen_error.setValue(10)
        self.spin_margen_error.setPrefix("Fallo: ")
        self.spin_margen_error.setSuffix("%")
        layout_extras.addWidget(self.spin_margen_error)

        self.chk_diseno = QCheckBox("Incluir Diseño 3D")
        self.chk_diseno.toggled.connect(lambda: self.spin_hs_diseno.setEnabled(self.chk_diseno.isChecked()))
        layout_extras.addWidget(self.chk_diseno)

        self.spin_hs_diseno = QSpinBox()
        self.spin_hs_diseno.setEnabled(False)
        self.spin_hs_diseno.setSuffix(" hs diseño")
        layout_extras.addWidget(self.spin_hs_diseno)

        group_extras.setLayout(layout_extras)
        layout.addWidget(group_extras)

        # BOTÓN CALCULAR
        btn_calc = QPushButton("CALCULAR IMPRESIÓN 🚀")
        btn_calc.setFixedHeight(45)
        btn_calc.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 5px;")
        btn_calc.clicked.connect(self.calcularImpresion)
        layout.addWidget(btn_calc)

        # Resultado
        self.txt_res_impresion = QTextEdit()
        self.txt_res_impresion.setReadOnly(True)
        self.txt_res_impresion.setMaximumHeight(150)
        layout.addWidget(self.txt_res_impresion)

        self.tab_cotizar.setLayout(layout)

    # ================= PESTAÑA 2: VENTAS DIRECTAS (LLAVEROS) =================
    def initTabLlaveros(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        info = QLabel("💡 Esta pestaña es para ventas directas que no requieren cálculo de electricidad o filamento (Ej: Stock de Llaveros, Reventa).")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-style: italic; margin-bottom: 20px;")
        layout.addWidget(info)

        form = QFormLayout()
        
        self.input_cliente_llav = QLineEdit()
        form.addRow("Cliente:", self.input_cliente_llav)

        self.input_modelo_llav = QLineEdit()
        self.input_modelo_llav.setPlaceholderText("Ej: Llavero Among Us")
        form.addRow("Producto/Modelo:", self.input_modelo_llav)

        self.spin_cant_llav = QSpinBox()
        self.spin_cant_llav.setRange(1, 10000)
        self.spin_cant_llav.setValue(10)
        form.addRow("Cantidad:", self.spin_cant_llav)

        self.input_precio_unit = QLineEdit()
        self.input_precio_unit.setPlaceholderText("Precio por unidad")
        form.addRow("Precio Unitario ($):", self.input_precio_unit)

        layout.addLayout(form)

        btn_calc_llav = QPushButton("REGISTRAR VENTA 💰")
        btn_calc_llav.setFixedHeight(50)
        btn_calc_llav.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; border-radius: 5px; margin-top: 20px;")
        btn_calc_llav.clicked.connect(self.calcularLlaveros)
        layout.addWidget(btn_calc_llav)

        self.txt_res_llav = QTextEdit()
        self.txt_res_llav.setReadOnly(True)
        layout.addWidget(self.txt_res_llav)

        self.tab_llaveros.setLayout(layout)

    # ================= PESTAÑA 3: HISTORIAL =================
    def initTabHistorial(self):
        layout = QVBoxLayout()
        self.tabla = QTableWidget()
        # Definimos las columnas exactas
        headers = ["Fecha", "Resp.", "Cliente", "Modelo", "Tipo", "Mat", "Color", "Peso", "Tiempo", "Cant", "Unitario", "Total"]
        self.tabla.setColumnCount(len(headers))
        self.tabla.setHorizontalHeaderLabels(headers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla)
        self.tab_historial.setLayout(layout)

    def agregarFilaHistorial(self, d):
        row = self.tabla.rowCount()
        self.tabla.insertRow(row)
        # d = lista de datos. Mapeamos a las columnas
        # Indices: 0:Fecha, 1:Hora, 2:Resp, 3:Cli, 4:Mod, 5:Tipo, 6:Mat, 7:Col, 8:Peso, 9:Tiempo, 10:Cant, 11:HsDis, 12:Unit, 13:Total
        mapping = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13] # Saltamos Hora y HsDiseno para la tabla visual
        
        for i, data_idx in enumerate(mapping):
            val = str(d[data_idx])
            if data_idx in [12, 13]: val = f"${float(d[data_idx]):.2f}"
            self.tabla.setItem(row, i, QTableWidgetItem(val))

    # ================= PESTAÑA 4: CONFIGURACIÓN =================
    def initTabConfig(self):
        layout = QFormLayout()
        
        layout.addRow(QLabel("<b>--- Precios Materiales ($/kg) ---</b>"))
        self.inputs_materiales = {}
        for mat, precio in self.precio_material.items():
            inp = QLineEdit(str(precio))
            layout.addRow(f"{mat}:", inp)
            self.inputs_materiales[mat] = inp

        layout.addRow(QLabel("<b>--- Costos Operativos ---</b>"))
        self.input_kwh = QLineEdit(str(self.configuracion["precio_kwh"]))
        layout.addRow("Precio kWh:", self.input_kwh)
        
        self.input_consumo = QLineEdit(str(self.configuracion["consumo_kw"]))
        layout.addRow("Consumo (kW):", self.input_consumo)

        self.input_ganancia = QLineEdit(str(self.configuracion["margen_ganancia"]))
        layout.addRow("Margen Ganancia (%):", self.input_ganancia)

        btn_save = QPushButton("Guardar Configuración")
        btn_save.clicked.connect(self.guardarConfig)
        layout.addRow(btn_save)

        self.tab_config.setLayout(layout)

    # ================= LÓGICA DE NEGOCIO =================
    
    # --- CÁLCULO IMPRESIÓN 3D ---
    def calcularImpresion(self):
        try:
            # 1. Inputs
            cli = self.input_cliente.text()
            mod = self.input_modelo.text() or "Sin nombre"
            mat = self.combo_material.currentText()
            col = self.combo_color.currentText()
            
            if not cli or not self.input_peso.text():
                QMessageBox.warning(self, "Error", "Falta Cliente o Peso")
                return

            peso = float(self.input_peso.text().replace(',', '.'))
            
            # Tiempo
            t_dias = self.spin_dias.value()
            t_horas = self.spin_horas.value()
            t_min = self.spin_min.value()
            total_horas_imp = (t_dias * 24) + t_horas + (t_min / 60)
            texto_tiempo = f"{t_dias}d {t_horas}h {t_min}m"
            
            if total_horas_imp == 0:
                QMessageBox.warning(self, "Error", "El tiempo no puede ser 0")
                return

            cant = self.spin_cantidad.value()
            hs_dis = self.spin_hs_diseno.value() if self.chk_diseno.isChecked() else 0

            # 2. Costos
            precio_k = self.precio_material[mat]
            costo_mat = (peso * (1 + self.spin_margen_error.value()/100) / 1000) * precio_k
            costo_luz = total_horas_imp * self.configuracion["consumo_kw"] * self.configuracion["precio_kwh"]
            costo_maq = total_horas_imp * self.configuracion["precio_desgaste_hora"]
            
            subtotal = costo_mat + costo_luz + costo_maq
            precio_venta = subtotal * (1 + self.configuracion["margen_ganancia"]/100)
            costo_diseno = hs_dis * self.configuracion["precio_hora_diseno"]
            
            total_lote = precio_venta + costo_diseno
            unitario = total_lote / cant

            # 3. Reporte
            msg = (f"✅ IMPRESIÓN 3D | {mod}\n"
                   f"Mat: ${costo_mat:.2f} | Luz: ${costo_luz:.2f} | Maq: ${costo_maq:.2f}\n"
                   f"----------------------------------\n"
                   f"PRECIO UNITARIO: ${unitario:.2f}\n"
                   f"PRECIO TOTAL:    ${total_lote:.2f}")
            self.txt_res_impresion.setText(msg)

            # 4. Guardar
            datos = [
                datetime.now().strftime("%d/%m/%Y"), # 0
                datetime.now().strftime("%H:%M:%S"), # 1
                self.combo_responsable.currentText(), # 2
                cli, mod, "Impresión 3D", mat, col, # 3,4,5,6,7
                peso, texto_tiempo, cant, hs_dis, unitario, total_lote # 8,9,10,11,12,13
            ]
            self.procesarGuardado(datos)

        except ValueError:
            QMessageBox.warning(self, "Error", "Revisa los números ingresados.")

    # --- CÁLCULO LLAVEROS / VENTA DIRECTA ---
    def calcularLlaveros(self):
        try:
            cli = self.input_cliente_llav.text()
            mod = self.input_modelo_llav.text() or "Producto Varios"
            
            if not cli or not self.input_precio_unit.text():
                QMessageBox.warning(self, "Error", "Falta Cliente o Precio")
                return

            cant = self.spin_cant_llav.value()
            unitario = float(self.input_precio_unit.text().replace(',', '.'))
            total = cant * unitario

            # Reporte
            msg = (f"✅ VENTA DIRECTA | {mod}\n"
                   f"Cantidad: {cant} u.\n"
                   f"Precio Unit: ${unitario:.2f}\n"
                   f"----------------------------------\n"
                   f"TOTAL A COBRAR: ${total:.2f}")
            self.txt_res_llav.setText(msg)

            # Guardar (rellenamos con "-" lo que no aplica)
            datos = [
                datetime.now().strftime("%d/%m/%Y"), # 0
                datetime.now().strftime("%H:%M:%S"), # 1
                self.combo_responsable.currentText(), # 2
                cli, mod, "Venta Directa", "-", "-", # 3,4,5,6,7
                0, "N/A", cant, 0, unitario, total # 8,9,10,11,12,13
            ]
            self.procesarGuardado(datos)

        except ValueError:
            QMessageBox.warning(self, "Error", "Precio inválido.")

    # --- GUARDADO UNIFICADO ---
    def procesarGuardado(self, datos):
        self.agregarFilaHistorial(datos)
        self.subirADrive(datos)
        QMessageBox.information(self, "Guardado", "Registro añadido con éxito.")

    def subirADrive(self, datos):
        if not os.path.exists(CREDENTIALS_JSON): return
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_JSON, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            sheet.append_row(datos)
        except Exception as e:
            print(f"Error Drive: {e}")
            QMessageBox.warning(self, "Alerta", "Guardado local OK, pero falló Google Drive.")

    # ================= UTILIDADES =================
    def guardarConfig(self):
        for mat, inp in self.inputs_materiales.items():
            try: self.precio_material[mat] = float(inp.text())
            except: pass
        
        try:
            self.configuracion["precio_kwh"] = float(self.input_kwh.text())
            self.configuracion["consumo_kw"] = float(self.input_consumo.text())
            self.configuracion["margen_ganancia"] = float(self.input_ganancia.text())
            
            with open(CONFIG_FILE, "w") as f:
                json.dump({"materiales": self.precio_material, "configuracion": self.configuracion}, f, indent=4)
            QMessageBox.information(self, "Éxito", "Configuración guardada.")
        except ValueError:
            QMessageBox.warning(self, "Error", "Números inválidos.")

    def loadConfig(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    d = json.load(f)
                    self.precio_material = d.get("materiales", self.default_precio_material)
                    self.configuracion = d.get("configuracion", self.default_config)
            except:
                self.precio_material = self.default_precio_material.copy()
                self.configuracion = self.default_config.copy()
        else:
            self.precio_material = self.default_precio_material.copy()
            self.configuracion = self.default_config.copy()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if HAS_THEME: qdarktheme.setup_theme("auto")
    else: app.setStyle("Fusion")
    
    ventana = CotizadorPro()
    ventana.show()
    sys.exit(app.exec())