"""Redacción automática (español académico) de métodos, resultados y limitaciones.

Cada función devuelve una lista de (subtítulo, párrafo) con los números reales del análisis.
"""
from __future__ import annotations

import platform

import numpy as np

from .decision import NIVEL_NO_PERECIBLE
from .utils import fmt_num as fn
from .utils import fmt_p


def _s(x):
    return f"S/ {fn(x)}"


def _pil(R):
    return "estudio piloto (prueba de concepto)" if R["n_dias"] < 28 else "estudio de caso"


def limitaciones(R) -> list[str]:
    L = []
    n = R["n_dias"]
    if n < 28:
        L.append(f"La serie abarca solo {n} días; con menos de cuatro semanas completas la estacionalidad "
                 "semanal se estima con muy pocas observaciones por día y los resultados deben considerarse preliminares.")
    if n < 14:
        L.append("Con menos de 14 días no se pudieron activar modelos estacionales (naïve estacional, perfil semanal).")
    if n < 28:
        L.append("El modelo Holt-Winters no se evaluó porque requiere al menos 28 días de datos.")
    L.append("Se asume que las ventas observadas equivalen a la demanda. En los días en que un producto se agotó, "
             "la venta subestima la demanda real (demanda censurada).")
    if R["n_agotados"]:
        L.append(f"Se registraron {R['n_agotados']} producto-días marcados como agotados; en ellos la demanda real "
                 "fue probablemente mayor que la venta, lo que sesga a la baja el pronóstico y el costo de faltante.")
    if R["fuente"] == "SIMULADO":
        L.append("No se dispuso de registros de producción ni de merma: los costos de merma y de faltante se "
                 "estimaron mediante simulación contrafactual y la práctica habitual (P0) es una regla supuesta, no observada.")
    L.append("Los costos unitarios se derivan del margen esperado declarado (c = p(1 − m)), no de una contabilidad de costos.")
    L.append("Los datos provienen de un único establecimiento, lo que limita la generalización de los resultados.")
    L.append(f"El periodo de prueba (≈{R['n_prueba']} días por producto) es corto; las pruebas de hipótesis tienen "
             "baja potencia estadística y los intervalos de confianza son amplios.")
    L.append("La selección del modelo y la evaluación de costos se realizaron sobre el mismo periodo de prueba, lo "
             "que puede producir un sesgo optimista en el desempeño del modelo ganador.")
    L.append("No se modelaron sustituciones entre productos, restricciones de capacidad ni efectos de precio o promociones.")
    if (R["calendario"] is None) or len(R["calendario"]) == 0 or not R["calendario"]["feriado"].any():
        L.append("No se incorporaron variables de calendario (feriados, eventos) por falta de datos suficientes.")
    return L


def metodos(R) -> list[tuple[str, str]]:
    n, k = R["n_dias"], R["n_productos"]
    tipos = R["clasif"]["tipo_demanda"].value_counts()
    n_int = int(R["clasif"]["intermitente"].sum())
    modelos = sorted(set(R["ranking"]["modelo"]))
    T = []
    T.append(("Diseño del estudio",
              f"Se realizó un {_pil(R)} de tipo cuantitativo, longitudinal y retrospectivo en {R['contexto']['caso']} "
              f"({R['contexto']['ciudad']}), un negocio de comida perecible. El objetivo fue evaluar si un sistema de pronóstico de demanda acoplado a una regla de "
              f"decisión óptima (modelo newsvendor) reduce los costos asociados a la sobreproducción (merma) y a la "
              f"subproducción (ventas perdidas) frente a una práctica de producción habitual."))
    T.append(("Datos",
              f"Se analizaron las ventas diarias de {k} productos durante {n} días de operación, entre el "
              f"{R['fecha_ini']:%d/%m/%Y} y el {R['fecha_fin']:%d/%m/%Y}, lo que suma {k * n} observaciones "
              f"producto-día. Para cada producto se registró el precio de venta, el margen esperado, su carácter "
              f"perecible y la receta de preparación. Los días sin registro se trataron según la indicación del "
              f"usuario (cerrado o venta cero). Se asumió que las ventas observadas equivalen a la demanda."
              + (f" En {R['n_agotados']} producto-días el producto se agotó, por lo que esas observaciones se "
                 "consideran censuradas." if R["n_agotados"] else "")))
    T.append(("Caracterización de la demanda",
              "Se calcularon estadísticos descriptivos (media, mediana, desviación estándar, coeficiente de "
              "variación, asimetría y curtosis). La demanda se clasificó según Syntetos y Boylan (2005) mediante el "
              "intervalo medio entre demandas (ADI) y el cuadrado del coeficiente de variación de los tamaños no "
              "nulos (CV²), con umbrales ADI = 1,32 y CV² = 0,49. "
              f"Resultaron {', '.join(f'{v} productos de tipo {t.lower()}' for t, v in tipos.items())}. "
              "Además se aplicó un análisis ABC por ingreso (80 % / 95 % acumulado) y XYZ por variabilidad "
              "(CV ≤ 0,5; ≤ 1,0; > 1,0). El efecto del día de la semana se evaluó con la prueba de Kruskal-Wallis "
              "y su tamaño de efecto ε², y la asociación entre productos con la correlación de Spearman."))
    T.append(("Modelos de pronóstico",
              "Dada la corta longitud de las series se emplearon únicamente modelos parsimoniosos: "
              f"{', '.join(modelos)}. El modelo naïve estacional y el perfil por día de la semana (media del mismo "
              "día con contracción hacia la media global, peso k = 1) se activan con al menos 14 días; Holt-Winters "
              "aditivo con estacionalidad semanal requiere 28 días. La suavización exponencial simple (SES) eligió α "
              "por mínimo error cuadrático en una rejilla de 0,05 a 0,95. Para productos intermitentes "
              f"(ADI > 1,32 y CV² ≥ 0,49; n = {n_int}) se añadieron los métodos de Croston (1972), SBA (Syntetos y "
              "Boylan, 2005) y TSB (Teunter et al., 2011) con α = β = 0,1. Se incluyó como candidato adicional una "
              "combinación por promedio simple de los tres mejores modelos. Todos los pronósticos se truncaron en cero."))
    T.append(("Validación y selección",
              f"El desempeño se evaluó mediante validación con origen rodante (rolling origin) a un día de horizonte: "
              f"cada modelo se reentrenó con los datos disponibles hasta el día t y pronosticó el día t + 1, con un "
              f"entrenamiento mínimo de {min(s['t0'] for s in R['sel'].values())} días, lo que generó "
              f"aproximadamente {R['n_prueba']} pronósticos fuera de muestra por producto"
              + (" (con series largas se evaluaron solo los últimos 28 orígenes)" if R["n_dias"] > 38 else "")
              + f". El modelo de cada producto "
              "se eligió por el menor error absoluto escalado medio (MASE; Hyndman y Koehler, 2006) o, para demanda "
              "intermitente, por la raíz del error cuadrático medio escalado (RMSSE). Se reportan además MAE, RMSE, "
              "WAPE y sesgo."))
    T.append(("Definición de métricas",
              "Siendo eₜ = yₜ − ŷₜ el error de pronóstico y Q la escala dada por el error medio del naïve dentro de "
              "la muestra de entrenamiento: MAE = (1/n) Σ|eₜ|; RMSE = √[(1/n) Σ eₜ²]; MASE = MAE / [(1/(T−1)) "
              "Σ|yₜ − yₜ₋₁|]; RMSSE = √{[(1/n) Σ eₜ²] / [(1/(T−1)) Σ (yₜ − yₜ₋₁)²]}; WAPE = Σ|eₜ| / Σ|yₜ| × 100; "
              "Sesgo = (1/n) Σ(ŷₜ − yₜ). Un MASE menor que 1 indica un desempeño mejor que el pronóstico naïve. La "
              "tasa de cumplimiento (fill rate) se definió como unidades vendidas / unidades demandadas × 100."))
    T.append(("Modelo de decisión (newsvendor)",
              "La cantidad a producir se determinó con el modelo del vendedor de periódicos (newsvendor). Para cada "
              "producto con precio p y margen m se definió el costo unitario c = p(1 − m/100), el costo de "
              "sobreproducir una unidad Cₒ = c − v (v = valor de rescate) y el costo de quedarse corto Cᵤ = p − c. "
              "La razón crítica es RC = Cᵤ / (Cᵤ + Cₒ) y la cantidad óptima Q* = F⁻¹(RC), donde F es la distribución "
              "de la demanda, estimada empíricamente como el pronóstico puntual más los residuos del backtesting "
              "(agrupados entre productos con escala normalizada cuando había menos de 10 residuos). Q* se redondeó "
              f"al entero superior y al múltiplo del tamaño de lote. Para productos no perecibles se fijó un nivel de "
              f"servicio de {fn(NIVEL_NO_PERECIBLE * 100, 0)} %. Las razones críticas obtenidas variaron entre "
              f"{fn(R['plan']['razon_critica'].min(), 2)} y {fn(R['plan']['razon_critica'].max(), 2)}. El intervalo "
              "de producción se reporta con los cuantiles 10 % y 90 %. Las necesidades de insumos se obtuvieron por "
              "explosión de materiales a partir de las recetas."))
    T.append(("Evaluación contrafactual",
              "Ante la ausencia de registros de merma, se simuló día a día en el periodo de prueba lo que habría "
              "ocurrido con cinco políticas: P0, práctica habitual simulada (media de los últimos 7 días × (1 + "
              f"colchón), colchón = {fn(R['colchon'] * 100, 0)} %); P1, naïve (venta del día anterior); P2, mismo día "
              "de la semana anterior; P3, media móvil de 7 días; y P4, VICTORA (modelo seleccionado + Q* del "
              "newsvendor, estimado solo con residuos anteriores a cada día). Para cada política se calcularon las "
              "unidades sobrantes y faltantes, el costo de merma (sobrante × Cₒ), el margen perdido (faltante × Cᵤ), "
              "el costo total y el fill rate."
              + (" Para P0 se emplearon los registros reales de producción disponibles." if R["fuente"] == "REAL" else "")))
    T.append(("Análisis estadístico",
              "La diferencia de costo diario por producto entre VICTORA y cada política se contrastó con la prueba de "
              "rangos con signo de Wilcoxon (bilateral), con tamaño de efecto de correlación biserial de rangos y "
              "corrección de Holm por comparaciones múltiples. Las cinco políticas se compararon conjuntamente con la "
              "prueba de Friedman y el coeficiente W de Kendall. El intervalo de confianza del ahorro se estimó por "
              f"bootstrap percentil con {R['boot']['replicas']} réplicas (semilla {R['semilla']}). Se trabajó con un "
              "nivel de significancia de 0,05. La sensibilidad se evaluó variando el colchón de P0 (0 %, 10 %, 15 %, "
              "25 % y 40 %) y el margen (± 10 puntos porcentuales)."))
    T.append(("Software",
              f"Los análisis se realizaron con {R['contexto']['software']} v{R['version']} (Python {platform.python_version()}; "
              "pandas, NumPy, SciPy, statsmodels y matplotlib). Los resultados son reproducibles con semilla fija "
              f"({R['semilla']}); identificador de datos (hash): {R['hash']}."))
    return T


def resultados(R) -> list[tuple[str, str]]:
    rp = R["res_pol"].set_index("politica")
    p0, p4 = rp.loc["P0"], rp.loc["P4"]
    b = R["boot"]
    d = R["desc"].sort_values("media", ascending=False)
    kw = R["kw"]
    sig_kw = int((kw["p_valor"] < 0.05).sum())
    gan = R["ganadores"]
    frec = gan["modelo"].value_counts()
    mase_med = gan.loc[gan["metrica_principal"] == "MASE", "MASE"].median()
    n_mejor = int((gan["MASE"] < 1).sum())
    w = R["wilcoxon"].set_index("comparacion")
    fr = R["friedman"]
    etiqueta = "simulados" if R["fuente"] == "SIMULADO" else "estimados con producción real"
    mejor_pol = rp["costo_total"].idxmin()
    T = []
    T.append(("Caracterización de la demanda",
              f"La venta media diaria varió entre {fn(d['media'].min(), 1)} y {fn(d['media'].max(), 1)} unidades "
              f"(Tabla 2); el producto de mayor rotación fue {d['nombre'].iloc[0]} (M = {fn(d['media'].iloc[0], 1)}, "
              f"DE = {fn(d['DE'].iloc[0], 1)}). El coeficiente de variación osciló entre {fn(d['CV'].min(), 2)} y "
              f"{fn(d['CV'].max(), 2)}. Según la clasificación de Syntetos–Boylan (Tabla 3; Figura 5), "
              f"{int(R['clasif']['intermitente'].sum())} de {R['n_productos']} productos "
              f"cumplieron el criterio de demanda intermitente o irregular (ADI > 1,32 y CV² ≥ 0,49) para los métodos de Croston. La prueba de Kruskal-Wallis detectó un efecto significativo del día de la semana en "
              f"{sig_kw} de {len(kw)} productos (Tabla 5); dado que cada día de la semana cuenta con "
              f"{int(kw['obs_min_por_dia'].min())} a {int(kw['obs_min_por_dia'].max())} observaciones, la potencia de "
              "esta prueba es baja y la ausencia de significancia no debe interpretarse como ausencia de efecto."))
    T.append(("Desempeño de los modelos de pronóstico",
              f"En la validación con origen rodante (Tabla 9; Figura 4), el modelo ganador con mayor frecuencia fue "
              f"{frec.index[0]} ({frec.iloc[0]} de {R['n_productos']} productos). La mediana del MASE del modelo "
              f"seleccionado fue {fn(mase_med, 2)}; en {n_mejor} de {R['n_productos']} productos el modelo elegido "
              f"superó al pronóstico naïve (MASE < 1)."
              + (" En los productos restantes ningún modelo mejoró al naïve, lo que es esperable en series tan cortas."
                 if n_mejor < R["n_productos"] else "")))
    T.append(("Plan de producción",
              f"Para los siete días siguientes al periodo analizado, el modelo newsvendor recomendó producir en total "
              f"{int(R['plan']['producir'].sum())} unidades (Tabla 19), frente a un pronóstico puntual acumulado de "
              f"{fn(R['plan']['pronostico'].sum(), 0)} unidades; la diferencia refleja el inventario de seguridad "
              "implícito en las razones críticas, que favorecen producir algo más cuando el margen es alto."))
    T.append(("Impacto económico (evaluación contrafactual)",
              f"En el periodo de prueba, la práctica habitual simulada (P0) habría generado un costo total de "
              f"{_s(p0['costo_total'])} ({_s(p0['costo_merma'])} en merma y {_s(p0['margen_perdido'])} en margen "
              f"perdido), con un fill rate de {fn(p0['fill_rate_pct'], 1)} %. Con VICTORA (P4) el costo habría sido "
              f"{_s(p4['costo_total'])} ({_s(p4['costo_merma'])} en merma y {_s(p4['margen_perdido'])} en margen "
              f"perdido) y el fill rate de {fn(p4['fill_rate_pct'], 1)} % (Tabla 1 y Tabla 15; Figuras 1 y 2). Esto representa un "
              f"ahorro de {_s(b['ahorro_S/'])} ({fn(b['ahorro_pct'], 1)} %; IC 95 % bootstrap: "
              f"{fn(b['IC95_pct_inf'], 1)} % a {fn(b['IC95_pct_sup'], 1)} %). Estos valores son {etiqueta}. "
              f"La política de menor costo total fue {mejor_pol}."
              + ("" if b["ahorro_S/"] > 0 else " Es decir, en estos datos VICTORA no redujo el costo frente a la "
                 "práctica habitual simulada, resultado que debe reportarse como tal.")))
    wp = w.loc["P0 vs P4"] if "P0 vs P4" in w.index else None
    if wp is not None:
        sig = wp["p_Holm"] < 0.05
        T.append(("Contraste de hipótesis",
                  f"La prueba de Wilcoxon indicó que la diferencia en el costo diario entre P0 y VICTORA "
                  f"{'fue' if sig else 'no fue'} estadísticamente significativa (W = {fn(wp['W'], 1)}, "
                  f"{fmt_p(wp['p_valor'])}, p ajustado por Holm = {fn(wp['p_Holm'], 3)}, r = "
                  f"{fn(wp['r_rank_biserial'], 2)}; Tabla 12). La prueba de Friedman sobre las cinco políticas "
                  f"arrojó χ²({fr['gl']}) = {fn(fr['chi2'], 2)}, {fmt_p(fr['p_valor'])}, W de Kendall = "
                  f"{fn(fr['W_Kendall'], 3)}."
                  + ("" if sig else " Con el tamaño de muestra disponible no puede descartarse que la diferencia "
                     "observada se deba al azar; se requiere un periodo de observación mayor para confirmarla.")))
    sc = R["sens_col"]
    T.append(("Análisis de sensibilidad",
              f"Al variar el colchón de P0 entre 0 % y 40 %, el ahorro de VICTORA osciló entre "
              f"{_s(sc['ahorro'].min())} y {_s(sc['ahorro'].max())} (Tabla 17; Figura 3). Con variaciones de ± 10 puntos en el "
              f"margen, el ahorro se mantuvo entre {_s(R['sens_mar']['ahorro'].min())} y "
              f"{_s(R['sens_mar']['ahorro'].max())}."))
    T.append(("Interpretación",
              f"En conjunto, estos resultados de un {_pil(R)} con {R['n_dias']} días de datos sugieren que un sistema "
              f"de pronóstico y decisión óptima podría {'reducir' if b['ahorro_S/'] > 0 else 'no reducir'} los costos "
              f"de producción en torno a {fn(abs(b['ahorro_pct']), 1)} %. La evidencia debe confirmarse con datos de "
              "un periodo más largo y, de ser posible, con registros reales de producción y merma."))
    return T


def resumen(R) -> list[str]:
    rp = R["res_pol"].set_index("politica")
    b = R["boot"]
    return [
        f"Se analizaron {R['n_productos']} productos durante {R['n_dias']} días ({R['fecha_ini']:%d/%m/%Y} – {R['fecha_fin']:%d/%m/%Y}).",
        f"Sin VICTORA (práctica habitual P0) el costo de merma + ventas perdidas habría sido {_s(rp.loc['P0', 'costo_total'])}.",
        f"Con VICTORA (P4) habría sido {_s(rp.loc['P4', 'costo_total'])}: ahorro de {_s(b['ahorro_S/'])} ({fn(b['ahorro_pct'], 1)} %).",
        f"Cifras: ⚠️ {R['fuente']}. Intervalo de confianza 95 % del ahorro: {fn(b['IC95_pct_inf'], 1)} % a {fn(b['IC95_pct_sup'], 1)} %.",
        f"El modelo más elegido fue {R['ganadores']['modelo'].value_counts().index[0]}.",
        f"Para la próxima semana se recomienda producir {int(R['plan']['producir'].sum())} unidades en total.",
        ("Estudio piloto: con menos de 28 días los resultados son preliminares." if R["n_dias"] < 28
         else "Con 28 días o más se activaron todos los modelos."),
    ]


def hallazgos(R) -> list[str]:
    """Hallazgos clave (3–5 viñetas) para la parte superior de la pestaña de análisis."""
    d = R["desc"].sort_values("media", ascending=False)
    n_int = int(R["clasif"]["intermitente"].sum())
    tot = R["perfil"].sum(axis=1)
    frec = R["ganadores"]["modelo"].value_counts()
    return [
        f"El producto más vendido es {d['nombre'].iloc[0]} con {fn(d['media'].iloc[0], 1)} unidades/día en promedio.",
        f"{n_int} de {R['n_productos']} productos tienen demanda intermitente (se venden algunos días sí y otros no).",
        f"El día de mayor venta es {tot.idxmax()}; el de menor venta es {tot.idxmin()}.",
        f"El modelo que más veces gana es {frec.index[0]} ({frec.iloc[0]} de {R['n_productos']} productos).",
        f"Clase A (≈80 % del ingreso): {int((R['clasif']['ABC'] == 'A').sum())} productos.",
    ]


def ecuaciones_latex(R) -> list[tuple[str, str]]:
    """Ecuaciones del método en LaTeX (entorno equation con label), con parámetros reales de la ejecución."""
    from .config import ENTRENAMIENTO_MIN, MAX_PRUEBA, N_BOOT
    B = int(R.get("boot", {}).get("replicas", N_BOOT))
    nv = NIVEL_NO_PERECIBLE
    eqs = [
        ("eq:costo_unitario", r"c_i = p_i\left(1 - \frac{m_i}{100}\right)"),
        ("eq:costo_exceso", r"C_{o,i} = c_i - v_i"),
        ("eq:costo_faltante", r"C_{u,i} = p_i - c_i"),
        ("eq:razon_critica", r"CR_i = \frac{C_{u,i}}{C_{u,i} + C_{o,i}}"
                             rf"\quad (\text{{no perecibles: }} CR_i = {nv:.2f})".replace(".", "{,}")),
        ("eq:newsvendor", r"Q_{i,t}^{*} = \hat{F}_{i,t}^{-1}(CR_i), \quad "
                          r"\hat{F}_{i,t}(x) = \frac{1}{n}\sum_{k=1}^{n} \mathbf{1}\left\{\max\left(0,\ \hat{y}_{i,t} + e_{i,k}\right) \le x\right\}"),
        ("eq:mase", r"\mathrm{MASE} = \frac{\frac{1}{h}\sum_{t=T+1}^{T+h} \lvert y_t - \hat{y}_t \rvert}"
                    r"{\frac{1}{T-1}\sum_{t=2}^{T} \lvert y_t - y_{t-1} \rvert}"),
        ("eq:rmsse", r"\mathrm{RMSSE} = \sqrt{\frac{\frac{1}{h}\sum_{t=T+1}^{T+h} (y_t - \hat{y}_t)^2}"
                     r"{\frac{1}{T-1}\sum_{t=2}^{T} (y_t - y_{t-1})^2}}"),
        ("eq:adi_cv2", r"\mathrm{ADI} = \frac{N}{N_{+}}, \quad \mathrm{CV}^2 = \left(\frac{\sigma_{y^{+}}}{\mu_{y^{+}}}\right)^2,"
                       r"\quad \text{intermitente} \iff \mathrm{ADI} > 1{,}32 \ \wedge\ \mathrm{CV}^2 \ge 0{,}49"),
        ("eq:wilcoxon", r"W^{+} = \sum_{j:\, d_j > 0} R_j, \quad W^{-} = \sum_{j:\, d_j < 0} R_j, \quad "
                        r"r_{rb} = \frac{W^{+} - W^{-}}{W^{+} + W^{-}}"),
        ("eq:bootstrap", rf"\mathrm{{IC}}_{{95\%}} = \left[\hat{{\theta}}^{{*}}_{{(0{{,}}025)}},\ \hat{{\theta}}^{{*}}_{{(0{{,}}975)}}\right],"
                         rf"\quad \hat{{\theta}}^{{*}}_b = \bar{{A}}^{{*}}_b,\ b = 1,\dots,B,\ B = {B}"),
    ]
    notas = {"eq:newsvendor": f"% e_{{i,k}}: residuos del backtesting rolling origin (entrenamiento mínimo {ENTRENAMIENTO_MIN} días, "
                              f"máximo {MAX_PRUEBA} orígenes); Q* truncado en 0 y ajustado al lote.\n"}
    return [(et, notas.get(et, "") + "\\begin{equation}\\label{" + et + "}\n" + tex + "\n\\end{equation}") for et, tex in eqs]


def marco_normativo() -> str:
    """Párrafo académico que vincula el pronóstico de demanda de perecibles con la normativa sanitaria aplicable."""
    return (
        "Desde la perspectiva normativa, un mejor pronóstico de la demanda de productos perecibles no es solo una "
        "cuestión de costos: al ajustar la producción diaria a la demanda esperada se reduce el inventario remanente "
        "que, al final de la jornada, tiende a conservarse más allá de su vida útil o a reutilizarse en condiciones "
        "inadecuadas. Así, la reducción de la merma contribuye directamente al cumplimiento de la vida útil declarada "
        "y, con ello, a la inocuidad del alimento que llega al consumidor. En el Perú, la Ley N.° 26842, Ley General "
        "de Salud (1997), establece que la producción y comercialización de alimentos está sujeta a vigilancia "
        "sanitaria y que los alimentos destinados al consumo humano deben ser inocuos; el Decreto Legislativo "
        "N.° 1062, Ley de Inocuidad de los Alimentos (2008), consagra la responsabilidad del proveedor sobre la "
        "inocuidad de lo que produce y comercializa. El Decreto Supremo N.° 007-98-SA, Reglamento sobre Vigilancia y "
        "Control Sanitario de Alimentos y Bebidas (1998), regula las condiciones de fabricación, almacenamiento y "
        "conservación de los alimentos elaborados, y la Resolución Ministerial N.° 822-2018/MINSA, que aprueba la "
        "Norma Sanitaria para Restaurantes y Servicios Afines [VERIFICAR: número de NTS y vigencia], fija criterios "
        "de manipulación y conservación de preparaciones en establecimientos de expendio de comidas. En el plano "
        "internacional, los Principios Generales de Higiene de los Alimentos del Codex Alimentarius (CXC 1-1969, "
        "antes CAC/RCP 1-1969, revisados en 2020) recomiendan controlar el tiempo y la temperatura de los alimentos "
        "listos para el consumo y rotar las existencias. En consecuencia, un plan de producción basado en el modelo "
        "newsvendor, que limita la sobreproducción sistemática, constituye una herramienta de gestión que apoya el "
        "cumplimiento de estas exigencias sanitarias, además de contribuir a la reducción de la pérdida y el "
        "desperdicio de alimentos promovida por la FAO (2019)."
    )
