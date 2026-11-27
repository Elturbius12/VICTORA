"""Bibliografía del artículo en formato APA 7.

Cada referencia es un dict con: autor, año, titulo, revista (o editorial en libros),
volumen, paginas, doi y verificar. Los DOI se comprobaron contra la API de doi.org; si un
DOI no pudo confirmarse se deja vacío y ``verificar`` queda en True.
"""
from __future__ import annotations

_CAMPOS = ("autor", "año", "titulo", "revista", "volumen", "paginas", "doi", "verificar")

_REFS: list[tuple] = [
    ("Arrow, K. J., Harris, T., & Marschak, J.", 1951, "Optimal inventory policy", "Econometrica", "19(3)", "250–272", "10.2307/1906813"),
    ("Bakker, M., Riezebos, J., & Teunter, R. H.", 2012, "Review of inventory systems with deterioration since 2001", "European Journal of Operational Research", "221(2)", "275–284", "10.1016/j.ejor.2012.03.004"),
    ("Croston, J. D.", 1972, "Forecasting and stock control for intermittent demands", "Operational Research Quarterly", "23(3)", "289–303", "10.1057/jors.1972.50"),
    ("Efron, B., & Tibshirani, R. J.", 1993, "An introduction to the bootstrap", "Chapman & Hall/CRC", "", "", "10.1201/9780429246593"),
    ("Food and Agriculture Organization of the United Nations", 2019, "The state of food and agriculture 2019: Moving forward on food loss and waste reduction", "FAO", "", "", ""),
    ("Friedman, M.", 1937, "The use of ranks to avoid the assumption of normality implicit in the analysis of variance", "Journal of the American Statistical Association", "32(200)", "675–701", "10.1080/01621459.1937.10503522"),
    ("Gardner, E. S., Jr.", 2006, "Exponential smoothing: The state of the art—Part II", "International Journal of Forecasting", "22(4)", "637–666", "10.1016/j.ijforecast.2006.03.005"),
    ("Goyal, S. K., & Giri, B. C.", 2001, "Recent trends in modeling of deteriorating inventory", "European Journal of Operational Research", "134(1)", "1–16", "10.1016/S0377-2217(00)00248-4"),
    ("Gustavsson, J., Cederberg, C., Sonesson, U., van Otterdijk, R., & Meybeck, A.", 2011, "Global food losses and food waste: Extent, causes and prevention", "FAO", "", "", ""),
    ("Holm, S.", 1979, "A simple sequentially rejective multiple test procedure", "Scandinavian Journal of Statistics", "6(2)", "65–70", ""),
    ("Holt, C. C.", 2004, "Forecasting seasonals and trends by exponentially weighted moving averages", "International Journal of Forecasting", "20(1)", "5–10", "10.1016/j.ijforecast.2003.09.015"),
    ("Hyndman, R. J., & Athanasopoulos, G.", 2021, "Forecasting: Principles and practice (3rd ed.)", "OTexts", "", "", ""),
    ("Hyndman, R. J., & Koehler, A. B.", 2006, "Another look at measures of forecast accuracy", "International Journal of Forecasting", "22(4)", "679–688", "10.1016/j.ijforecast.2006.03.001"),
    ("Kerby, D. S.", 2014, "The simple difference formula: An approach to teaching nonparametric correlation", "Comprehensive Psychology", "3", "Artículo 1", "10.2466/11.IT.3.1"),
    ("Khouja, M.", 1999, "The single-period (news-vendor) problem: Literature review and suggestions for future research", "Omega", "27(5)", "537–553", "10.1016/S0305-0483(99)00017-1"),
    ("Kruskal, W. H., & Wallis, W. A.", 1952, "Use of ranks in one-criterion variance analysis", "Journal of the American Statistical Association", "47(260)", "583–621", "10.1080/01621459.1952.10483441"),
    ("Makridakis, S., Spiliotis, E., & Assimakopoulos, V.", 2020, "The M4 Competition: 100,000 time series and 61 forecasting methods", "International Journal of Forecasting", "36(1)", "54–74", "10.1016/j.ijforecast.2019.04.014"),
    ("Makridakis, S., Spiliotis, E., & Assimakopoulos, V.", 2022, "M5 accuracy competition: Results, findings, and conclusions", "International Journal of Forecasting", "38(4)", "1346–1364", "10.1016/j.ijforecast.2021.11.013"),
    ("Nahmias, S.", 1982, "Perishable inventory theory: A review", "Operations Research", "30(4)", "680–708", "10.1287/opre.30.4.680"),
    ("Petropoulos, F., & Kourentzes, N.", 2015, "Forecast combinations for intermittent demand", "Journal of the Operational Research Society", "66(6)", "914–924", "10.1057/jors.2014.62"),
    ("Petropoulos, F., Apiletti, D., Assimakopoulos, V., Babai, M. Z., Barrow, D. K., Ben Taieb, S., et al.", 2022, "Forecasting: Theory and practice", "International Journal of Forecasting", "38(3)", "705–871", "10.1016/j.ijforecast.2021.11.001"),
    ("Qin, Y., Wang, R., Vakharia, A. J., Chen, Y., & Seref, M. M. H.", 2011, "The newsvendor problem: Review and directions for future research", "European Journal of Operational Research", "213(2)", "361–374", "10.1016/j.ejor.2010.11.024"),
    ("Silver, E. A., Pyke, D. F., & Thomas, D. J.", 2017, "Inventory and production management in supply chains (4th ed.)", "CRC Press", "", "", "10.1201/9781315374406"),
    ("Spearman, C.", 1904, "The proof and measurement of association between two things", "The American Journal of Psychology", "15(1)", "72–101", "10.2307/1412159"),
    ("Syntetos, A. A., & Boylan, J. E.", 2005, "The accuracy of intermittent demand estimates", "International Journal of Forecasting", "21(2)", "303–314", "10.1016/j.ijforecast.2004.10.001"),
    ("Syntetos, A. A., Boylan, J. E., & Croston, J. D.", 2005, "On the categorization of demand patterns", "Journal of the Operational Research Society", "56(5)", "495–503", "10.1057/palgrave.jors.2601841"),
    ("Tashman, L. J.", 2000, "Out-of-sample tests of forecasting accuracy: An analysis and review", "International Journal of Forecasting", "16(4)", "437–450", "10.1016/S0169-2070(00)00065-0"),
    ("Teunter, R. H., Syntetos, A. A., & Babai, M. Z.", 2011, "Intermittent demand: Linking forecasting to inventory obsolescence", "European Journal of Operational Research", "214(3)", "606–615", "10.1016/j.ejor.2011.05.018"),
    ("Wilcoxon, F.", 1945, "Individual comparisons by ranking methods", "Biometrics Bulletin", "1(6)", "80–83", "10.2307/3001968"),
    ("Winters, P. R.", 1960, "Forecasting sales by exponentially weighted moving averages", "Management Science", "6(3)", "324–342", "10.1287/mnsc.6.3.324"),
]

# DOI que no pudieron confirmarse en doi.org (se vacían y se marcan para verificar)
_NO_CONFIRMADOS: set[str] = set()


def bibliografia() -> list[dict]:
    """Lista de referencias (dicts) ordenada alfabéticamente por autor y año."""
    out = []
    for autor, anio, tit, rev, vol, pag, doi in _REFS:
        verificar = doi in _NO_CONFIRMADOS
        out.append(dict(zip(_CAMPOS, (autor, anio, tit, rev, vol, pag, "" if verificar else doi, verificar))))
    return sorted(out, key=lambda r: (r["autor"], r["año"]))


def formato_apa(ref: dict) -> str:
    """Devuelve la referencia en formato APA 7 (texto plano; las cursivas no se representan)."""
    base = f"{ref['autor']} ({ref['año']}). {ref['titulo']}."
    if ref["volumen"] or ref["paginas"]:
        vol = f", {ref['volumen']}" if ref["volumen"] else ""
        pag = f", {ref['paginas']}" if ref["paginas"] else ""
        base += f" {ref['revista']}{vol}{pag}."
    else:
        base += f" {ref['revista']}."
    if ref["doi"]:
        base += f" https://doi.org/{ref['doi']}"
    if ref.get("verificar"):
        base += " [VERIFICAR]"
    return base
