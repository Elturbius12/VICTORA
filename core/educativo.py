"""Módulo educativo: explicaciones simples de cada modelo de pronóstico.

Cada modelo tiene:
- nombre: nombre del modelo
- formula: la fórmula matemática
- explicacion: explicación como para un niño de 10 años
- ejemplo: función que genera un ejemplo paso a paso con datos reales
"""
import numpy as np


def _fmt(x):
    return f"{x:.1f}" if x != int(x) else str(int(x))


MODELOS_EDUCATIVOS = {
    "Ingenuo (ayer)": {
        "nombre": "Modelo Ingenuo (Naive)",
        "formula": "Pronóstico = Venta de ayer",
        "explicacion": (
            "Este es el modelo más simple que existe. Dice:\n\n"
            "\"Lo que vendiste ayer, eso mismo venderás mañana.\"\n\n"
            "Es como si mañana fuera a llover solo porque hoy llovió. "
            "No siempre acierta, pero es un buen punto de partida para "
            "comparar si los otros modelos realmente son mejores."
        ),
        "ejemplo": lambda y, dates: _ejemplo_naive(y, dates),
    },
    "Promedio histórico": {
        "nombre": "Promedio Histórico",
        "formula": "Pronóstico = (Venta día 1 + Venta día 2 + ... + Venta día N) / N",
        "explicacion": (
            "Imagina que vendes limonada. Algunos días vendes 10, otros 5, otros 8.\n\n"
            "El promedio histórico dice: \"Suma todo lo que vendiste y divide entre "
            "los días. Eso es lo que probablemente venderás mañana.\"\n\n"
            "Es como sacar el promedio de tus notas del colegio: "
            "te da una idea general de cómo te va."
        ),
        "ejemplo": lambda y, dates: _ejemplo_promedio(y, dates),
    },
    "Media móvil 3d": {
        "nombre": "Media Móvil de 3 días",
        "formula": "Pronóstico = (Venta de hace 3 días + hace 2 días + ayer) / 3",
        "explicacion": (
            "En vez de promediar TODOS los días (como el promedio histórico), "
            "solo promediamos los 3 últimos días.\n\n"
            "¿Por qué? Porque lo que pasó la semana pasada importa más que "
            "lo que pasó hace un mes. Es como estudiar para un examen: "
            "repasas lo más reciente, no todo desde el inicio del año.\n\n"
            "Si los últimos 3 días vendiste 8, 10 y 6 pollos, "
            "el pronóstico es (8 + 10 + 6) / 3 = 8 pollos."
        ),
        "ejemplo": lambda y, dates: _ejemplo_media_movil(y, dates, 3),
    },
    "Media móvil 7d": {
        "nombre": "Media Móvil de 7 días",
        "formula": "Pronóstico = (Ventas de los últimos 7 días) / 7",
        "explicacion": (
            "Igual que la media de 3 días, pero usa los últimos 7 días completos "
            "(una semana entera).\n\n"
            "Esto es útil porque muchos negocios de comida tienen un patrón semanal: "
            "los viernes y sábados se vende más, los lunes menos. "
            "Al usar 7 días, capturas ese ciclo completo."
        ),
        "ejemplo": lambda y, dates: _ejemplo_media_movil(y, dates, 7),
    },
    "Suavizamiento exp. simple": {
        "nombre": "Suavización Exponencial Simple (SES)",
        "formula": "Nivel_t = α × Venta_t + (1 - α) × Nivel_{t-1}\nPronóstico = Nivel más reciente",
        "explicacion": (
            "Imagina una balanza con dos platillos:\n\n"
            "- En un platillo pones lo que VENDISTE HOY (el dato nuevo)\n"
            "- En el otro pones lo que YA CREÍAS que ibas a vender (el pronóstico anterior)\n\n"
            "α (alfa) es qué tanto le crees a lo nuevo. Si α = 0.3, le das 30% de peso "
            "a lo de hoy y 70% a lo que ya creías.\n\n"
            "Si α es alto (ej. 0.8), reaccionas rápido a cambios. "
            "Si es bajo (ej. 0.1), eres más estable y no te asustas por un día raro.\n\n"
            "El software prueba muchos valores de α y elige el que produce menos error."
        ),
        "ejemplo": lambda y, dates: _ejemplo_ses(y, dates),
    },
    "Holt amortiguado": {
        "nombre": "Holt Amortiguado (Damped Trend)",
        "formula": "Nivel_t = α × Venta_t + (1-α) × (Nivel_{t-1} + φ × Tendencia_{t-1})\nTendencia_t = β × (Nivel_t - Nivel_{t-1}) + (1-β) × φ × Tendencia_{t-1}",
        "explicacion": (
            "Este modelo es como SES pero además detecta si las ventas van SUBIENDO "
            "o BAJANDO (la tendencia).\n\n"
            "Imagina que cada semana vendes un poco más de hamburguesas. "
            "SES no ve esa subida; Holt sí.\n\n"
            "La parte \"amortiguada\" (φ) hace que la tendencia se frene poco a poco: "
            "no asume que vas a seguir subiendo para siempre, "
            "sino que eventualmente se estabiliza. Es más realista."
        ),
        "ejemplo": lambda y, dates: _ejemplo_holt(y, dates),
    },
    "Perfil día de semana": {
        "nombre": "Perfil por Día de la Semana",
        "formula": "Pronóstico = Promedio de ventas de ese mismo día de la semana\n(con ajuste de contracción hacia el promedio general)",
        "explicacion": (
            "Este modelo dice: \"Los lunes se vende diferente que los viernes.\"\n\n"
            "Calcula cuánto vendes en promedio cada día de la semana por separado. "
            "Si los viernes promedias 15 pollos pero los martes solo 8, "
            "usa esos promedios.\n\n"
            "El \"ajuste de contracción\" es para cuando tienes pocos datos de un día "
            "(ej. solo 2 viernes). En ese caso, mezcla el promedio del viernes "
            "con el promedio general para no confiar demasiado en tan pocos datos."
        ),
        "ejemplo": lambda y, dates: _ejemplo_perfil_dia(y, dates),
    },
    "Holt-Winters semanal": {
        "nombre": "Holt-Winters Aditivo (Estacionalidad Semanal)",
        "formula": "Nivel + Tendencia + Factor_Estacional[día_semana]",
        "explicacion": (
            "Este es uno de los modelos más completos. Combina tres cosas:\n\n"
            "1. NIVEL: ¿cuánto se vende en general?\n"
            "2. TENDENCIA: ¿las ventas están subiendo o bajando?\n"
            "3. ESTACIONALIDAD: ¿qué día de la semana es? "
            "(porque los viernes se vende más que los martes)\n\n"
            "Es como un calendario inteligente: sabe que es viernes "
            "(va a vender más), que la tendencia es de subida "
            "(cada semana un poquito más), y lo combina todo.\n\n"
            "Necesita al menos 2 semanas de datos para funcionar bien. "
            "Con más semanas, se vuelve muy preciso.\n\n"
            "La literatura (Veiga et al., 2014) encontró que este modelo "
            "superó a ARIMA en retail de alimentos con MAPE de solo 4.97%."
        ),
        "ejemplo": lambda y, dates: _ejemplo_hw(y, dates),
    },
    "Croston": {
        "nombre": "Método de Croston",
        "formula": "Pronóstico = Tamaño promedio de demanda / Intervalo promedio entre demandas",
        "explicacion": (
            "Algunos productos no se venden todos los días. "
            "La gaseosa, por ejemplo, se vende 0, 0, 3, 0, 0, 2, 0, 4...\n\n"
            "Los otros modelos se confunden con tantos ceros. "
            "Croston es diferente: solo mira los días en que SÍ hubo venta.\n\n"
            "Calcula dos cosas:\n"
            "- ¿Cuánto se vende CUANDO se vende? (tamaño promedio)\n"
            "- ¿Cada cuántos días hay una venta? (intervalo promedio)\n\n"
            "Luego divide: tamaño / intervalo = pronóstico diario.\n\n"
            "Si vendes 3 gaseosas cada 3 días → pronóstico = 3/3 = 1 por día."
        ),
        "ejemplo": lambda y, dates: _ejemplo_croston(y, dates),
    },
    "Croston SBA": {
        "nombre": "Croston SBA (Syntetos-Boylan Approximation)",
        "formula": "Pronóstico Croston × (1 - α/2)",
        "explicacion": (
            "Es una mejora del método de Croston.\n\n"
            "Se descubrió que Croston tiende a predecir un poquito de más "
            "(sobreestima). La corrección SBA multiplica por (1 - α/2) "
            "para ajustar esa sobreestimación.\n\n"
            "Si α = 0.2, multiplica por 0.9 (le quita 10%). "
            "Es un ajuste pequeño pero mejora la precisión."
        ),
        "ejemplo": lambda y, dates: _ejemplo_croston(y, dates, sba=True),
    },
    "TSB": {
        "nombre": "TSB (Teunter-Syntetos-Babai)",
        "formula": "Pronóstico = Tamaño promedio × Probabilidad de demanda",
        "explicacion": (
            "Similar a Croston, pero en vez de usar el intervalo entre ventas, "
            "estima directamente la PROBABILIDAD de que haya venta cada día.\n\n"
            "Si la probabilidad de vender gaseosa un día es 40% "
            "y cuando vendes, vendes en promedio 3, entonces:\n"
            "Pronóstico = 3 × 0.40 = 1.2 gaseosas por día.\n\n"
            "La ventaja es que si un producto deja de venderse, "
            "la probabilidad va bajando poco a poco hasta cero. "
            "Croston no hace eso."
        ),
        "ejemplo": lambda y, dates: _ejemplo_tsb(y, dates),
    },
    "Regresión ridge (tend.+día)": {
        "nombre": "Regresión Ridge (Tendencia + Día de la Semana)",
        "formula": "Pronóstico = b₀ + b₁×(número de día) + b₂×(es lunes) + b₃×(es martes) + ...",
        "explicacion": (
            "Imagina que dibujas una línea recta sobre tus ventas.\n\n"
            "Esa línea tiene dos ingredientes:\n"
            "- TENDENCIA: la línea sube, baja o se queda plana\n"
            "- DÍA DE SEMANA: cada día tiene un \"bonus\" o \"descuento\"\n\n"
            "El \"Ridge\" es un truco para que la línea no se vuelva loca "
            "cuando tienes pocos datos. Le dice: \"no exageres las diferencias "
            "entre días\".\n\n"
            "Es como ajustar una regla sobre los datos, "
            "pero con un poquito de flexibilidad."
        ),
        "ejemplo": lambda y, dates: _ejemplo_ridge(y, dates),
    },
    "Ensamble (top 3)": {
        "nombre": "Ensemble (Promedio de los 3 Mejores)",
        "formula": "Pronóstico = (Pronóstico Modelo A + Pronóstico Modelo B + Pronóstico Modelo C) / 3",
        "explicacion": (
            "En vez de confiar en UN solo modelo, ¿por qué no preguntar a los "
            "3 mejores y promediar sus respuestas?\n\n"
            "Es como pedir opinión a 3 amigos sobre cuánta comida preparar "
            "para una fiesta: si uno dice 20, otro dice 25 y otro dice 22, "
            "el promedio (22.3) probablemente sea mejor que cualquiera solo.\n\n"
            "El software automáticamente identifica los 3 modelos con menor error "
            "y promedia sus pronósticos.\n\n"
            "La revisión de literatura (Petrisia & Kularatne, 2024) confirma que "
            "los enfoques ensemble reducen errores entre 14-52%."
        ),
        "ejemplo": lambda y, dates: _ejemplo_ensemble(y, dates),
    },
}


# --- Funciones de ejemplo ---

def _ejemplo_naive(y, dates):
    if len(y) < 2:
        return "Necesitas al menos 2 días de datos para este ejemplo."
    ayer = _fmt(y[-1])
    antier = _fmt(y[-2])
    return (
        f"Datos reales:\n"
        f"  Antes de ayer: {antier} unidades\n"
        f"  Ayer: {ayer} unidades\n\n"
        f"Pronóstico para mañana:\n"
        f"  = Venta de ayer = {ayer} unidades\n\n"
        f"Así de simple: si ayer vendiste {ayer}, mañana el pronóstico es {ayer}."
    )


def _ejemplo_promedio(y, dates):
    n = min(len(y), 5)
    datos = y[-n:]
    vals = " + ".join(_fmt(v) for v in datos)
    prom = np.mean(datos)
    return (
        f"Últimos {n} días de ventas: {', '.join(_fmt(v) for v in datos)}\n\n"
        f"Pronóstico = ({vals}) / {n}\n"
        f"           = {_fmt(sum(datos))} / {n}\n"
        f"           = {_fmt(prom)} unidades"
    )


def _ejemplo_media_movil(y, dates, k):
    if len(y) < k:
        return f"Necesitas al menos {k} días de datos."
    datos = y[-k:]
    vals = " + ".join(_fmt(v) for v in datos)
    prom = np.mean(datos)
    return (
        f"Últimos {k} días: {', '.join(_fmt(v) for v in datos)}\n\n"
        f"Pronóstico = ({vals}) / {k}\n"
        f"           = {_fmt(sum(datos))} / {k}\n"
        f"           = {_fmt(prom)} unidades"
    )


def _ejemplo_ses(y, dates):
    if len(y) < 3:
        return "Necesitas al menos 3 días."
    alpha = 0.3
    datos = y[-4:] if len(y) >= 4 else y[-3:]
    lines = [f"Usamos α = {alpha}\n"]
    lines.append(f"Día 1: Venta = {_fmt(datos[0])}, Nivel = {_fmt(datos[0])} (empezamos aquí)\n")
    nivel = float(datos[0])
    for i, v in enumerate(datos[1:], 2):
        nuevo = alpha * v + (1 - alpha) * nivel
        lines.append(
            f"Día {i}: Venta = {_fmt(v)}\n"
            f"  Nivel = {alpha} × {_fmt(v)} + {1-alpha} × {_fmt(nivel)}\n"
            f"       = {_fmt(alpha*v)} + {_fmt((1-alpha)*nivel)} = {_fmt(nuevo)}\n"
        )
        nivel = nuevo
    lines.append(f"\nPronóstico para mañana = {_fmt(nivel)} unidades")
    return "".join(lines)


def _ejemplo_holt(y, dates):
    if len(y) < 3:
        return "Necesitas al menos 3 días."
    return (
        "Ejemplo simplificado con los últimos 3 datos:\n"
        f"  Ventas: {_fmt(y[-3])}, {_fmt(y[-2])}, {_fmt(y[-1])}\n\n"
        f"  Tendencia ≈ ({_fmt(y[-1])} - {_fmt(y[-3])}) / 2 = {_fmt((y[-1]-y[-3])/2)}\n"
        f"  Nivel actual ≈ {_fmt(y[-1])}\n"
        f"  Pronóstico = Nivel + Tendencia amortiguada\n"
        f"             = {_fmt(y[-1])} + 0.9 × {_fmt((y[-1]-y[-3])/2)}\n"
        f"             = {_fmt(y[-1] + 0.9 * (y[-1]-y[-3])/2)} unidades\n\n"
        "El 0.9 es φ (phi), el factor de amortiguamiento que frena la tendencia."
    )


def _ejemplo_perfil_dia(y, dates):
    if len(y) < 7:
        return "Necesitas al menos 7 días para ver el patrón semanal."
    import pandas as pd
    dias_es = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 6: "Sáb", 5: "Dom"}
    ds = pd.Series(y, index=pd.DatetimeIndex(dates))
    por_dia = ds.groupby(ds.index.dayofweek).mean()
    lines = ["Promedio de ventas por día de la semana:\n"]
    for d, val in por_dia.items():
        lines.append(f"  {dias_es.get(d, d)}: {_fmt(val)} unidades\n")
    prom = np.mean(y)
    lines.append(f"\nPromedio general: {_fmt(prom)}\n")
    lines.append("\nEl pronóstico para mañana usa el promedio de ese día específico,")
    lines.append("\najustado hacia el promedio general si hay pocos datos de ese día.")
    return "".join(lines)


def _ejemplo_hw(y, dates):
    return (
        "Holt-Winters necesita al menos 14 días (2 semanas completas).\n\n"
        "Ejemplo conceptual:\n"
        "  Nivel general: 10 unidades/día\n"
        "  Tendencia: +0.5 por día (subiendo)\n"
        "  Factor viernes: +3 unidades (los viernes se vende más)\n"
        "  Factor martes: -2 unidades (los martes se vende menos)\n\n"
        "  Pronóstico para el viernes:\n"
        "  = Nivel + Tendencia + Factor_Viernes\n"
        "  = 10 + 0.5 + 3 = 13.5 unidades\n\n"
        "  Pronóstico para el martes:\n"
        "  = 10 + 0.5 + (-2) = 8.5 unidades"
    )


def _ejemplo_croston(y, dates, sba=False):
    # Buscar demanda no-cero
    nz = [(i, v) for i, v in enumerate(y) if v > 0]
    if len(nz) < 2:
        return "No hay suficientes ventas no-cero para este ejemplo."
    intervalos = [nz[i+1][0] - nz[i][0] for i in range(min(3, len(nz)-1))]
    tamaños = [v for _, v in nz[:min(4, len(nz))]]
    tam_prom = np.mean(tamaños)
    int_prom = np.mean(intervalos)
    pron = tam_prom / int_prom if int_prom > 0 else tam_prom
    lines = [
        f"Ventas no-cero encontradas: {', '.join(_fmt(v) for v in tamaños)}\n",
        f"Intervalos entre ventas (en días): {', '.join(str(i) for i in intervalos)}\n\n",
        f"Tamaño promedio de demanda: {_fmt(tam_prom)}\n",
        f"Intervalo promedio: {_fmt(int_prom)} días\n\n",
        f"Pronóstico Croston = {_fmt(tam_prom)} / {_fmt(int_prom)} = {_fmt(pron)} unidades/día\n",
    ]
    if sba:
        alpha = 0.2
        corr = pron * (1 - alpha / 2)
        lines.append(f"\nCorrección SBA: {_fmt(pron)} × (1 - {alpha}/2) = {_fmt(pron)} × {1-alpha/2} = {_fmt(corr)}")
    return "".join(lines)


def _ejemplo_tsb(y, dates):
    nz = sum(1 for v in y if v > 0)
    n = len(y)
    prob = nz / n if n > 0 else 0
    tam = np.mean([v for v in y if v > 0]) if nz > 0 else 0
    return (
        f"De {n} días, hubo venta en {nz} días.\n\n"
        f"Probabilidad de venta = {nz}/{n} = {prob:.2f} ({prob*100:.0f}%)\n"
        f"Tamaño promedio cuando hay venta = {_fmt(tam)}\n\n"
        f"Pronóstico TSB = {_fmt(tam)} × {prob:.2f} = {_fmt(tam * prob)} unidades/día"
    )


def _ejemplo_ridge(y, dates):
    if len(y) < 3:
        return "Necesitas al menos 3 días."
    return (
        "Ejemplo simplificado:\n\n"
        f"Con {len(y)} datos, el modelo ajusta una línea con:\n"
        f"  - Una pendiente (tendencia): ¿las ventas suben o bajan?\n"
        f"  - Un ajuste por día: lun/mar/mié/jue/vie/sáb/dom\n\n"
        f"Promedio actual: {_fmt(np.mean(y))} unidades\n"
        f"Si la tendencia es +0.3/día y mañana es viernes con bonus +2:\n"
        f"  Pronóstico = {_fmt(np.mean(y))} + 0.3 + 2.0 = {_fmt(np.mean(y)+2.3)}\n\n"
        "Ridge evita que los bonos por día sean exagerados\n"
        "cuando hay pocos datos (regularización)."
    )


def _ejemplo_ensemble(y, dates):
    return (
        "Supongamos que los 3 mejores modelos pronostican:\n\n"
        "  Media Móvil 3d: 8 unidades\n"
        "  SES: 9 unidades\n"
        "  Perfil día de semana: 7 unidades\n\n"
        "Ensamble = (8 + 9 + 7) / 3 = 8.0 unidades\n\n"
        "El software elige automáticamente los 3 modelos\n"
        "con menor error en el backtesting para cada producto."
    )
