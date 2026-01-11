import streamlit as st
import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Cotizador 3D Pro Web",
    page_icon="🖨️",
    layout="centered"
)

# --- CONSTANTES ---
CONFIG_FILE = "configuracion.json"
CREDENTIALS_JSON = 'credenciales.json'
SHEET_NAME = 'PythonProyecTabla'

# --- DATOS POR DEFECTO ---
DEFAULT_PRECIO_MATERIAL = {"PLA": 20000, "PETG": 16450, "ABS": 19000, "TPU": 22700, "Resina": 35000}
DEFAULT_CONFIG = {
    "precio_kwh": 170, "consumo_kw": 0.2, "precio_hora_diseno": 8500,
    "margen_ganancia": 100, "precio_desgaste_hora": 200
}

# --- FUNCIONES DE CARGA Y GUARDADO ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {"materiales": DEFAULT_PRECIO_MATERIAL, "configuracion": DEFAULT_CONFIG}
    return {"materiales": DEFAULT_PRECIO_MATERIAL, "configuracion": DEFAULT_CONFIG}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def subir_a_drive(datos):
    """Sube una lista de datos a Google Sheets"""
    if not os.path.exists(CREDENTIALS_JSON):
        st.error("❌ No se encontró el archivo credenciales.json")
        return False
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_JSON, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row(datos)
        return True
    except Exception as e:
        st.error(f"❌ Error conectando con Google Drive: {e}")
        return False

# --- INICIO DE LA APP ---
config_data = load_config()
precios_materiales = config_data.get("materiales", DEFAULT_PRECIO_MATERIAL)
params_config = config_data.get("configuracion", DEFAULT_CONFIG)

st.title("🖨️ Cotizador 3D Pro - Web")

# Barra lateral para el Responsable
st.sidebar.header("👤 Sesión")
responsable = st.sidebar.selectbox("Responsable:", ["Nahuel", "Seba", "Otro"])

# Crear pestañas
tab1, tab2, tab3, tab4 = st.tabs(["🖨️ Cotizar", "🔑 Llaveros", "📋 Historial (Sesión)", "⚙️ Configuración"])

# ================= TAB 1: COTIZAR =================
with tab1:
    st.subheader("Datos del Proyecto")
    
    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Cliente")
    with col2:
        modelo = st.text_input("Modelo/Pieza (STL)")
    
    st.markdown("---")
    st.subheader("Parámetros Técnicos")
    
    c_mat, c_col = st.columns(2)
    with c_mat:
        material = st.selectbox("Material", list(precios_materiales.keys()))
    with c_col:
        color = st.selectbox("Color", ["Negro", "Blanco", "Gris", "Rojo", "Azul", "Naranja", "Verde", "Multicolor"]) # Puedes hacerlo editable con st.text_input si prefieres
    
    peso = st.number_input("Peso Total (g)", min_value=0.0, format="%.2f")
    
    # Selector de tiempo (Horas/Minutos)
    st.write("Tiempo de Impresión:")
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        tipo_tiempo = st.radio("Unidad", ["Horas", "Minutos"], horizontal=True)
    with col_t2:
        valor_tiempo = st.number_input("Valor Tiempo", min_value=0.0, format="%.2f")

    cantidad = st.number_input("Cantidad (unid.)", min_value=1, value=1)
    
    st.markdown("---")
    st.subheader("Extras")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        margen_error = st.number_input("Margen de Fallo (%)", value=10)
    with col_e2:
        incluir_diseno = st.checkbox("Incluir Diseño 3D")
        hs_diseno = 0
        if incluir_diseno:
            hs_diseno = st.number_input("Horas de Diseño", min_value=0)

    # BOTÓN CALCULAR
    if st.button("CALCULAR IMPRESIÓN 🚀", type="primary"):
        if not cliente or peso == 0 or valor_tiempo == 0:
            st.warning("⚠️ Por favor completa Cliente, Peso y Tiempo.")
        else:
            # Lógica de cálculo
            if tipo_tiempo == "Horas":
                total_horas = valor_tiempo
                txt_tiempo = f"{valor_tiempo} hs"
            else:
                total_horas = valor_tiempo / 60
                txt_tiempo = f"{valor_tiempo} min"
            
            precio_k = precios_materiales[material]
            costo_mat = (peso * (1 + margen_error/100) / 1000) * precio_k
            costo_luz = total_horas * params_config["consumo_kw"] * params_config["precio_kwh"]
            costo_maq = total_horas * params_config["precio_desgaste_hora"]
            
            subtotal = costo_mat + costo_luz + costo_maq
            precio_venta = subtotal * (1 + params_config["margen_ganancia"]/100)
            costo_diseno_total = hs_diseno * params_config["precio_hora_diseno"]
            
            total_lote = precio_venta + costo_diseno_total
            unitario = total_lote / cantidad

            # Mostrar Resultados
            st.success("✅ Cálculo Exitoso")
            st.info(f"""
            **Detalle de Costos:**
            - Material: ${costo_mat:,.2f}
            - Luz: ${costo_luz:,.2f}
            - Desgaste: ${costo_maq:,.2f}
            -------------------------
            **💰 PRECIO UNITARIO: ${unitario:,.2f}** **💰 TOTAL LOTE: ${total_lote:,.2f}**
            """)

            # Guardar
            datos = [
                datetime.now().strftime("%d/%m/%Y"),
                datetime.now().strftime("%H:%M:%S"),
                responsable,
                cliente, modelo, "Impresión 3D", material, color,
                peso, txt_tiempo, cantidad, hs_diseno, unitario, total_lote
            ]
            
            if subir_a_drive(datos):
                st.toast("Guardado en Google Sheets con éxito!", icon="☁️")
                # Guardar en historial de sesión local
                if 'historial' not in st.session_state: st.session_state.historial = []
                st.session_state.historial.append(datos)

# ================= TAB 2: LLAVEROS =================
with tab2:
    st.info("💡 Ventas directas (Stock, Llaveros, Reventa)")
    
    cli_llav = st.text_input("Cliente (Venta Directa)")
    mod_llav = st.text_input("Producto/Modelo", placeholder="Ej: Llavero Among Us")
    cant_llav = st.number_input("Cantidad", min_value=1, value=10, key="cant_llav")
    prec_llav = st.number_input("Precio Unitario ($)", min_value=0.0, format="%.2f")
    
    if st.button("REGISTRAR VENTA 💰"):
        if not cli_llav or prec_llav == 0:
            st.warning("Completa Cliente y Precio.")
        else:
            total_llav = cant_llav * prec_llav
            st.success(f"✅ Total a Cobrar: ${total_llav:,.2f}")
            
            datos = [
                datetime.now().strftime("%d/%m/%Y"),
                datetime.now().strftime("%H:%M:%S"),
                responsable,
                cli_llav, mod_llav, "Venta Directa", "-", "-",
                0, "N/A", cant_llav, 0, prec_llav, total_llav
            ]
            
            if subir_a_drive(datos):
                st.toast("Venta registrada en Drive!", icon="☁️")
                if 'historial' not in st.session_state: st.session_state.historial = []
                st.session_state.historial.append(datos)

# ================= TAB 3: HISTORIAL =================
with tab3:
    st.write("📋 Historial de esta sesión:")
    if 'historial' in st.session_state and st.session_state.historial:
        # Convertir a DataFrame para mostrar bonito
        headers = ["Fecha", "Hora", "Resp.", "Cliente", "Modelo", "Tipo", "Mat", "Color", "Peso", "Tiempo", "Cant", "Hs Dis", "Unitario", "Total"]
        df = pd.DataFrame(st.session_state.historial, columns=headers)
        st.dataframe(df)
    else:
        st.info("Aún no has realizado cálculos en esta sesión.")

# ================= TAB 4: CONFIGURACIÓN =================
with tab4:
    st.header("⚙️ Configuración de Precios")
    
    with st.form("config_form"):
        st.subheader("Materiales ($/kg)")
        new_materials = {}
        cols = st.columns(3)
        for i, (mat, prec) in enumerate(precios_materiales.items()):
            with cols[i % 3]:
                new_materials[mat] = st.number_input(f"{mat}", value=float(prec))
        
        st.markdown("---")
        st.subheader("Costos Operativos")
        new_kwh = st.number_input("Precio kWh", value=float(params_config["precio_kwh"]))
        new_consumo = st.number_input("Consumo (kW)", value=float(params_config["consumo_kw"]), format="%.3f")
        new_ganancia = st.number_input("Margen Ganancia (%)", value=float(params_config["margen_ganancia"]))
        new_desgaste = st.number_input("Desgaste Maquina ($/h)", value=float(params_config["precio_desgaste_hora"])) # Agregado que faltaba editar en GUI anterior
        new_hora_diseno = st.number_input("Precio Hora Diseño ($)", value=float(params_config["precio_hora_diseno"]))

        submitted = st.form_submit_button("Guardar Cambios")
        
        if submitted:
            new_data = {
                "materiales": new_materials,
                "configuracion": {
                    "precio_kwh": new_kwh,
                    "consumo_kw": new_consumo,
                    "precio_hora_diseno": new_hora_diseno,
                    "margen_ganancia": new_ganancia,
                    "precio_desgaste_hora": new_desgaste
                }
            }
            save_config(new_data)
            st.success("Configuración actualizada y guardada en JSON.")
            st.rerun() # Recarga la app para tomar los nuevos precios