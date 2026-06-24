# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 12:14:03 2026

@author: ASUS
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 08:33:30 2026

@author: ASUS
"""

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# =======================================================
# Configuración de la página web (Estilo CELEC)
st.set_page_config(page_title="Reporte de Radiación Solar - Pimampiro", layout="wide")
st.title("☀️ Plataforma de Evaluación de Recurso Solar - Interactiva")
st.markdown("### Proyecto Fotovoltaico - CELEC EP")

st.info("Por favor, sube los archivos `.dat` de la estación para generar el análisis automatizado.")

# =======================================================
# 0. CONTROLES DE CARGA DE ARCHIVOS EN LA WEB
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

# =======================================================
# 1. RUTAS Y CARGA DE DATOS
# =======================================================
ruta = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\35645_Table1_2025-09-11T12-51.dat"
ruta1 = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\35645_Table2_2025-09-11T12-51.dat"

df = pd.read_csv(ruta, skiprows=[0,2,3])
df1 = pd.read_csv(ruta1, skiprows=[0,2,3])

# Limpieza y cruce
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
df1["TIMESTAMP"] = pd.to_datetime(df1["TIMESTAMP"])

# Evitar duplicados antes del merge
df = df.drop_duplicates(subset=["TIMESTAMP"])
df1 = df1.drop_duplicates(subset=["TIMESTAMP"])

df2 = pd.merge(df, df1, on="TIMESTAMP", how="inner")
df2.columns = df2.columns.str.strip()

# --- CORRECCIÓN CRÍTICA: Filtro estricto año 2024 completo ---
df2_2024 = df2[(df2["TIMESTAMP"] >= "2024-01-01") & (df2["TIMESTAMP"] < "2025-01-01")].copy()

# =======================================================
# 2. CONTROL DE CALIDAD (CONTEO EXACTO DE MINUTOS)
# =======================================================
minutos_totales_año = len(df2_2024)
minutos_na = df2_2024["SR20T1_RadiacionCorregida_Avg"].isna().sum()

df2_2024["rad_corr"] = pd.to_numeric(df2_2024["SR20T1_RadiacionCorregida_Avg"], errors="coerce")

# Contamos los minutos antes de limpiar la tabla
minutos_cero_o_negativos = (df2_2024["rad_corr"] <= 0).sum()
valores_negativos = (df2_2024["rad_corr"] < 0).sum()
valores_altos_erroneos = (df2_2024["rad_corr"] > 1500).sum()

# Minutos de sol efectivo REAL (valores mayores a 0 y menores o iguales a 1500)
minutos_sol_efectivo = ((df2_2024["rad_corr"] > 0) & (df2_2024["rad_corr"] <= 1500)).sum()

# --- APLICACIÓN DEL FILTRO DE RANGO ESTRICTO ---
df2_2024.loc[df2_2024["rad_corr"] < 0, "rad_corr"] = 0
df2_2024 = df2_2024[(df2_2024["rad_corr"] <= 1500) & (df2_2024["rad_corr"].notna())]

# CONVERSIÓN DE REGISTROS A HORAS REALES (LÓGICA AJUSTADA A 10 MINUTOS)
horas_totales_registro = (minutos_totales_año * 10) / 60
horas_perdidas_na = (minutos_na * 10) / 60
horas_no_sol_nocturno = (minutos_cero_o_negativos * 10) / 60
horas_sol_efectivo = (minutos_sol_efectivo * 10) / 60
horas_descartadas_error = (valores_altos_erroneos * 10) / 60

# =======================================================
# 3. CÁLCULOS ENERGÉTICOS ANUALES Y MESES PICO
# =======================================================
# Transformación: (W/m² / 1000) * (10 min / 60 min) = kWh/m²
df2_2024["energia_kwh"] = (df2_2024["rad_corr"] / 1000) * (10 / 60)

irradiacion_anual = df2_2024["energia_kwh"].sum()
hsp_anual = irradiacion_anual 
promedio_diario_hsp = irradiacion_anual / 366 # 2024 bisiesto

# Identificación de comportamiento estacional por mes
df2_2024["MES_N"] = df2_2024["TIMESTAMP"].dt.month
energia_por_mes = df2_2024.groupby("MES_N")["energia_kwh"].sum()

nombres_meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

mes_max_num = energia_por_mes.idxmax()
mes_min_num = energia_por_mes.idxmin()

resumen_anual = pd.DataFrame({
    "Indicador Anual 2024": [
        "Irradiación Total Acumulada (kWh/m²/año)", 
        "Horas Sol Pico Totales (HSP/año)", 
        "Promedio Diario de HSP (HSP/día)",
        "Mes de Radiación PICO",
        "Mes más CRÍTICO (Bajo)"
    ],
    "Valor": [
        round(irradiacion_anual, 2), 
        round(hsp_anual, 2), 
        round(promedio_diario_hsp, 2),
        f"{nombres_meses[mes_max_num]} ({round(energia_por_mes.max(), 2)} kWh/m²)",
        f"{nombres_meses[mes_min_num]} ({round(energia_por_mes.min(), 2)} kWh/m²)"
    ]
})

# =======================================================
# 4. CONSTRUCCIÓN DE LA TABLA DE DISPONIBILIDAD CORREGIDA
# =======================================================
tabla_disponibilidad = pd.DataFrame({
    "Estado del Recurso Solar 2024": [
        "Horas con Radiación Útil (Sol Efectivo)",
        "Horas de No Sol (Periodo Nocturno / Nubosidad Extrema)",
        "Horas Perdidas por Fallas de la Estación (NAs)",
        "Horas Descartadas por Error Físico (>1500 W/m²)",
        "Total de Horas Evaluadas en el Año"
    ],
    "Tiempo (Horas)": [
        round(horas_sol_efectivo, 1),
        round(horas_no_sol_nocturno, 1),
        round(horas_perdidas_na, 1),
        round(horas_descartadas_error, 1),
        round(horas_totales_registro, 1)
    ]
})

# =======================================================
# X. CREACIÓN DE TABLA MENSUAL DETALLADA (CON MÍNIMO DIURNO)
# =======================================================

# 1. Columnas de apoyo temporales
df2_2024["ANIO_MES"] = df2_2024["TIMESTAMP"].dt.to_period("M")
df2_2024["FECHA_SOLO"] = df2_2024["TIMESTAMP"].dt.date
df2_2024["HORA"] = df2_2024["TIMESTAMP"].dt.hour

# --- CÁLCULO PREVIO: Extraemos el mínimo solo en horas de sol (06h00 a 18h00) ---
df_diurno = df2_2024[df2_2024["HORA"].between(6, 18)]
minimos_diurnos = df_diurno.groupby("ANIO_MES")["rad_corr"].min()

# 2. Agrupamos los datos generales del año
tabla_mensual_datos = df2_2024.groupby("ANIO_MES").agg(
    radiacion_global_mediana=("rad_corr", "median"),
    radiacion_global_max=("rad_corr", "max"),
    energia_total_mes=("energia_kwh", "sum"),
    dias_unicos=("FECHA_SOLO", "nunique")
).reset_index()

# 3. Calculamos la Energía Promedio Diaria
tabla_mensual_datos["energia_promedio_diaria"] = tabla_mensual_datos["energia_total_mes"] / tabla_mensual_datos["dias_unicos"]

# 4. Convertimos la Energía acumulada mensual a Megavatios-hora (MWh/m²)
tabla_mensual_datos["ENERGIA_MWh_mes"] = tabla_mensual_datos["energia_total_mes"] / 1000

# 5. Estructuramos el DataFrame final para el Excel
tabla_mensual_final = pd.DataFrame({
    "Fecha (Año-Mes)": tabla_mensual_datos["ANIO_MES"].astype(str),
    "Radiación Mediana (W/m²)": round(tabla_mensual_datos["radiacion_global_mediana"], 1),
    "Radiación Máxima (W/m²)": round(tabla_mensual_datos["radiacion_global_max"], 1),
    "Energía Promedio Diaria (HSP/día)": round(tabla_mensual_datos["energia_promedio_diaria"], 2),
    "Energía Mensual Acumulada (MWh/m²)": round(tabla_mensual_datos["ENERGIA_MWh_mes"], 5)
})

# =======================================================
# 6. IMPRESIÓN DE REPORTES EN CONSOLA
# =======================================================
print("\n==========================================")
print("   ¡EL SCRIPT ANUAL EJECUTÓ CON ÉXITO!    ")
print("==========================================")
print(resumen_anual.to_string(index=False))

print("\n=== DIAGNÓSTICO DE CALIDAD DE DATOS (QC) ===")
print(f"Registros analizados en el año: {minutos_totales_año}")
print(f"Valores vacíos (NAs) eliminados: {minutos_na}")
print(f"Registros nocturnos negativos corregidos a 0: {valores_negativos}")
print(f"Registros por encima del límite físico (>1500 W/m²) descartados: {valores_altos_erroneos}")
print(f"Porcentaje de datos válidos para el diseño: {(len(df2_2024)/minutos_totales_año)*100:.2f}%")

print("\n=== TABLA DE DISPONIBILIDAD ===")
print(tabla_disponibilidad.to_string(index=False))

print("\n=== TABLA DE EVALUACIÓN MENSUAL INTRA-ANUAL ===")
print(tabla_mensual_final.to_string(index=False))
print("==========================================\n")

# =======================================================
# 7. GUARDADO FINAL DE RESULTADOS EN EXCEL (TODAS LAS PESTAÑAS)
# =======================================================
ruta_salida = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\ANUAL.xlsx"

with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
    resumen_anual.to_excel(writer, sheet_name="KPIs Anuales", index=False)
    tabla_disponibilidad.to_excel(writer, sheet_name="Calidad y No Sol", index=False)
    tabla_mensual_final.to_excel(writer, sheet_name="Resumen Mensual MWh", index=False)

print(f"Archivo Excel creado de forma consolidada en: {ruta_salida}")

# =======================================================
# 8. GENERACIÓN DE GRÁFICAS AUTOMÁTICAS
# =======================================================
meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
energia_ordenada = [energia_por_mes.get(m, 0) for m in range(1, 13)]

# --- GRÁFICA A: BARRAS (VARIACIÓN ESTACIONAL) ---
plt.figure(figsize=(10, 5))
barras = plt.bar(meses_nombres, energia_ordenada, color="#29b6f6", edgecolor="#0288d1", alpha=0.8)
barras[mes_max_num - 1].set_color("#f57c00")
barras[mes_max_num - 1].set_edgecolor("#e65100")

for barra in barras:
    yval = barra.get_height()
    plt.text(barra.get_x() + barra.get_width()/2, yval + 2, f"{round(yval, 1)}", ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.title("Variación Estacional de la Irradiación Mensual Acumulada 2024", fontsize=13, fontweight='bold')
plt.xlabel("Meses del Año", fontsize=11)
plt.ylabel("Energía Acumulada (kWh/m²/mes)", fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.ylim(0, max(energia_ordenada) * 1.15)
plt.tight_layout()
ruta_grafica_barras = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\Grafica_Estacional_Anual.png"
plt.savefig(ruta_grafica_barras, dpi=300)
plt.close()

# --- GRÁFICA B: MULTIMES (VARIABILIDAD HORARIA) ---
df2_2024["HORA"] = df2_2024["TIMESTAMP"].dt.hour
perfil_horario_mes = df2_2024.groupby(["MES_N", "HORA"])["rad_corr"].median().reset_index()

fig, axes = plt.subplots(3, 4, figsize=(16, 10), sharex=True, sharey=True)
axes = axes.flatten()

for mes in range(1, 13):
    ax = axes[mes - 1]
    datos_mes = perfil_horario_mes[perfil_horario_mes["MES_N"] == mes]
    ax.plot(datos_mes["HORA"], datos_mes["rad_corr"], color="#e53935", linewidth=2)
    ax.fill_between(datos_mes["HORA"], datos_mes["rad_corr"], color="#e53935", alpha=0.1)
    ax.set_title(nombres_meses[mes], fontsize=11, fontweight='bold', pad=5)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.set_xlim(0, 23)
    ax.set_xticks([0, 6, 12, 18, 23])

fig.suptitle("Variabilidad Horaria de la Radiación Solar Global por Meses\nPimampiro 2024 (Mediana Horaria)", fontsize=14, fontweight='bold', y=0.96)
fig.text(0.5, 0.02, "Hora del Día", ha="center", fontsize=12, fontweight='bold')
fig.text(0.02, 0.5, "Radiación Solar Global (W/m²)", va="center", rotation="vertical", fontsize=12, fontweight='bold')
plt.tight_layout(rect=[0.03, 0.04, 0.98, 0.93])
ruta_grafica_multimes = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\Grafica_Variabilidad_Horaria_Mensual.png"
plt.savefig(ruta_grafica_multimes, dpi=300)
plt.close()

# --- GRÁFICA C: CAMPANA ANUAL PROMEDIO ---
perfil_anual_horario = df2_2024.groupby("HORA")["rad_corr"].mean().reset_index()
plt.figure(figsize=(10, 5.5))
plt.plot(perfil_anual_horario["HORA"], perfil_anual_horario["rad_corr"], color="#f57c00", linewidth=3)
plt.fill_between(perfil_anual_horario["HORA"], perfil_anual_horario["rad_corr"], color="#ffe082", alpha=0.4)

hora_pico_anual = perfil_anual_horario.loc[perfil_anual_horario["rad_corr"].idxmax(), "HORA"]
rad_pico_anual = perfil_anual_horario["rad_corr"].max()
plt.scatter(hora_pico_anual, rad_pico_anual, color="#e65100", s=80, zorder=5)
plt.annotate(f"Pico Máximo: {round(rad_pico_anual, 1)} W/m²\na las {int(hora_pico_anual)}:00",
             xy=(hora_pico_anual, rad_pico_anual), xytext=(hora_pico_anual + 1.5, rad_pico_anual - 50),
             arrowprops=dict(facecolor='#e65100', arrowstyle="->", lw=1.5), fontsize=10, fontweight='bold', color='#e65100')

plt.title("Perfil Horario Promedio de la Radiación Solar Global (Anual 2024)\nEstación Pimampiro - CELEC EP", fontsize=13, fontweight='bold', pad=15)
plt.xlabel("Hora del Día (Formato 24h)", fontsize=11, fontweight='bold')
plt.ylabel("Irradiancia Global Horizontal (W/m²)", fontsize=11, fontweight='bold')
plt.xticks(range(0, 24))
plt.grid(axis='both', linestyle=':', alpha=0.6)
plt.xlim(0, 23)
plt.ylim(0, rad_pico_anual * 1.15)
plt.tight_layout()
ruta_grafica_campana = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\Grafica_Campana_Anual.png"
plt.savefig(ruta_grafica_campana, dpi=300)
plt.close()

# --- GRÁFICA D: VARIACIÓN INTRA-ANUAL (ÁREA CONTINUA) ---
plt.figure(figsize=(10, 5.5))
plt.plot(meses_nombres, energia_ordenada, color="#fbc02d", linewidth=3, marker="o", markersize=6)
plt.fill_between(meses_nombres, energia_ordenada, color="#fff59d", alpha=0.6)

for i, val in enumerate(energia_ordenada):
    plt.text(i, val + (max(energia_ordenada)*0.02), f"{round(val, 1)}", ha="center", fontsize=9, fontweight="bold")

plt.title("Variación Intra-anual de Energía Acumulada 2024\nEstación Pimampiro - CELEC EP", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Meses del Año", fontsize=11, fontweight="bold")
plt.ylabel("Energía Mensual Generada (kWh/m²/mes)", fontsize=11, fontweight="bold")
plt.grid(True, linestyle=":", alpha=0.5)
plt.ylim(0, max(energia_ordenada) * 1.15)
plt.tight_layout()
ruta_grafica_intraanual = r"C:\CELEC 2025\FOTOVOLTAICO\DATOS\PIMAMPIRO\Grafica_Variacion_Intraanual.png"
plt.savefig(ruta_grafica_intraanual, dpi=300)
plt.close()
# --- GRÁFICA EXTRA: BOXPLOT MENSUAL DIURNO ---
plt.figure(figsize=(12, 6))

# Filtramos solo registros diurnos para que las cajas no se aplasten contra el cero
df_diurno_grafico = df2_2024[df2_2024["HORA"].between(6, 18)]


print("==========================================")
print(" ¡TODOS LOS ENTREGABLES GENERADOS COMPLETOS! ")
print("==========================================")
