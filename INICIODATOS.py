# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 12:39:42 2026

@author: ASUS
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Configuración de la página web (Estilo CELEC)
st.set_page_config(page_title="Reporte de Radiación Solar - Pimampiro", layout="wide")
st.title("☀️ Plataforma de Evaluación de Recurso Solar - Interactiva")
st.markdown("### Proyecto Fotovoltaico - CELEC EP")

st.info("Por favor, sube los archivos `.dat` de la estación para generar el análisis automatizado.")

# =======================================================
# CONTROLES DE CARGA DE ARCHIVOS EN LA WEB
# =======================================================
col1, col2 = st.columns(2)

with col1:
    archivo_tabla1 = st.file_uploader("Subir Tabla 1 (Datos de Radiación)", type=["dat", "csv"])

with col2:
    archivo_tabla2 = st.file_uploader("Subir Tabla 2 (Datos de Soporte)", type=["dat", "csv"])

# Solo si ambos archivos han sido subidos por el usuario, se ejecuta el análisis
if archivo_tabla1 is not None and archivo_tabla2 is not None:
    
    @st.cache_data
    def procesar_archivos_subidos(f1, f2):
        # Leemos los archivos que el usuario cargó en la web
        df = pd.read_csv(f1, skiprows=[0,2,3])
        df1 = pd.read_csv(f2, skiprows=[0,2,3])
        
        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
        df1["TIMESTAMP"] = pd.to_datetime(df1["TIMESTAMP"])
        df = df.drop_duplicates(subset=["TIMESTAMP"])
        df1 = df1.drop_duplicates(subset=["TIMESTAMP"])
        
        df2 = pd.merge(df, df1, on="TIMESTAMP", how="inner")
        df2.columns = df2.columns.str.strip()
        
        df2_2024 = df2[(df2["TIMESTAMP"] >= "2024-01-01") & (df2["TIMESTAMP"] < "2025-01-01")].copy()
        df2_2024["rad_corr"] = pd.to_numeric(df2_2024["SR20T1_RadiacionCorregida_Avg"], errors="coerce")
        df2_2024.loc[df2_2024["rad_corr"] < 0, "rad_corr"] = 0
        df2_2024 = df2_2024[(df2_2024["rad_corr"] <= 1500) & (df2_2024["rad_corr"].notna())]
        
        df2_2024["energia_kwh"] = (df2_2024["rad_corr"] / 1000) * (10 / 60)
        df2_2024["MES_N"] = df2_2024["TIMESTAMP"].dt.month
        df2_2024["HORA"] = df2_2024["TIMESTAMP"].dt.hour
        df2_2024["ANIO_MES"] = df2_2024["TIMESTAMP"].dt.to_period("M")
        df2_2024["FECHA_SOLO"] = df2_2024["TIMESTAMP"].dt.date
        return df2_2024

    df2_2024 = procesar_archivos_subidos(archivo_tabla1, archivo_tabla2)
    st.success("¡Archivos procesados con éxito!")

    # =======================================================
    # CREACIÓN DE LAS PESTAÑAS (IDÉNTICO A TU PANTALLA)
    # =======================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Registro de Datos (Tabla)", 
        "📈 Perfil Horario Promedio", 
        "🗺️ Variabilidad Multimes", 
        "⚡ Variación Intra-anual (MWh)"
    ])

    # --- PESTAÑA 1: REGISTRO DE DATOS ---
    with tab1:
        st.subheader("Resumen de Evaluación Mensual Intra-anual")
        tabla_mensual_datos = df2_2024.groupby("ANIO_MES").agg(
            radiacion_global_mediana=("rad_corr", "median"),
            radiacion_global_min=("rad_corr", "min"),
            radiacion_global_max=("rad_corr", "max"),
            energia_total_mes=("energia_kwh", "sum"),
            dias_unicos=("FECHA_SOLO", "nunique")
        ).reset_index()
        
        df_diurno = df2_2024[df2_2024["HORA"].between(9, 15)]
        minimos_diurnos = df_diurno.groupby("ANIO_MES")["rad_corr"].min()
        tabla_mensual_datos["radiacion_global_min_diurna"] = tabla_mensual_datos["ANIO_MES"].map(minimos_diurnos)
        tabla_mensual_datos["energia_promedio_diaria"] = tabla_mensual_datos["energia_total_mes"] / tabla_mensual_datos["dias_unicos"]
        tabla_mensual_datos["ENERGIA_MWh_mes"] = tabla_mensual_datos["energia_total_mes"] / 1000
        
        tabla_mensual_final = pd.DataFrame({
            "Fecha (Año-Mes)": tabla_mensual_datos["ANIO_MES"].astype(str),
            "Radiación Mediana (W/m²)": round(tabla_mensual_datos["radiacion_global_mediana"], 1),
            "Radiación Mínima Diurna (W/m²)": round(tabla_mensual_datos["radiacion_global_min_diurna"], 1),
            "Radiación Máxima (W/m²)": round(tabla_mensual_datos["radiacion_global_max"], 1),
            "Energía Promedio Diaria (HSP/día)": round(tabla_mensual_datos["energia_promedio_diaria"], 2),
            "Energía Mensual Acumulada (MWh/m²)": round(tabla_mensual_datos["ENERGIA_MWh_mes"], 5)
        })
        st.dataframe(tabla_mensual_final, use_container_width=True)

    # --- PESTAÑA 2: PERFIL HORARIO PROMEDIO ---
    with tab2:
        st.subheader("Curva de Campana Anual del Recurso Solar")
        perfil_anual_horario = df2_2024.groupby("HORA")["rad_corr"].mean().reset_index()
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(perfil_anual_horario["HORA"], perfil_anual_horario["rad_corr"], color="#f57c00", linewidth=3)
        ax.fill_between(perfil_anual_horario["HORA"], perfil_anual_horario["rad_corr"], color="#ffe082", alpha=0.4)
        ax.set_xlabel("Hora del Día")
        ax.set_ylabel("Irradiancia (W/m²)")
        ax.set_xticks(range(0, 24))
        ax.grid(True, linestyle=":", alpha=0.6)
        st.pyplot(fig)

    # --- PESTAÑA 3: VARIABILIDAD MULTIMES ---
    with tab3:
        st.subheader("Campanas Horarias por Cada Mes")
        perfil_horario_mes = df2_2024.groupby(["MES_N", "HORA"])["rad_corr"].median().reset_index()
        nombres_meses = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
        fig, axes = plt.subplots(3, 4, figsize=(14, 8), sharex=True, sharey=True)
        axes = axes.flatten()
        for mes in range(1, 13):
            ax = axes[mes - 1]
            datos_mes = perfil_horario_mes[perfil_horario_mes["MES_N"] == mes]
            ax.plot(datos_mes["HORA"], datos_mes["rad_corr"], color="#e53935", linewidth=2)
            ax.fill_between(datos_mes["HORA"], datos_mes["rad_corr"], color="#e53935", alpha=0.1)
            ax.set_title(nombres_meses[mes], fontsize=10, fontweight='bold')
            ax.grid(True, linestyle=":", alpha=0.5)
            ax.set_xlim(0, 23)
        plt.tight_layout()
        st.pyplot(fig)

    # --- PESTAÑA 4: VARIACIÓN INTRA-ANUAL DE ENERGÍA ---
    with tab4:
        st.subheader("Curva de Área Mensual (Estilo Mazar / CELEC)")
        energia_por_mes = df2_2024.groupby("MES_N")["energia_kwh"].sum()
        meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        energia_ordenada = [energia_por_mes.get(m, 0) for m in range(1, 13)]
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(meses_nombres, energia_ordenada, color="#fbc02d", linewidth=3, marker="o")
        ax.fill_between(meses_nombres, energia_ordenada, color="#fff59d", alpha=0.6)
        ax.set_ylabel("Energía Mensual Generada (kWh/m²/mes)")
        ax.grid(True, linestyle=":", alpha=0.5)
        st.pyplot(fig)
else:
    st.warning("Esperando que se carguen ambos archivos `.dat` para activar las pestañas de reporte.")