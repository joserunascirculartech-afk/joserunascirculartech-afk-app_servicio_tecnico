import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Técnico CICLA", page_icon="🔧", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
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
                # --- SECCIÓN 1: ESTADO ---
                estados = ["Ingresado", "En Revisión", "Presupuesto/Diagnóstico Enviado", 
                           "Esperando Repuestos", "En Mantención", "Listo para Retiro", "Entregado"]
                
                estado_actual = datos_ticket.get('Estado', 'Ingresado')
                idx_estado = estados.index(estado_actual) if estado_actual in estados else 0
                nuevo_estado = st.selectbox("Estado del Equipo", estados, index=idx_estado)

                st.markdown("---")
                
                # --- SECCIÓN 2: DESGLOSE DE COSTOS ---
                st.markdown("### 💰 Costos y Presupuesto")
                
                # Intentamos recuperar el costo anterior si existe
                costo_previo_str = str(datos_ticket.get('Costo', '0')).replace('$','').replace('.','')
                try: costo_previo = int(costo_previo_str)
                except: costo_previo = 0

                c1, c2, c3 = st.columns(3)
                with c1:
                    v_repuestos = st.number_input("Repuestos ($)", min_value=0, step=1000, help="Valor de las piezas")
                with c2:
                    v_mantencion = st.number_input("Mantenimiento ($)", min_value=0, step=1000, help="Limpieza y ajuste")
                with c3:
                    # Ponemos el costo previo aquí por defecto para no perderlo si no desglosan
                    v_reparacion = st.number_input("Reparación ($)", value=costo_previo, min_value=0, step=1000, help="Mano de obra compleja")

                # CÁLCULO AUTOMÁTICO DEL TOTAL
                total_calculado = v_repuestos + v_mantencion + v_reparacion
                
                # Mostrar el total en grande y bonito
                st.metric(label="💵 TOTAL FINAL A COBRAR", value=f"${total_calculado:,.0f}")

                st.markdown("---")

                # --- SECCIÓN 3: TEXTOS ---
                nuevo_diag = st.text_area("Diagnóstico Técnico", value=str(datos_ticket.get('Diagnostico Final', '')))
                
                # Aquí guardaremos el detalle de los repuestos y costos
                texto_repuestos_previo = str(datos_ticket.get('Repuestos', ''))
                nuevo_repuestos_desc = st.text_area("Detalle de Repuestos / Notas", value=texto_repuestos_previo)

                st.markdown("---")
                avisar = st.checkbox("📧 Enviar notificación al cliente", value=True)
                btn_guardar = st.form_submit_button("💾 GUARDAR CAMBIOS")

            if btn_guardar:
                msg = st.empty()
                msg.info("⏳ Guardando...")
                
                try:
                    # Crear un texto resumen del desglose para guardarlo en la columna "Repuestos"
                    # Así queda constancia de cuánto fue cada cosa.
                    desglose_texto = f"{nuevo_repuestos_desc} | (Desglose: Repuestos ${v_repuestos} + Mantención ${v_mantencion} + Reparación ${v_reparacion})"

                    # Actualizamos celdas
                    hoja.update_cell(num_fila_excel, 11, nuevo_estado)      # Estado
                    hoja.update_cell(num_fila_excel, 12, nuevo_diag)        # Diagnóstico
                    hoja.update_cell(num_fila_excel, 13, desglose_texto)    # Repuestos (Con el desglose escrito)
                    hoja.update_cell(num_fila_excel, 14, total_calculado)   # Costo Total (Numérico)
                    
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
