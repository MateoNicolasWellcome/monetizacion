import streamlit as st
import pandas as pd
import numpy as np
import os

# ---------------- FUNCIONES DE PROCESAMIENTO ----------------
def fix_raw_data(csv_airbnb_file, name_source):
    df = pd.read_csv(csv_airbnb_file)
    need_columns = ['Fecha', 'Tipo', 'Código de confirmación', 'Detalles', 'Código de referencia', 'Moneda', 'Monto', 'Total pagado']
    df = df[need_columns]
    df['fuente'] = name_source
    df['Fecha'] = pd.to_datetime(df['Fecha'], format='%m/%d/%Y')
    df['Total pagado'] = df['Total pagado'].replace(to_replace=np.nan, method='ffill', inplace=False)
    df['Código de referencia'] = df['Código de referencia'].replace(to_replace=np.nan, method='ffill', inplace=False)
    return df

def update_airbnb_historical(df_nuevo):
    nombre_archivo_acumulado = 'aribnb_reservations_paid_historico_.csv'
    if os.path.exists(nombre_archivo_acumulado):
        df_acumulado = pd.read_csv(nombre_archivo_acumulado, parse_dates=['Fecha'])
    else:
        df_acumulado = pd.DataFrame(columns=df_nuevo.columns)
    df_nuevo = df_nuevo[~df_nuevo['Tipo'].str.contains('Payout', case=False, na=False)]
    df_final = pd.concat([df_acumulado, df_nuevo], ignore_index=True)
    df_final.drop_duplicates(inplace=True)
    return df_final

def update_payout(df):
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Fecha'] = df['Fecha'].dt.date
    df_transacciones = df.groupby('Código de referencia').agg({
        'Monto': 'sum',
        'Total pagado': 'first',
        'Fecha': 'first',
        'Código de referencia': 'count',
        'fuente': 'first'
    }).rename(columns={'Código de referencia': 'Cantidad reservas'}).reset_index()
    df_transacciones = df_transacciones.sort_values(by='Fecha')
    df_transacciones['id_accival'] = ''
    return df_transacciones

def update_monetizacion(df, archivo_monetizaciones):
    df_validos = df.dropna(subset=['id_accival'])
    df_nuevo = df_validos.groupby(['id_accival']).agg({
        'Total pagado': 'sum',
        'Cantidad reservas': 'count'
    }).reset_index()
    df_nuevo.rename(columns={
        'Total pagado': 'monto_usd',
        'Cantidad reservas': 'num_transacciones'
    }, inplace=True)
    df_nuevo['trm'] = ''
    df_nuevo['monto_cop'] = ''
    df_nuevo['costo'] = ''
    if os.path.exists(archivo_monetizaciones):
        df_existente = pd.read_csv(archivo_monetizaciones)
        df_actualizado = pd.concat([df_existente, df_nuevo], ignore_index=True)
        df_actualizado.drop_duplicates(subset=['id_accival'], inplace=True)
    else:
        df_actualizado = df_nuevo
    return df_actualizado

def run_monetizacion(csv_airbnb_file, name_source):
    df_arreglado = fix_raw_data(csv_airbnb_file, name_source)
    df_arreglado.to_csv("fix_airbnb.csv")
    df_historico = update_airbnb_historical(df_arreglado)
    df_historico.to_csv("aribnb_reservations_paid_historico_.csv", index=False)
    df_payout = update_payout(df_historico)
    df_payout.to_csv("transacciones_payout.csv", index=False)
    return df_payout

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Monetizaciones Airbnb", layout="wide")
st.title("Gestor de Monetizaciones desde Airbnb")

if st.text_input("Contraseña", type="password") != "wellcome2025":
    st.warning("Acceso restringido")
    st.stop()

uploaded_file = st.file_uploader("Sube el archivo CSV de Airbnb", type=["csv"])
if uploaded_file:
    with st.spinner("Procesando archivo..."):
        df_payout = run_monetizacion(uploaded_file, "airbnb_maestro")

    st.success("Transacciones de payout generadas ✅")

    st.subheader("Asignar ID Accival manualmente")
    for i, row in df_payout.iterrows():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**{row['Código de referencia']}** ({row['Fecha']})")
        with col2:
            new_id = st.text_input("ID Accival", value=row['id_accival'], key=f"accival_{i}")
            df_payout.at[i, 'id_accival'] = new_id

    st.subheader("Monetizaciones generadas")
    archivo_monetizaciones = 'monetizaciones.csv'
    df_monetizacion = update_monetizacion(df_payout, archivo_monetizaciones)
    df_monetizacion.to_csv(archivo_monetizaciones, index=False)
    st.dataframe(df_monetizacion)

    st.download_button("Descargar archivo monetizaciones.csv", data=df_monetizacion.to_csv(index=False), file_name="monetizaciones.csv", mime="text/csv")
