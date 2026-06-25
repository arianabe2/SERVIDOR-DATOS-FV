import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
# =======================================================
# CONFIGURACIÓN GENERAL
# =======================================================
st.set_page_config(page_title="Reportes Radiación Solar", layout="wide")

st.title("📊 Reportes Radiación Solar - CELEC")
st.markdown("Sistema de análisis de datos fotovoltaicos")

# =======================================================
# 🔵 MENÚ PRINCIPAL (COMO TU IMAGEN)
# =======================================================
menu = st.sidebar.radio(
    "📌 Menú principal",
    [
        "📥 Carga de datos",
        "📊 Análisis Anual",
        "📈 Análisis Mensual",
        "⏱️ Series temporales"
    ]
)

# =======================================================
# 🔧 FUNCIÓN DE LECTURA (REUTILIZABLE)
# =======================================================
@st.cache_data
def cargar_datos(f1, f2):

    df = pd.read_csv(f1, skiprows=[0, 2, 3])
    df1 = pd.read_csv(f2, skiprows=[0, 2, 3])

    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
    df1["TIMESTAMP"] = pd.to_datetime(df1["TIMESTAMP"])

    df = df.drop_duplicates(subset=["TIMESTAMP"])
    df1 = df1.drop_duplicates(subset=["TIMESTAMP"])

    df2 = pd.merge(df, df1, on="TIMESTAMP", how="inner")
    df2.columns = df2.columns.str.strip()

    # 🔵 CAMBIO IMPORTANTE: AÑO DINÁMICO
    df2["AÑO"] = df2["TIMESTAMP"].dt.year
    df2["MES"] = df2["TIMESTAMP"].dt.month
    df2["HORA"] = df2["TIMESTAMP"].dt.hour

    # 🔵 Radiación corregida
    df2["rad_corr"] = pd.to_numeric(
        df2["SR20T1_RadiacionCorregida_Avg"],
        errors="coerce"
    )
#CORRECCIÓN DE LOS DATOS
    df2.loc[df2["rad_corr"] < 0, "rad_corr"] = 0
    df2 = df2[(df2["rad_corr"] <= 1500) & (df2["rad_corr"].notna())]

    # 🔵 Energía simple
    df2["energia_kwh"] = (df2["rad_corr"] / 1000) * (10 / 60)
    df2["MES_N"] = df2["TIMESTAMP"].dt.month
    df2["HORA"] = df2["TIMESTAMP"].dt.hour
    df2["ANIO_MES"] = df2["TIMESTAMP"].dt.to_period("M")
    df2["FECHA_SOLO"] = df2["TIMESTAMP"].dt.date

    return df2


# =======================================================
# 📥 1. CARGA DE DATOS
# =======================================================
if menu == "📥 Carga de datos":

    st.header("Carga de archivos")

    archivo1 = st.file_uploader("Subir Tabla 1", type=["dat", "csv"])
    archivo2 = st.file_uploader("Subir Tabla 2", type=["dat", "csv"])

    if archivo1 and archivo2:
        st.session_state["data"] = cargar_datos(archivo1, archivo2)
        st.success("✔ Datos cargados correctamente")

# =======================================================
# 📊 2. ANÁLISIS ANUAL (TU PRINCIPAL)
# =======================================================
elif menu == "📊 Análisis Anual":

    st.header("Análisis Anual")

    # 🔴 CONTROL IMPORTANTE: evitar error si no hay datos
    if "data" not in st.session_state:
        st.warning("Primero carga los datos en 'Carga de datos'")
        st.stop()

    df2 = st.session_state["data"]

    estacion = st.selectbox("Estación", ["Pimampiro", "Riobamba"])
    anio = st.selectbox("Año", sorted(df2["AÑO"].unique()))

    df = df2[df2["AÑO"] == anio]
    
    st.subheader("Control de calidad de datos")

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Máximo", round(df["rad_corr"].max(), 2))
    
    with col2:
        st.metric("Mínimo", round(df["rad_corr"].min(), 2))
    
    with col3:
        st.metric("Media", round(df["rad_corr"].mean(), 2))
    
    with col4:
        st.metric("Mediana", round(df["rad_corr"].median(), 2))
        
    st.subheader("20 valores más altos de radiación")

    st.dataframe(
        df[["TIMESTAMP", "rad_corr"]]
        .sort_values("rad_corr", ascending=False)
        .head(20),
        use_container_width=True
        )

    st.subheader(f"{estacion} - {anio}")

    # TABLA MENSUAL
    tabla = df.groupby("MES").agg(
        radiacion_global_media=("rad_corr", "mean"),
        radiacion_global_min=("rad_corr", "min"),
        radiacion_global_max=("rad_corr", "max"),
        energia_total=("energia_kwh", "sum")
    ).reset_index()
    
    tabla_mensual = pd.DataFrame({
        "Fecha (Año-Mes)": tabla["MES"].astype(str),
        "Radiación Mediana (W/m²)": round(tabla["radiacion_global_media"], 1),
        "Radiación Mínima (W/m²)": round(tabla["radiacion_global_min"], 1),
        "Radiación Máxima (W/m²)": round(tabla["radiacion_global_max"], 1),
        "Energía Mensual Acumulada (kWh/m²)": round(tabla["energia_total"], 5)
    })    
    

    st.dataframe(tabla_mensual, use_container_width=True)

    # GRÁFICAS

    
##GRÁFICAS##

# ==========================================
# GRÁFICA 1 - RADIACIÓN MENSUAL
# ==========================================

    fig1 = px.line(
        tabla,
        x="MES",
        y="radiacion_global_media",
        markers=True,
        title=f"Variación mensual - {estacion} ({anio})"
        )

    fig1.update_layout(
        xaxis_title="Mes",
        yaxis_title="Radiación solar global (W/m²)",
        height=500
        )

    st.plotly_chart(fig1, use_container_width=True)

# ==========================================
# GRÁFICA 2 - ENERGÍA MENSUAL
# ==========================================

    fig2 = px.bar(
        tabla,
        x="MES",
        y="energia_total",
        title=f"Variación intranual de energía - {estacion} ({anio})"
        )

    fig2.update_layout(
        xaxis_title="Mes",
        yaxis_title="Energía (kWh/m²)",
        height=500
        )

    st.plotly_chart(fig2, use_container_width=True)
    
    
# ==========================================
# GRÁFICA 3 - RADIACIÓN SOLAR MENSUAL
# ==========================================

    perfil_horario_mes = (
        df.groupby(["MES","HORA"])["rad_corr"]
        .median()
        .reset_index()
        )

    perfil_horario_mes["MES_NOMBRE"] = (
        perfil_horario_mes["MES"]
        .map({
            1:"Ene",2:"Feb",3:"Mar",4:"Abr",
            5:"May",6:"Jun",7:"Jul",8:"Ago",
            9:"Sep",10:"Oct",11:"Nov",12:"Dic"
        })
    )

    fig3 = px.line(
        perfil_horario_mes,
        x="HORA",
        y="rad_corr",
        color="MES_NOMBRE",
        markers=True,
        title=f"Variabilidad horaria en los meses del año - {estacion} ({anio})"
    )

    fig3.update_layout(
        xaxis_title="Hora",
        yaxis_title="Radiación solar global (W/m²)",
        height=700
    )

    st.plotly_chart(fig3, use_container_width=True)

# ==========================================
# GRÁFICA 3 - RADIACIÓN SOLAR MENSUAL
# ==========================================

# =======================================================
# 📈 3. ANÁLISIS MENSUAL
# =======================================================

elif menu == "📈 Análisis Mensual":

    st.header("Análisis Mensual")

    if "data" not in st.session_state:
        st.warning("Primero carga los datos")
        st.stop()

    df2 = st.session_state["data"]

    mes = st.selectbox("Mes", range(1, 13))
    df_mes = df2[df2["MES"] == mes]

    fig, ax = plt.subplots()
    ax.plot(df_mes["HORA"], df_mes["rad_corr"])

    ax.set_title(f"Perfil horario - Mes {mes}")
    ax.set_xlabel("Hora")
    ax.set_ylabel("W/m²")
    ax.grid(True)

    st.pyplot(fig)

# =======================================================
# ⏱️ 4. SERIES TEMPORALES
# =======================================================
elif menu == "⏱️ Series temporales":

    st.header("Series Temporales")

    if "data" not in st.session_state:
        st.warning("Primero carga los datos")
        st.stop()

    df2 = st.session_state["data"]

    fig, ax = plt.subplots()
    ax.plot(df2["TIMESTAMP"], df2["rad_corr"])

    ax.set_title("Serie temporal de radiación")
    ax.set_xlabel("Tiempo")
    ax.set_ylabel("W/m²")

    st.pyplot(fig)
    