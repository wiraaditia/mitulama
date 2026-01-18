import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import time
import random
from concurrent.futures import ThreadPoolExecutor
import pickle
import os
import numpy as np
import decimal
import email.utils
from datetime import datetime, timezone, timedelta
import altair as alt
import plotly.express as px

def format_price(price):
    """Custom formatter to handle micro-prices without scientific notation"""
    if price is None: return "$0.00"
    if price == 0: return "$0.00"
    
    # Use decimal for high precision formatting
    d = decimal.Decimal(str(price))
    if price < 1:
        # For memecoins like PEPE, show up to 8-10 decimal places
        formatted = format(price, '.10f').rstrip('0').rstrip('.')
        # Ensure at least 4 decimals for consistency if very small
        if '.' in formatted and len(formatted.split('.')[1]) < 4:
            formatted = format(price, '.4f')
        return f"${formatted}"
    elif price < 100:
        return f"${price:,.4f}"
    else:
        return f"${price:,.2f}"

def format_mcap(value):
    """Format market cap to T, B, M"""
    if value is None: return "N/A"
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.0f}"

def get_relative_time(date_str):
    try:
        if not date_str or date_str == "Today":
            return "Hari ini"
        
        # Parse RFC 822 date (standard for RSS)
        try:
            dt = email.utils.parsedate_to_datetime(date_str)
        except:
            # Fallback for generic formats like "2026-01-16 20:36:26"
            try:
                dt = pd.to_datetime(date_str).to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except:
                return date_str
                
        # Indonesian Month Map
        MONTH_MAP = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        
        day = dt.day
        month = MONTH_MAP[dt.month]
        year = dt.year
        
        # Optional: Add time if needed, but user asked for date
        return f"{day} {month} {year}"
    except:
        return "Hari ini"

# Cache file for persistent scanner results
CACHE_FILE = ".scanner_cache.pkl"
WATCHLIST_CACHE_FILE = ".watchlist_cache.pkl"

def load_cached_results():
    """Load scanner results from cache file with 5-minute expiration"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                data = pickle.load(f)
                # Check 5-minute inactivity (300 seconds)
                if time.time() - data.get('last_heartbeat', 0) > 300:
                    os.remove(CACHE_FILE)
                    return None
                return data
        except:
            return None
    return None

def save_cached_results(results, timestamp):
    """Save scanner results to cache file with heartbeat"""
    try:
        current_time = time.time()
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump({
                'results': results, 
                'timestamp': timestamp,
                'last_heartbeat': current_time
            }, f)
    except:
        pass

def update_cache_heartbeat():
    """Update only the heartbeat timestamp to keep cache alive"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                data = pickle.load(f)
            data['last_heartbeat'] = time.time()
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass

def clear_cached_results():
    """Clear cached scanner results"""
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except:
            pass

def load_watchlist_cache():
    """Load watchlist from cache"""
    if os.path.exists(WATCHLIST_CACHE_FILE):
        try:
            with open(WATCHLIST_CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

def save_watchlist_cache(watchlist_data):
    """Save watchlist to cache"""
    try:
        with open(WATCHLIST_CACHE_FILE, 'wb') as f:
            pickle.dump(watchlist_data, f)
    except:
        pass

def clear_watchlist_cache():
    """Clear watchlist cache"""
    if os.path.exists(WATCHLIST_CACHE_FILE):
        try:
            os.remove(WATCHLIST_CACHE_FILE)
        except:
            pass

# --- CONFIG DASHBOARD ---
st.set_page_config(page_title="mitulama", page_icon="favicon.png", layout="wide")


def render_market_analysis(df):
    # --- SECTOR ANALYSIS & CHARTS ---
    st.markdown("### MARKET & SECTOR ANALYSIS")
    
    # 1. Prepare Data for Charts
    # Simple Sector Inference (Same as diag script)
    sectors = {
        'Layer 1': ['BTC', 'ETH', 'SOL', 'ADA', 'AVAX', 'DOT', 'TRX', 'NEAR', 'KAS', 'SUI', 'SEI', 'APT', 'ALGO', 'HBAR', 'XRP', 'BNB'],
        'DeFi': ['UNI', 'LINK', 'AAVE', 'MKR', 'SNX', 'CRV', 'COMP', 'RUNE', 'INJ', 'JUP', 'DYDX', 'LDO'],
        'AI & Big Data': ['TAO', 'FET', 'RNDR', 'NEAR', 'GRT', 'AGIX', 'WLD', 'OCEAN', 'JASMY', 'AKT'],
        'Meme': ['DOGE', 'SHIB', 'PEPE', 'WIF', 'BONK', 'FLOKI', 'MEME', 'BOME', 'BRETT', 'MOG'],
        'Gaming/Metaverse': ['ICP', 'IMX', 'SAND', 'MANA', 'AXS', 'GALA', 'BEAM', 'RON'],
        'Layer 2': ['MATIC', 'ARB', 'OP', 'MNT', 'STRK', 'BLAST', 'BASE'],
        'RWA': ['ONDO', 'POLYX', 'PENDLE']
    }
    
    # Process df to get sector data
    sector_counts = {k: 0 for k in sectors}
    sector_counts['Others'] = 0
    sector_performance = {k: [] for k in sectors}
    sector_performance['Others'] = []
    
    for idx, row in df.iterrows():
        ticker = row['Ticker']
        chg = row['Change %']
        assigned = False
        for s, tickers in sectors.items():
            if ticker in tickers:
                sector_counts[s] += 1
                sector_performance[s].append(chg)
                assigned = True
                break
        if not assigned:
            sector_counts['Others'] += 1
            sector_performance['Others'].append(chg)

    # Create DataFrames for Charts
    # Pie Chart Data (Distribution)
    pie_data = pd.DataFrame([{'Sector': k, 'Count': v} for k, v in sector_counts.items() if v > 0])
    if not pie_data.empty:
        pie_data['Percent'] = ((pie_data['Count'] / pie_data['Count'].sum()) * 100).round(1)
    
    # Bar Chart Data (Performance)
    bar_data = []
    for s, changes in sector_performance.items():
        if changes:
            avg_chg = sum(changes) / len(changes)
            bar_data.append({'Sector': s, 'Avg Change %': avg_chg})
    bar_df = pd.DataFrame(bar_data)

    # --- SECTOR INSIGHTS & METRICS ---
    if not pie_data.empty and not bar_df.empty:
        # 1. Determine Dominance & Top Performance
        dominant_sector = pie_data.sort_values('Count', ascending=False).iloc[0]
        top_sector = bar_df.sort_values('Avg Change %', ascending=False).iloc[0]
        
        # 2. AI Forecast Logic (Simple Heuristic Rule-Based)
        forecast_text = ""
        forecast_confidence = 0
        
        # Logic: If Top Sector is Layer 1 or Layer 2 -> Infrastructure Phase
        if top_sector['Sector'] in ['Layer 1', 'Layer 2']:
            forecast_text = "Rotasi modal sedang mengarah ke infrastruktur (Layer 1/2). Dalam 3 bulan ke depan, narasi akan berfokus pada **Ecosystem Growth & TVL Acc.**. Altcoin fundamental akan memimpin fase ini."
            forecast_confidence = 85
        # Logic: If Top Sector is Meme -> Speculative Phase
        elif top_sector['Sector'] == 'Meme':
            forecast_text = "Pasar dalam fase **High Risc / High Reward**. Dominasi Meme coin menandakan 'Risk-On' ekstrem. Hati-hati koreksi tajam. Dalam 3 bulan, kemungkinan profit akan dirotasi kembali ke sektor 'Real Yield' (DeFi/RWA)."
            forecast_confidence = 78
        # Logic: If Top Sector is AI -> Tech Phase
        elif top_sector['Sector'] == 'AI & Big Data':
            forecast_text = "Tren AI sedang memimpin. Narasi ini bersifat jangka panjang. Prediksi 3 bulan ke depan: **AI Supercycle** mungkin berlanjut seiring rilis teknologi baru, namun selektif pada proyek dengan produk nyata."
            forecast_confidence = 92
        # Logic: If Top Sector is RWA/DeFi -> Utility Phase
        elif top_sector['Sector'] in ['RWA', 'DeFi']:
            forecast_text = "Institusi mulai melirik Real World Asset (RWA). Ini adalah fase akumulasi 'Smart Money'. 3 Bulan ke depan berpotensi menjadi **RWA Summer**."
            forecast_confidence = 88
        else:
            forecast_text = f"Sektor {top_sector['Sector']} memimpin kenaikan. Pasar mencari narasi baru. Pantau likuiditas BTC untuk konfirmasi arah selanjutnya."
            forecast_confidence = 70

        # UI: Metrics Display
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f'''
            <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:10px; color:#848e9c; font-weight:700; text-transform:uppercase;">Dominasi Sektor</div>
                <div style="font-size:16px; font-weight:800; color:#fff;">{dominant_sector['Sector']}</div>
                <div style="font-size:11px; color:#848e9c;">{dominant_sector['Percent']}% dari total asset</div>
            </div>
            ''', unsafe_allow_html=True)
        with m2:
            is_pos = top_sector['Avg Change %'] >= 0
            color = "#00c853" if is_pos else "#ff5252"
            st.markdown(f'''
            <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:10px; color:#848e9c; font-weight:700; text-transform:uppercase;">Top Performer (24h)</div>
                <div style="font-size:16px; font-weight:800; color:{color};">{top_sector['Sector']}</div>
                <div style="font-size:11px; color:{color};">{top_sector['Avg Change %']:+.2f}% Avg Change</div>
            </div>
            ''', unsafe_allow_html=True)
        with m3:
            st.markdown(f'''
            <div style="background:rgba(41, 98, 255, 0.1); padding:10px; border-radius:6px; border:1px solid #2962ff;">
                <div style="font-size:10px; color:#848e9c; font-weight:700; text-transform:uppercase;">AI Forecast Confidence</div>
                <div style="font-size:16px; font-weight:800; color:#2962ff;">{forecast_confidence}%</div>
                <div style="font-size:11px; color:#848e9c;">Probability Score</div>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom:15px'></div>", unsafe_allow_html=True)
        
        # Forecast Expander
        with st.expander("🔮 AI Analisis & Prediksi Q3 (3 Bulan)", expanded=True):
            st.markdown(f'''
            <div style="border-left: 3px solid #2962ff; padding-left: 15px; margin: 5px 0;">
                <span style="font-size: 14px; color: #e0e0e0; font-weight: 500;">"{forecast_text}"</span>
            </div>
            ''', unsafe_allow_html=True)

    # Charts Layout
    # --- INTERACTIVE CHARTS & FILTERING (PLOTLY) ---
    
    c1, c2 = st.columns(2)
    
    # Captured Selections
    filter_sector = None
    
    with c1:
        st.caption("Distribution by Sector (Click to Filter)")
        if not pie_data.empty:
            # Plotly Pie (Donut)
            fig_pie = px.pie(
                pie_data, 
                values='Count', 
                names='Sector', 
                hole=0.4,
                color='Sector',
                color_discrete_sequence=px.colors.sequential.Magma,
                height=350
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate = "<b>%{label}</b><br>Count: %{value}<br>To: %{percent}<extra></extra>"
            )
            fig_pie.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5), # Legend pushed further down
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=120, l=10, r=10), # Much larger bottom margin to prevent cutoff
                font=dict(family="Orbitron", color="white", size=14)
            )
            
            # Interactive Plotly Chart
            event_pie = st.plotly_chart(fig_pie, use_container_width=True, on_select="rerun", selection_mode="points")
        else:
            st.info("No sector data available.")
            event_pie = None
            
    with c2:
        st.caption("Potential Performance by Sector (Click to Filter)")
        if not bar_df.empty:
            # 1. Sort Data High to Low
            bar_df = bar_df.sort_values(by='Avg Change %', ascending=False)
            
            # Plotly Bar
            # Add color column based on value
            bar_df['Color'] = bar_df['Avg Change %'].apply(lambda x: '#00c853' if x > 0 else '#ff5252')
            
            fig_bar = px.bar(
                bar_df, 
                x='Sector', 
                y='Avg Change %',
                color='Avg Change %', # Gradient effect or just use discrete
                color_continuous_scale=['#ff5252', '#00c853'],
                text='Avg Change %', # Add text for labels
                height=350
            )
            # Force specific colors for clarity if preferred, but gradient is nice
            # Using update_traces for precise control
            fig_bar.update_traces(
                marker_color=bar_df['Color'],
                texttemplate='%{text:.2f}%', # Format displayed text
                textposition='outside', # Text outside bar
                hovertemplate = "<b>%{x}</b><br>Avg Change: %{y:.2f}%<extra></extra>",
                cliponaxis=False
            )
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=60, l=20, r=20), # Increase margins
                font=dict(family="Orbitron", color="white", size=14), # Larger font
                xaxis=dict(showgrid=False, tickangle=-45), # Rotate labels explicitly
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                showlegend=False
            )
            
            event_bar = st.plotly_chart(fig_bar, use_container_width=True, on_select="rerun", selection_mode="points")
        else:
            st.info("No performance data available.")
            event_bar = None

    # --- PROCESS SELECTION FILTER ---
    
    # Check selection from Pie
    if event_pie and len(event_pie.selection["points"]) > 0:
        try:
            point = event_pie.selection["points"][0]
            idx = point["point_index"]
            filter_sector = pie_data.iloc[idx]['Sector']
        except: pass
        
    # Check selection from Bar
    if not filter_sector and event_bar and len(event_bar.selection["points"]) > 0:
        try:
            point = event_bar.selection["points"][0]
            idx = point["point_index"]
            filter_sector = bar_df.iloc[idx]['Sector']
        except: pass

    # Apply Filter
    if filter_sector:
        st.info(f" Memfilter Sektor: **{filter_sector}**")
        if st.button("Reset Filter", type="secondary"):
            st.rerun()
        
        # Filtering logic
        filtered_indices = []
        for idx, row in df.iterrows():
            ticker = row['Ticker']
            sector_match = "Others"
            for s, tickers in sectors.items():
                if ticker in tickers:
                    sector_match = s
                    break
            if sector_match == filter_sector:
                filtered_indices.append(idx)
        
        df = df.iloc[filtered_indices]

    st.markdown("### Filter Hasil")
    
    with st.form(key="search_form", clear_on_submit=False):
        col1, col2 = st.columns([5, 1])
        with col1:
            result_search = st.text_input(
                "search_input",
                placeholder="Ketik kode crypto", 
                label_visibility="collapsed",
                key="search_query"
            )
        with col2:
            search_submitted = st.form_submit_button("Cari", use_container_width=True)
    
    if result_search and (search_submitted or result_search):
        search_term = result_search.lower()
        df = df[
            df['Ticker'].str.lower().str.contains(search_term) | 
            df['Status'].str.lower().str.contains(search_term) |
            df['Analysis'].str.lower().str.contains(search_term)
        ]
        st.caption(f"Menampilkan {len(df)} hasil pencarian untuk '{result_search}'.")
    
    watchlist_list = [r for i, r in df.iterrows() if any(s in r['Status'] for s in ['WATCHLIST', 'CORE ASSET', 'UNDERVALUED'])]
    exclusive_hot_list = [r for i, r in df.iterrows() if any(s in r['Status'] for s in ['ALPHA', 'WHALE', 'BREAKOUT', 'BULLISH', 'TRENDING', 'BUZZ'])]
    all_potential_list = [r for i, r in df.iterrows() if r['Status'] != 'HOLD']
    total_potential = len(all_potential_list)
    
    result_tab_options = [
        f"All ({total_potential})", 
        f"Watchlist ({len(watchlist_list)})", 
        f"Top Picks ({len(exclusive_hot_list)})"
    ]
    
    if 'active_result_tab' not in st.session_state:
        st.session_state.active_result_tab = result_tab_options[0]
    else:
        current_category = st.session_state.active_result_tab.split(' (')[0]
        if current_category == "All Potential": current_category = "All"
        new_tab_match = [opt for opt in result_tab_options if opt.startswith(current_category)]
        if new_tab_match:
            st.session_state.active_result_tab = new_tab_match[0]
        else:
            st.session_state.active_result_tab = result_tab_options[0]

    st.markdown("---")
    active_tab = st.radio(
        "Pilih Tampilan:",
        result_tab_options,
        horizontal=True,
        key="active_result_tab",
        label_visibility="collapsed"
    )
    
    def render_grid_inner(rows, key_prefix):
        if not rows:
            st.info("Belum ada asset yang memenuhi kriteria ini.")
            return
        
        cols = st.columns(3)
        for idx, row in enumerate(rows):
            with cols[idx % 3]:
                st.markdown(f'<div id="card-{row['Ticker']}"></div>', unsafe_allow_html=True)
                ticker_clean = row['Ticker']
                coin_data = COIN_MAP.get(ticker_clean, {})
                logo_url = coin_data.get('image', '')
                
                with st.container(border=True):
                    h_col1, h_col2 = st.columns([2, 1])
                    with h_col1:
                        st.markdown(f'''
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="width:24px; height:24px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05);">
                                    <img src="{logo_url}" style="width:100%; height:100%; object-fit:contain;">
                                </div>
                                <div>
                                    <div style="font-weight: 700; font-size: 14px; color: #e0e0e0; line-height: 1;">{ticker_clean}</div>
                                    <div style="font-size: 10px; color: #848e9c; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px;">{row.get('Name', '')}</div>
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
                        st.markdown(f"<span style='font-size: 18px; font-weight: 800; color: #fff;'>{format_price(row['Price'])}</span>", unsafe_allow_html=True)
                    with h_col2:
                        st.markdown(f"<div style='text-align: right; font-size: 11px; font-weight: 700; color: #848e9c; margin-top: 5px;'>{row['Status']}</div>", unsafe_allow_html=True)

                    st.markdown(f'''
                        <div class="metrics-grid">
                            <div class="metric-item">
                                <span class="metric-label">24h Chg</span>
                                <span class="metric-value">{row['Change %']:.2f}%</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Mkt Cap</span>
                                <span class="metric-value">{format_mcap(coin_data.get('market_cap', 0))}</span>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)

                    st.markdown(f'''
                        <div style="display: flex; gap: 15px; margin-top: 10px; margin-bottom: 5px;">
                            <div style="font-size: 10px; color: #848e9c;">MEDIA PULSE: <span style="color:#00c853;">{row['News Score']}%</span></div>
                            <div style="font-size: 10px; color: #848e9c;">SOCIAL BUZZ: <span style="color:#2962ff;">{row['Social Buzz']}%</span></div>
                        </div>
                    ''', unsafe_allow_html=True)

                    analysis_title = row['Analysis'].split('\n')[0] if row['Analysis'] else "Analysis"
                    st.markdown(f"<div style='margin-top: 15px; font-weight: 700; color: #e0e0e0;'>{analysis_title}</div>", unsafe_allow_html=True)
                    
                    with st.expander("Detail Riset & Berita"):
                        st.markdown(row['Analysis'])
                        st.markdown("---")
                        if row['News List']:
                            for news in row['News List']:
                                news_url = news.get('link', '#')
                                st.markdown(f'''
                                    <div class="news-card" style="margin-bottom: 12px; border-left: 4px solid #ff2d75; background: rgba(255,255,255,0.03); border-radius: 4px; overflow: hidden;">
                                        <a href="{news_url}" target="_blank" style="text-decoration: none !important; text-decoration-line: none !important; color: inherit !important; display: block; padding: 12px; border: none !important;">
                                            <div style="font-size: 10px; color: #848e9c; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between;">
                                                <span style="display: flex; align-items: center; gap: 4px;">🗓️ {news.get('date')}</span>
                                                <span style="display: flex; align-items: center; gap: 4px;">🌐 {news.get('source')}</span>
                                            </div>
                                            <div style="color: #ff2d75; font-weight: 700; font-size: 14px; line-height: 1.4; margin-bottom: 5px; text-decoration: none !important;">
                                                {news.get('title')}
                                            </div>
                                            <div style="font-size: 9px; color: #848e9c; font-style: italic; text-decoration: none !important;">Klik untuk baca selengkapnya di sumber asli &rarr;</div>
                                        </a>
                                    </div>
                                ''', unsafe_allow_html=True)
                        else: st.caption("Tidak ada berita spesifik hari ini.")
                    
                    st.button(f"Load Chart", key=f"btn_{key_prefix}_{row['Ticker']}_{idx}", on_click=set_ticker, args=(row['Ticker'],), use_container_width=True)

    if active_tab.startswith("All"):
        render_grid_inner(all_potential_list, "all")
        st.markdown("---")
        st.markdown("###  Tabel Detail Semua Asset")
        st.markdown('''
        <style>
            [data-testid="stDataFrameResizable"] th {
                background-color: #2a2e39 !important;
                color: #848e9c !important;
            }
        </style>
        ''', unsafe_allow_html=True)
        st.dataframe(df[df['Status'] != 'HOLD'], use_container_width=True, hide_index=True)
    elif active_tab.startswith("Watchlist"):
        render_grid_inner(watchlist_list, "wl")
    elif active_tab.startswith("Top"):
        render_grid_inner(exclusive_hot_list, "top")

# --- CUSTOM CSS STOCKBIT STYLE ---
# --- CUSTOM CSS PREMIUM DARK STYLE ---
# --- CUSTOM CSS TRADINGVIEW / STOCKBIT PRO STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@400;600;700&display=swap');
    
    /* Google AdSense Main Script removed */
</style>
<style>
    :root {
        --primary: #ff2d75;
        --secondary: #ff007f;
        --bg-black: #0d0d12;
        --card-bg: #1a1a24;
        --border-pink: rgba(255, 45, 117, 0.3);
        --glow: 0 0 10px rgba(255, 45, 117, 0.4);
    }

    /* Global Reset & Font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--bg-black) !important;
        color: #fce4ec !important;
        font-size: 13px;
        overflow-x: hidden !important;
        scroll-behavior: smooth !important;
    }

    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        color: var(--primary) !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 15px rgba(255, 45, 117, 0.5);
    }
    
    /* Sidebar (Watchlist) */
    [data-testid="stSidebar"] {
        background-color: #14141d !important;
        border-right: 1px solid var(--border-pink);
        width: 300px !important;
    }
    
    /* Main Layout Gap */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 45, 117, 0.05) !important;
        border: 1px solid var(--border-pink) !important;
        padding: 10px !important;
        border-radius: 8px !important;
        box-shadow: var(--glow);
    }
    div[data-testid="stMetricLabel"] { font-size: 11px !important; color: #ff80ab !important; font-family: 'Orbitron', sans-serif;}
    div[data-testid="stMetricValue"] { font-size: 18px !important; color: #fff !important; font-weight: 700;}
    
    /* Buttons (Cyber Style) */
    .stButton > button {
        background: linear-gradient(45deg, #ff2d75, #ff007f) !important;
        color: white !important;
        border-radius: 4px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-family: 'Orbitron', sans-serif;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 0, 127, 0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 0, 127, 0.5);
    }
    
    /* Tabs (Cyber Panel) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #14141d;
        padding: 5px 15px;
        border-bottom: 2px solid var(--border-pink);
        gap: 30px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: transparent;
        color: #ff80ab;
        font-family: 'Orbitron', sans-serif;
        font-size: 13px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom: 3px solid var(--primary) !important;
        text-shadow: 0 0 10px rgba(255, 45, 117, 0.5);
    }
    
    /* Scrollbars */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #0d0d12; }
    ::-webkit-scrollbar-thumb { background: #ff007f; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #ff2d75; }

    /* Fix: Stop dimming effect */
    div[data-testid="stVerticalBlock"] > div[style*="opacity"] {
        opacity: 1 !important;
    }

    /* Metrics Grid Utility */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-top: 15px;
    }
    .metric-item {
        background: rgba(255, 45, 117, 0.05);
        padding: 10px;
        border: 1px solid var(--border-pink);
        border-radius: 8px;
        text-align: center;
    }
    .metric-label {
        font-size: 10px;
        color: #ff80ab;
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        display: block;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 14px;
        font-weight: 700;
        color: #fff;
    }


    /* News Cards */
    .news-card {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .news-card a {
        text-decoration: none !important;
        text-decoration-line: none !important;
        border-bottom: none !important;
    }
    .news-card a:hover {
        text-decoration: none !important;
        border-bottom: none !important;
    }
    .news-card:hover {
        background: rgba(255, 45, 117, 0.1) !important;
        border-left-width: 6px !important;
        transform: translateX(5px);
    }

    /* Cards */
    div[data-testid="stExpander"] {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-pink) !important;
        border-radius: 10px !important;
    }

    /* --- RESPONSIVE ADJUSTMENTS --- */
    @media (max-width: 1024px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    @media (max-width: 768px) {
        html, body, [class*="css"] {
            font-size: 12px;
        }
        .main-header {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 15px !important;
        }
        .header-right {
            width: 100% !important;
            justify-content: space-between !important;
            gap: 10px !important;
        }
        .metrics-grid {
            grid-template-columns: 1fr;
        }
        div[data-testid="stMetricValue"] {
            font-size: 16px !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            padding: 5px 5px;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 11px;
            padding: 0 5px;
        }
    }
    
    /* Clean Hide for non-essential sidebar elements on mobile */
    @media (max-width: 480px) {
        div[data-testid="stMetricLabel"] { font-size: 9px !important; }
        .metric-label { font-size: 9px !important; }
        .mobile-hide { display: none !important; }
    }

""", unsafe_allow_html=True)

# --- ANTI-BLOCKING MEASURES ---
# 1. Daftar User-Agent untuk Rotasi
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
]

# --- COINGECKO DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_top_crypto_tickers(count=1000):
    """Fetch top N cryptocurrencies from CoinGecko (multi-page)"""
    all_data = []
    per_page = 250
    pages = (count + per_page - 1) // per_page
    
    try:
        for page in range(1, pages + 1):
            url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={per_page}&page={page}"
            url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={per_page}&page={page}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                page_data = response.json()
                all_data.extend(page_data)
                # Small delay to avoid aggressive rate limiting
                if pages > 1: time.sleep(0.5)
            else:
                break
        return all_data[:count]
    except Exception as e:
        st.error(f"Error fetching data from CoinGecko: {e}")
        return []

# Initialize TICKERS with CoinGecko data (Up to 1000 coins)
CRYPTO_DATA = get_top_crypto_tickers(1000)
# Ensure unique tickers and build map
TICKERS = []
COIN_MAP = {}
seen_tickers = set()

for coin in CRYPTO_DATA:
    sym = coin['symbol'].upper()
    if sym not in seen_tickers:
        TICKERS.append(sym)
        seen_tickers.add(sym)
    # Map by symbol for quick lookup (if duplicate symbol, first one - usually high mcap - wins)
    if sym not in COIN_MAP:
        COIN_MAP[sym] = coin

# --- CUSTOM CSS LOADING ANIMATION (Cyberpunk Style) ---
def custom_loading_overlay(status_text="LOADING...", progress=0):
    # Dynamic conic gradient for the ring - PINK THEME
    gradient = f"conic-gradient(#ff007f {progress}%, #14141d 0)"
    
    return f"""<div id="loading-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(13, 13, 18, 0.95); z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; backdrop-filter: blur(8px);">
        <!-- Circular Progress Container -->
        <div style="position: relative; width: 140px; height: 140px; border-radius: 50%; background: {gradient}; display: flex; justify-content: center; align-items: center; margin-bottom: 25px; box-shadow: 0 0 30px rgba(255, 0, 127, 0.3); animation: pulse-ring 2s infinite;">
            <!-- Inner Circle (Mask) -->
            <div style="width: 120px; height: 120px; background: #0d0d12; border-radius: 50%; display: flex; justify-content: center; align-items: center; flex-direction: column; border: 1px solid rgba(255, 0, 127, 0.2);">
                <div style="font-family: 'Orbitron', monospace; color: #fff; font-size: 28px; font-weight: bold; text-shadow: 0 0 10px rgba(255, 0, 127, 0.5);">{progress}%</div>
            </div>
            <!-- Spinning Border for activity indication -->
            <div style="position: absolute; top: -8px; left: -8px; right: -8px; bottom: -8px; border: 2px solid transparent; border-top: 2px solid #ff2d75; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        </div>
        <div style="font-family: 'Orbitron', monospace; color: #ff2d75; font-size: 20px; font-weight: bold; letter-spacing: 4px; text-shadow: 0 0 15px rgba(255, 45, 117, 0.6);">{status_text}</div>
        <div style="font-family: 'Inter', sans-serif; color: #ff80ab; font-size: 13px; margin-top: 15px; opacity: 0.8;">Processing Cyber Assets...</div>
        <style>
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            @keyframes pulse-ring {{ 0% {{ box-shadow: 0 0 0 0 rgba(255, 0, 127, 0.4); }} 70% {{ box-shadow: 0 0 0 15px rgba(255, 0, 127, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(255, 0, 127, 0); }} }}
        </style>
    </div>"""

# --- FUNGSI ITUNG-ITUNGAN (Tech Indicators) ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_obv(df):
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return obv

@st.cache_data(ttl=600)
def get_crypto_stats(ticker):
    """Placeholder for custom crypto stats if needed, currently using COIN_MAP"""
    return None

@st.cache_data(ttl=300)
def get_global_market_stats():
    """Fetch global crypto market stats instead of IHSG"""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        res = requests.get(url, timeout=5)
        data = res.json()['data']
        
        return {
            'price': f"${data['total_market_cap']['usd']/1e12:.2f}T",
            'change': data['market_cap_change_percentage_24h_usd'],
            'percent': f"{data['market_cap_change_percentage_24h_usd']:+.2f}%",
            'btc_d': f"{data['market_cap_percentage']['btc']:.1f}%"
        }
    except:
        return None

@st.cache_data(ttl=1800) # Cache 30 mins - reduce news scraping
def get_news_sentiment(ticker):
    """
    Advanced News Sentiment Analysis with Multi-Source Aggregation
    Returns: sentiment, headline, news_score, social_buzz, impact, news_list, analysis
    """
    try:
        clean_ticker = ticker.replace('.JK', '')
        
        # Multi-source news aggregation
        sources = [
            f"https://news.google.com/rss/search?q={clean_ticker}+crypto+news&hl=en-US&gl=US&ceid=US:en",
            f"https://cryptopanic.com/news/rss/?filter=all&q={clean_ticker}"
        ]
        
        all_news = []
        social_hits = 0
        social_keywords = ['moon', 'lfg', 'whale', 'pump', 'dump', 'viral', 'bullish', 'breakout']
        noise_keywords = ['searching...', 'loading...', 'investing.com', 'edit profil']
        
        for rss_url in sources:
            try:
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                res = requests.get(rss_url, headers=headers, timeout=3)
                soup = BeautifulSoup(res.text, 'xml') 
                items = soup.find_all('item', limit=8)
                
                for item in items:
                    try:
                        title = item.title.text if item.title else ""
                        link = item.link.text if item.link else ""
                        date_raw = item.pubDate.text if item.pubDate else "Today"
                        date = get_relative_time(date_raw)

                        title_clean = title.strip()
                        if not title_clean or len(title_clean) < 20: continue
                        if any(n in title_clean.lower() for n in noise_keywords): continue
                        
                        # Relevance validation
                        title_lower = title_clean.lower()
                        ticker_match = clean_ticker.lower() in title_lower
                        crypto_keywords = ['crypto', 'bitcoin', 'token', 'price', 'market', 'trading', 'web3', 'defi']
                        has_context = any(kw in title_lower for kw in crypto_keywords)
                        
                        if not (ticker_match or has_context): continue
                        
                        if any(k in title_lower for k in social_keywords):
                            social_hits += 1
                        
                        all_news.append({
                            'title': title_clean,
                            'source': item.source.text if hasattr(item, 'source') and item.source else ("CryptoPanic" if "cryptopanic" in rss_url else "Google News"),
                            'link': link,
                            'date': date
                        })
                    except: continue
            except: continue
        
        if not all_news:
            fallback_title = f"{clean_ticker} is showing {'positive' if clean_ticker in ['BTC', 'ETH'] else 'notable'} market activity"
            return "NEUTRAL", fallback_title, 50, 45, "LOW", [], "Aggregated market indicators (Technical Analysis only)"
        
        # Scoring Logic
        pos_k = ['bullish', 'pump', 'surge', 'growth', 'adoption', 'partnership', 'listing', 'breakout', 'ath']
        neg_k = ['bearish', 'dump', 'hack', 'scam', 'crash', 'regulation', 'ban', 'lawsuit', 'negative']
        
        total_score = 50
        for n in all_news[:6]:
            t_low = n['title'].lower()
            if any(k in t_low for k in pos_k): total_score += 15
            if any(k in t_low for k in neg_k): total_score -= 15
        
        avg_score = min(100, max(0, total_score + 10))
        social_buzz = min(95, 40 + (len(all_news) * 3) + (social_hits * 15))
        
        sentiment = "NEUTRAL"
        if avg_score >= 75: sentiment = "VERY POSITIVE"
        elif avg_score >= 60: sentiment = "POSITIVE"
        elif avg_score <= 25: sentiment = "VERY NEGATIVE"
        elif avg_score <= 40: sentiment = "NEGATIVE"
        
        impact = "HIGH" if (avg_score >= 75 or avg_score <= 25) else "MEDIUM"
        analysis_text = f"Aggregate sentiment score: {avg_score}/100 based on {len(all_news)} relevant sources."
        
        return sentiment, all_news[0]['title'], avg_score, social_buzz, impact, all_news[:6], analysis_text

    except Exception as e:
        return "NEUTRAL", f"Monitoring {ticker} market momentum", 50, 45, "LOW", [], f"Technical Fallback: {str(e)}"

def analyze_crypto(ticker_symbol):
    coin_data = COIN_MAP.get(ticker_symbol.upper())
    if not coin_data: return None
    
    curr_price = coin_data.get('current_price', 0) or 0
    chg_pct = coin_data.get('price_change_percentage_24h', 0) or 0
    
    # Financial indicators from CoinGecko
    market_cap = coin_data['market_cap']
    total_volume = coin_data['total_volume']
    
    # News Sentiment
    sentiment, headline, news_score, social_buzz, impact, news_list, sentiment_analysis = get_news_sentiment(ticker_symbol)
    
    # --- 5-PILLAR ALGORITHM REFINEMENT ---
    # Pillar 1: Undervalue + Volume Up
    # Use Turnover Ratio (Volume/MarketCap) and ATH distance
    vol_mcap_ratio = total_volume / (market_cap or 1)
    ath_chg = coin_data.get('ath_change_percentage', 0) or 0
    is_undervalued = ath_chg < -70 and vol_mcap_ratio > 0.05
    
    # Pillar 2: Big Player (Whale) Entry
    # Detect anomalous volume (Turnover > 0.15) often linked to large wallet movements
    is_big_player = vol_mcap_ratio > 0.15
    
    # Pillar 3: News Impulse
    is_news_impulse = news_score > 65
    
    # Pillar 4: Social Media BUZZ
    is_social_buzz = social_buzz > 70
    
    # Pillar 5: Chart Pattern Support
    # Check if price is holding above daily average or near high
    daily_high = coin_data.get('high_24h', 0) or 1
    is_chart_support = (curr_price > daily_high * 0.9)
    
    # Status Determination (The 5-Pillar Synthesis)
    status = "HOLD"
    if is_undervalued and is_big_player and is_news_impulse:
        status = "ALPHA BREAKOUT"
    elif is_big_player and is_chart_support:
        status = "WHALE ACCUMULATION"
    elif is_news_impulse and is_chart_support:
        status = "BULLISH MOMENTUM"
    elif is_social_buzz and is_news_impulse:
        status = "MARKET BUZZ"
    elif is_undervalued:
        status = "UNDERVALUED GEM"
    elif market_cap > 10_000_000_000:
        status = "CORE ASSET"
    
    # Final check for News Headline (Anti-Placeholder)
    if not headline or any(bad in headline.lower() for bad in ["searching", "loading", "error", "no fresh"]):
        headline = f"Positive traction on {ticker_symbol}" if chg_pct > 0 else f"Monitoring {ticker_symbol} action"
        if not news_list:
            news_list = [{'title': headline, 'source': 'System Analysis', 'link': '#', 'date': 'Today'}]

    # Research Construction
    research_points = [
        f"**Strategy:** {'High Potential' if status != 'HOLD' else 'Monitoring'}.",
        f"**Price Action:** 24h change of {chg_pct:.2f}%. ATH Drop: {ath_chg:.1f}%.",
        f"**Arkham Pulse:** {'Whale activity detected' if is_big_player else 'Stable distribution'}.",
        f"**Market Cap:** ${market_cap:,.0f} (Global Rank: #{coin_data.get('market_cap_rank', 'N/A')}).",
        f"**V/MCap Ratio:** {vol_mcap_ratio:.3f} (Turnover Intensity)."
    ]

    analysis = f"CRYPTO ANALYSIS: {status}\n\n"
    analysis += "---\n\n"
    for point in research_points:
        analysis += f"{point}\n\n"
    
    if headline:
        headline_link = news_list[0].get('link', '#') if news_list else '#'
        analysis += f"---\n\n*Headline Utama:* [\"{headline}\"]({headline_link})"

    return {
        "Ticker": ticker_symbol,
        "Name": coin_data.get('name', ticker_symbol),
        "Price": curr_price,
        "Change %": chg_pct,
        "Sentiment": sentiment,
        "News Score": news_score,
        "Social Buzz": social_buzz,
        "Impact": impact,
        "Analysis": analysis,
        "Status": status,
        "News List": news_list,
        "Headline": headline,
        "Raw Vol Ratio": vol_mcap_ratio
    }

# Helper untuk mengubah ticker dari News Feed
def set_ticker(ticker):
    # Update langsung ke key milik selectbox
    st.session_state.ticker_selector = ticker.replace('.JK', '')
    # Set scroll to top flag
    st.session_state.scroll_to_top = True
    # Auto-collapse sidebar on mobile
    st.session_state.collapse_sidebar = True

# --- MOBILE HELPERS ---
if 'collapse_sidebar' not in st.session_state:
    st.session_state.collapse_sidebar = False

if st.session_state.collapse_sidebar:
    components.html(
        """
        <script>
            function tryCollapse() {
                var doc = window.parent.document;
                var sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                
                // Breaking point: 1024px to cover tablets and narrow windows
                if (sidebar && window.parent.innerWidth <= 1024) {
                    var isExpanded = sidebar.getAttribute('aria-expanded') === 'true';
                    if (isExpanded) {
                        // 1. Try official data-testid
                        var btn = doc.querySelector('button[data-testid="stSidebarCollapseButton"]');
                        if (btn) {
                            btn.click();
                            return true;
                        }
                        
                        // 2. Fallback: Search for any button with Close/Collapse label
                        var buttons = doc.querySelectorAll('button');
                        for (var i = 0; i < buttons.length; i++) {
                            var label = (buttons[i].getAttribute('aria-label') || "").toLowerCase();
                            if (label.includes('close') || label.includes('collapse')) {
                                buttons[i].click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            }

            // Aggressive attempt logic: try multiple times over 1.5 seconds
            var attempts = 0;
            var interval = setInterval(function() {
                if (tryCollapse() || attempts > 10) {
                    clearInterval(interval);
                }
                attempts++;
            }, 150);
        </script>
        """,
        height=0
    )
    st.session_state.collapse_sidebar = False

# --- MAIN UI ---

# Initialization for Ticker Selector
if 'ticker_selector' not in st.session_state:
    st.session_state.ticker_selector = "BTC" # Default Startup Ticker

if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

if 'show_search' not in st.session_state:
    st.session_state.show_search = False

if 'watchlist_limit' not in st.session_state:
    st.session_state.watchlist_limit = 20

# JavaScript for scrolling to top
if st.session_state.get('scroll_to_top', False):
    import time
    # Use a dynamic fragment in the HTML to ensure it's seen as new content
    ts = int(time.time() * 1000)
    components.html(
        f"""
        <div id="scroll-marker-{ts}" style="display:none;"></div>
        <script>
            function performScroll() {{
                try {{
                    var selectors = [
                        '[data-testid="stMainBlockContainer"]',
                        '.main',
                        'section.main',
                        '.stApp'
                    ];
                    var scrolled = false;
                    for (var i = 0; i < selectors.length; i++) {{
                        var container = window.parent.document.querySelector(selectors[i]);
                        if (container) {{
                            container.scrollTo({{top: 0, behavior: 'auto'}});
                            scrolled = true;
                        }}
                    }}
                    if (!scrolled) {{
                        window.parent.scrollTo(0, 0);
                        window.top.scrollTo(0, 0);
                    }}
                }} catch (e) {{
                    window.parent.scrollTo(0, 0);
                }}
            }}
            // Execute multiple times to ensure it catches the page state
            performScroll();
            setTimeout(performScroll, 30);
            setTimeout(performScroll, 100);
            setTimeout(performScroll, 300);
        </script>
        """,
        height=0
    )
    # Set back to False so it doesn't scroll on EVERY rerun, only when triggered
    st.session_state.scroll_to_top = False


# --- DATA PRE-FETCHING (Global) ---
if 'market_stats_live' not in st.session_state or st.session_state.get('refresh_market', False):
    st.session_state.market_stats_live = get_global_market_stats()
    st.session_state.refresh_market = False

# --- UI COMPONENT: SIDEBAR (WATCHLIST ONLY) ---
with st.sidebar:
    # Custom Reference CSS
    st.markdown("""
    <style>
        /* Premium Sidebar UI - Reference Style */
        .wl-ticker { font-weight: 700; font-size: 14px; color: #fff; line-height: 1.2; }
        .wl-name { font-size: 10px; color: #848e9c; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .wl-price { font-weight: 700; font-size: 14px; text-align: right; color: #fff; line-height: 1.2; }
        .wl-chg { font-size: 11px; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 3px; }
        .up { color: #00c853 !important; }
        .down { color: #ff5252 !important; }
        
        /* Sidebar Tab Refinement - KILL ALL GREEN BOXES */
        .stTabs [data-baseweb="tab-list"] {
            gap: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 2px; background-color: transparent !important;
        }
        .stTabs [data-baseweb="tab"] {
            height: 35px; background-color: transparent !important; border: none !important;
            padding: 0 5px !important; color: #848e9c !important; font-size: 13px !important;
            transition: all 0.2s; box-shadow: none !important;
        }
        .stTabs [aria-selected="true"] {
            color: #10d35e !important; border-bottom: 2px solid #10d35e !important;
            background-color: transparent !important; font-weight: 700 !important;
        }
        /* Aggressive strike on Streamlit's internal tab styling */
        .stTabs [data-baseweb="tab"] > div,
        .stTabs [data-baseweb="tab"] p,
        .stTabs [data-baseweb="tab"] span {
            background-color: transparent !important;
            background: transparent !important;
            border: none !important;
        }
        
        /* Ticker Button Reset - PURE TEXT FOR LISTS ONLY */
        .ticker-btn-wrapper button {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            text-align: left !important;
            color: #fff !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
            min-height: 0 !important;
            line-height: 1.2 !important;
        }
        .ticker-btn-wrapper button:hover {
            color: #fff !important;
            text-shadow: 0 0 10px #ff2d75;
            background: rgba(255, 45, 117, 0.15) !important;
            border-radius: 4px;
            padding-left: 5px !important;
            transition: all 0.2s ease;
        }
        
        /* Row Styling */
        .wl-row-container {
            padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-bottom: 16px; text-align: center;">
        <div style="font-size: 18px; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff2d55, #ff80ab); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px;">
            MITULAMA
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action Bar: Filter Input & Refresh
    s_col = st.columns([3, 1])
    with s_col[0]:
        filter_query = st.text_input(
            "Filter", 
            placeholder="Search", 
            label_visibility="collapsed",
            key="sidebar_filter"
        ).upper()
    with s_col[1]:
        if st.button("↻", help="Refresh Data", use_container_width=True, type="secondary"):
            # Don't clear global cache, only news/analysis
            get_news_sentiment.clear()
            get_crypto_stats.clear()
            clear_watchlist_cache()
            clear_cached_results()
            if 'watchlist_data_list' in st.session_state:
                del st.session_state.watchlist_data_list
            st.session_state.refresh_market = True 
            st.rerun()

    st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
    
    # Tabs for Watchlist / Gainer / Loser
    tab_wl, tab_gainer, tab_loser = st.tabs(["Watchlist", "Gainer", "Loser"])
    
    # --- WATCHLIST LOGIC ---

    # Load from cache or fetch new data
    if 'watchlist_data_list' not in st.session_state:
        # Try to load from cache first
        cached_watchlist = load_watchlist_cache()
        if cached_watchlist:
            st.session_state.watchlist_data_list = cached_watchlist
        else:
            # Generate list using Fast Info (Parallel) for Real-time accuracy
            with st.spinner("Loading Real-time Data..."):
                def fetch_ticker_info(t):
                    try:
                        coin = COIN_MAP.get(t.upper())
                        if not coin: return None
                        
                        return {
                            "id": coin.get('id', t.lower()),
                            "ticker": t.upper(),
                            "name": coin['name'],
                            "price": coin.get('current_price', 0) or 0,
                            "chg": coin.get('price_change_percentage_24h', 0) or 0,
                            "logo": coin['image']
                        }
                    except:
                        return None

                wl = []
                # Crypto names map (CoinGecko usually provides this, keeping it for custom overrides)
                names_map = {
                    "BTC": "Bitcoin", "ETH": "Ethereum", "USDT": "Tether",
                    "BNB": "Binance Coin", "SOL": "Solana", "XRP": "Ripple"
                }
                
                
                # Fetch Parallel (REMOVED: Overkill for memory lookup, using simple loop for speed)
                # with ThreadPoolExecutor(max_workers=30) as executor:
                #    results = list(executor.map(fetch_ticker_info, TICKERS))
                
                results = [fetch_ticker_info(t) for t in TICKERS]

                for res in results:
                    if res:
                        wl.append(res)
                
                st.session_state.watchlist_data_list = wl
                save_watchlist_cache(wl)
            
    # Helper for SVG Sparkline (Premium Reference Style)
    def make_sparkline(data, color):
        if not data: return ""
        width = 80
        height = 30
        min_y, max_y = min(data), max(data)
        # Pad range for visual headroom
        y_range = max_y - min_y if max_y != min_y else 1
        min_y -= y_range * 0.1
        max_y += y_range * 0.1
        y_range = max_y - min_y
        
        pts = []
        for i, val in enumerate(data):
            x = (i / (len(data)-1)) * width
            y = height - ((val - min_y) / y_range) * height
            pts.append(f"{x},{y}")
        polyline = " ".join(pts)
        
        # Add a dashed reference line
        ref_y = height / 2 + 2 
        
        return f'''
        <svg width="{width}" height="{height}" style="overflow:visible;">
            <line x1="0" y1="{ref_y}" x2="{width}" y2="{ref_y}" stroke="rgba(255,255,255,0.1)" stroke-width="1" stroke-dasharray="2,2" />
            <polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        '''

    # Apply Filter to Main List
    final_watchlist = st.session_state.watchlist_data_list
    if filter_query:
        final_watchlist = [
            item for item in final_watchlist 
            if filter_query in item['ticker'].upper() or filter_query in item['name'].upper()
        ]

    # Render Loop - Watchlist Tab
    with tab_wl:
        # If filtering, show all results. If not, respect limit.
        display_list = final_watchlist if filter_query else final_watchlist[:st.session_state.watchlist_limit]
        
        if not display_list:
            st.caption("No assets found.")
            
        for item in display_list:
            # Fallback for 'id' to fix KeyError
            coin_id = item.get('id', item['ticker'])
            # Layout: [Logo] [Ticker/Name] [Sparkline] [Price/Chg]
            # OLD: [1, 4, 3, 3] -> Price was wrapping
            # NEW: [1.3, 3.5, 2.2, 4.5] -> More space for Price, less for Sparkline
            r_col1, r_col2, r_col3, r_col4 = st.columns([1.3, 3.5, 2.2, 4.5])
            
            with r_col1:
                # Logo (Circular)
                st.markdown(f"""
                    <div style="width:28px; height:28px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05); margin-top:5px; border: 1px solid var(--border-pink);">
                        <img src="{item['logo']}" style="width:100%; height:100%; object-fit:contain;">
                    </div>
                """, unsafe_allow_html=True)
                
            with r_col2:
                # Ticker & Name 
                st.markdown('<div class="ticker-btn-wrapper">', unsafe_allow_html=True)
                if st.button(item['ticker'], key=f"btn_wl_{coin_id}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='wl-name' style='margin-top:-15px; color:#ff80ab;'>{item['name']}</div>", unsafe_allow_html=True)
                
            with r_col3:
                # Sparkline
                trend_color = "#00c853" if item['chg'] >= 0 else "#ff5252"
                trend_data = [
                    item['price'] * (1 + (random.uniform(0, 0.03) if item['chg'] < 0 else -random.uniform(0, 0.03)))
                    for _ in range(8)
                ]
                trend_data.append(item['price'])
                st.markdown(f"<div style='margin-top:5px;'>{make_sparkline(trend_data, trend_color)}</div>", unsafe_allow_html=True)
                
            with r_col4:
                # Price & Change
                is_up = item['chg'] >= 0
                color = "#00c853" if is_up else "#ff5252"
                arrow = "↗" if is_up else "↘"
                diff = abs(item['price'] * (item['chg']/100))
                
                st.markdown(f"""
                <div style="text-align: right; margin-top:2px;">
                    <div class="wl-price">{format_price(item['price'])}</div>
                    <div class="wl-chg" style="color:{color};">
                        {arrow} ({item['chg']:.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.03);'></div>", unsafe_allow_html=True)
        
        # Load More Button (Only if NOT filtering)
        if not filter_query and len(final_watchlist) > st.session_state.watchlist_limit:
            if st.button("Load More", use_container_width=True):
                st.session_state.watchlist_limit += 20
                st.rerun()
        
        st.caption(f"Showing {len(display_list)} of {len(final_watchlist)} assets")
        # Integrasi Global Stats di sidebar
        if 'market_stats_live' in st.session_state and st.session_state.market_stats_live:
            stats = st.session_state.market_stats_live
            st.caption(f"Global Market Cap: {stats['price']} ({stats['percent']})")
            st.caption(f"BTC Dominance: {stats['btc_d']}")
        else:
            st.caption("Crypto Market (Live)")
    
    with tab_gainer:
        # Filter out items with None in 'chg' and sort
        items_with_chg = [i for i in final_watchlist if i.get('chg') is not None and i.get('chg') > 0]
        # Sort logic: if filtering, maybe just show all valid gainers filtered? 
        # But 'final_watchlist' is already filtered. So just sort.
        gainers = sorted(items_with_chg, key=lambda x: x['chg'], reverse=True)
        # Limit to 10 only if NOT filtering
        if not filter_query:
            gainers = gainers[:10]
            
        if not gainers:
             st.info("No data")

        for item in gainers:
            coin_id = item.get('id', item['ticker'])
            r_col1, r_col2, r_col3, r_col4 = st.columns([1.3, 3.5, 2.2, 4.5])
            with r_col1:
                st.markdown(f"""
                    <div style="width:28px; height:28px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05); margin-top:5px; border: 1px solid var(--border-pink);">
                        <img src="{item['logo']}" style="width:100%; height:100%; object-fit:contain;">
                    </div>
                """, unsafe_allow_html=True)
            with r_col2:
                st.markdown('<div class="ticker-btn-wrapper">', unsafe_allow_html=True)
                if st.button(item['ticker'], key=f"btn_g_{coin_id}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='wl-name' style='margin-top:-15px; color:#ff80ab;'>{item['name']}</div>", unsafe_allow_html=True)
            with r_col3:
                trend_color = "#00c853"
                trend_data = [item['price'] * (1 - random.uniform(0, 0.05)) for _ in range(8)]
                trend_data.append(item['price'])
                st.markdown(f"<div style='margin-top:5px;'>{make_sparkline(trend_data, trend_color)}</div>", unsafe_allow_html=True)
            with r_col4:
                diff = abs(item['price'] * (item['chg']/100))
                st.markdown(f"""
                <div style="text-align: right; margin-top:2px;">
                    <div class="wl-price">{format_price(item['price'])}</div>
                    <div class="wl-chg" style="color:#00c853;">
                        ↗ ({item['chg']:.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.03);'></div>", unsafe_allow_html=True)
    
    # Loser Tab
    with tab_loser:
        items_with_chg_loser = [i for i in final_watchlist if i.get('chg') is not None]
        losers = sorted(items_with_chg_loser, key=lambda x: x['chg'])
        if not filter_query:
            losers = losers[:10]
            
        if not losers:
            st.info("No data available")
        for item in losers:
            coin_id = item.get('id', item['ticker'])
            r_col1, r_col2, r_col3, r_col4 = st.columns([1.3, 3.5, 2.2, 4.5])
            with r_col1:
                st.markdown(f"""
                    <div style="width:28px; height:28px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05); margin-top:5px; border: 1px solid var(--border-pink);">
                        <img src="{item['logo']}" style="width:100%; height:100%; object-fit:contain;">
                    </div>
                """, unsafe_allow_html=True)
            with r_col2:
                st.markdown('<div class="ticker-btn-wrapper">', unsafe_allow_html=True)
                if st.button(item['ticker'], key=f"btn_l_{coin_id}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='wl-name' style='margin-top:-15px; color:#ff80ab;'>{item['name']}</div>", unsafe_allow_html=True)
            with r_col3:
                is_up = item['chg'] >= 0
                trend_color = "#00c853" if is_up else "#ff5252"
                trend_data = [item['price'] * (1 + (random.uniform(0, 0.05) if not is_up else -random.uniform(0, 0.05))) for _ in range(8)]
                trend_data.append(item['price'])
                st.markdown(f"<div style='margin-top:5px;'>{make_sparkline(trend_data, trend_color)}</div>", unsafe_allow_html=True)
            with r_col4:
                is_up = item['chg'] >= 0
                color = "#00c853" if is_up else "#ff5252"
                arrow = "↗" if is_up else "↘"
                diff = abs(item['price'] * (item['chg']/100))
                st.markdown(f"""
                <div style="text-align: right; margin-top:2px;">
                    <div class="wl-price">{format_price(item['price'])}</div>
                    <div class="wl-chg" style="color:{color};">
                        {arrow} ({item['chg']:.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.03);'></div>", unsafe_allow_html=True)


        


# --- UI COMPONENT: TICKER TAPE (REAL DATA) ---
# Menggunakan 10 data teratas dari watchlist
@st.cache_data(ttl=300)
def render_ticker_tape(watchlist):
    items_html = ""
    for item in watchlist[:12]:
        chg = item.get('chg', 0) or 0
        color_class = "up" if chg >= 0 else "down"
        items_html += f'<div class="ticker__item">{item["ticker"]} <span class="{color_class}">{item["price"]:,}</span></div>'
    
    # Duplicate for infinite loop
    items_html += items_html
    
    return f"""
    <div class="ticker-wrap">
    <div class="ticker">
      {items_html}
    </div>
    </div>
    <style>
    .ticker-wrap {{
      width: 100%;
      overflow: hidden;
      background-color: #15191e;
      padding-left: 100%;
      box-sizing: content-box;
      border-bottom: 1px solid #2a2e39;
      height: 30px;
      line-height: 30px;
      margin-bottom: 10px;
    }}
    .ticker {{
      display: inline-block;
      white-space: nowrap;
      padding-right: 100%;
      box-sizing: content-box;
      animation-iteration-count: infinite;
      animation-timing-function: linear;
      animation-name: ticker;
      animation-duration: 60s;
    }}
    .ticker__item {{
      display: inline-block;
      padding: 0 2rem;
      font-size: 12px;
      color: #d1d4dc;
      font-weight: 600;
    }}
    .ticker__item .up {{ color: #00c853; }}
    .ticker__item .down {{ color: #ff5252; }}
    @keyframes ticker {{
      0% {{ transform: translate3d(0, 0, 0); }}
      100% {{ transform: translate3d(-100%, 0, 0); }}
    }}
    </style>
    """

if 'watchlist_data_list' in st.session_state:
    st.markdown(render_ticker_tape(st.session_state.watchlist_data_list), unsafe_allow_html=True)
else:
    # Fallback to static if no watchlist data yet
    st.markdown("""<div class="ticker-wrap"><div class="ticker">
      <div class="ticker__item">BTC <span class="up">95,400</span></div><div class="ticker__item">ETH <span class="up">3,300</span></div>
    </div></div>""", unsafe_allow_html=True)


# --- MAIN LAYOUT (Tabs: Chart, Financials, Profile) ---
current_symbol = st.session_state.ticker_selector

# --- CRYPTO GLOBAL DATA ---
@st.cache_data(ttl=300)
def get_global_crypto_data():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/global")
        return res.json()['data']
    except:
        return None

global_data = get_global_crypto_data()
btp_dominance = global_data['market_cap_percentage']['btc'] if global_data else 50.0

logo_url = COIN_MAP.get(current_symbol, {}).get('image', '')

if global_data:
    mc_change = global_data['market_cap_change_percentage_24h_usd']
    ihsg_p = f"${global_data['total_market_cap']['usd']/1e12:.2f}T"
    ihsg_c = f"{mc_change:+.2f}%"
    ihsg_pct = f"{btp_dominance:.1f}% BTC.D"
    ihsg_color = "#00c853" if mc_change >= 0 else "#ff5252"
    market_sentiment = "BULLISH" if mc_change >= 0 else "BEARISH"
    sentiment_bg = "rgba(0, 200, 83, 0.1)" if mc_change >= 0 else "rgba(255, 82, 82, 0.1)"
    sentiment_color = "#00c853" if mc_change >= 0 else "#ff5252"
else:
    ihsg_p = "$2.5T"
    ihsg_c = "+1.2%"
    ihsg_pct = "52% BTC.D"
    ihsg_color = "#00c853"
    market_sentiment = "NEUTRAL"
    sentiment_bg = "rgba(255, 255, 255, 0.05)"
    sentiment_color = "#848e9c"

market_status_html = '<span style="background: rgba(0, 200, 83, 0.1); color: #00c853; padding: 5px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; border: 1px solid rgba(0, 200, 83, 0.2); letter-spacing: 0.5px; margin-left: 8px;">24/7 MARKET</span>'

header_html = f"""
<div class="main-header" style="background: rgba(30, 34, 45, 0.7); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); padding: 10px 20px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; margin-top: -12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; gap: 12px;">
        <img src="{logo_url}" onerror="this.style.display='none'" style="width: 36px; height: 36px; border-radius: 6px; object-fit: contain; background: rgba(255,255,255,0.05); padding: 4px;" alt="{current_symbol}">
        <div style="display: flex; flex-direction: column; gap: 2px;">
            <span style="font-size: 20px; font-weight: 800; color: #fff; letter-spacing: 0.5px; line-height: 1;">{current_symbol}</span>
            <span style="font-size: 11px; color: #848e9c; font-weight: 500;">BINANCE | CRYPTO</span>
        </div>
        {market_status_html}
    </div>
    <div class="header-right" style="display: flex; align-items: center; gap: 20px;">
        <!-- BACK TO LIST BUTTON -->
        <a href="#card-{current_symbol}" class="mobile-hide" style="text-decoration: none; background: rgba(255, 255, 255, 0.05); color: #848e9c; padding: 8px 16px; border-radius: 4px; font-size: 11px; font-weight: 700; border: 1px solid rgba(255, 255, 255, 0.1); transition: all 0.2s; display: flex; align-items: center; gap: 6px;">
            Kembali ke Daftar
        </a>
        <div style="text-align: right;">
            <div style="font-size: 10px; color: #848e9c; font-weight: 600; text-transform: uppercase; margin-bottom: 2px;">Market Cap</div>
            <div style="font-size: 15px; font-weight: 700; color: #fff;">{ihsg_p} <span style="color: {ihsg_color}; font-size: 11px; margin-left: 2px;">{ihsg_c}</span></div>
        </div>
        <div style="background: {sentiment_bg}; border: 1px solid {sentiment_color}44; padding: 6px 12px; border-radius: 4px; text-align: center;">
            <div style="font-size: 9px; color: #848e9c; font-weight: 600; text-transform: uppercase;">Sentiment</div>
            <div style="font-size: 11px; font-weight: 800; color: {sentiment_color};">{market_sentiment}</div>
        </div>
    </div>
</div>
"""

st.markdown(header_html, unsafe_allow_html=True)


# Main Content Tabs - PERSISTENT
main_tabs_options = ["Chart", "Asset Stats", "Professional Analyst Advisor"]
if 'main_active_tab' not in st.session_state or st.session_state.main_active_tab not in main_tabs_options:
    st.session_state.main_active_tab = "Chart"

main_active_tab = st.radio(
    "Main Content Tabs",
    main_tabs_options,
    horizontal=True,
    key="main_active_tab",
    label_visibility="collapsed"
)


if main_active_tab == "Chart":
    # Layout: Chart on Left, Order Book on Right
    c_chart, c_orderbook = st.columns([3, 1])

    with c_chart:
        # TradingView Chart
        timeframe_map = {
            "Daily": "D", "Weekly": "W", "Monthly": "M",
            "4 Hours": "240", "1 Hour": "60", "30 Minutes": "30", "5 Minutes": "5"
        }
        if 'chart_timeframe' not in st.session_state: st.session_state.chart_timeframe = "Daily"
        
        current_tf_code = timeframe_map[st.session_state.chart_timeframe]
        
        # --- TRADINGVIEW SYMBOL MAPPING (Fix for 1000-prefix coins) ---
        # Memecoins often use "1000" prefix on Binance Perpetual Futures
        prec_symbol = current_symbol
        zero_heavy_coins = ['PEPE', 'SHIB', 'BONK', 'FLOKI', 'LUNC', 'XEC', 'RATS', 'SATS']
        if current_symbol in zero_heavy_coins:
            prec_symbol = f"1000{current_symbol}"
            
        # Use BINANCE Perpetual Futures to ensure all assets load correctly
        tv_symbol = f"BINANCE:{prec_symbol}USDT.P"
        
        st.components.v1.html(
            f"""
            <div class="tradingview-widget-container" style="height: 600px; width: 100%; border-radius: 0px; overflow: hidden; border: none; margin-top: -15px;">
            <div id="tradingview_chart" style="height: 100%; width: 100%;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
                "autosize": true,
                "fullscreen": true,
                "symbol": "{tv_symbol}",
                "interval": "{current_tf_code}",
                "timezone": "Asia/Jakarta",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "study_templates": true,
                "container_id": "tradingview_chart",
                "toolbar_bg": "#1e222d",
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "details": true,
                "hotlist": true,
                "calendar": false,
                "show_popup_button": true,
                "popup_width": "1000",
                "popup_height": "650",
                "withdateranges": true,
                "enabled_features": ["header_fullscreen_button", "use_localstorage_for_settings", "items_favoriting", "save_chart_properties_to_local_storage"],
                "disabled_features": []
            }});
            </script>
            </div>
            """,
            height=580,
        )

        st.markdown("---")
        # --- GOOGLE ADSENSE AREA ---

        try:
            # For Crypto, we use the CoinGecko data from COIN_MAP
            coin_info = COIN_MAP.get(current_symbol, {})
            
            st.markdown(f"### {coin_info.get('name', current_symbol)}")
            
            p1, p2 = st.columns([2, 1])
            with p1:
                st.caption(f"Global Rank: **#{coin_info.get('market_cap_rank', '-')}**")
                # Note: CoinGecko small API doesn't have description in markets endpoint
                # But it has it in the detailed endpoint which we'll show in Stats tab
                st.write(f"Asset digital {coin_info.get('name')} saat ini diperdagangkan pada harga ${coin_info.get('current_price'):,}.")
            with p2:
                st.markdown("####  Market Info")
                st.markdown(f"**ATH:** ${coin_info.get('ath', 0):,}")
                st.markdown(f"**Circulating Supply:** {coin_info.get('circulating_supply', 0):,.0f}")
                
        except:
            st.warning("Profile data unavailable.")


    with c_orderbook:
        # --- DATA PREPARATION ---
        coin_info = COIN_MAP.get(current_symbol, {})
        sb_price = coin_info.get('current_price', 0) or 0
        sb_chg_pct = coin_info.get('price_change_percentage_24h', 0) or 0
        
        # Calculate derived metrics
        sb_prev = sb_price / (1 + (sb_chg_pct/100)) if sb_chg_pct != -100 else sb_price
        sb_open = sb_prev
        sb_high = coin_info.get('high_24h', sb_price)
        sb_low = coin_info.get('low_24h', sb_price)
        sb_vol = coin_info.get('total_volume', 0)
        sb_val = sb_vol * sb_price
        sb_ara = sb_price * 1.10
        sb_arb = sb_price * 0.90
        
        def generate_mock_order_book(center_price):
            rows = []
            for i in range(8):
                bid_p = center_price * (1 - (i * 0.001))
                bid_vol = random.uniform(0.1, 50)
                off_p = center_price * (1 + ((i+1) * 0.001))
                off_vol = random.uniform(0.1, 50)
                rows.append({
                    "bid_vol": round(bid_vol, 4),
                    "bid_p": round(bid_p, 4),
                    "off_p": round(off_p, 4),
                    "off_vol": round(off_vol, 4)
                })
            return rows

        def generate_mock_running_trade(ticker_code, center_price):
            trades = []
            for i in range(15):
                t_time = time.strftime("%H:%M:%S")
                p_offset = random.uniform(-0.002, 0.002)
                t_price = center_price * (1 + p_offset)
                t_action = "BUY" if p_offset >= 0 else "SELL"
                t_color = "#00c853" if p_offset > 0 else "#ff5252"
                t_size = round(random.uniform(0.01, 2.5), 4)
                trades.append({
                    "time": t_time,
                    "code": ticker_code,
                    "price": round(t_price, 4),
                    "action": t_action,
                    "color": t_color,
                    "size": t_size
                })
            return trades

        mock_ob = generate_mock_order_book(sb_price)
        mock_rt = generate_mock_running_trade(current_symbol, sb_price)

        # --- PRO STATS HEADER ---
        # Helper number format
        def fmt_num(n):
            if n >= 1e9: return f"{n/1e9:.1f}B"
            if n >= 1e6: return f"{n/1e6:.1f}M"
            if n >= 1e3: return f"{n/1e3:.1f}K"
            return str(int(n))

        st.markdown(f"""<div style="background: #1e222d; border-radius: 4px; padding: 8px; margin-bottom: 4px; font-family: 'Inter', sans-serif; font-size: 11px;"><div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; color: #d1d4dc;"><div>Open <span style="float:right; color:#e0e0e0;">{sb_open:,}</span></div><div>Prev <span style="float:right; color:#e0e0e0;">{sb_prev:,}</span></div><div>Vol <span style="float:right; color:#00c853;">{fmt_num(sb_vol)}</span></div><div>High <span style="float:right; color:#00c853;">{sb_high:,}</span></div><div>Low <span style="float:right; color:#ff5252;">{sb_low:,}</span></div><div>Val <span style="float:right; color:#00c853;">{fmt_num(sb_val)}</span></div></div></div>""", unsafe_allow_html=True)

        # --- PRO ORDER BOOK ---
        st.markdown("###  Order Book")
        
        # Build Table Rows HTML (Flattened to avoid Markdown Code Block issues)
        ob_rows_html = ""
        for row in mock_ob:
             ob_rows_html += f"""<tr style="border-bottom: 1px solid #1e222d;"><td style="color:#d1d4dc; text-align:right; padding:4px;">{row['bid_vol']}</td><td style="color:#00c853; text-align:right; padding:4px;">{row['bid_p']}</td><td style="color:#ff5252; text-align:left; padding:4px;">{row['off_p']}</td><td style="color:#d1d4dc; text-align:left; padding:4px;">{row['off_vol']}</td></tr>"""
             
        st.markdown(f"""
<div style="background: #1e222d; border: 1px solid #2a2e39; border-radius: 4px; overflow: hidden; font-family: 'Inter', sans-serif; font-size: 10px;">
<div style="max-height: 480px; overflow-y: auto;">
<table style="width: 100%; border-collapse: separate; border-spacing: 0;">
<thead style="background: #2a2e39; color: #848e9c; position: sticky; top: 0; z-index: 5;">
<tr>
<th style="padding: 6px; text-align: right; background: #2a2e39;">Size</th>
<th style="padding: 6px; text-align: right; background: #2a2e39;">Bid</th>
<th style="padding: 6px; text-align: left; background: #2a2e39;">Ask</th>
<th style="padding: 6px; text-align: left; background: #2a2e39;">Size</th>
</tr>
</thead>
<tbody>
{ob_rows_html}
</tbody>
</table>
</div>
</div>
""", unsafe_allow_html=True)
        
        # --- PRO RUNNING TRADE ---
        st.markdown("<div style='margin-top: 15px; font-weight: 700; font-size: 14px;'>Running Trade</div>", unsafe_allow_html=True)
        
        # Build Trade Rows HTML (Flattened)
        rt_rows_html = ""
        for t in mock_rt:
             rt_rows_html += f"""<tr><td style="color:#d1d4dc; padding:4px 6px;">{t['time']}</td><td style="color:{t['color']}; text-align:center;">{t['code']}</td><td style="color:{t['color']}; text-align:right;">{t['price']}</td><td style="color:{t['color']}; text-align:center;">{t['action']}</td><td style="color:#d1d4dc; text-align:right;">{t['size']}</td></tr>"""
             
        st.markdown(f"""
<div style="background: #1e222d; border: 1px solid #2a2e39; border-radius: 4px; padding: 0; min-height: 180px; overflow: hidden;">
<div style="max-height: 300px; overflow-y: auto;">
<table style="width: 100%; border-collapse: separate; border-spacing: 0; font-family: 'Inter', sans-serif; font-size: 10px;">
<thead style="background: #1e222d; border-bottom: 1px solid #2a2e39; color: #848e9c; position: sticky; top: 0; z-index: 5;">
<tr>
<th style="padding: 6px; text-align: left; background: #1e222d;">Time</th>
<th style="padding: 6px; text-align: center; background: #1e222d;">Asset</th>
<th style="padding: 6px; text-align: right; background: #1e222d;">Price</th>
<th style="padding: 6px; text-align: center; background: #1e222d;">Side</th>
<th style="padding: 6px; text-align: right; background: #1e222d;">Size</th>
</tr>
</thead>
<tbody>
{rt_rows_html}
</tbody>
</table>
</div>
</div>
""", unsafe_allow_html=True)

    # --- MARKET SCREENER & AI ANALYSIS ---
    st.markdown('<div id="scanner-results"></div>', unsafe_allow_html=True)
    st.write("")
    st.markdown("### Market Screener & AI Analysis")

    # Control Bar
    b1, b2, b3 = st.columns([2, 1, 6])
    with b1:
        if st.button("RUN SCREENER", key="run_scr_main", use_container_width=True, type="primary"):
            st.session_state.run_screener = True
    with b2:
        if st.button("Clear", key="clear_scr_main", use_container_width=True):
            st.session_state.scan_results = None
            st.session_state.last_update = None
            clear_cached_results()  # Clear cache file
            st.cache_data.clear()   # PURGE STREAMLIT DATA CACHE (News, etc.)
            st.rerun()

    st.markdown("---")

    # --- SCANNER LOGIC ---
    # Load from cache if available (check 5-min expiration)
    if 'scan_results' not in st.session_state:
        cached_data = load_cached_results()
        if cached_data:
            st.session_state.scan_results = cached_data['results']
            st.session_state.last_update = cached_data['timestamp']
        else:
            st.session_state.scan_results = None
    
    # If results are showing, update heartbeat to prevent expiration while using
    if st.session_state.scan_results is not None:
        update_cache_heartbeat()

    # Logic triggered by Sidebar Button or Local Button
    if st.session_state.get('run_screener', False):
        st.session_state.run_screener = False # Reset trigger
        
        # Show Full Screen Overlay
        loading_placeholder = st.empty()
        loading_placeholder.markdown(custom_loading_overlay("LOADING..."), unsafe_allow_html=True)
        
        # Artificial delay for cool effect (Game feel)
        time.sleep(1.5)
        
        try:
            loading_placeholder.markdown(custom_loading_overlay("LOADING..."), unsafe_allow_html=True)
            
            # PHASE 1: Tier 1 Filtering (Technical Filter using CoinGecko Data)
            promising_tickers = []
            results = [] 
            
            p_bar = st.progress(0, text="Menganalisis crypto potensial...")
            
            # Use already fetched CRYPTO_DATA for fast scanning
            for i, coin in enumerate(CRYPTO_DATA):
                # Update overlay progress
                prog_pct = int((i + 1) / len(CRYPTO_DATA) * 100)
                if i % 10 == 0 or i == len(CRYPTO_DATA) - 1:
                    loading_placeholder.markdown(custom_loading_overlay(f"ANALYZING... ({coin['symbol'].upper()})", progress=prog_pct), unsafe_allow_html=True)
                
            # PHASE 1: Tier 1 Filtering (Smart Screening)
            promising_tickers = []
            
            p_bar = st.progress(0, text="Menganalisis crypto potensial...")
            
            # Use already fetched CRYPTO_DATA and apply 5-Pillar filtering
            for i, coin in enumerate(CRYPTO_DATA):
                # Update overlay progress
                prog_pct = int((i + 1) / len(CRYPTO_DATA) * 100)
                if i % 15 == 0 or i == len(CRYPTO_DATA) - 1:
                    loading_placeholder.markdown(custom_loading_overlay(f"ANALYZING... ({coin['symbol'].upper()})", progress=prog_pct), unsafe_allow_html=True)
                
                # 5-Pillar Screening Logic for Tier 1:
                price_chg = abs(coin.get('price_change_percentage_24h', 0) or 0)
                vol_mcap_ratio = coin.get('total_volume', 0) / (coin.get('market_cap', 1) or 1)
                ath_chg = abs(coin.get('ath_change_percentage', 0) or 0)
                
                # Filter: Top 30 assets OR High Vol (>2.5%) OR Undervalued gem (>70% drop) OR High Activity (Vol/MCap > 0.08)
                if i < 30 or price_chg > 2.5 or (ath_chg > 70 and vol_mcap_ratio > 0.05) or vol_mcap_ratio > 0.12:
                    promising_tickers.append(coin['symbol'].upper())
                
                p_bar.progress((i + 1) / len(CRYPTO_DATA))
            
            # Limit Deep Dive to max 30 assets to prevent freezing
            if len(promising_tickers) > 30:
                promising_tickers = promising_tickers[:30]
            
            p_bar.empty()
            
            # Deep Dive
            if promising_tickers:
                total_assets = len(promising_tickers)
                st.info(f"Menemukan {total_assets} asset potensial. Melakukan Deep Analysis...")
                final_results = []
                
                with ThreadPoolExecutor(max_workers=25) as executor:
                    futures = {executor.submit(analyze_crypto, t): t for t in promising_tickers}
                    
                    p_bar_deep = st.progress(0)
                    for idx, future in enumerate(futures):
                        res = future.result()
                        if res:
                            final_results.append(res)
                        
                        prog_deep = int((idx + 1) / len(promising_tickers) * 100)
                        loading_placeholder.markdown(custom_loading_overlay(f"DEEP ANALYSIS {idx+1}/{len(promising_tickers)}", progress=prog_deep), unsafe_allow_html=True)
                        p_bar_deep.progress((idx + 1) / len(promising_tickers))
                    p_bar_deep.empty()
                results = final_results
            
            if results:
                st.session_state.scan_results = pd.DataFrame(results)
                st.session_state.last_update = time.strftime("%H:%M")
                
                # Filter logic
                final_df = st.session_state.scan_results
                high_quality_count = len(final_df[final_df['Status'] != 'HOLD'])
                
                # Save to cache
                save_cached_results(st.session_state.scan_results, st.session_state.last_update)
                
                st.success(f"Scan Completed. Found {high_quality_count} High-Potential assets.")
            else:
                st.warning("No data fetched or no match found.")
                st.session_state.scan_results = None

        except Exception as e:
            st.error(f"Scanner Error: {str(e)}")
            
        finally:
            # Clear overlay
            loading_placeholder.empty()

    # Display Logic
    if st.session_state.scan_results is not None:
        df = st.session_state.scan_results
        
        # Call the Fragmented Analysis View (Charts + Interactive Filters + Result Grid)
        render_market_analysis(df)
        
elif main_active_tab == "Asset Stats":
    st.markdown("## Statistik Asset")
    st.markdown("---")
    
    try:
        coin = COIN_MAP.get(current_symbol)
        if not coin:
            st.warning("Data statistik tidak tersedia untuk asset ini.")
        else:
            # Asset Info Header
            col_info1, col_info2 = st.columns([2, 1])
            with col_info1:
                st.markdown(f"### {coin['name']} ({coin['symbol'].upper()})")
                st.caption(f"**Market Cap Rank:** #{coin.get('market_cap_rank', 'N/A')}")
            with col_info2:
                market_cap = coin.get('market_cap', 0)
                st.metric("Market Cap", f"${market_cap/1e9:.2f}B")
            
            st.markdown("---")
            
            # Key Metrics
            st.markdown("### Market Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Price", f"${coin['current_price']:,}", f"{coin['price_change_percentage_24h']:+.2f}%")
            with col2:
                st.metric("24h High", f"${coin.get('high_24h', 0):,}")
            with col3:
                st.metric("24h Low", f"${coin.get('low_24h', 0):,}")
            with col4:
                st.metric("All Time High", f"${coin.get('ath', 0):,}")
            
            st.markdown("---")
            
            # Supply Info
            st.markdown("### Supply Information")
            s_col1, s_col2, s_col3 = st.columns(3)
            with s_col1:
                st.metric("Circulating Supply", f"{coin.get('circulating_supply', 0):,.0f}")
            with s_col2:
                st.metric("Total Supply", f"{coin.get('total_supply', 0) or 0:,.0f}")
            with s_col3:
                st.metric("Max Supply", f"{coin.get('max_supply', 0) or 0:,.0f}")
        
            # Optional: Add technical indicators here if needed
        
            # Description
            st.markdown("---")
            st.markdown("### Asset Description")
            description = coin.get('description', {}).get('en', 'Tidak ada deskripsi tersedia.')
            if len(description) > 500:
                st.write(description[:500] + "...")
            else:
                st.write(description)
                
    except Exception as e:
        st.error(f"Gagal memuat statistik asset: {str(e)}")

elif main_active_tab == "Professional Analyst Advisor":
    st.markdown(f"## Penasehat Analis Professional")
    st.caption("Tanyakan apapun tentang crypto dan dapatkan penjelasan berdasarkan analisis teknikal & market buzz.")
    st.markdown("---")
    
    # Initialize chat history
    if 'advisor_chat_history' not in st.session_state:
        st.session_state.advisor_chat_history = []
    
    # Query Input - Compact Layout
    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        query = st.text_input(
            "Cari Kode Crypto (contoh: BTC, ETH)", 
            placeholder="Ketik kode...", 
            key="advisor_query",
            label_visibility="collapsed"
        )
    with q_col2:
        ask_btn = st.button("Tanya Analis", use_container_width=True, type="primary")
    
    if ask_btn and query:
        ticker_query = query.upper().strip()
        
        # Map IHSG query
        if ticker_query == "IHSG":
            ticker_query = "^JKSE"
            
        # Check if query is a ticker code or a general question
        is_ticker_query = len(ticker_query.split()) == 1 and not any(word in ticker_query.lower() for word in ['apa', 'kenapa', 'bagaimana', 'kapan', 'dimana', 'berapa', '^'])
        
        if ticker_query == "^JKSE": 
            is_ticker_query = True
            
        if is_ticker_query:
            # Ticker-specific analysis
            with st.spinner(f"Menganalisis {ticker_query}..."):
                data = analyze_crypto(ticker_query)
                
                if data:
                    # Store in chat history
                    st.session_state.advisor_chat_history.append({
                        'type': 'ticker_analysis',
                        'query': query,
                        'data': data
                    })
                    
                    st.markdown(f"### Analisis Untuk: {data['Name']} ({data['Ticker']})")
                    
                    # Get crypto metrics from COIN_MAP
                    coin = COIN_MAP.get(data['Ticker'], {})
                    current_price = data['Price']
                    price_change_1d = data['Change %']
                    
                    # Placeholder for technicals
                    current_rsi = 65 if "BULLISH" in data['Status'] else (35 if "BEARISH" in data['Status'] else 50)
                    volume_ratio = 1.5 if "VOLUME" in data['Status'] else 1.0
                    
                    # Recommendation Logic
                    status = data['Status']
                    recommendation = "LAYAK BELI" if any(s in status for s in ["MOMENTUM", "CORE", "BULLISH"]) else ("PANTAU" if "WATCHLIST" in status else "TUNGGU (HOLD)")
                    rec_color = "#00c853" if "LAYAK" in recommendation else ("#2962ff" if "PANTAU" in recommendation else "#ff5252")
                    
                    # Display Recommendation
                    st.markdown(f"""
                    <div style="background: {rec_color}22; border: 1px solid {rec_color}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <div style="font-size: 14px; color: #848e9c; font-weight: 600;">REKOMENDASI ANALIS:</div>
                        <div style="font-size: 28px; font-weight: 800; color: {rec_color};">{recommendation}</div>
                        <div style="font-size: 14px; color: #d1d4dc; margin-top: 10px;">Status Sistem: <b>{status}</b></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Technical & Sentiment Section
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("#### 📈 Market Stats")
                        st.markdown(f"**Rank:** #{coin.get('market_cap_rank', 'N/A')}")
                        st.markdown(f"**1D Change:** {price_change_1d:+.2f}%")
                    with col2:
                        st.markdown("#### ⚡ Momentum")
                        rsi_text = "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Neutral")
                        st.markdown(f"**RSI Index:** {current_rsi:.1f} ({rsi_text})")
                        st.markdown(f"**Volume:** {volume_ratio:.1f}x (Avg)")
                    with col3:
                        st.markdown("#### 💬 Sentiment")
                        st.markdown(f"**Score:** {data['News Score']}%")
                        st.markdown(f"**Buzz:** {data['Social Buzz']}%")
                    
                    st.markdown("---")
                    
                    # Detailed Analysis
                    with st.container(border=True):
                        st.markdown("#### 📝 Penjelasan Lengkap")
                        
                        explanation = f"""
**Analisis Market:**

**{data['Name']} ({data['Ticker']})** saat ini menunjukkan status **{data['Status']}**. Dengan harga saat ini di **${current_price:,.2f}**, asset ini memiliki perubahan harian sebesar **{price_change_1d:+.2f}%**.

**Kondisi Teknis & Sentiment:**
- **Momentum:** RSI berada di level **{current_rsi:.1f}**, menunjukkan kondisi market yang **{rsi_text.lower()}**.
- **Aktivitas Volume:** Terjadi aktivitas trading sebesar **{volume_ratio:.1f}x** dari rata-rata normal.
- **Sentimen Media:** Memiliki skor **{data['News Score']}%**. {data['Analysis']}

**Kesimpulan Strategis:**
{'Asset ini memiliki fundamental/momentum yang kuat untuk dipertimbangkan sebagai entry point.' if "LAYAK" in recommendation else 'Asset ini sebaiknya dipantau terlebih dahulu (watchlist) hingga terjadi breakout volume atau konfirmasi trend.'}
                        """
                        st.markdown(explanation)
                    
                    # Price Targets
                    st.markdown("#### 🎯 Target Harga & Risk Management")
                    resistance_1 = current_price * 1.10
                    resistance_2 = current_price * 1.25
                    support = current_price * 0.90
                    
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 15px; border-radius: 4px; border: 1px solid #2a2e39;">
                            <div style="font-size: 12px; color: #848e9c; margin-bottom: 12px; font-weight: 600;">📈 TARGET PROFIT:</div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Target 1 (Konservatif):</span> <span style="color:#00c853; font-weight:700;">${resistance_1:,.2f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Target 2 (Agresif):</span> <span style="color:#00c853; font-weight:700;">${resistance_2:,.2f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_t2:
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 15px; border-radius: 4px; border: 1px solid #2a2e39;">
                            <div style="font-size: 12px; color: #848e9c; margin-bottom: 12px; font-weight: 600;">🛡️ RISK MANAGEMENT:</div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Stop Loss:</span> <span style="color:#ff5252; font-weight:700;">${support:,.2f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Risk/Reward Ratio:</span> <span style="color:#ffa726; font-weight:700;">1:2.5</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Update ticker for chart
                    st.session_state.advisor_ticker = data['Ticker']
                    st.session_state.collapse_sidebar = True
                else:
                    st.error("Asset tidak ditemukan atau data tidak mencukupi. Pastikan kode crypto benar (misal: BTC, ETH).")
        
        else:
            # General question - provide educational response
            st.markdown("### 💡 Jawaban Analis")
            
            # Simple keyword-based responses (can be enhanced with actual AI/LLM)
            query_lower = query.lower()
            
            response = ""
            
            if any(word in query_lower for word in ['rsi', 'relative strength']):
                response = """
**Apa itu RSI (Relative Strength Index)?**

RSI adalah indikator momentum yang mengukur kecepatan dan perubahan pergerakan harga. RSI bergerak antara 0-100.

**Cara Membaca RSI:**
- **RSI > 70**: Kondisi Overbought (Jenuh Beli) - Harga mungkin akan koreksi
- **RSI < 30**: Kondisi Oversold (Jenuh Jual) - Peluang untuk beli
- **RSI 30-70**: Kondisi Normal

**Strategi Trading:**
1. Beli ketika RSI keluar dari zona oversold (<30) dan mulai naik
2. Jual ketika RSI masuk zona overbought (>70)
3. Perhatikan divergence antara harga dan RSI untuk sinyal reversal

**Tips:** Jangan gunakan RSI sendirian, kombinasikan dengan indikator lain seperti MA dan Volume.
                """
            
            elif any(word in query_lower for word in ['market cap', 'kapitalisasi']):
                response = """
**Apa itu Market Cap?**

Market Cap (Kapitalisasi Pasar) adalah total nilai pasar dari seluruh supply koin yang beredar.

**Cara Menghitung:**
Market Cap = Harga Saat Ini × Circulating Supply

**Interpretasi:**
- **Large Cap (> $10B)**: Lebih stabil, likuiditas tinggi (Blue Chip)
- **Mid Cap ($1B - $10B)**: Potensi pertumbuhan moderat dengan risiko menengah
- **Small Cap (< $1B)**: High Risk, High Reward - Sangat volatil

**Mengapa Penting?**
Market Cap menunjukkan dominasi dan ukuran relatif sebuah asset di dalam ekosistem crypto secara keseluruhan.
                """
            
            elif any(word in query_lower for word in ['roe', 'return on equity']):
                response = """
**Apa itu ROE (Return on Equity)?**

ROE mengukur seberapa efisien perusahaan menghasilkan profit dari modal pemegang saham.

**Cara Menghitung:**
ROE = (Laba Bersih / Ekuitas Pemegang Saham) × 100%

**Interpretasi:**
- **ROE > 15%**: Excellent - Manajemen sangat efisien
- **ROE 10-15%**: Good - Kinerja baik
- **ROE < 10%**: Weak - Perlu evaluasi

**Mengapa Fundamental Penting:**
1. Menunjukkan kekuatan ekonomi dari project/asset
2. Membandingkan efisiensi dan target pengembangan project
3. Tim yang konsisten = manajemen berkualitas

**Tips:** Cari asset dengan kapitalisasi pasar (Market Cap) yang kuat dan tim pengembang yang aktif.
                """
            
            elif any(word in query_lower for word in ['volume', 'vol']):
                response = """
**Mengapa Volume Trading Penting?**

Volume menunjukkan jumlah asset yang diperdagangkan dalam periode tertentu. Volume adalah konfirmasi dari pergerakan harga.

**Prinsip Dasar:**
- **Volume Tinggi + Harga Naik** = Trend naik kuat (Bullish)
- **Volume Tinggi + Harga Turun** = Trend turun kuat (Bearish)
- **Volume Rendah** = Pergerakan tidak terkonfirmasi, bisa false signal

**Volume Ratio:**
- **> 1.5x**: Akumulasi kuat, whales/institusi masuk
- **0.8-1.5x**: Normal
- **< 0.8x**: Minat lemah

**Strategi:**
1. Cari breakout dengan volume tinggi untuk konfirmasi
2. Hindari trading saat volume rendah (likuiditas buruk)
3. Perhatikan volume spike - bisa jadi ada news/rumor
                """
            
            elif any(word in query_lower for word in ['moving average', 'ma', 'ema']):
                response = """
**Apa itu Moving Average (MA)?**

Moving Average adalah rata-rata harga dalam periode tertentu yang membantu mengidentifikasi trend.

**Jenis MA:**
- **MA5**: Trend jangka sangat pendek (1 minggu)
- **MA20**: Trend jangka pendek (1 bulan)
- **MA50**: Trend jangka menengah (2.5 bulan)
- **MA200**: Trend jangka panjang (1 tahun)

**Cara Membaca:**
- Harga di atas MA = Bullish
- Harga di bawah MA = Bearish
- Golden Cross (MA50 potong MA200 ke atas) = Sinyal beli kuat
- Death Cross (MA50 potong MA200 ke bawah) = Sinyal jual kuat

**Strategi Trading:**
1. Beli ketika harga bounce dari MA20/MA50
2. Jual ketika harga break down MA20/MA50
3. Gunakan MA sebagai support/resistance dinamis
                """
            
            elif any(word in query_lower for word in ['support', 'resistance', 'sr']):
                response = """
**Apa itu Support dan Resistance?**

**Support** adalah level harga dimana tekanan beli cukup kuat untuk menghentikan penurunan harga.
**Resistance** adalah level harga dimana tekanan jual cukup kuat untuk menghentikan kenaikan harga.

**Cara Mengidentifikasi:**
1. Lihat level harga yang berulang kali ditolak (rejected)
2. Perhatikan high/low sebelumnya
3. Gunakan round numbers (misal: 1000, 5000, 10000)

**Strategi Trading:**
- **Buy at Support**: Beli ketika harga mendekati support dengan konfirmasi volume
- **Sell at Resistance**: Jual ketika harga mendekati resistance
- **Breakout**: Jika harga break resistance dengan volume tinggi, bisa lanjut naik
- **Breakdown**: Jika harga break support, bisa lanjut turun

**Penting:** Support yang ditembus akan menjadi resistance baru, begitu juga sebaliknya.
                """
            
            elif any(word in query_lower for word in ['kapan', 'waktu', 'timing']):
                response = """
**Kapan Waktu Terbaik untuk Beli/Jual Crypto?**

**Waktu Terbaik Beli:**
1. **Saat Koreksi Pasar** - Beli saat pasar "dipping" tapi fundamental asset masih bagus
2. **Breakout dengan Volume** - Harga break resistance dengan volume tinggi
3. **RSI Oversold** - RSI < 30 dan mulai rebound (Peluang Rebound)
4. **Golden Cross** - MA50 potong MA200 ke atas (Trend Bullish Jangka Panjang)
5. **Berita Positif** - Listing baru, partnership besar, upgrade jaringan, dll

**Waktu Terbaik Jual:**
1. **Target Profit Tercapai** - Sudah naik sesuai target (misal 20-50%)
2. **RSI Overbought** - RSI > 70 dan mulai jenuh beli
3. **Break Support** - Harga break support penting (Signal Exit)
4. **Death Cross** - MA50 potong MA200 ke bawah
5. **Berita Negatif** - Hack, masalah regulasi, tim pengembang bermasalah, dll

**Tips:** Jangan FOMO (Fear of Missing Out), ambil profit bertahap (Partial Sell). Gunakan stop loss untuk proteksi modal.
                """
            
            elif any(word in query_lower for word in ['diversifikasi', 'portofolio']):
                response = """
**Pentingnya Diversifikasi Portofolio**

**Apa itu Diversifikasi?**
Menyebar investasi ke berbagai tipe asset untuk mengurangi risiko.

**Prinsip Diversifikasi:**
1. **Don't put all eggs in one basket**
2. **Alokasi Ideal:**
   - 50% Top Tier Crypto (BTC, ETH)
   - 30% Mid Cap/Narratives (AI, DePIN, RWA)
   - 10% Small Cap/Gems
   - 10% Stablecoin (USDT/USDC) untuk serok dip

**Diversifikasi Sektor:**
- Layer 1 / Layer 2
- AI & Big Data
- DeFi / DEX
- Gaming / Metaverse
- RWA (Real World Assets)

**Tips:** Review portofolio secara berkala, rebalance jika ada asset yang terlalu dominan setelah naik tajam.
                """
            
            else:
                response = f"""
**Pertanyaan Anda: "{query}"**

Maaf, saya belum memiliki informasi spesifik untuk pertanyaan ini. Namun, saya bisa membantu Anda dengan:

**Topik yang Bisa Ditanyakan:**
- Analisis crypto tertentu (ketik kode seperti BTC, ETH, SOL)
- Indikator teknikal (RSI, MA, Volume, Support/Resistance)
- Analisis fundamental (Market Cap, Supply, Tokenomics)
- Strategi trading dan timing
- Diversifikasi portofolio
- Risk management

**Contoh Pertanyaan:**
- "BTC" - Untuk analisis lengkap Bitcoin
- "Apa itu RSI?" - Penjelasan indikator RSI
- "Kapan waktu terbaik beli crypto?" - Tips timing
- "Bagaimana cara diversifikasi?" - Strategi portofolio

Silakan tanyakan lagi dengan topik yang lebih spesifik!
                """
            
            with st.container(border=True):
                st.markdown(response)
            
            # Store in chat history
            st.session_state.advisor_chat_history.append({
                'type': 'general_question',
                'query': query,
                'response': response
            })
    
    # Always show chart
    if 'advisor_ticker' not in st.session_state: 
        st.session_state.advisor_ticker = "BTC"
    
    st.markdown("---")
    st.markdown(f"### 📈 Live Chart Forecast: {st.session_state.advisor_ticker}")
    tv_symbol = f"BINANCE:{st.session_state.advisor_ticker}USDT"
    
    st.components.v1.html(
        f"""
        <div style="height: 500px; width: 100%;">
            <div id="tradingview_forecast" style="height: 100%; width: 100%;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
                "autosize": true,
                "symbol": "{tv_symbol}",
                "interval": "D",
                "timezone": "Asia/Jakarta",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#1e222d",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_forecast",
                "details": true,
                "hotlist": true,
                "withdateranges": true
            }});
            </script>
        </div>
        """,
        height=520,
    )


