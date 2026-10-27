"""Flujo automatizado para procesamiento de la serie oficial 3.1.1 de exportaciones FOB del Banco Central del Ecuador.
Integrantes: Edwin Cevallos - Diplomado Big Data e IA
Fuente: Boletín de Comercio Exterior BCE (export.csv - Cifras provisionales en miles de USD)
SI FALLA: Notificar inmediatamente a la Dirección de Estadísticas Económicas del BCE (estadisticas@bce.ec) y verificar si la estructura mensual del reporte o las notas metodológicas al pie fueron modificadas."""
import os, sys, logging
from datetime import date
from pathlib import Path
import pandas as pd

# ---------- 1 · PARAMETROS (todo lo que puede cambiar, junto y arriba) ----------
RUTA_ENTRADA    = "datos/export.csv" if os.path.exists("datos/export.csv") else "export.csv"
SALIDA          = f"salida/bce_exportaciones_mensuales_{date.today().isoformat()}.csv"
FILAS_ESPERADAS = 32
COLUMNAS_MIN    = 15

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.FileHandler("flujo.log"), logging.StreamHandler()])
log = logging.getLogger("mi_flujo_bce")

# ---------- 2 · LAS TRES FUNCIONES (cada una con su docstring) ----------
def extraer():
    """Lee el archivo CSV bruto del BCE con delimitador punto y coma y maneja codificacion UTF-8."""
    if not os.path.exists(RUTA_ENTRADA):
        raise FileNotFoundError(f"No se encontro el archivo de entrada en {RUTA_ENTRADA}")
    tabla = pd.read_csv(RUTA_ENTRADA, sep=";", header=None, encoding="utf-8-sig")
    log.info("extraidas %d filas crudas desde %s", len(tabla), RUTA_ENTRADA)
    return tabla

def transformar(tabla):
    """Filtra la serie mensual (2024-2026), limpia separadores de miles y valida consistencia."""
    # Extraemos el bloque de datos mensuales (filas 15 a 45 inclusive)
    df_mensual = tabla.iloc[15:46, :26].copy()

    # Control 1: Conteo estructural de períodos mensuales esperados
    if len(df_mensual) != FILAS_ESPERADAS:
        raise ValueError(f"esperaba {FILAS_ESPERADAS} filas y llegaron {len(df_mensual)}")

    # Control 2: Validacion de dimensionalidad
    if df_mensual.shape[1] < COLUMNAS_MIN:
        raise ValueError(f"esperaba al menos {COLUMNAS_MIN} columnas y llegaron {df_mensual.shape[1]}")

    # Normalizacion de tiempo: rellenar el anio hacia abajo (forward fill)
    df_mensual[0] = df_mensual[0].ffill()

    # Asignacion de nombres representativos a las columnas principales
    columnas = [
        "anio", "mes", "total_exportaciones_miles_usd", "total_primarios_miles_usd",
        "petroleo_crudo", "banano_platano", "cafe", "camaron", "cacao", "abaca",
        "madera", "atun", "pescado", "flores_naturales", "otros_primarios",
        "total_industrializados_miles_usd", "derivados_petroleo", "cafe_elaborado",
        "elaborados_cacao", "harina_pescado", "otros_elaborados_mar", "quimicos_farmacos",
        "manufacturas_metales", "sombreros", "manufacturas_textiles", "otros_industrializados"
    ]
    df_mensual.columns = columnas[:df_mensual.shape[1]]

    # Conversion de montos: remover punto de miles y convertir a float
    cols_numericas = [c for c in df_mensual.columns if c not in ("anio", "mes")]
    for col in cols_numericas:
        df_mensual[col] = df_mensual[col].astype(str).str.replace(".", "", regex=False)
        df_mensual[col] = pd.to_numeric(df_mensual[col], errors="coerce").fillna(0)

    # Control 3: Integridad de negocio (los totales no pueden ser negativos o cero)
    if (df_mensual["total_exportaciones_miles_usd"] <= 0).any():
        raise ValueError("se detectaron registros con exportaciones totales menores o iguales a cero")

    log.info("serie mensual transformada exitosamente: %d periodos procesados", len(df_mensual))
    return df_mensual

def cargar(tabla):
    """Crea la carpeta de salida si no existe y almacena el resultado fechado."""
    os.makedirs("salida", exist_ok=True)
    tabla.to_csv(SALIDA, index=False)
    log.info("guardado %s (%d filas)", SALIDA, len(tabla))

# ---------- 3 · LA LOGICA, EN ORDEN ----------
if __name__ == "__main__":
    try:
        cargar(transformar(extraer()))
        log.info("FIN OK")
    except Exception as error:
        log.error("EL FLUJO FALLO: %s", error)
        sys.exit(1)
