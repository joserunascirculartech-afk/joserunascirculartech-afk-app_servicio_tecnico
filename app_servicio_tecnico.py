import streamlit as st
import pandas as pd
import gspread
# 👇 ESTA ES LA LÍNEA QUE ARREGLA EL ERROR (MOTOR NUEVO)
from google.oauth2.service_account import Credentials 
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Técnico CICLA", page_icon="🔧", layout="centered")

# --- CONEXIÓN BLINDADA (MOTOR NUEVO) ---
@st.cache_resource
def conectar_google_sheet():
    # Permisos necesarios
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # OPCIÓN A: USANDO SECRETS (NUBE)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 🛠️ Parche automático para la clave privada (arregla los \n)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        # Conectamos usando la librería MODERNA (google-auth)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    # OPCIÓN B: USANDO ARCHIVO LOCAL (PC)
    else:
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
            
    client = gspread.authorize(creds)
    
    # 🆔 ID DEL ARCHIVO (Ficha Recepción...)
    ID_ARCHIVO = "1xcATaxfbrREwp83kQ5eGr_cjG8V2GElEF7JZD7puK9E"
    
    return client.open_by_key(ID_ARCHIVO).sheet1

# --- VALIDACIÓN DE CONEXIÓN ---
try:
    hoja = conectar_google_sheet()
except Exception as e:
    st.error("❌ ERROR DE CONEXIÓN")
    st.error(f"Detalle: {e}")
    # Si ves este mensaje, es que requirements.txt está mal o faltan secrets
    st.info("Verifica que en requirements.txt diga 'google-auth' y NO 'oauth2client'")
    st.stop()

# --- INTERFAZ DE LA APP ---
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

if buscar or numero_caso:
    id_buscado = f"CASO-{int(numero_caso)}"
    
    try:
        datos = hoja.get_all_records()
        df = pd.DataFrame(datos)
        
        if 'ID_TICKET' not in df.columns:
            st.error("⚠️ Error: No encuentro la columna 'ID_TICKET' en el Excel.")
            st.stop()
            
        fila_encontrada = df[df['ID_TICKET'] == id_buscado]

        if not fila_encontrada.empty:
            num_fila_excel = int(fila_encontrada.index[0] + 2)
            datos_ticket = fila_encontrada.iloc[0]

            st.info(f"📂 Caso: {id_buscado} | Cliente: {datos_ticket.get('Nombre del Cliente:', '---')}")

            with st.form("form_tecnico"):
                estados = ["Ingresado", "En Revisión", "Presupuesto/Diagnóstico Enviado", 
                           "Esperando Repuestos", "En Mantención", "Listo para Retiro", "Entregado"]
                
                estado_actual = datos_ticket.get('Estado', 'Ingresado')
                idx_estado = estados.index(estado_actual) if estado_actual in estados else 0

                nuevo_estado = st.selectbox("Estado", estados, index=idx_estado)
                
                col_costo, _ = st.columns(2)
                with col_costo:
                    costo_str = str(datos_ticket.get('Costo', '0')).replace('$','').replace('.','')
                    try: val_costo = int(costo_str)
                    except: val_costo = 0
                    nuevo_costo = st.number_input("Costo Total ($)", value=val_costo, step=1000)

                nuevo_diag = st.text_area("Diagnóstico", value=str(datos_ticket.get('Diagnostico Final', '')))
                nuevo_repuestos = st.text_area("Repuestos", value=str(datos_ticket.get('Repuestos', '')))

                st.markdown("---")
                avisar = st.checkbox("📧 Enviar notificación", value=True)
                btn_guardar = st.form_submit_button("💾 GUARDAR CAMBIOS")

            if btn_guardar:
                msg = st.empty()
                msg.info("⏳ Guardando...")
                
                try:
                    # Guardamos datos (K=11, L=12, M=13, N=14, O=15)
                    hoja.update_cell(num_fila_excel, 11, nuevo_estado)
                    hoja.update_cell(num_fila_excel, 12, nuevo_diag)
                    hoja.update_cell(num_fila_excel, 13, nuevo_repuestos)
                    hoja.update_cell(num_fila_excel, 14, nuevo_costo)
                    
                    if avisar:
                        hoja.update_cell(num_fila_excel, 15, "NOTIFICAR")
                        st.toast("Orden enviada al Robot 🤖", icon="📧")
                    else:
                        hoja.update_cell(num_fila_excel, 15, "")

                    msg.success("✅ ¡Guardado!")
                    time.sleep(1.5)
                    st.rerun()
                    
                except Exception as e:
                    msg.error(f"❌ Error al guardar: {e}")

        else:
            st.warning(f"🔍 No existe el ticket {id_buscado}")
            
    except Exception as e:
        st.error(f"Error leyendo datos: {e}")