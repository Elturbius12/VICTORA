"""Parámetros configurables de VICTORA (un solo lugar)."""

SEMILLA = 42                 # semilla de todo lo aleatorio
COLCHON_P0 = 0.15            # colchón de la práctica habitual simulada
N_BOOT = 2000                # réplicas bootstrap
NIVEL_NO_PERECIBLE = 0.95    # nivel de servicio para productos no perecibles
MAX_PRUEBA = 28              # máximo de orígenes de prueba en el rolling origin
ENTRENAMIENTO_MIN = 7        # días mínimos de entrenamiento
HORIZONTE = 7                # días de plan de producción
MIN_DIAS_BLOQUEO, MIN_DIAS_ADVERTENCIA, MIN_DIAS_AVISO = 7, 14, 28

# Valores del caso de estudio (el usuario puede cambiarlos en la app; se insertan en los textos)
CONTEXTO_DEFECTO = {
    "software": "VICTORA",
    "caso": "La Victoriana",
    "ciudad": "Juliaca, Perú",
}

# Hojas del reporte Excel (descripción de cada una)
HOJAS_REPORTE = {
    "00_Portada": "Título, fecha, versión, periodo, número de productos y días, parámetros.",
    "01_Resumen": "Hallazgos clave en lenguaje llano.",
    "02_Problema_Ahorro": "Costo por política y ahorro de VICTORA frente a la práctica habitual.",
    "03_Descriptivos": "Estadística descriptiva por producto.",
    "04_Clasificacion": "ADI, CV², tipo de demanda, ABC y XYZ.",
    "05_Dia_Semana": "Perfil por día de la semana y Kruskal-Wallis.",
    "06_Correlaciones": "Spearman entre productos y con el día de la semana.",
    "07_Backtesting": "Errores por producto, modelo y fecha.",
    "08_Ranking_Modelos": "MASE, RMSSE, MAE, RMSE, WAPE, sesgo; ganador y frecuencia de victorias.",
    "09_Pruebas": "Wilcoxon, Friedman y bootstrap.",
    "10_Simulacion": "Resultados completos de la simulación contrafactual.",
    "11_Sensibilidad": "Sensibilidad al colchón de P0 y al margen.",
    "12_Plan_Produccion": "Producción recomendada para 7 días con intervalo.",
    "13_Insumos": "Necesidad de insumos y lista de compras.",
    "14_Texto_Metodos": "Párrafos de métodos ya redactados.",
    "15_Texto_Resultados": "Párrafos de resultados ya redactados.",
    "16_Limitaciones": "Limitaciones del estudio.",
    "17_Figuras": "Figuras con título y leyenda sugeridos (300 dpi).",
    "18_Reproducibilidad": "Versiones, semilla, parámetros y hash de los datos.",
    "99_Datos_Limpios": "Datos validados usados en el análisis.",
}
