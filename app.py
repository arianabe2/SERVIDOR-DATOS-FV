import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =======================================================
# CONFIGURACIÓN GENERAL
# =======================================================
st.set_page_config(page_title="Reporte de Radiación Solar", layout="wide")

st.title("📊 Reporte de Radiación Solar")
st.markdown("**Prospección Fotovoltaica - CELEC EP**")

# 🔵 CAMBIO 1: Nombre de estación (NUEVO)
estacion = st.selectbox(
    "Nombre de la estación",
    ["Pimampiro", "Riobamba"]
)

st.info("Sube los archivos `.dat` de la estación para generar el análisis.")

# =======================================================
# CARGA DE ARCHIVOS
# =======================================================
col1, col2 = st.columns(2)

with col1:
    archivo_tabla1 = st.file_uploader("Subir Tabla 1 (Radiación)", type=["dat", "csv"])

with col2:
    archivo_tabla2 = st.file_uploader("Subir Tabla 2 (Soporte)", type=["dat", "csv"])

# =======================================================
# PROCESAMIENTO
# =======================================================
if archivo_tabla1 is not None and archivo_tabla2 is not None:

    @st.cache_data
    def procesar_archivos(f1, f2):

        df = pd.read_csv(f1, skiprows=[0, 2, 3])
        df1 = pd.read_csv(f2, skiprows=[0, 2, 3])

        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
        df1["TIMESTAMP"] = pd.to_datetime(df1["TIMESTAMP"])

        df = df.drop_duplicates(subset=["TIMESTAMP"])
        df1 = df1.drop_duplicates(subset=["TIMESTAMP"])

        df2 = pd.merge(df, df1, on="TIMESTAMP", how="inner")
        df2.columns = df2.columns.str.strip()

        # =======================================================
        # CAMBIO 2: NO FIJAR AÑO (ANTES ERA SOLO 2024)
        # =======================================================
        df2["AÑO"] = df2["TIMESTAMP"].dt.year

        df2["rad_corr"] = pd.to_numeric(df2["SR20T1_RadiacionCorregida_Avg"], errors="coerce")
        df2.loc[df2["rad_corr"] < 0, "rad_corr"] = 0
        df2 = df2[(df2["rad_corr"] <= 1500) & (df2["rad_corr"].notna())]

        df2["energia_kwh"] = (df2["rad_corr"] / 1000) * (10 / 60)

        df2["MES_N"] = df2["TIMESTAMP"].dt.month
        df2["HORA"] = df2["TIMESTAMP"].dt.hour
        df2["ANIO_MES"] = df2["TIMESTAMP"].dt.to_period("M")
        df2["FECHA_SOLO"] = df2["TIMESTAMP"].dt.date

        return df2


    df2 = procesar_archivos(archivo_tabla1, archivo_tabla2)
    st.success("✔ Datos procesados correctamente")

    # =======================================================
    # CAMBIO 3: SELECTOR DE AÑO (CLAVE)
    # =======================================================
    anio = st.selectbox(
        "📅 Selecciona el año de análisis",
        sorted(df2["AÑO"].unique())
    )

    # FILTRO POR AÑO (CLAVE)
    df_anio = df2[df2["AÑO"] == anio]

    # =======================================================
    # PESTAÑAS
    # =======================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Registro",
        "📈 Perfil Horario",
        "🗺️ Variabilidad Mensual",
        "⚡ Energía"
    ])

    # =======================================================
    # TAB 1 - REGISTRO
    # =======================================================
    with tab1:
        st.subheader(f"Resumen de datos - {estacion} ({anio})")

        tabla_mensual = df_anio.groupby("ANIO_MES").agg(
            radiacion_mediana=("rad_corr", "median"),
            radiacion_min=("rad_corr", "min"),
            radiacion_max=("rad_corr", "max"),
            energia_total=("energia_kwh", "sum"),
            dias=("FECHA_SOLO", "nunique")
        ).reset_index()

        tabla_mensual["energia_diaria"] = tabla_mensual["energia_total"] / tabla_mensual["dias"]

        st.dataframe(tabla_mensual, use_container_width=True)

    # =======================================================
    # TAB 2 - PERFIL HORARIO
    # =======================================================
    with tab2:
        st.subheader(f"Perfil Horario - {estacion} ({anio})")

        perfil = df_anio.groupby("HORA")["rad_corr"].mean()

        fig, ax = plt.subplots()
        ax.plot(perfil.index, perfil.values, linewidth=3)
        ax.set_xlabel("Hora")
        ax.set_ylabel("W/m²")
        ax.grid(True)

        st.pyplot(fig)

    # =======================================================
    # TAB 3 - VARIABILIDAD MENSUAL
    # =======================================================
    with tab3:
        st.subheader(f"Variabilidad Mensual - {estacion} ({anio})")

        perfil_mes = df_anio.groupby(["MES_N", "HORA"])["rad_corr"].median().reset_index()

        fig, ax = plt.subplots()

        for m in range(1, 13):
            data = perfil_mes[perfil_mes["MES_N"] == m]
            ax.plot(data["HORA"], data["rad_corr"], alpha=0.6)

        ax.set_xlabel("Hora")
        ax.set_ylabel("W/m²")
        ax.grid(True)

        st.pyplot(fig)

    # =======================================================
    # TAB 4 - ENERGÍA
    # =======================================================
    with tab4:
        st.subheader(f"Energía Mensual - {estacion} ({anio})")

        energia = df_anio.groupby("MES_N")["energia_kwh"].sum()

        fig, ax = plt.subplots()
        ax.plot(energia.index, energia.values, marker="o")
        ax.set_xlabel("Mes")
        ax.set_ylabel("kWh/m²")
        ax.grid(True)

        st.pyplot(fig)

else:
    st.warning("Carga ambos archivos para iniciar el análisis")