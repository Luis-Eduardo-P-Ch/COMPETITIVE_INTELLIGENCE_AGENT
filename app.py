"""
app.py — Competitive Intelligence Agent
========================================
Interfaz Streamlit: dashboard de métricas + agente conversacional con reglas.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from calculos import (
    cargar_competitive, cargar_sov,
    metricas_competitive, metricas_sov,
    analizar_brechas, agente_responder,
    _detectar_alertas, _fmt_num
)

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Competitive Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
.metric-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
}
.alert-danger  { background:#fff5f5; border-left:4px solid #e53e3e; padding:10px 14px; border-radius:4px; margin:6px 0; }
.alert-warning { background:#fffbea; border-left:4px solid #d69e2e; padding:10px 14px; border-radius:4px; margin:6px 0; }
.alert-info    { background:#ebf8ff; border-left:4px solid #3182ce; padding:10px 14px; border-radius:4px; margin:6px 0; }
.alert-success { background:#f0fff4; border-left:4px solid #38a169; padding:10px 14px; border-radius:4px; margin:6px 0; }
.chat-user  { background:#EBF8FF; border-radius:12px 12px 4px 12px; padding:10px 14px; margin:6px 0 6px 40px; font-size:14px; }
.chat-agent { background:#F7FAFC; border:1px solid #E2E8F0; border-radius:12px 12px 12px 4px; padding:10px 14px; margin:6px 40px 6px 0; font-size:14px; }
.agent-label { font-size:11px; color:#718096; margin-bottom:2px; font-weight:500; }
div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR — CARGA DE ARCHIVOS
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 Competitive Intelligence Agent")
    st.markdown("---")
    st.markdown("### Cargar datos")

    file_comp = st.file_uploader("**Competitive Analyzer**", type=['xlsx', 'xls'], key="comp")
    file_sov  = st.file_uploader("**SOV Analyzer**", type=['xlsx', 'xls'], key="sov")

    st.markdown("---")
    st.markdown("### Preguntas rápidas")

    preguntas_rapidas = [
        "Diagnóstico completo",
        "Análisis de mercado",
        "Análisis de SOV y medios",
        "¿Hay brechas SOV-SOM?",
        "Narrativa ejecutiva para deck",
        "¿Qué alertas hay?",
        "Análisis de precios",
        "Análisis de distribución",
        "Concentración del mix (HHI)",
        "Análisis de competencia",
    ]

    for preg in preguntas_rapidas:
        if st.button(preg, key=f"btn_{preg}", use_container_width=True):
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            st.session_state.chat_history.append({'rol': 'usuario', 'texto': preg})
            st.session_state.pregunta_pendiente = preg

    st.markdown("---")
    st.caption("v1.0 · Hackathon LATAM Agentic Minds")


# ─────────────────────────────────────────────
# CARGA Y CÁLCULO DE MÉTRICAS
# ─────────────────────────────────────────────

mc, ms = None, None

if file_comp:
    try:
        df_comp = cargar_competitive(file_comp)
        mc = metricas_competitive(df_comp)
    except Exception as e:
        st.error(f"Error al cargar Competitive Analyzer: {e}")

if file_sov:
    try:
        df_sov = cargar_sov(file_sov)
        ms = metricas_sov(df_sov)
    except Exception as e:
        st.error(f"Error al cargar SOV Analyzer: {e}")


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("# 🧠 Competitive Intelligence Agent")
    if mc and ms:
        st.caption(f"Listerine · {mc['fecha_inicio']} — {mc['fecha_fin']} · {mc['periodos']} períodos")
    elif mc:
        st.caption(f"Listerine · {mc['fecha_inicio']} — {mc['fecha_fin']} · Solo datos de mercado")
    elif ms:
        st.caption(f"Listerine · {ms['fecha_inicio']} — {ms['fecha_fin']} · Solo datos de medios")
    else:
        st.caption("Cargá los archivos Excel para comenzar el análisis")

with col_h2:
    if mc or ms:
        estado = "✅ Agente activo" if (mc and ms) else "⚠️ Datos parciales"
        st.info(estado)

st.markdown("---")


# ─────────────────────────────────────────────
# ALERTAS AUTOMÁTICAS
# ─────────────────────────────────────────────

if mc or ms:
    alertas = _detectar_alertas(mc, ms)
    if alertas:
        with st.expander(f"⚠️ **{len(alertas)} alerta(s) detectada(s)**", expanded=True):
            for a in alertas:
                nivel = a['nivel']
                icono = {'danger': '🔴', 'warning': '🟡', 'info': '🔵', 'success': '🟢'}.get(nivel, '●')
                st.markdown(f'<div class="alert-{nivel}">{icono} {a["texto"]}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DASHBOARD DE MÉTRICAS
# ─────────────────────────────────────────────

if mc or ms:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Mercado", "📡 Medios & SOV", "🔍 Brechas", "💬 Agente"])
else:
    tab4, = st.tabs(["💬 Agente"])
    tab1 = tab2 = tab3 = None


# ──── TAB 1: MERCADO ─────────────────────────
if tab1 and mc:
    with tab1:
        # KPIs fila 1
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            delta_ms = f"{mc['ms_valor_cambio']:+.1f} pp" if 'ms_valor_cambio' in mc else None
            st.metric("MS Valor (actual)", f"{mc.get('ms_valor_actual','N/D')}%", delta=delta_ms)
        with c2:
            delta_u = f"{mc['ms_unid_cambio']:+.1f} pp" if 'ms_unid_cambio' in mc else None
            st.metric("MS Unidades (actual)", f"{mc.get('ms_unid_actual','N/D')}%", delta=delta_u)
        with c3:
            idx = mc.get('precio_indice')
            st.metric("Índice Precio vs Comp.", f"{idx}" if idx else "N/D", help="100 = paridad con competencia")
        with c4:
            st.metric("Distribución (actual)", f"{mc.get('dist_actual', 0):.0f} pts", delta=f"{mc.get('dist_cambio',0):+.0f} pts")

        st.markdown("---")

        col_a, col_b = st.columns(2)

        # Gráfico MS Valor en el tiempo
        with col_a:
            if 'SalesValue_LISTERINE' in df_comp.columns:
                valor_cols = ['SalesValue_LISTERINE', 'SalesValue_COLGPLAX', 'SalesValue_ORALB', 'SalesValue_SENSO']
                valor_cols = [c for c in valor_cols if c in df_comp.columns]
                totales = df_comp[valor_cols].sum(axis=1)
                ms_serie = (df_comp['SalesValue_LISTERINE'] / totales.replace(0, pd.NA) * 100).fillna(0)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_comp['Date'], y=ms_serie.round(1),
                    mode='lines+markers', name='MS Valor',
                    line=dict(color='#3182CE', width=2.5),
                    marker=dict(size=5)
                ))
                fig.update_layout(
                    title="Market Share en Valor (%)",
                    xaxis_title="", yaxis_title="%",
                    height=280, margin=dict(t=40, b=20, l=30, r=10),
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)

        # Gráfico precios
        with col_b:
            precio_cols = {
                'Listerine': 'Precio_LISTERINE',
                'Colgate': 'Precio_COLGPLAX',
                'Oral-B': 'Precio_ORALB',
                'Sensodyne': 'Precio_SENSO'
            }
            precio_cols = {k: v for k, v in precio_cols.items() if v in df_comp.columns}
            if precio_cols:
                fig2 = go.Figure()
                colores = {'Listerine': '#3182CE', 'Colgate': '#E53E3E', 'Oral-B': '#38A169', 'Sensodyne': '#D69E2E'}
                for marca, col in precio_cols.items():
                    fig2.add_trace(go.Scatter(
                        x=df_comp['Date'], y=df_comp[col],
                        mode='lines', name=marca,
                        line=dict(color=colores.get(marca, '#718096'), width=2.5 if marca == 'Listerine' else 1.5),
                    ))
                fig2.update_layout(
                    title="Evolución de Precios",
                    xaxis_title="", yaxis_title="$",
                    height=280, margin=dict(t=40, b=20, l=30, r=10),
                    hovermode='x unified', legend=dict(orientation='h', y=-0.2)
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Distribución comparativa
        if mc.get('dist_comp'):
            st.markdown("#### Distribución — comparativa (último período)")
            dist_data = {'Listerine': mc.get('dist_actual', 0)}
            dist_data.update(mc['dist_comp'])
            fig3 = go.Figure(go.Bar(
                x=list(dist_data.keys()),
                y=list(dist_data.values()),
                marker_color=['#3182CE'] + ['#CBD5E0'] * (len(dist_data) - 1),
                text=[f"{v:.0f}" for v in dist_data.values()],
                textposition='outside'
            ))
            fig3.update_layout(height=260, margin=dict(t=20, b=20, l=30, r=10), yaxis_title="Puntos de distribución")
            st.plotly_chart(fig3, use_container_width=True)

elif tab1:
    with tab1:
        st.info("Cargá el archivo del Competitive Analyzer para ver los datos de mercado.")


# ──── TAB 2: MEDIOS & SOV ────────────────────
if tab2 and ms:
    with tab2:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            delta_sov = f"{ms['sov_cambio']:+.1f} pp" if 'sov_cambio' in ms else None
            st.metric("SOV Promedio", f"{ms.get('sov_promedio','N/D')}%", delta=delta_sov)
        with c2:
            st.metric("Inversión Total Cliente", _fmt_num(ms.get('inv_total_cliente', 0)))
        with c3:
            st.metric("HHI Concentración", ms.get('hhi', 'N/D'), help="<1500 diversificado · >2500 concentrado")
        with c4:
            st.metric("Canal Dominante", ms.get('medio_dominante', 'N/D'), delta=f"{ms.get('medio_dominante_pct',0)}%")

        st.markdown("---")
        col_a, col_b = st.columns(2)

        # Gráfico SOV en el tiempo
        with col_a:
            if 'SOV_Client' in df_sov.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_sov['DATE'], y=df_sov['SOV_Client'],
                    mode='lines+markers', name='SOV Cliente',
                    line=dict(color='#3182CE', width=2.5),
                    fill='tozeroy', fillcolor='rgba(49,130,206,0.1)'
                ))
                fig.add_hline(y=50, line_dash='dash', line_color='gray', annotation_text='50%')
                fig.update_layout(
                    title="Evolución SOV (%)",
                    xaxis_title="", yaxis_title="%",
                    height=280, margin=dict(t=40, b=20, l=30, r=10)
                )
                st.plotly_chart(fig, use_container_width=True)

        # Mix de medios (torta)
        with col_b:
            if ms.get('mix_medios'):
                labels = [m[0] for m in ms['mix_medios']]
                values = [m[1] for m in ms['mix_medios']]
                fig2 = go.Figure(go.Pie(
                    labels=labels, values=values,
                    hole=0.4,
                    marker_colors=px.colors.qualitative.Set2
                ))
                fig2.update_layout(
                    title="Mix de Medios del Cliente (%)",
                    height=280, margin=dict(t=40, b=10, l=10, r=10)
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Inversión competencia
        if ms.get('inv_por_competidor'):
            st.markdown("#### Inversión en Medios — Cliente vs Competencia")
            inv_data = {'Listerine': ms['inv_total_cliente']}
            inv_data.update(ms['inv_por_competidor'])
            fig3 = go.Figure(go.Bar(
                x=list(inv_data.keys()),
                y=list(inv_data.values()),
                marker_color=['#3182CE'] + ['#CBD5E0'] * (len(inv_data) - 1),
                text=[_fmt_num(v) for v in inv_data.values()],
                textposition='outside'
            ))
            fig3.update_layout(height=260, margin=dict(t=20, b=20, l=30, r=10), yaxis_title="Inversión total")
            st.plotly_chart(fig3, use_container_width=True)

elif tab2:
    with tab2:
        st.info("Cargá el archivo del SOV Analyzer para ver los datos de medios.")


# ──── TAB 3: BRECHAS ─────────────────────────
if tab3:
    with tab3:
        if mc and ms:
            brechas = analizar_brechas(mc, ms)
            sov = ms.get('sov_promedio', 0)
            som = mc.get('ms_valor_promedio', 0)
            brecha_val = brechas.get('brecha_sov_som', 0)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("SOV Promedio", f"{sov}%")
            with c2:
                st.metric("Market Share Valor", f"{som}%")
            with c3:
                st.metric("Brecha SOV-SOM", f"{brecha_val:+.1f} pp",
                          delta="Ineficiencia" if brecha_val > 10 else ("Eficiencia" if brecha_val < -5 else "Alineado"),
                          delta_color="inverse" if brecha_val > 10 else "normal")

            st.markdown("---")

            # Gauge de brecha
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=sov,
                delta={'reference': som, 'suffix': " pp vs MS"},
                title={'text': "SOV vs Market Share"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#3182CE"},
                    'steps': [
                        {'range': [0, som], 'color': '#C6F6D5'},
                        {'range': [som, 100], 'color': '#FED7D7'}
                    ],
                    'threshold': {
                        'line': {'color': "#E53E3E", 'width': 3},
                        'thickness': 0.75,
                        'value': som
                    }
                }
            ))
            fig.update_layout(height=300, margin=dict(t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

            nivel = a = brechas.get('diagnostico_brecha', '')
            if nivel == 'inversion_excesiva':
                st.markdown(f'<div class="alert-warning">⚠️ {brechas["mensaje_brecha"]}</div>', unsafe_allow_html=True)
            elif nivel == 'eficiencia_positiva':
                st.markdown(f'<div class="alert-success">✅ {brechas["mensaje_brecha"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-info">ℹ️ {brechas["mensaje_brecha"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Cargá ambos archivos para ver el análisis de brechas SOV-SOM.")


# ──── TAB 4: AGENTE ──────────────────────────
with tab4:
    st.markdown("### 💬 Preguntale al agente")
    st.caption("El agente responde en base a los datos cargados, usando reglas definidas sobre los cálculos reales.")

    # Inicializar historial
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.chat_history.append({
            'rol': 'agente',
            'texto': (
                "¡Hola! Soy el Competitive Intelligence Agent. "
                "Puedo analizar la posición de mercado de Listerine, su Share of Voice en medios, "
                "detectar brechas SOV-SOM y generar narrativas ejecutivas.\n\n"
                "Usá las preguntas rápidas del panel izquierdo o escribime directamente."
                if (mc or ms) else
                "¡Hola! Soy el Competitive Intelligence Agent. "
                "Cargá los archivos Excel en el panel izquierdo para comenzar el análisis."
            )
        })

    # Procesar pregunta pendiente (desde botones rápidos)
    if 'pregunta_pendiente' in st.session_state and st.session_state.pregunta_pendiente:
        preg = st.session_state.pregunta_pendiente
        st.session_state.pregunta_pendiente = None
        resultado = agente_responder(preg, mc, ms)
        st.session_state.chat_history.append({'rol': 'agente', 'texto': resultado['respuesta']})

    # Mostrar historial de chat
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg['rol'] == 'usuario':
                st.markdown(f'<div class="chat-user">👤 {msg["texto"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="agent-label">🧠 Agente</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-agent">{msg["texto"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Input del usuario
    with st.form(key='chat_form', clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            pregunta_usuario = st.text_input(
                "Tu pregunta",
                placeholder="Ej: ¿Cómo está el market share? ¿Hay brechas en medios?",
                label_visibility='collapsed'
            )
        with col_btn:
            enviar = st.form_submit_button("Enviar", use_container_width=True)

    if enviar and pregunta_usuario.strip():
        st.session_state.chat_history.append({'rol': 'usuario', 'texto': pregunta_usuario})
        resultado = agente_responder(pregunta_usuario, mc, ms)
        st.session_state.chat_history.append({'rol': 'agente', 'texto': resultado['respuesta']})
        st.rerun()
