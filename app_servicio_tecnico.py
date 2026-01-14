import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Técnico CICLA", page_icon="🔧", layout="centered")

# --- CONEXIÓN BLINDADA ---
@st.cache_resource
def conectar_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
            
    client = gspread.authorize(creds)
    ID_ARCHIVO = "1xcATaxfbrREwp83kQ5eGr_cjG8V2GElEF7JZD7puK9E"
    return client.open_by_key(ID_ARCHIVO).sheet1

# --- VALIDACIÓN ---
try:
    hoja = conectar_google_sheet()
except Exception as e:
    st.error("❌ ERROR DE CONEXIÓN")
    st.error(f"Detalle: {e}")
    st.stop()

# --- INTERFAZ ---
st.title("🔧 Gestión Taller CICLA 3D")

param_id = st.query_params.get("id", None)

if not param_id:
    col1, col2 = st.columns([2, 1])
    with col1:
        numero_caso = st.number_input("N° de Caso", min_value=1, step=1, label_visibility="collapsed", placeholder="Ej: 10")
    with col2:
        buscar = st.button("Buscar")
else:
    numero_caso = param_id
    buscar = True

# --- PROCESAMIENTO ---
if buscar or numero_caso:
    id_buscado = f"CASO-{int(numero_caso)}"
    
    try:
        datos = hoja.get_all_records()
        df = pd.DataFrame(datos)
        
        if 'ID_TICKET' not in df.columns:
            st.error("⚠️ Error: No encuentro la columna 'ID_TICKET'.")
            st.stop()
            
        fila_encontrada = df[df['ID_TICKET'] == id_buscado]

        if not fila_encontrada.empty:
            num_fila_excel = int(fila_encontrada.index[0] + 2)
            datos_ticket = fila_encontrada.iloc[0]

            st.info(f"📂 Caso: {id_buscado} | Cliente: {datos_ticket.get('Nombre del Cliente:', '---')}")

            with st.form("form_tecnico"):
                # --- ESTADO ---
                estados = ["Ingresado", "En Revisión", "Presupuesto/Diagnóstico Enviado", 
                           "Esperando Repuestos", "En Mantención", "Listo para Retiro", "Entregado"]
                
                estado_actual = datos_ticket.get('Estado', 'Ingresado')
                idx_estado = estados.index(estado_actual) if estado_actual in estados else 0
                nuevo_estado = st.selectbox("Estado del Equipo", estados, index=idx_estado)

                st.markdown("---")
                st.markdown("### 💰 Repuestos y Costos")
                
                # --- SECCIÓN REPUESTOS (CON DETALLE) ---
                # Fila 1: Cicla
                c_rep_cicla_val, c_rep_cicla_txt = st.columns([1, 2])
                with c_rep_cicla_val:
                    v_rep_cicla = st.number_input("Valor Rep. CICLA ($)", min_value=0, step=1000)
                with c_rep_cicla_txt:
                    d_rep_cicla = st.text_input("Detalle Repuestos CICLA", placeholder="Ej: 1x Boquilla, 1x Ventilador...")

                # Fila 2: Externos
                c_rep_ext_val, c_rep_ext_txt = st.columns([1, 2])
                with c_rep_ext_val:
                    v_rep_ext = st.number_input("Valor Rep. EXTERNOS ($)", min_value=0, step=1000)
                with c_rep_ext_txt:
                    d_rep_ext = st.text_input("Detalle Repuestos EXTERNOS", placeholder="Ej: Compra en Casa Royal...")

                st.markdown("---")
                
                # --- SECCIÓN MANO DE OBRA ---
                st.markdown("### 🛠️ Mano de Obra")
                
                # Recuperar costo previo para no perderlo
                costo_previo_str = str(datos_ticket.get('Costo', '0')).replace('$','').replace('.','')
                try: costo_previo = int(costo_previo_str)
                except: costo_previo = 0
                
                c_man1, c_man2 = st.columns(2)
                with c_man1:
                    v_mantencion = st.number_input("Mantenimiento ($)", min_value=0, step=1000)
                with c_man2:
                    v_reparacion = st.number_input("Reparación ($)", value=costo_previo, min_value=0, step=1000)

                # CÁLCULO TOTAL
                total_calculado = v_rep_cicla + v_rep_ext + v_mantencion + v_reparacion
                st.metric(label="💵 TOTAL A COBRAR", value=f"${total_calculado:,.0f}")

                st.markdown("---")

                # --- INFORMES TÉCNICOS ---
                st.markdown("### 📋 Informe Técnico")
                
                # Carga el diagnóstico existente
                diag_previo = str(datos_ticket.get('Diagnostico Final', ''))
                
                nuevo_diag = st.text_area("Diagnóstico Inicial / Problema Reportado", value=diag_previo, height=100)
                detalle_tecnico = st.text_area("Detalle del Trabajo Realizado (Técnico)", placeholder="Describe aquí la solución técnica aplicada...", height=100)

                st.markdown("---")
                avisar = st.checkbox("📧 Enviar notificación al cliente", value=True)
                btn_guardar = st.form_submit_button("💾 GUARDAR CAMBIOS")

            if btn_guardar:
                msg = st.empty()
                msg.info("⏳ Guardando...")
                
                try:
                    # 1. Construir el Texto de Repuestos (Columna M)
                    # Formato: [CICLA: detalle ($val)] | [EXT: detalle ($val)]
                    texto_repuestos = ""
                    if v_rep_cicla > 0 or d_rep_cicla:
                        texto_repuestos += f"CICLA: {d_rep_cicla} (${v_rep_cicla}) "
                    if v_rep_ext > 0 or d_rep_ext:
                        if texto_repuestos: texto_repuestos += "| "
                        texto_repuestos += f"EXTERNO: {d_rep_ext} (${v_rep_ext}) "
                    
                    # Agregamos desglose de mano de obra al final para registro interno
                    texto_repuestos += f"| [MO: Mant ${v_mantencion} + Rep ${v_reparacion}]"

                    # 2. Construir el Informe Técnico (Columna L)
                    # Si el técnico escribió algo nuevo, lo agregamos al diagnóstico
                    texto_informe = nuevo_diag
                    if detalle_tecnico:
                        texto_informe += f"\n\n--- TRABAJO REALIZADO ---\n{detalle_tecnico}"

                    # Actualizamos celdas
                    hoja.update_cell(num_fila_excel, 11, nuevo_estado)      # Col K (Estado)
                    hoja.update_cell(num_fila_excel, 12, texto_informe)     # Col L (Diagnóstico + Informe)
                    hoja.update_cell(num_fila_excel, 13, texto_repuestos)   # Col M (Detalle Repuestos)
                    hoja.update_cell(num_fila_excel, 14, total_calculado)   # Col N (Total $)
                    
                    if avisar:
                        hoja.update_cell(num_fila_excel, 15, "NOTIFICAR")
                        st.toast("Orden enviada al Robot 🤖", icon="📧")
                    else:
                        hoja.update_cell(num_fila_excel, 15, "")

                    msg.success(f"✅ ¡Guardado! Total: ${total_calculado:,.0f}")
                    time.sleep(1.5)
                    st.rerun()
                    
                except Exception as e:
                    msg.error(f"❌ Error al guardar: {e}")

        else:
            st.warning(f"🔍 No existe el ticket {id_buscado}")
            
    except Exception as e:
        st.error(f"Error: {e}")
