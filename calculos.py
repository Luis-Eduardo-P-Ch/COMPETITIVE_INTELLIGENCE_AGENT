"""
calculos.py — Competitive Intelligence Agent
=============================================
Módulo central de cálculos: mercado, medios y agente con reglas.
Integra Competitive Analyzer + SOV Analyzer + Agente de reglas.
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# CONFIGURACIÓN FIJA DE COLUMNAS
# (basada en estructura real de Listerine)
# ─────────────────────────────────────────────

# Competitive Analyzer (Base_Listerine)
COMP_DATE_COL     = 'Date'
COMP_CLIENT       = 'LISTERINE'
COMP_COMPETITORS  = ['COLGPLAX', 'ORALB', 'SENSO']

COMP_PRICE_CLIENT = 'Precio_LISTERINE'
COMP_PRICE_COMP   = {'Colgate': 'Precio_COLGPLAX', 'Oral-B': 'Precio_ORALB', 'Sensodyne': 'Precio_SENSO'}

COMP_VALUE_CLIENT = 'SalesValue_LISTERINE'
COMP_VALUE_COMP   = {'Colgate': 'SalesValue_COLGPLAX', 'Oral-B': 'SalesValue_ORALB', 'Sensodyne': 'SalesValue_SENSO'}

COMP_UNITS_CLIENT = 'UNID_LISTERINE'
COMP_UNITS_COMP   = {'Colgate': 'UNID_COLGPLAX', 'Oral-B': 'UNID_ORALB', 'Sensodyne': 'UNID_SENSO'}

COMP_DIST_CLIENT  = 'DIST_LISTERINE'
COMP_DIST_COMP    = {'Colgate': 'DIST_COLGPLAX', 'Oral-B': 'Dist_ORALB', 'Sensodyne': 'Dist_SENSO'}

COMP_GT_CLIENT    = 'GT_LISTERINE'
COMP_GT_COMP      = {'Colgate': 'GT_COLGENJUAGUE'}

# SOV Analyzer (AR_Data_Listerine)
SOV_DATE_COL      = 'DATE'
SOV_MEDIA_COLS    = ['CADREON_DP','CADREON_OV','DOOH','ECOMMERCE','FARMACITY',
                     'FB_DP','FB_OV','INFLUENCERS','MERCADO_LIBRE','SEARCH',
                     'SEEDTAG','STREAMING','TIKTOK','TVA']
SOV_SPD_COLS      = {'Colgate': 'COLGATE_ALL_SPD', 'Oral-B': 'ORALB_ALL_SPD', 'Sensodyne': 'SENSODYNE_ALL_SPD'}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _num(v):
    try:
        return float(v)
    except:
        return 0.0

def _safe_div(a, b):
    return a / b if b != 0 else 0.0

def _pct_change(first, last):
    return round(_safe_div(last - first, first) * 100, 1) if first else 0.0

def _round2(v):
    return round(float(v), 2)

def _fmt_num(v):
    """Formatea número grande con sufijo K/M"""
    v = abs(float(v))
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

def cargar_competitive(filepath):
    """Carga y limpia el archivo del Competitive Analyzer."""
    df = pd.read_excel(filepath)
    df = df.dropna(how='all').reset_index(drop=True)
    df[COMP_DATE_COL] = pd.to_datetime(df[COMP_DATE_COL], errors='coerce')
    df = df.dropna(subset=[COMP_DATE_COL]).sort_values(COMP_DATE_COL).reset_index(drop=True)
    return df

def cargar_sov(filepath):
    """Carga y limpia el archivo del SOV Analyzer."""
    df = pd.read_excel(filepath)
    df = df.dropna(how='all').reset_index(drop=True)
    df[SOV_DATE_COL] = pd.to_datetime(df[SOV_DATE_COL], errors='coerce')
    df = df.dropna(subset=[SOV_DATE_COL]).sort_values(SOV_DATE_COL).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────
# CÁLCULOS: COMPETITIVE ANALYZER
# ─────────────────────────────────────────────

def calcular_market_share(df, col_cliente, cols_comp):
    """Calcula market share del cliente en una dimensión."""
    all_cols = [col_cliente] + list(cols_comp.values())
    # Filtrar columnas que existen
    all_cols = [c for c in all_cols if c in df.columns]
    totales = df[all_cols].sum(axis=1)
    shares = df[col_cliente].apply(_num) / totales.replace(0, np.nan) * 100
    return shares.fillna(0)

def calcular_indice_precio(df):
    """Índice de precio del cliente vs promedio competencia (100 = paridad)."""
    comp_cols = [c for c in COMP_PRICE_COMP.values() if c in df.columns]
    if not comp_cols:
        return None
    avg_comp = df[comp_cols].mean(axis=1).mean()
    avg_client = df[COMP_PRICE_CLIENT].mean() if COMP_PRICE_CLIENT in df.columns else None
    if avg_client and avg_comp:
        return round(avg_client / avg_comp * 100)
    return None

def calcular_share_of_search(df):
    """Share of Search del cliente vs competencia en Google Trends."""
    gt_cols = [COMP_GT_CLIENT] + [c for c in COMP_GT_COMP.values() if c in df.columns]
    gt_cols = [c for c in gt_cols if c in df.columns]
    if len(gt_cols) < 2:
        return None
    totales = df[gt_cols].sum(axis=1)
    shares = df[COMP_GT_CLIENT].apply(_num) / totales.replace(0, np.nan) * 100
    avg = round(shares.fillna(0).mean(), 1)
    current = round(shares.fillna(0).iloc[-1], 1)
    return {'promedio': avg, 'actual': current}

def metricas_competitive(df):
    """Calcula todas las métricas del Competitive Analyzer."""
    m = {}
    n = len(df)
    m['periodos'] = n
    m['fecha_inicio'] = df[COMP_DATE_COL].iloc[0].strftime('%b %Y')
    m['fecha_fin']    = df[COMP_DATE_COL].iloc[-1].strftime('%b %Y')

    # Market Share Valor
    if COMP_VALUE_CLIENT in df.columns:
        ms_val = calcular_market_share(df, COMP_VALUE_CLIENT, COMP_VALUE_COMP)
        m['ms_valor_promedio'] = _round2(ms_val.mean())
        m['ms_valor_actual']   = _round2(ms_val.iloc[-1])
        m['ms_valor_cambio']   = _round2(ms_val.iloc[-1] - ms_val.iloc[0])

    # Market Share Unidades
    if COMP_UNITS_CLIENT in df.columns:
        ms_uni = calcular_market_share(df, COMP_UNITS_CLIENT, COMP_UNITS_COMP)
        m['ms_unid_promedio'] = _round2(ms_uni.mean())
        m['ms_unid_actual']   = _round2(ms_uni.iloc[-1])
        m['ms_unid_cambio']   = _round2(ms_uni.iloc[-1] - ms_uni.iloc[0])

    # Distribución
    if COMP_DIST_CLIENT in df.columns:
        dist = df[COMP_DIST_CLIENT].apply(_num)
        m['dist_actual']  = _round2(dist.iloc[-1])
        m['dist_promedio']= _round2(dist.mean())
        m['dist_cambio']  = _round2(dist.iloc[-1] - dist.iloc[0])
        # Distribución competencia
        dist_comp = {}
        for nombre, col in COMP_DIST_COMP.items():
            if col in df.columns:
                dist_comp[nombre] = _round2(df[col].apply(_num).iloc[-1])
        m['dist_comp'] = dist_comp

    # Precios
    if COMP_PRICE_CLIENT in df.columns:
        precio = df[COMP_PRICE_CLIENT].apply(_num)
        m['precio_actual']   = _round2(precio.iloc[-1])
        m['precio_promedio'] = _round2(precio.mean())
        m['precio_cambio_pct'] = _pct_change(precio.iloc[0], precio.iloc[-1])
        m['precio_indice'] = calcular_indice_precio(df)

    # Google Trends / Share of Search
    sos = calcular_share_of_search(df)
    if sos:
        m['sos_promedio'] = sos['promedio']
        m['sos_actual']   = sos['actual']

    # Ventas valor cliente
    if COMP_VALUE_CLIENT in df.columns:
        ventas = df[COMP_VALUE_CLIENT].apply(_num)
        m['ventas_total']   = round(ventas.sum())
        m['ventas_promedio']= round(ventas.mean())
        m['ventas_cambio_pct'] = _pct_change(ventas.iloc[0], ventas.iloc[-1])

    # Unidades cliente
    if COMP_UNITS_CLIENT in df.columns:
        unid = df[COMP_UNITS_CLIENT].apply(_num)
        m['unid_total']    = round(unid.sum())
        m['unid_promedio'] = round(unid.mean())
        m['unid_cambio_pct'] = _pct_change(unid.iloc[0], unid.iloc[-1])

    return m


# ─────────────────────────────────────────────
# CÁLCULOS: SOV ANALYZER
# ─────────────────────────────────────────────

def metricas_sov(df):
    """Calcula todas las métricas del SOV Analyzer."""
    m = {}
    n = len(df)
    m['periodos'] = n
    m['fecha_inicio'] = df[SOV_DATE_COL].iloc[0].strftime('%b %Y')
    m['fecha_fin']    = df[SOV_DATE_COL].iloc[-1].strftime('%b %Y')

    # Columnas de medios que existen
    media_cols = [c for c in SOV_MEDIA_COLS if c in df.columns]
    spd_cols   = {k: v for k, v in SOV_SPD_COLS.items() if v in df.columns}

    # Inversión total cliente
    inv_cliente = df[media_cols].sum(axis=1)
    m['inv_total_cliente']   = round(inv_cliente.sum())
    m['inv_promedio_cliente']= round(inv_cliente.mean())

    # Inversión total competencia
    if spd_cols:
        inv_comp = df[list(spd_cols.values())].sum(axis=1)
        m['inv_total_comp'] = round(inv_comp.sum())

        # SOV por período
        total_mkt = inv_cliente + inv_comp
        sov_serie = (inv_cliente / total_mkt.replace(0, np.nan) * 100).fillna(0)
        m['sov_promedio'] = _round2(sov_serie.mean())
        m['sov_actual']   = _round2(sov_serie.iloc[-1])
        m['sov_cambio']   = _round2(sov_serie.iloc[-1] - sov_serie.iloc[0])
        m['sov_inicio']   = _round2(sov_serie.iloc[0])

        # Inversión por competidor
        inv_por_comp = {}
        for nombre, col in spd_cols.items():
            inv_por_comp[nombre] = round(df[col].apply(_num).sum())
        m['inv_por_competidor'] = inv_por_comp

    # Top medios por inversión
    totales_medio = {col: round(df[col].apply(_num).sum()) for col in media_cols}
    top_medios = sorted(totales_medio.items(), key=lambda x: x[1], reverse=True)
    m['top_medios']    = top_medios[:5]
    m['todos_medios']  = top_medios

    # Mix de medios (% de cada medio sobre total cliente)
    inv_total = m['inv_total_cliente']
    mix = [(col, round(val / inv_total * 100, 1)) for col, val in top_medios if inv_total > 0]
    m['mix_medios'] = mix

    # HHI (concentración del mix)
    hhi = sum((pct ** 2) for _, pct in mix)
    m['hhi'] = round(hhi)
    m['hhi_nivel'] = 'Alta' if hhi > 2500 else ('Media' if hhi > 1500 else 'Baja')

    # Medio dominante
    if top_medios:
        m['medio_dominante']     = top_medios[0][0]
        m['medio_dominante_pct'] = mix[0][1] if mix else 0

    return m


# ─────────────────────────────────────────────
# ANÁLISIS DE BRECHAS SOV vs SOM
# ─────────────────────────────────────────────

def analizar_brechas(mc, ms):
    """
    Cruza métricas de mercado y medios para detectar brechas SOV-SOM.
    mc = metricas_competitive, ms = metricas_sov
    """
    b = {}
    sov = ms.get('sov_promedio')
    som = mc.get('ms_valor_promedio')

    if sov is not None and som is not None:
        brecha = round(sov - som, 1)
        b['brecha_sov_som'] = brecha
        if brecha > 15:
            b['diagnostico_brecha'] = 'inversion_excesiva'
            b['mensaje_brecha'] = (
                f"El cliente invierte {sov}% del total del mercado en medios (SOV) "
                f"pero captura solo {som}% del valor de mercado (MS). "
                f"Brecha de {brecha} pp: posible problema de eficiencia de medios o conversión en punto de venta."
            )
        elif brecha < -10:
            b['diagnostico_brecha'] = 'eficiencia_positiva'
            b['mensaje_brecha'] = (
                f"El cliente captura {som}% del mercado con solo {sov}% de SOV. "
                f"Eficiencia positiva: la marca convierte mejor que lo que invierte en medios."
            )
        else:
            b['diagnostico_brecha'] = 'alineado'
            b['mensaje_brecha'] = (
                f"SOV ({sov}%) y Market Share ({som}%) están razonablemente alineados "
                f"(brecha de {abs(brecha)} pp). La inversión en medios es proporcional a la participación de mercado."
            )

    return b


# ─────────────────────────────────────────────
# AGENTE CON REGLAS
# ─────────────────────────────────────────────

def agente_responder(pregunta, mc, ms):
    """
    Agente basado en reglas que responde preguntas usando los datos calculados.
    mc = metricas_competitive (puede ser None)
    ms = metricas_sov (puede ser None)
    Retorna dict con 'respuesta' (str) y 'alertas' (list).
    """
    p = pregunta.lower().strip()
    alertas = _detectar_alertas(mc, ms)

    # ── DIAGNÓSTICO COMPLETO ──────────────────
    if any(w in p for w in ['diagnóstico', 'diagnostico', 'completo', 'resumen', 'todo', 'situación', 'situacion']):
        return {'respuesta': _respuesta_diagnostico(mc, ms), 'alertas': alertas}

    # ── MARKET SHARE / POSICIÓN DE MERCADO ───
    if any(w in p for w in ['market share', 'participación', 'participacion', 'cuota', 'mercado']):
        return {'respuesta': _respuesta_mercado(mc), 'alertas': alertas}

    # ── PRECIOS ───────────────────────────────
    if any(w in p for w in ['precio', 'price', 'costo', 'indice']):
        return {'respuesta': _respuesta_precios(mc), 'alertas': alertas}

    # ── DISTRIBUCIÓN ─────────────────────────
    if any(w in p for w in ['distribución', 'distribucion', 'dist', 'cobertura', 'punto de venta']):
        return {'respuesta': _respuesta_distribucion(mc), 'alertas': alertas}

    # ── SOV / MEDIOS / INVERSIÓN ──────────────
    if any(w in p for w in ['sov', 'share of voice', 'medios', 'inversión', 'inversion', 'pauta', 'canal']):
        return {'respuesta': _respuesta_sov(ms), 'alertas': alertas}

    # ── BRECHAS ───────────────────────────────
    if any(w in p for w in ['brecha', 'gap', 'diferencia', 'alineado', 'eficiencia']):
        brechas = analizar_brechas(mc or {}, ms or {})
        return {'respuesta': _respuesta_brechas(brechas, mc, ms), 'alertas': alertas}

    # ── GOOGLE TRENDS / SHARE OF SEARCH ──────
    if any(w in p for w in ['google', 'trend', 'search', 'búsqueda', 'busqueda']):
        return {'respuesta': _respuesta_search(mc), 'alertas': alertas}

    # ── ALERTAS ───────────────────────────────
    if any(w in p for w in ['alerta', 'riesgo', 'problema', 'atención', 'atencion', 'warning']):
        if alertas:
            resp = "**Alertas detectadas:**\n\n" + "\n".join(f"• {a['texto']}" for a in alertas)
        else:
            resp = "✅ No se detectaron alertas críticas en el período analizado. Los indicadores se encuentran dentro de rangos normales."
        return {'respuesta': resp, 'alertas': alertas}

    # ── NARRATIVA EJECUTIVA ───────────────────
    if any(w in p for w in ['narrativa', 'deck', 'ejecutivo', 'presentación', 'presentacion', 'párrafo', 'parrafo', 'cliente']):
        return {'respuesta': _respuesta_narrativa(mc, ms), 'alertas': alertas}

    # ── HHI / CONCENTRACIÓN ───────────────────
    if any(w in p for w in ['hhi', 'concentración', 'concentracion', 'diversificación', 'diversificacion', 'mix']):
        return {'respuesta': _respuesta_hhi(ms), 'alertas': alertas}

    # ── COMPETENCIA ───────────────────────────
    if any(w in p for w in ['competencia', 'competidor', 'rival', 'colgate', 'oral', 'sensodyne']):
        return {'respuesta': _respuesta_competencia(mc, ms), 'alertas': alertas}

    # ── FALLBACK ──────────────────────────────
    return {
        'respuesta': (
            "Puedo responderte sobre:\n\n"
            "• **Market share** y posición de mercado\n"
            "• **Precios** e índice vs competencia\n"
            "• **Distribución** en punto de venta\n"
            "• **Share of Voice** e inversión en medios\n"
            "• **Brechas SOV-SOM**\n"
            "• **Google Trends / Share of Search**\n"
            "• **Alertas** y riesgos detectados\n"
            "• **Narrativa ejecutiva** para deck\n"
            "• **Diagnóstico completo**\n\n"
            "¿Sobre cuál de estos temas querés profundizar?"
        ),
        'alertas': alertas
    }


# ─────────────────────────────────────────────
# RESPUESTAS INDIVIDUALES
# ─────────────────────────────────────────────

def _respuesta_diagnostico(mc, ms):
    partes = []

    if mc:
        partes.append("**📊 Posición de Mercado**")
        if 'ms_valor_actual' in mc:
            tendencia = "▲" if mc['ms_valor_cambio'] >= 0 else "▼"
            partes.append(f"• Market Share en valor: **{mc['ms_valor_actual']}%** ({tendencia} {abs(mc['ms_valor_cambio'])} pp vs inicio)")
        if 'ms_unid_actual' in mc:
            partes.append(f"• Market Share en unidades: **{mc['ms_unid_actual']}%**")
        if 'precio_indice' in mc and mc['precio_indice']:
            partes.append(f"• Índice de precio vs competencia: **{mc['precio_indice']}** ({'premium' if mc['precio_indice']>100 else 'bajo la competencia'})")
        if 'dist_actual' in mc:
            partes.append(f"• Distribución actual: **{mc['dist_actual']:.0f}** puntos de venta")

    if ms:
        partes.append("\n**📡 Share of Voice y Medios**")
        if 'sov_promedio' in ms:
            tendencia = "▲" if ms['sov_cambio'] >= 0 else "▼"
            partes.append(f"• SOV promedio: **{ms['sov_promedio']}%** ({tendencia} {abs(ms['sov_cambio'])} pp en el período)")
        if 'medio_dominante' in ms:
            partes.append(f"• Canal dominante: **{ms['medio_dominante']}** ({ms['medio_dominante_pct']}% del total)")
        if 'hhi' in ms:
            partes.append(f"• Concentración del mix (HHI): **{ms['hhi']}** — nivel {ms['hhi_nivel']}")

    if mc and ms:
        partes.append("\n**🔍 Brecha SOV-SOM**")
        brechas = analizar_brechas(mc, ms)
        if 'mensaje_brecha' in brechas:
            partes.append(f"• {brechas['mensaje_brecha']}")

    return "\n".join(partes) if partes else "Cargá los archivos para ver el diagnóstico completo."


def _respuesta_mercado(mc):
    if not mc:
        return "Cargá el archivo del Competitive Analyzer para ver los datos de mercado."
    partes = ["**📊 Posición de Mercado — Listerine**\n"]

    if 'ms_valor_actual' in mc:
        tend = "▲" if mc['ms_valor_cambio'] >= 0 else "▼"
        partes.append(f"**Market Share en Valor:**\n• Actual: {mc['ms_valor_actual']}% | Promedio: {mc['ms_valor_promedio']}% | Cambio: {tend} {abs(mc['ms_valor_cambio'])} pp")
        if mc['ms_valor_cambio'] < -1:
            partes.append(f"  ⚠️ Tendencia negativa sostenida — requiere atención.")
        elif mc['ms_valor_cambio'] > 1:
            partes.append(f"  ✅ Ganando participación de mercado en el período.")

    if 'ms_unid_actual' in mc:
        tend = "▲" if mc['ms_unid_cambio'] >= 0 else "▼"
        partes.append(f"\n**Market Share en Unidades:**\n• Actual: {mc['ms_unid_actual']}% | Promedio: {mc['ms_unid_promedio']}% | Cambio: {tend} {abs(mc['ms_unid_cambio'])} pp")

    if 'dist_actual' in mc:
        partes.append(f"\n**Distribución:**\n• Actual: {mc['dist_actual']:.0f} puntos | Promedio: {mc['dist_promedio']:.0f} puntos | Cambio: {mc['dist_cambio']:+.0f} puntos")
        if mc.get('dist_comp'):
            comp_str = " | ".join(f"{k}: {v:.0f}" for k, v in mc['dist_comp'].items())
            partes.append(f"• Competencia: {comp_str}")

    if 'unid_cambio_pct' in mc:
        partes.append(f"\n**Volumen de Ventas:**\n• Tendencia de unidades: {mc['unid_cambio_pct']:+.1f}% en el período")

    return "\n".join(partes)


def _respuesta_precios(mc):
    if not mc:
        return "Cargá el archivo del Competitive Analyzer para ver los datos de precios."
    partes = ["**💰 Análisis de Precios — Listerine**\n"]

    if 'precio_actual' in mc:
        partes.append(f"**Precio del cliente:**\n• Actual: ${mc['precio_actual']:,.0f} | Promedio período: ${mc['precio_promedio']:,.0f} | Variación: {mc['precio_cambio_pct']:+.1f}%")

    if 'precio_indice' in mc and mc['precio_indice']:
        idx = mc['precio_indice']
        if idx > 120:
            interp = f"El cliente está significativamente por encima del promedio competitivo ({idx-100}% más caro). Puede estar afectando volumen."
        elif idx > 105:
            interp = f"Leve posicionamiento premium ({idx-100}% sobre la competencia). Rango manejable."
        elif idx < 95:
            interp = f"El cliente está por debajo del promedio de precios competitivos. Margen para ajuste."
        else:
            interp = "Precio en paridad con la competencia."
        partes.append(f"\n**Índice de precio vs competencia:** {idx}\n• {interp}")

    return "\n".join(partes)


def _respuesta_distribucion(mc):
    if not mc or 'dist_actual' not in mc:
        return "Cargá el archivo del Competitive Analyzer para ver los datos de distribución."
    partes = ["**🏪 Análisis de Distribución — Listerine**\n"]
    partes.append(f"• Distribución actual: **{mc['dist_actual']:.0f}** puntos de venta")
    partes.append(f"• Promedio período: {mc['dist_promedio']:.0f} puntos")
    partes.append(f"• Cambio absoluto: {mc['dist_cambio']:+.0f} puntos")

    if mc.get('dist_comp'):
        partes.append("\n**Distribución competencia (último período):**")
        for comp, val in mc['dist_comp'].items():
            partes.append(f"• {comp}: {val:.0f} puntos")

    return "\n".join(partes)


def _respuesta_sov(ms):
    if not ms:
        return "Cargá el archivo del SOV Analyzer para ver los datos de medios."
    partes = ["**📡 Share of Voice e Inversión en Medios — Listerine**\n"]

    if 'sov_promedio' in ms:
        tend = "▲" if ms['sov_cambio'] >= 0 else "▼"
        partes.append(f"**Share of Voice:**\n• SOV promedio: {ms['sov_promedio']}% | Actual: {ms['sov_actual']}% | Tendencia: {tend} {abs(ms['sov_cambio'])} pp")

    partes.append(f"\n**Inversión total del cliente:** {_fmt_num(ms['inv_total_cliente'])}")
    if 'inv_total_comp' in ms:
        ratio = _safe_div(ms['inv_total_cliente'], ms['inv_total_comp'])
        partes.append(f"• Inversión competencia: {_fmt_num(ms['inv_total_comp'])} | Ratio cliente/comp: {ratio:.2f}x")

    if ms.get('top_medios'):
        partes.append("\n**Top 5 canales por inversión:**")
        for canal, monto in ms['top_medios']:
            pct = next((p for c, p in ms['mix_medios'] if c == canal), 0)
            partes.append(f"• {canal}: {_fmt_num(monto)} ({pct}%)")

    if 'inv_por_competidor' in ms:
        partes.append("\n**Inversión competencia por marca:**")
        for comp, monto in ms['inv_por_competidor'].items():
            partes.append(f"• {comp}: {_fmt_num(monto)}")

    return "\n".join(partes)


def _respuesta_brechas(brechas, mc, ms):
    if not brechas or 'mensaje_brecha' not in brechas:
        if not mc and not ms:
            return "Cargá ambos archivos para analizar brechas SOV-SOM."
        if not mc:
            return "Cargá el archivo del Competitive Analyzer para completar el análisis de brechas."
        if not ms:
            return "Cargá el archivo del SOV Analyzer para completar el análisis de brechas."

    partes = ["**🔍 Análisis de Brechas SOV-SOM**\n"]
    sov = ms.get('sov_promedio', 'N/D')
    som = mc.get('ms_valor_promedio', 'N/D')
    partes.append(f"• SOV del cliente: **{sov}%**")
    partes.append(f"• Market Share en valor: **{som}%**")
    partes.append(f"\n{brechas['mensaje_brecha']}")

    diag = brechas.get('diagnostico_brecha')
    if diag == 'inversion_excesiva':
        partes.append("\n**Recomendación:** Revisar eficiencia de canales y conversión en punto de venta antes de mantener el nivel de inversión.")
    elif diag == 'eficiencia_positiva':
        partes.append("\n**Recomendación:** La marca tiene una base sólida. Evaluar incremento selectivo de inversión en canales de mayor retorno.")

    return "\n".join(partes)


def _respuesta_search(mc):
    if not mc or 'sos_actual' not in mc:
        return "No se encontraron datos de Google Trends en el archivo cargado."
    partes = ["**🔎 Share of Search (Google Trends) — Listerine**\n"]
    partes.append(f"• Share of Search actual: **{mc['sos_actual']}%**")
    partes.append(f"• Promedio período: {mc['sos_promedio']}%")
    if mc['sos_actual'] < 40:
        partes.append("• ⚠️ Bajo interés de búsqueda orgánica vs competencia. Puede indicar menor awareness o presencia digital.")
    elif mc['sos_actual'] > 60:
        partes.append("• ✅ Alta presencia en búsquedas orgánicas. Señal positiva de salud de marca.")
    return "\n".join(partes)


def _respuesta_hhi(ms):
    if not ms or 'hhi' not in ms:
        return "Cargá el archivo SOV Analyzer para ver el análisis de concentración del mix."
    partes = ["**📐 Concentración del Mix de Medios (HHI)**\n"]
    partes.append(f"• HHI: **{ms['hhi']}** — Concentración {ms['hhi_nivel']}")
    if ms['hhi'] > 2500:
        partes.append(f"• ⚠️ El mix está muy concentrado en pocos canales. Canal dominante: **{ms.get('medio_dominante','N/D')}** ({ms.get('medio_dominante_pct',0)}%)")
        partes.append("• Riesgo: alta dependencia de un canal único. Se recomienda diversificar.")
    elif ms['hhi'] > 1500:
        partes.append("• Mix con concentración media. Hay diversificación pero con algunos canales dominantes.")
    else:
        partes.append("• ✅ Mix bien diversificado entre canales.")

    if ms.get('mix_medios'):
        partes.append("\n**Distribución del mix:**")
        for canal, pct in ms['mix_medios']:
            partes.append(f"• {canal}: {pct}%")

    return "\n".join(partes)


def _respuesta_competencia(mc, ms):
    partes = ["**🏢 Análisis de Competencia**\n"]

    if mc and mc.get('dist_comp'):
        partes.append("**Distribución por marca (último período):**")
        if 'dist_actual' in mc:
            partes.append(f"• Listerine: {mc['dist_actual']:.0f} puntos")
        for comp, val in mc['dist_comp'].items():
            partes.append(f"• {comp}: {val:.0f} puntos")

    if ms and ms.get('inv_por_competidor'):
        partes.append("\n**Inversión en medios (total período):**")
        if 'inv_total_cliente' in ms:
            partes.append(f"• Listerine: {_fmt_num(ms['inv_total_cliente'])}")
        for comp, monto in ms['inv_por_competidor'].items():
            partes.append(f"• {comp}: {_fmt_num(monto)}")

    if not mc and not ms:
        return "Cargá los archivos para ver el análisis de competencia."

    return "\n".join(partes)


def _respuesta_narrativa(mc, ms):
    partes = []

    sov = ms.get('sov_promedio', 'N/D') if ms else 'N/D'
    som = mc.get('ms_valor_actual', 'N/D') if mc else 'N/D'
    som_cambio = mc.get('ms_valor_cambio', 0) if mc else 0
    tend = "recuperando posiciones" if som_cambio > 0 else "bajo presión"

    if mc and ms:
        brechas = analizar_brechas(mc, ms)
        brecha_msg = brechas.get('mensaje_brecha', '')
        narrativa = (
            f"Listerine cerró el período con un market share en valor de **{som}%**, {tend} frente a sus competidores directos. "
            f"En términos de inversión en medios, la marca sostuvo un Share of Voice promedio de **{sov}%**, "
            f"con foco en {ms.get('medio_dominante','los canales digitales')} como canal principal. "
            f"{brecha_msg} "
            f"De cara a los próximos períodos, se recomienda una revisión del mix de medios para optimizar la eficiencia de la inversión y consolidar la participación de mercado."
        )
    elif mc:
        narrativa = (
            f"Listerine cerró el período con un market share en valor de **{som}%**, {tend} frente a sus competidores. "
            f"La distribución alcanzó {mc.get('dist_actual','N/D'):.0f} puntos de venta con un precio "
            f"{'premium' if mc.get('precio_indice',100)>100 else 'competitivo'} vs la categoría."
        )
    elif ms:
        narrativa = (
            f"En términos de inversión en medios, Listerine mantuvo un Share of Voice promedio de **{sov}%** durante el período, "
            f"con {ms.get('medio_dominante','los canales digitales')} como canal principal ({ms.get('medio_dominante_pct',0)}% del mix)."
        )
    else:
        return "Cargá los archivos para generar la narrativa ejecutiva."

    return f"**📝 Narrativa ejecutiva (lista para deck):**\n\n{narrativa}"


# ─────────────────────────────────────────────
# DETECCIÓN DE ALERTAS
# ─────────────────────────────────────────────

def _detectar_alertas(mc, ms):
    alertas = []

    if mc:
        if mc.get('ms_valor_cambio', 0) < -1.5:
            alertas.append({'nivel': 'danger', 'texto': f"Caída de market share en valor: {mc['ms_valor_cambio']} pp en el período."})
        if mc.get('ms_unid_cambio', 0) < -1.5:
            alertas.append({'nivel': 'warning', 'texto': f"Caída de market share en unidades: {mc['ms_unid_cambio']} pp."})
        if mc.get('precio_indice', 100) > 125:
            alertas.append({'nivel': 'warning', 'texto': f"Precio {mc['precio_indice']-100}% por encima del promedio competitivo. Riesgo de pérdida de volumen."})
        if mc.get('dist_cambio', 0) < -30:
            alertas.append({'nivel': 'warning', 'texto': f"Caída de distribución: {mc['dist_cambio']:+.0f} puntos en el período."})

    if ms:
        if ms.get('hhi', 0) > 2500:
            alertas.append({'nivel': 'warning', 'texto': f"Alta concentración del mix de medios (HHI {ms['hhi']}). Dependencia excesiva de {ms.get('medio_dominante','un canal')}."})
        if ms.get('sov_cambio', 0) < -5:
            alertas.append({'nivel': 'warning', 'texto': f"Pérdida de SOV: {ms['sov_cambio']} pp en el período."})

    if mc and ms:
        brechas = analizar_brechas(mc, ms)
        if brechas.get('diagnostico_brecha') == 'inversion_excesiva':
            brecha = brechas['brecha_sov_som']
            alertas.append({'nivel': 'info', 'texto': f"Brecha SOV-SOM de {brecha} pp: inversión en medios desproporcionada vs participación de mercado."})

    return alertas
