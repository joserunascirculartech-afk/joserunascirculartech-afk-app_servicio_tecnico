import streamlit as st

st.title("🕵️‍♂️ Inspector de Secretos")

st.write("---")

# 1. Verificamos si existe el "cajón" principal
if "gcp_service_account" in st.secrets:
    st.success("✅ ¡BIEN! El encabezado [gcp_service_account] existe.")
    
    # 2. Verificamos si dentro están los datos
    datos = st.secrets["gcp_service_account"]
    if "private_key" in datos:
        st.success("✅ La Clave Privada está cargada.")
        if "-----BEGIN PRIVATE KEY-----" in datos["private_key"]:
             st.success("✅ El formato de la clave parece correcto.")
        else:
             st.error("❌ La clave privada no tiene el formato correcto (falta el BEGIN...).")
    else:
        st.error("❌ Falta el campo 'private_key' dentro de los secretos.")
        
    if "client_email" in datos:
        st.info(f"🤖 El robot es: {datos['client_email']}")
    else:
        st.error("❌ Falta el correo del robot (client_email).")

else:
    st.error("❌ ERROR GRAVE: No encuentro el encabezado [gcp_service_account].")
    st.warning("⚠️ Asegúrate de que la PRIMERA LÍNEA en tus Secrets sea: [gcp_service_account]")
    
    st.write("Lo que Streamlit está viendo actualmente es esto:")
    st.json(dict(st.secrets))
