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
st.set_page_config(page_title="EmitScan Indonesia", page_icon="favicon.png", layout="wide")

# --- CUSTOM CSS STOCKBIT STYLE ---
# --- CUSTOM CSS PREMIUM DARK STYLE ---
# --- CUSTOM CSS TRADINGVIEW / STOCKBIT PRO STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Reset & Font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #131722 !important; /* TradingView Black */
        color: #e0e0e0 !important;
        font-size: 13px; /* Smaller font for pro feel */
        overflow-x: hidden !important; /* Remove horizontal scroll */
        scroll-behavior: smooth !important;
    }
    
    /* Sidebar (Watchlist) */
    [data-testid="stSidebar"] {
        background-color: #1e222d !important;
        border-right: 1px solid #2a2e39;
        width: 300px !important;
    }
    
    /* Main Layout Gap */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
    }
    
    /* Responsive Sidebar Auto-Collapse Support */
    @media (max-width: 768px) {
        div[data-testid="stSidebar"][aria-expanded="true"] {
            /* We can't easily force it closed with pure CSS but we can hint UI */
        }
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    div[data-testid="stMetricLabel"] { font-size: 11px !important; color: #787b86 !important; }
    div[data-testid="stMetricValue"] { font-size: 16px !important; color: #d1d4dc !important; }
    
    /* Buttons (Buy/Sell Style) */
    .stButton > button {
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
        padding: 4px 12px;
        border: none;
    }
    
    /* Order Book Table */
    .order-book-cell {
        font-family: 'Roboto Mono', monospace;
        font-size: 12px;
        padding: 4px;
    }
    
    /* Tabs (Bottom Panel) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e222d;
        padding: 0px 10px;
        border-bottom: 1px solid #2a2e39;
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 0px;
        color: #787b86;
        font-size: 13px;
        font-weight: 500;
        padding-top: 0;
        padding-bottom: 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #2962ff;
        border-bottom: 2px solid #2962ff;
    }
    
    /* Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #131722; }
    ::-webkit-scrollbar-thumb { background: #363a45; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #4e525e; }

    /* Fix: Stop dimming effect during script execution (Anti-Shadow) */
    div[data-testid="stVerticalBlock"] > div[style*="opacity"] {
        opacity: 1 !important;
    }

    /* RESPONSIVE DESIGN OVERRIDES */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Header Stack */
        .main-header {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 15px !important;
            padding: 15px !important;
        }
        .header-right {
            width: 100% !important;
            justify-content: space-between !important;
            flex-wrap: wrap !important;
            gap: 10px !important;
        }
        
        /* Sidebar layout adjustment */
        [data-testid="stSidebar"] {
            width: 100% !important;
        }
        
        /* Sidebar Tab Adjustments */
        .stTabs [data-baseweb="tab-list"] {
            gap: 5px !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 11px !important;
            padding: 0 4px !important;
        }

        /* Metrics Grid for Stock Cards */
        .metrics-grid {
            grid-template-columns: repeat(2, 1fr) !important;
        }
        
        /* Adjust Font Sizes for Mobile */
        span[style*="font-size: 20px"] { font-size: 16px !important; }
        .wl-price { font-size: 12px !important; }
        .wl-ticker { font-size: 12px !important; }
        
        /* Hide non-critical buttons on very small screens if needed */
        @media (max-width: 480px) {
            .header-right a { padding: 4px 8px !important; font-size: 9px !important; }
        }
    }
    
    /* Metrics Grid Utility */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .metric-item {
        background: rgba(255,255,255,0.02);
        padding: 6px;
        border-radius: 4px;
        text-align: center;
    }
    .metric-label {
        font-size: 9px;
        color: #848e9c;
        text-transform: uppercase;
        display: block;
        margin-bottom: 2px;
    }
    .metric-value {
        font-size: 12px;
        font-weight: 700;
        color: #e0e0e0;
    }
    
    /* Prevent horizontal scroll from sparklines */
    svg { max-width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- ANTI-BLOCKING MEASURES ---
# 1. Daftar User-Agent untuk Rotasi
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
]

# --- EXPANDED TICKER DATABASE (LQ45 + POPULAR) ---
# Simulasi "Semua Emiten" dengan mengambil 50 sahama teraktif/populer.
TICKERS = list(dict.fromkeys([
    # --- BANKING & FINANCE ---
    'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'BBNI.JK', 'BBTN.JK', 'ARTO.JK', 'BRIS.JK', 'PNBN.JK', 'BDMN.JK', 'BJBR.JK',
    'BJTM.JK', 'BTPN.JK', 'BNGA.JK', 'BNII.JK', 'MEGA.JK', 'MAYB.JK', 'AGRO.JK', 'BBYB.JK', 'BVIC.JK', 'DNAR.JK',
    # --- TECH & DIGITAL ---
    'GOTO.JK', 'BUKA.JK', 'BELI.JK', 'WIFI.JK', 'MTDL.JK', 'ATIC.JK', 'MCAS.JK', 'DMMX.JK', 'MLPT.JK', 'DCII.JK',
    # --- ENERGY (OIL, GAS, COAL) ---
    'ADRO.JK', 'PTBA.JK', 'ITMG.JK', 'PGAS.JK', 'MEDC.JK', 'AKRA.JK', 'HRUM.JK', 'INDY.JK', 'BUMI.JK', 'DOID.JK',
    'ABMM.JK', 'DSSP.JK', 'ENRG.JK', 'ELSA.JK', 'RAJA.JK', 'KKGI.JK', 'MBMA.JK', 'ADMR.JK', 'TOBA.JK', 'SGER.JK',
    # --- METALS & MINING ---
    'ANTM.JK', 'INCO.JK', 'TINS.JK', 'MDKA.JK', 'BRMS.JK', 'PSAB.JK', 'MBSS.JK', 'NCKL.JK', 'NICL.JK', 'DKFT.JK',
    'ZINC.JK', 'SQMI.JK', 'CITA.JK', 'TPIA.JK', 'FNI.JK',
    # --- CONSUMER GOODS ---
    'UNVR.JK', 'ICBP.JK', 'INDF.JK', 'MYOR.JK', 'AMRT.JK', 'CPIN.JK', 'JPFA.JK', 'HMSP.JK', 'GGRM.JK', 'KLBF.JK',
    'SIDO.JK', 'WIIM.JK', 'ULTJ.JK', 'ROTI.JK', 'CLEO.JK', 'STTP.JK', 'ADES.JK', 'WOOD.JK', 'CMRY.JK',
    # --- HEALTHCARE ---
    'HEAL.JK', 'MIKA.JK', 'SILO.JK', 'PRDA.JK', 'PEHA.JK', 'SAME.JK', 'BMHS.JK', 'DGNS.JK',
    # --- RETAIL & TRADE ---
    'ACES.JK', 'MAPI.JK', 'MAPA.JK', 'RALS.JK', 'LPPF.JK', 'ERAA.JK', 'MDRN.JK', 'MPPA.JK', 'MIDI.JK', 'CSAP.JK',
    # --- PROPERTY & REAL ESTATE ---
    'BSDE.JK', 'PWON.JK', 'CTRA.JK', 'SMRA.JK', 'ASRI.JK', 'APLN.JK', 'DILD.JK', 'BKSL.JK', 'DUTI.JK', 'SSIA.JK',
    'PPRO.JK', 'DMAS.JK', 'MKPI.JK', 'LPKR.JK', 'LPCK.JK', 'GMTD.JK', 'BEST.JK', 'KIJA.JK', 'FMII.JK', 'MTLA.JK',
    # --- INFRASTRUCTURE & TELECOM ---
    'TLKM.JK', 'ISAT.JK', 'EXCL.JK', 'FREN.JK', 'JSMR.JK', 'WIKA.JK', 'PTPP.JK', 'ADHI.JK', 'WSKT.JK', 'NRCA.JK',
    'META.JK', 'TOWR.JK', 'TBIG.JK', 'CENT.JK', 'BALI.JK', 'IDPR.JK', 'BIRD.JK', 'ASSA.JK', 'WEHA.JK', 'SMDR.JK',
    # --- BASIC INDUSTRY & CHEMICALS ---
    'SMGR.JK', 'INTP.JK', 'SMBR.JK', 'INKP.JK', 'TKIM.JK', 'MAIN.JK', 'ANJT.JK', 'LSIP.JK', 'SIMP.JK',
    'BWPT.JK', 'SSMS.JK', 'AALI.JK', 'TAPG.JK', 'DSNG.JK', 'STAA.JK', 'KRAS.JK', 'BAJA.JK', 'ISSP.JK', 'NIKL.JK',
    # --- CEMENT & CONSTRUCTION ---
    'WTON.JK', 'ACST.JK', 'TOTL.JK', 'WEGE.JK', 'PPRE.JK', 'JKON.JK',
    # --- TRANSPORT & LOGISTICS ---
    'GIAA.JK', 'TMAS.JK', 'NELY.JK', 'PSSI.JK', 'TPMA.JK', 'HAIS.JK', 'IPCC.JK', 'PORT.JK',
    # --- OTHERS / POPULAR ---
    'MNCN.JK', 'SCMA.JK', 'MSIN.JK', 'VIVA.JK', 'LINK.JK', 'MLBI.JK', 'VICI.JK', 'MARK.JK', 'BELL.JK',
    'TFAS.JK', 'KRAH.JK', 'GTSI.JK', 'LABA.JK', 'OASA.JK', 'SPTO.JK', 'TRJA.JK', 'UCID.JK', 'URBN.JK', 'VOKS.JK'
]))

# --- CUSTOM CSS LOADING ANIMATION (Cyberpunk Style) ---
def custom_loading_overlay(status_text="LOADING...", progress=0):
    # Dynamic conic gradient for the ring
    gradient = f"conic-gradient(#00c853 {progress}%, #1e222d 0)"
    
    return f"""<div id="loading-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(19, 23, 34, 0.95); z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; backdrop-filter: blur(5px);">
        <!-- Circular Progress Container -->
        <div style="position: relative; width: 120px; height: 120px; border-radius: 50%; background: {gradient}; display: flex; justify-content: center; align-items: center; margin-bottom: 20px; box-shadow: 0 0 20px rgba(0, 200, 83, 0.2); animation: pulse-ring 2s infinite;">
            <!-- Inner Circle (Mask) -->
            <div style="width: 100px; height: 100px; background: #131722; border-radius: 50%; display: flex; justify-content: center; align-items: center; flex-direction: column;">
                <div style="font-family: 'Courier New', monospace; color: #fff; font-size: 24px; font-weight: bold;">{progress}%</div>
            </div>
            <!-- Spinning Border for activity indication -->
            <div style="position: absolute; top: -5px; left: -5px; right: -5px; bottom: -5px; border: 2px solid transparent; border-top: 2px solid #00c853; border-radius: 50%; animation: spin 1.5s linear infinite;"></div>
        </div>
        <div style="font-family: 'Courier New', monospace; color: #00c853; font-size: 18px; font-weight: bold; letter-spacing: 2px; text-shadow: 0 0 10px rgba(0, 200, 83, 0.5);">{status_text}</div>
        <div style="font-family: 'Courier New', monospace; color: #848e9c; font-size: 12px; margin-top: 10px;">Mencari emiten dari berbagai sumber...</div>
        <style>
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            @keyframes pulse-ring {{ 0% {{ box-shadow: 0 0 0 0 rgba(0, 200, 83, 0.4); }} 70% {{ box-shadow: 0 0 0 10px rgba(0, 200, 83, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(0, 200, 83, 0); }} }}
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

# --- FUNGSI LOGIKA (SAFE VERSION) ---
@st.cache_data(ttl=600) # Cache 10 mins
def get_stock_data(ticker, hist=None):
    # Optimasi: Kurangi delay untuk kecepatan maksimal (0.01-0.05s)
    time.sleep(random.uniform(0.01, 0.05))
    
    try:
        stock = yf.Ticker(ticker)
        # Optimasi: Gunakan data historis yang sudah diunduh jika tersedia
        if hist is None:
            # Fetch 3 months for OBV and Trend Analysis
            hist = stock.history(period="3mo")
        
        if len(hist) < 30: return None # Need more data for RSI/OBV (relaxed to 30)
        
        # Fundamental data
        try: 
            info = stock.info
            pbv = info.get('priceToBook', 0)
            
            # Fetch Cash Flow for better accuracy
            cf = stock.cashflow
            latest_cf = cf.iloc[:, 0] if not cf.empty else {}
            fcf = latest_cf.get('Free Cash Flow', 0)
            ocf = latest_cf.get('Operating Cash Flow', 0)
            cash_status = "BAIK" if (fcf > 0 or ocf > 0) else "BURUK"
            if fcf == 0 and ocf == 0: cash_status = "N/A"
            
        except: 
            info = {}
            pbv = 0
            cash_status = "N/A"
            
        return hist, pbv, info, cash_status
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def get_ihsg_info():
    try:
        ihsg = yf.Ticker("^JKSE")
        hist = ihsg.history(period="2d")
        if len(hist) < 2: return None
        
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100
        
        return {
            'price': current_price,
            'change': change,
            'percent': change_pct
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
        
        # Multi-source news aggregation with specific search logic
        # Optimize search query to avoid irrelevant results (e.g. BEST -> Video Game)
        # Use more specific query with "emiten" or "PT" to ensure stock-related news
        search_query = f"emiten {clean_ticker}"
        
        news_sources = [
            {"name": "CNBC Indonesia", "url": f"https://www.cnbcindonesia.com/search?query={search_query}"},
            {"name": "CNN Indonesia", "url": f"https://www.cnnindonesia.com/search/?query={search_query}"},
            {"name": "Kontan", "url": f"https://www.kontan.co.id/search?search={search_query}"},
            {"name": "Bisnis.com", "url": f"https://search.bisnis.com/?q={search_query}"},
        ]
        
        all_news = []
        social_keywords = ['netizen', 'viral', 'trending', 'socmed', 'X', 'twitter', 'perbincangan', 'ramai']
        noise_keywords = ['edit profil', 'hubungi kami', 'redaksi', 'career', 'iklan', 'disclaimer']
        
        # Add irrelevant keywords that might appear for certain tickers
        # For example: BEST might match "terbaik" (best in Indonesian)
        irrelevant_keywords = {
            'BEST': ['game', 'video game', 'gaming', 'juara', 'terbaik 2025', 'award'],
            'GOOD': ['baik untuk', 'makanan', 'resep'],
            'NICE': ['bagus untuk', 'tips'],
            'FAST': ['cepat untuk', 'cara cepat'],
            'LINK': ['tautan', 'cara link'],
        }
        
        social_hits = 0
        
        for src in news_sources:
            try:
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                res = requests.get(src['url'], headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Site-specific parsing
                articles = []
                if "CNBC" in src['name']:
                    articles = soup.find_all('article', limit=4)
                elif "CNN" in src['name']:
                    articles = soup.find_all('article', limit=4)
                elif "Kontan" in src['name']:
                    articles = soup.find_all('li', limit=4) # Container on Kontan search
                elif "Bisnis" in src['name']:
                    articles = soup.find_all('div', class_='art--row', limit=4)
                
                for article in articles:
                    try:
                        title = ""
                        link = ""
                        date = "Baru saja"
                        
                        if "CNBC" in src['name'] or "CNN" in src['name']:
                            title_elem = article.find(['h2', 'h3'])
                            link_elem = article.find('a')
                            title = title_elem.get_text().strip() if title_elem else ""
                            link = link_elem['href'] if link_elem else ""
                            
                            # Ekstraksi tanggal untuk CNBC/CNN
                            date_elem = article.find('span', class_='text-xs') # Common class found in research
                            if not date_elem:
                                # Fallback: cari span yang mengandung kata "lalu"
                                for s in article.find_all('span'):
                                    if "lalu" in s.get_text():
                                        date = s.get_text().replace('•', '').strip()
                                        break
                            else:
                                date = date_elem.get_text().replace('•', '').strip()
                        
                        elif "Kontan" in src['name']:
                            # Using selectors from browser research
                            title_container = article.find('div', class_='sp-hl')
                            title_elem = title_container.find('a') if title_container else article.find('a', class_='linkto-black')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link = title_elem['href'] if 'href' in title_elem.attrs else ""
                            
                            date_elem = article.find('div', class_='fs14 ff-opensans')
                            if date_elem:
                                date = date_elem.get_text().strip().split('|')[-1].strip()

                        elif "Bisnis" in src['name']:
                            title_elem = article.find('h4', class_='artTitle')
                            link_elem = article.find('a', class_='artLink')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link = link_elem['href'] if link_elem else ""
                            
                            date_elem = article.find('div', class_='artDate')
                            if date_elem:
                                date = date_elem.get_text().strip()

                        # --- NOISE FILTER ---
                        if not title or len(title) < 15: continue
                        if any(n in title.lower() for n in noise_keywords): continue
                        
                        # --- RELEVANCE VALIDATION ---
                        # Check if ticker code appears in title (case insensitive)
                        title_lower = title.lower()
                        ticker_in_title = clean_ticker.lower() in title_lower
                        
                        # Check for stock-related keywords to ensure it's about stocks
                        stock_keywords = ['saham', 'emiten', 'tbk', 'bursa', 'idx', 'ihsg', 'investor', 'dividen', 'laba', 'rugi', 'kinerja']
                        has_stock_context = any(kw in title_lower for kw in stock_keywords)
                        
                        # Check for irrelevant keywords specific to this ticker
                        is_irrelevant = False
                        if clean_ticker in irrelevant_keywords:
                            is_irrelevant = any(irr in title_lower for irr in irrelevant_keywords[clean_ticker])
                        
                        # STRICTER: Check if this is a "list article" mentioning many tickers
                        # Count how many other common tickers appear in the title
                        other_tickers = ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'UNVR', 'GOTO', 'BSDE', 'CTRA', 'DMAS', 
                                       'AKDA', 'KIJA', 'SSIA', 'MTEL', 'ADRO', 'ANTM', 'INCO', 'PTBA', 'SMGR', 'INTP']
                        ticker_count = sum(1 for t in other_tickers if t.lower() in title_lower and t != clean_ticker)
                        
                        # STRICTER: Check position of ticker in title
                        # If ticker appears only at the end (after comma or "dan"), it's likely a list
                        ticker_position = title_lower.find(clean_ticker.lower())
                        title_length = len(title_lower)
                        is_at_end = ticker_position > (title_length * 0.7) if ticker_position >= 0 else False
                        
                        # Reject if:
                        # 1. More than 2 other tickers mentioned (likely a list article)
                        # 2. Ticker only appears at the very end of title
                        if ticker_count > 2 or (ticker_count > 0 and is_at_end):
                            continue
                        
                        # Only accept if: (ticker in title OR has stock context) AND not irrelevant
                        if not ((ticker_in_title or has_stock_context) and not is_irrelevant):
                            continue
                        
                        # Fix links
                        if link and not link.startswith('http'):
                            if "CNBC" in src['name']: link = "https://www.cnbcindonesia.com" + link
                            elif "CNN" in src['name']: link = "https://www.cnnindonesia.com" + link
                            elif "Kontan" in src['name']: link = "https://www.kontan.co.id" + link
                        
                        # Check for social buzz in title
                        if any(k in title.lower() for k in social_keywords):
                            social_hits += 1
                        
                        all_news.append({
                            'title': title,
                            'source': src['name'],
                            'link': link,
                            'date': date
                        })
                    except: continue
                
                # time.sleep(0.2) # Optimasi: Hapus delay antar sumber berita
            except: continue
        
        if not all_news:
            return "NEUTRAL", "Tidak ada berita", 50, 45, "LOW", [], "Data terbatas"
        
        # Scoring Logic
        pos_k = ['naik', 'untung', 'laba', 'ekspansi', 'dividen', 'rekor', 'prospek', 'rebound', 'ara', 'hijau', 'melesat', 'terbang', 'akuisisi', 'investasi']
        neg_k = ['turun', 'rugi', 'anjlok', 'suspen', 'krisis', 'pkpu', 'phk', 'lemah', 'arb', 'merah', 'merosot', 'investigasi', 'sengketa']
        
        total_score = 50
        freshness_bonus = 0
        
        for n in all_news[:6]:
            t_low = n['title'].lower()
            d_low = n.get('date', '').lower()
            
            # Pillar 5: Fresh News Detection
            if any(k in d_low for k in ['detik', 'menit', 'jam', 'baru saja']):
                freshness_bonus += 10
            
            if any(k in t_low for k in pos_k): total_score += 15
            if any(k in t_low for k in neg_k): total_score -= 15
        
        avg_score = min(100, max(0, total_score + min(30, freshness_bonus)))
        
        # Social Buzz Score
        social_buzz = min(95, 40 + (len(all_news) * 3) + (social_hits * 15) + random.randint(0, 10))
        
        sentiment = "NEUTRAL"
        if avg_score >= 75: sentiment = "VERY POSITIVE"
        elif avg_score >= 60: sentiment = "POSITIVE"
        elif avg_score <= 25: sentiment = "VERY NEGATIVE"
        elif avg_score <= 40: sentiment = "NEGATIVE"
        
        impact = "HIGH" if (avg_score >= 75 or avg_score <= 25) else "MEDIUM"
        
        # Enhanced Analyst Research snippet
        analysis = f"**Analyst Research:** "
        if avg_score >= 60:
            analysis += f"Emiten ini layak mendapatkan perhatian karena berita terbaru ({all_news[0].get('date', 'Baru')}) menunjukkan fundamental yang menguat atau aksi korporasi positif. "
        elif avg_score <= 40:
            analysis += f"Waspada terhadap rilis berita negatif terbaru yang dapat menekan harga. "
        else:
            analysis += f"Sentimen media saat ini cenderung stabil tanpa gejolak berarti. "
            
        analysis += f"Skor sentimen agregat: {avg_score}/100."
        
        return sentiment, all_news[0]['title'], avg_score, social_buzz, impact, all_news[:6], analysis
        
    except Exception as e:
        return "NEUTRAL", "Tidak ada berita", 50, 45, "LOW", [], "Error mengambil data berita"

def analyze_stock(ticker, hist=None):
    data = get_stock_data(ticker, hist=hist)
    if not data: return None
    hist, pbv, info, cash_status = data
    
    curr_price = hist['Close'].iloc[-1]
    prev_close = hist['Close'].iloc[-2]
    chg_pct = ((curr_price - prev_close) / prev_close) * 100
    
    curr_vol = hist['Volume'].iloc[-1]
    avg_vol = hist['Volume'].tail(20).mean()
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
    
    # Financial Value Flow (Estimate)
    value_flow = curr_price * curr_vol
    
    ma5 = hist['Close'].tail(5).mean()
    ma20 = hist['Close'].tail(20).mean()
    ma50 = hist['Close'].tail(50).mean()
    
    # --- ADVANCED INDICATORS (Whale Hunter) ---
    rsi_series = calculate_rsi(hist['Close'])
    rsi = rsi_series.iloc[-1]
    
    # News Sentiment
    sentiment, headline, news_score, social_buzz, impact, news_list, sentiment_analysis = get_news_sentiment(ticker)
    
    # Fundamental Data
    roe = info.get('returnOnEquity', 0)
    debt_equity = info.get('debtToEquity', 0)
    if debt_equity and debt_equity > 0:
        debt_equity = debt_equity / 100 
    
    # --- 5 PILLARS LOGIC REFINEMENT (HIGH QUALITY ONLY) ---
    
    # Pillar 1: High Quality Fundamental
    is_high_roe = roe > 0.12 # ROE > 12%
    is_healthy_debt = debt_equity < 2.0 # DER < 2.0
    is_undervalue = pbv < 1.5 and pbv > 0
    
    # Pillar 2: Trend Alignment
    is_trend_up = (ma5 > ma20) and (ma20 > ma50) and (curr_price > ma20)
    
    # Pillar 3: Volume Intensity (Smart Money)
    # Require at least 500M IDR value flow for meaningful "Big Player" status
    is_meaningful_flow = value_flow > 500_000_000 
    is_big_volume = vol_ratio > 2.5
    
    # Pillar 4: Risk Check (Over-extended)
    is_overextended = curr_price > (ma20 * 1.15) # Price 15% above MA20
    
    # Pillar 5: Sentiment
    is_positive_sentiment = news_score >= 65 or social_buzz >= 75
    
    # Status Determination
    status = "HOLD"
    
    # TOP QUALITY: WHALE ACCUMULATION (Trend + Value + Quality)
    if is_trend_up and is_undervalue and is_high_roe and is_meaningful_flow:
        status = "WHALE ACCUMULATION"
    
    # TOP QUALITY: STRONG BUY (Quality + Sentiment + Trend)
    elif is_trend_up and is_high_roe and is_healthy_debt and is_positive_sentiment:
        status = "STRONG BUY"
        
    # BIG PLAYER ENTRY (Volume + Trend)
    elif is_big_volume and is_trend_up and is_meaningful_flow:
        status = "BIG PLAYER ENTRY"
        
    # WATCHLIST (Basic Potential)
    elif is_trend_up or (is_undervalue and is_high_roe):
        status = "WATCHLIST"
    
    # RISK OVERRIDE
    if is_overextended or rsi > 78:
        status = "HIGH RISK (Overextended)"
    
    # --- Analisis Riset Mendalam (Bahasa Indonesia) ---
    research_points = []
    
    # Technical Analysis
    if is_trend_up:
        research_points.append(f"**Trend Jangka Menengah:** Konfirmasi Bullish (MA5 > MA20 > MA50). Harga bergerak stabil di atas rata-rata.")
    
    if is_big_volume:
         research_points.append(f"**Aktivitas Volume:** Spike volume **{vol_ratio:.1f}x** dengan perputaran nilai **Rp {value_flow/1e6:.1f} Juta**.")
        
    # Fundamental Analysis
    if is_high_roe:
        research_points.append(f"**High Quality Profitability:** Emiten memiliki efisiensi modal yang sangat baik (**ROE {roe*100:.1f}%**).")
    
    if is_healthy_debt:
        research_points.append(f"**Rasio Utang:** Struktur modal sehat (**DER {debt_equity:.2f}x**), risiko kebangkrutan rendah.")
        
    if is_undervalue:
        research_points.append(f"**Valuasi Terdiskon:** Harga masih tergolong murah dibanding nilai asetnya (**PBV {pbv:.2f}x**).")
            
        


    # Synthesis Construction
    analysis = f"HASIL SCAN: {status}\n\n"
    if status == "WHALE ACCUMULATION":
        analysis = "PILIHAN PREMIUM\n\n"
        analysis += "**Terdeteksi fase akumulasi institusi/bandar.** Sangat direkomendasikan untuk entry bertahap (Cicil Beli) karena harga belum 'terbang' & downside risk minim.\n\n"
    elif status == "STRONG BUY":
        analysis = "KESIMPULAN\n\n"
        analysis += "**Emiten ini memiliki konvergensi teknikal dan fundamental yang sangat kuat.**\n\n"
    elif status == "BIG PLAYER ENTRY":
        analysis = "POTENSI AKUMULASI\n\n"
        analysis += "**Terlihat aktivitas volume tidak wajar** mengindikasikan entry Big Player, namun volatilitas harga masih agak tinggi.\n\n"
    
    analysis += "---\n\n"
    for point in research_points:
        analysis += f"{point}\n\n"
    
    if headline:
        analysis += f"---\n\n*Headline Utama:* \"{headline[:80]}...\""

    return {
        "Ticker": ticker.replace('.JK', ''),
        "Name": info.get('longName', ticker),
        "Price": curr_price,
        "Change %": chg_pct,
        "Sentiment": sentiment,
        "News Score": news_score,
        "Social Buzz": social_buzz,
        "Impact": impact,
        "Analysis": analysis,
        "Raw Vol Ratio": vol_ratio,
        "Raw PBV": pbv,
        "Fin Health": cash_status,
        "ROE": roe * 100 if roe else 0,
        "DER": debt_equity if debt_equity else 0,
        "Status": status,
        "MA Trend": "STRONG UP" if is_trend_up else ("UP" if ma5 > ma20 else "SIDEWAYS"),
        "News List": news_list,
        "Headline": headline
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

# Initialization for Ticker Selector (Since old widget is removed)
if 'ticker_selector' not in st.session_state:
    st.session_state.ticker_selector = "BBCA" # Default Startup Ticker

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
if 'ihsg_info_live' not in st.session_state or st.session_state.get('refresh_ihsg', False):
    st.session_state.ihsg_info_live = get_ihsg_info()
    st.session_state.refresh_ihsg = False

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
            color: #10d35e !important;
            background: transparent !important;
        }
        
        /* Row Styling */
        .wl-row-container {
            padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
        }
    </style>
    """, unsafe_allow_html=True)

    # BRANDING HEADER
    st.markdown("""
    <div style="margin-bottom: 16px; text-align: center;">
        <div style="font-size: 18px; font-weight: 800; background: -webkit-linear-gradient(45deg, #00c853, #b2ff59); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px;">
            EMITSCAN INDONESIA
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action Bar: Search & Refresh
    s_col = st.columns(2)
    with s_col[0]:
        if st.button("Search", help="Cari Emiten", use_container_width=True):
            st.session_state.show_search = not st.session_state.show_search
            st.rerun()
    with s_col[1]:
        if st.button("Refresh", use_container_width=True, type="secondary"):
            clear_watchlist_cache()
            if 'watchlist_data_list' in st.session_state:
                del st.session_state.watchlist_data_list
            st.session_state.refresh_ihsg = True 
            st.rerun()

    # Search Input (Conditional)
    if st.session_state.show_search:
        search_ticker = st.selectbox(
            "Cari Kode Saham:",
            options=[t.replace('.JK', '') for t in TICKERS],
            index=None,
            placeholder="Cari",
            label_visibility="collapsed"
        )
        if search_ticker:
            set_ticker(search_ticker)
            st.session_state.show_search = False
            st.rerun()
    
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    
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
                        ticker_obj = yf.Ticker(t)
                        # fast_info is often more real-time than history()
                        fi = ticker_obj.fast_info
                        current_price = fi.last_price
                        prev_close = fi.previous_close
                        
                        if current_price is None or prev_close is None:
                            # Fallback to history if fast_info fails
                            hist = ticker_obj.history(period="2d")
                            if not hist.empty:
                                current_price = hist['Close'].iloc[-1]
                                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[0]
                            else:
                                return None

                        chg_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                        
                        # Get company name
                        company_name = ticker_obj.info.get('longName', "Emiten Indonesia Tbk")
                        
                        return {
                            "ticker": t.replace('.JK', ''),
                            "name": company_name,
                            "price": int(current_price),
                            "chg": chg_pct,
                            "prev": prev_close
                        }
                    except:
                        return None

                wl = []
                # Fallback names map
                names_map = {
                    "BBCA": "Bank Central Asia Tbk.", "BBRI": "Bank Rakyat Indonesia.", "BMRI": "Bank Mandiri (Persero).",
                    "GOTO": "GoTo Gojek Tokopedia Tbk.", "TLKM": "Telkom Indonesia Tbk.", "ASII": "Astra International Tbk."
                }
                
                # Fetch Parallel
                with ThreadPoolExecutor(max_workers=30) as executor:
                    results = list(executor.map(fetch_ticker_info, TICKERS))
                
                for res in results:
                    if res:
                        ticker = res['ticker']
                        logo = f"https://assets.stockbit.com/logos/companies/{ticker}.png"
                        wl.append({
                            "ticker": ticker,
                            "name": res['name'],
                            "price": res['price'],
                            "chg": res['chg'],
                            "logo": logo
                        })
                
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

    # Render Loop - Watchlist Tab
    with tab_wl:
        for item in st.session_state.watchlist_data_list[:st.session_state.watchlist_limit]:
            # Layout: [Logo] [Ticker/Name] [Sparkline] [Price/Chg]
            r_col1, r_col2, r_col3, r_col4 = st.columns([1, 4, 3, 3])
            
            with r_col1:
                # Logo (Circular)
                st.markdown(f"""
                    <div style="width:28px; height:28px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05); margin-top:5px;">
                        <img src="{item['logo']}" style="width:100%; height:100%; object-fit:contain;">
                    </div>
                """, unsafe_allow_html=True)
                
            with r_col2:
                # Ticker & Name 
                st.markdown('<div class="ticker-btn-wrapper">', unsafe_allow_html=True)
                if st.button(item['ticker'], key=f"btn_wl_{item['ticker']}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='wl-name' style='margin-top:-15px;'>{item['name']}</div>", unsafe_allow_html=True)
                
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
                    <div class="wl-price">{item['price']:,}</div>
                    <div class="wl-chg" style="color:{color};">
                        {arrow} {int(diff):,} ({item['chg']:.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.03);'></div>", unsafe_allow_html=True)
        
        # Load More Button
        if len(st.session_state.watchlist_data_list) > st.session_state.watchlist_limit:
            if st.button("Load More", use_container_width=True):
                st.session_state.watchlist_limit += 20
                st.rerun()
        
        st.caption(f"Showing {min(st.session_state.watchlist_limit, len(st.session_state.watchlist_data_list))} of {len(st.session_state.watchlist_data_list)} assets")
        # Integrasi IHSG dinamis di sidebar
        if 'ihsg_info_live' in st.session_state and st.session_state.ihsg_info_live:
            ihsg = st.session_state.ihsg_info_live
            st.caption(f"IHSG {ihsg['price']:,.2f} ({ihsg['percent']:+.2f}%)")
        else:
            st.caption("IHSG 7,350.12 (Live)")
    
    # Gainer Tab
    with tab_gainer:
        gainers = sorted([i for i in st.session_state.watchlist_data_list if i['chg'] > 0], key=lambda x: x['chg'], reverse=True)[:10]
        for item in gainers:
            r_col1, r_col2, r_col3, r_col4 = st.columns([1, 4, 3, 3])
            with r_col1:
                st.markdown(f"""
                    <div style="width:28px; height:28px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05); margin-top:5px;">
                        <img src="{item['logo']}" style="width:100%; height:100%; object-fit:contain;">
                    </div>
                """, unsafe_allow_html=True)
            with r_col2:
                st.markdown('<div class="ticker-btn-wrapper">', unsafe_allow_html=True)
                if st.button(item['ticker'], key=f"btn_g_{item['ticker']}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='wl-name' style='margin-top:-15px;'>{item['name']}</div>", unsafe_allow_html=True)
            with r_col3:
                trend_color = "#00c853"
                trend_data = [item['price'] * (1 - random.uniform(0, 0.05)) for _ in range(8)]
                trend_data.append(item['price'])
                st.markdown(f"<div style='margin-top:5px;'>{make_sparkline(trend_data, trend_color)}</div>", unsafe_allow_html=True)
            with r_col4:
                diff = abs(item['price'] * (item['chg']/100))
                st.markdown(f"""
                <div style="text-align: right; margin-top:2px;">
                    <div class="wl-price">{item['price']:,}</div>
                    <div class="wl-chg" style="color:#00c853;">
                        ↗ {int(diff):,} ({item['chg']:.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.03);'></div>", unsafe_allow_html=True)
    
    # Loser Tab
    with tab_loser:
        losers = sorted(st.session_state.watchlist_data_list, key=lambda x: x['chg'])[:10]
        if not losers:
            st.info("No data available")
        for item in losers:
            r_col1, r_col2, r_col3, r_col4 = st.columns([1, 4, 3, 3])
            with r_col1:
                st.markdown(f"""
                    <div style="width:28px; height:28px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05); margin-top:5px;">
                        <img src="{item['logo']}" style="width:100%; height:100%; object-fit:contain;">
                    </div>
                """, unsafe_allow_html=True)
            with r_col2:
                st.markdown('<div class="ticker-btn-wrapper">', unsafe_allow_html=True)
                if st.button(item['ticker'], key=f"btn_l_{item['ticker']}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='wl-name' style='margin-top:-15px;'>{item['name']}</div>", unsafe_allow_html=True)
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
                    <div class="wl-price">{item['price']:,}</div>
                    <div class="wl-chg" style="color:{color};">
                        {arrow} {int(diff):,} ({item['chg']:.2f}%)
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
        color_class = "up" if item['chg'] >= 0 else "down"
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
      <div class="ticker__item">BBCA <span class="up">10,100</span></div><div class="ticker__item">BBRI <span class="down">4,800</span></div>
    </div></div>""", unsafe_allow_html=True)


# --- MAIN LAYOUT (Tabs: Chart, Financials, Profile) ---
current_symbol = st.session_state.ticker_selector

# Top Bar (Symbol Info) with Logo
logo_url = f"https://assets.stockbit.com/logos/companies/{current_symbol}.png"

# --- IHSG DATA ---
ihsg_data = st.session_state.ihsg_info_live
if ihsg_data:
    ihsg_p = f"{ihsg_data['price']:,.2f}"
    ihsg_c = f"{ihsg_data['change']:+.2f}"
    ihsg_pct = f"{ihsg_data['percent']:+.2f}%"
    ihsg_color = "#00c853" if ihsg_data['change'] >= 0 else "#ff5252"
    ihsg_trend = "" 
    market_sentiment = "POSITIVE" if ihsg_data['change'] >= 0 else "NEGATIVE"
    sentiment_bg = "rgba(0, 200, 83, 0.1)" if ihsg_data['change'] >= 0 else "rgba(255, 82, 82, 0.1)"
    sentiment_color = "#00c853" if ihsg_data['change'] >= 0 else "#ff5252"
else:
    ihsg_p = "7,215.30"
    ihsg_c = "-12.45"
    ihsg_pct = "-0.17%"
    ihsg_color = "#ff5252"
    ihsg_trend = ""
    market_sentiment = "NEUTRAL"
    sentiment_bg = "rgba(255, 255, 255, 0.05)"
    sentiment_color = "#848e9c"

# Check if market is open (Monday-Friday only)
import datetime
current_day = datetime.datetime.now().weekday()  # 0=Monday, 6=Sunday
is_weekday = current_day < 5  # Monday to Friday

market_status_html = ""
if is_weekday:
    market_status_html = '<span style="background: rgba(0, 200, 83, 0.1); color: #00c853; padding: 5px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; border: 1px solid rgba(0, 200, 83, 0.2); letter-spacing: 0.5px; margin-left: 8px;">MARKET OPEN</span>'
else:
    market_status_html = '<span style="background: rgba(255, 82, 82, 0.1); color: #ff5252; padding: 5px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; border: 1px solid rgba(255, 82, 82, 0.2); letter-spacing: 0.5px; margin-left: 8px;">MARKET CLOSED</span>'

header_html = f"""
<div class="main-header" style="background: rgba(30, 34, 45, 0.7); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); padding: 10px 20px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; margin-top: -12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; gap: 12px;">
        <img src="{logo_url}" onerror="this.style.display='none'" style="width: 36px; height: 36px; border-radius: 6px; object-fit: contain; background: rgba(255,255,255,0.05); padding: 4px;" alt="{current_symbol}">
        <div style="display: flex; flex-direction: column; gap: 2px;">
            <span style="font-size: 20px; font-weight: 800; color: #fff; letter-spacing: 0.5px; line-height: 1;">{current_symbol}</span>
            <span style="font-size: 11px; color: #848e9c; font-weight: 500;">JKSE | STOCK</span>
        </div>
        {market_status_html}
    </div>
    <div class="header-right" style="display: flex; align-items: center; gap: 20px;">
        <!-- BACK TO SCANNER BUTTON - Specific to current ticker card -->
        <a href="#card-{current_symbol}" style="text-decoration: none; background: rgba(255, 255, 255, 0.05); color: #848e9c; padding: 8px 16px; border-radius: 4px; font-size: 11px; font-weight: 700; border: 1px solid rgba(255, 255, 255, 0.1); transition: all 0.2s; display: flex; align-items: center; gap: 6px;">
            Kembali ke {current_symbol}
        </a>
        <div style="text-align: right;">
            <div style="font-size: 10px; color: #848e9c; font-weight: 600; text-transform: uppercase; margin-bottom: 2px;">IHSG Index {ihsg_trend}</div>
            <div style="font-size: 16px; font-weight: 700; color: #fff;">{ihsg_p} <span style="color: {ihsg_color}; font-size: 12px; margin-left: 4px;">{ihsg_c} ({ihsg_pct})</span></div>
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
main_tabs_options = ["Chart", "Financial statement", "Professional Analyst Advisor"]
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
        tv_symbol = "IDX:COMPOSITE" if current_symbol == "COMPOSITE" else f"IDX:{current_symbol}"
        
        st.components.v1.html(
            f"""
            <div class="tradingview-widget-container" style="height: 600px; width: 100%; border-radius: 0px; overflow: hidden; border: none; margin-top: -15px;">
            <div id="tradingview_chart" style="height: 100%; width: 100%;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
                "autosize": true,
                "symbol": "{tv_symbol}",
                "interval": "{current_tf_code}",
                "timezone": "Asia/Jakarta",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_chart",
                "toolbar_bg": "#1e222d",
                "hide_side_toolbar": false,
                "details": true,
                "hotlist": true,
                "calendar": false,
                "withdateranges": true
            }});
            </script>
            </div>
            """,
            height=580,
        )

        # --- COMPANY PROFILE (NEW LOCATION) ---
        st.markdown("---")
        try:
            yf_ticker = yf.Ticker(current_symbol + ".JK")
            info = yf_ticker.info
            
            st.markdown(f"### {info.get('longName', current_symbol)}")
            
            p1, p2 = st.columns([2, 1])
            with p1:
                st.caption(f"Sector: **{info.get('sector', '-')}** | Industry: **{info.get('industry', '-')}**")
                st.write(info.get('longBusinessSummary', 'No description available.'))
            with p2:
                st.markdown("#### 👥 Key Executives")
                officers = info.get('companyOfficers', [])
                if officers:
                    # Filter and show top 3
                    for off in officers[:3]:
                        st.markdown(f"**{off.get('name')}**")
                        st.caption(f"{off.get('title')}")
                else:
                    st.write("No executive info available.")
                
                if info.get('website'):
                    st.markdown(f"🌐 [Visit Website]({info.get('website')})")
                    
        except:
            st.warning("Profile data unavailable.")


    with c_orderbook:
        # --- DATA PREPARATION ---
        # Fetch fresh data for the selected ticker to ensure sidebar matches selection
        try:
            # Re-fetch or reuse logic if optimized, but for now safe to call our cached function
            sidebar_data = get_stock_data(current_symbol + ".JK")
            if sidebar_data:
                sb_hist, sb_pbv, sb_info, sb_cash = sidebar_data
                # Current Price from history to be safe
                sb_price = sb_hist['Close'].iloc[-1]
                sb_prev = sb_hist['Close'].iloc[-2]
                sb_open = sb_hist['Open'].iloc[-1]
                sb_high = sb_hist['High'].iloc[-1]
                sb_low = sb_hist['Low'].iloc[-1]
                sb_vol = sb_hist['Volume'].iloc[-1]
                
                # Mock Frequency (Freq) - usually not in free yfinance
                sb_freq = int(sb_vol / random.randint(100, 500)) if sb_vol > 0 else 0
                
                # Mock Foreign Buy/Sell (Estimasi)
                sb_f_buy = sb_vol * sb_price * 0.3 # 30% foreign
                sb_f_sell = sb_vol * sb_price * 0.25 # 25% foreign
                
                # ARA / ARB Simulation (approx 20-35% limits in ID but keeping simple)
                sb_ara = int(sb_prev * 1.25) 
                sb_arb = int(sb_prev * 0.75) 
                
                # Value
                sb_val = sb_vol * sb_price
            else:
                # Fallback if no data
                sb_price = 4200
                sb_prev = 4150
                sb_open = 4200
                sb_high = 4350
                sb_low = 4180
                sb_vol = 1120000
                sb_freq = 1900
                sb_f_buy = 5200000000
                sb_f_sell = 2100000000
                sb_ara = 5200
                sb_arb = 3900
                sb_val = 8400000000
        
        except:
             # Fallback crash protection
            sb_price = 0
            sb_prev = 0
            sb_open = 0
            sb_high = 0
            sb_low = 0
            sb_vol = 0
            sb_freq = 0
            sb_f_buy = 0
            sb_f_sell = 0
            sb_ara = 0
            sb_arb = 0
            sb_val = 0

        # Create Helper for Mock Order Book
        def generate_mock_order_book(center_price):
            # Generate 5-10 rows
            rows = []
            # Bid side (Left) - descending from price
            # Offer side (Right) - ascending from price
            
            # Start slightly below/above current price
            # Adjust step based on price fraction (tick size logic simplified)
            tick = 5 if center_price < 200 else (25 if center_price < 5000 else 50)
            
            # Round center price to nearest tick
            base_price = int(round(center_price / tick) * tick)
            
            for i in range(8):
                # BID
                bid_p = base_price - (i * tick)
                bid_vol = random.randint(100, 50000)
                bid_freq = random.randint(5, 500)
                
                # OFFER
                off_p = base_price + ((i+1) * tick) # Start 1 tick above
                off_vol = random.randint(100, 50000)
                off_freq = random.randint(5, 500)
                
                rows.append({
                    "bid_freq": bid_freq,
                    "bid_vol": bid_vol,
                    "bid_p": bid_p,
                    "off_p": off_p,
                    "off_vol": off_vol,
                    "off_freq": off_freq
                })
            return rows

        # Create Helper for Mock Running Trade
        def generate_mock_running_trade(ticker_code, center_price):
            trades = []
            brokers = ["YP", "PD", "KK", "NI", "CC", "LG", "SQ", "OD", "XL", "XC", "AK", "BK"]
            types = ["D", "F"] # Domestic, Foreign
            
            tick = 5 if center_price < 200 else (25 if center_price < 5000 else 50)
            base_price = int(round(center_price / tick) * tick)
            
            import datetime
            now = datetime.datetime.now()
            
            for i in range(15):
                t_time = (now - datetime.timedelta(seconds=i*random.randint(2, 10))).strftime("%H:%M:%S")
                # Price randomly +/- 1-2 ticks
                p_offset = random.choice([-tick, 0, tick])
                t_price = base_price + p_offset
                
                t_action = "Buy" if p_offset >= 0 else "Sell"
                t_color = "#00c853" if p_offset > 0 else ("#ff5252" if p_offset < 0 else "#e0e0e0")
                
                t_lot = random.randint(1, 500)
                t_buy_code = random.choice(brokers)
                t_buy_type = random.choice(types)
                t_buyer = f"{t_buy_code} [{t_buy_type}]"
                
                trades.append({
                    "time": t_time,
                    "code": ticker_code,
                    "price": t_price,
                    "action": t_action,
                    "color": t_color,
                    "lot": t_lot,
                    "buyer": t_buyer
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

        st.markdown(f"""<div style="background: #1e222d; border-radius: 4px; padding: 8px; margin-bottom: 4px; font-family: 'Roboto', sans-serif; font-size: 11px;"><div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; color: #d1d4dc;"><div>Open <span style="float:right; color:#e0e0e0;">{sb_open:,}</span></div><div>Prev <span style="float:right; color:#e0e0e0;">{sb_prev:,}</span></div><div>Lot <span style="float:right; color:#00c853;">{fmt_num(sb_vol)}</span></div><div>High <span style="float:right; color:#00c853;">{sb_high:,}</span></div><div>ARA <span style="float:right; color:#e0e0e0;">{sb_ara:,}</span></div><div>Val <span style="float:right; color:#00c853;">{fmt_num(sb_val)}</span></div><div>Low <span style="float:right; color:#ff5252;">{sb_low:,}</span></div><div>ARB <span style="float:right; color:#e0e0e0;">{sb_arb:,}</span></div><div>Avg <span style="float:right; color:#e0e0e0;">{(sb_high+sb_low)//2:,}</span></div><div>F Buy <span style="float:right; color:#00c853;">{fmt_num(sb_f_buy)}</span></div><div>F Sell <span style="float:right; color:#ff5252;">{fmt_num(sb_f_sell)}</span></div><div>Freq <span style="float:right; color:#e0e0e0;">{fmt_num(sb_freq)}</span></div></div></div>""", unsafe_allow_html=True)

        # --- PRO ORDER BOOK ---
        st.markdown("###  Order Book")
        
        # Build Table Rows HTML (Flattened to avoid Markdown Code Block issues)
        ob_rows_html = ""
        for row in mock_ob:
             ob_rows_html += f"""<tr style="border-bottom: 1px solid #1e222d;"><td style="color:#787b86; text-align:center;">{row['bid_freq']}</td><td style="color:#d1d4dc; text-align:right;">{row['bid_vol']:,}</td><td style="color:#00c853; text-align:right;">{row['bid_p']:,}</td><td style="color:#ff5252; text-align:left;">{row['off_p']:,}</td><td style="color:#d1d4dc; text-align:right;">{row['off_vol']:,}</td><td style="color:#787b86; text-align:center;">{row['off_freq']}</td></tr>"""
             
        # Total Row
        total_bid_vol = sum(r['bid_vol'] for r in mock_ob)
        total_off_vol = sum(r['off_vol'] for r in mock_ob)
        total_bid_freq = sum(r['bid_freq'] for r in mock_ob)
        total_off_freq = sum(r['off_freq'] for r in mock_ob)

        st.markdown(f"""
<div style="background: #1e222d; border: 1px solid #2a2e39; border-radius: 4px; overflow: hidden; font-family: 'Roboto Mono', monospace; font-size: 10px;">
<div style="max-height: 480px; overflow-y: auto;">
<table style="width: 100%; border-collapse: separate; border-spacing: 0;">
<thead style="background: #2a2e39; color: #848e9c; position: sticky; top: 0; z-index: 5;">
<tr>
<th style="padding: 4px; text-align: center; border-bottom: 1px solid #1e222d; background: #2a2e39;">Freq</th>
<th style="padding: 4px; text-align: right; border-bottom: 1px solid #1e222d; background: #2a2e39;">Lot</th>
<th style="padding: 4px; text-align: right; border-bottom: 1px solid #1e222d; background: #2a2e39;">Bid</th>
<th style="padding: 4px; text-align: left; border-bottom: 1px solid #1e222d; background: #2a2e39;">Offer</th>
<th style="padding: 4px; text-align: right; border-bottom: 1px solid #1e222d; background: #2a2e39;">Lot</th>
<th style="padding: 4px; text-align: center; border-bottom: 1px solid #1e222d; background: #2a2e39;">Freq</th>
</tr>
</thead>
<tbody>
{ob_rows_html}
<tr style="border-bottom: 1px solid #1e222d; border-top: 1px solid #444; position: sticky; bottom: 0; background: #1e222d; z-index: 5; box-shadow: 0 -2px 5px rgba(0,0,0,0.2);">
<td style="color:#e0e0e0; text-align:center; font-weight:bold;">{total_bid_freq:,}</td>
<td style="color:#e0e0e0; text-align:right; font-weight:bold;">{fmt_num(total_bid_vol)}</td>
<td style="color:#848e9c; text-align:center; font-size:9px;" colspan="2">TOTAL</td>
<td style="color:#e0e0e0; text-align:right; font-weight:bold;">{fmt_num(total_off_vol)}</td>
<td style="color:#e0e0e0; text-align:center; font-weight:bold;">{total_off_freq:,}</td>
</tr>
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
             rt_rows_html += f"""<tr><td style="color:#d1d4dc; padding:4px 6px;">{t['time']}</td><td style="color:{t['color']}; text-align:center;">{t['code']}</td><td style="color:{t['color']}; text-align:right;">{t['price']:,}</td><td style="color:{t['color']}; text-align:center;">{t['action']}</td><td style="color:#d1d4dc; text-align:right;">{t['lot']}</td><td style="color:#aa00ff; text-align:right;">{t['buyer']}</td></tr>"""
             
        st.markdown(f"""
<div style="background: #1e222d; border: 1px solid #2a2e39; border-radius: 4px; padding: 0; min-height: 180px; overflow: hidden;">
<div style="max-height: 300px; overflow-y: auto;">
<table style="width: 100%; border-collapse: separate; border-spacing: 0; font-family: 'Roboto Mono', monospace; font-size: 10px;">
<thead style="background: #1e222d; border-bottom: 1px solid #2a2e39; color: #848e9c; position: sticky; top: 0; z-index: 5;">
<tr>
<th style="padding: 6px; text-align: left; background: #1e222d;">Time</th>
<th style="padding: 6px; text-align: center; background: #1e222d;">Code</th>
<th style="padding: 6px; text-align: right; background: #1e222d;">Price</th>
<th style="padding: 6px; text-align: center; background: #1e222d;">Action</th>
<th style="padding: 6px; text-align: right; background: #1e222d;">Lot</th>
<th style="padding: 6px; text-align: right; background: #1e222d;">Buyer</th>
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
            # PHASE 1: Batch Download Historical Data (Extremely Fast)
            try:
                all_hist = yf.download(TICKERS, period="3mo", group_by='ticker', threads=True, progress=False)
            except:
                all_hist = {}

            # PHASE 2: Tier 1 Filtering (Technical Filter)
            promising_tickers = []
            results = [] 
            
            p_bar = st.progress(0, text="Menyaring emiten potensial...")
            for i, t in enumerate(TICKERS):
                # Update overlay progress
                prog_pct = int((i + 1) / len(TICKERS) * 100)
                if i % 3 == 0 or i == len(TICKERS) - 1: # Update every 3 items
                    loading_placeholder.markdown(custom_loading_overlay(f"LOADING... ({t})", progress=prog_pct), unsafe_allow_html=True)
                
                try:
                    # Safely check if ticker exists in downloaded data
                    hist = None
                    if isinstance(all_hist, pd.DataFrame) and not all_hist.empty:
                        # Check if multi-level columns exist
                        if hasattr(all_hist.columns, 'levels'):
                            if t in list(all_hist.columns.levels[0]):
                                hist = all_hist[t]
                        elif t in all_hist.columns:
                            hist = all_hist[[t]]
                    
                    if hist is not None and not hist.empty and len(hist) >= 50:
                        # Calculate needed Indicators
                        close_prices = hist['Close']
                        ma5 = close_prices.tail(5).mean()
                        ma20 = close_prices.tail(20).mean()
                        ma50 = close_prices.tail(50).mean()
                        
                        curr_vol = hist['Volume'].iloc[-1]
                        avg_vol = hist['Volume'].tail(20).mean() # 20-day average volume
                        
                        # --- RELAXED FILTERING FOR BETTER WATCHLIST VISIBILITY ---
                        # 1. Trend: Bullish alignment
                        cond_trend = (ma5 > ma20) and (ma20 > ma50) and (close_prices.iloc[-1] > ma20)
                        
                        # 2. Volume: At least 1.5x average volume (Lowered from 2.0x)
                        cond_vol = curr_vol > (avg_vol * 1.5) 
                        
                        # 3. Tightness: Detect consolidation
                        range_crude = (hist['High'].tail(5).max() - hist['Low'].tail(5).min()) / hist['Low'].tail(5).min() * 100
                        cond_tight = range_crude < 4.5 # Relaxed from 3.5%
                        
                        # Pass if Trend is good AND (Volume is decent OR Price is consolidating)
                        # This ensures "Watchlist" items (early move) are captured
                        if cond_trend and (cond_vol or cond_tight):
                            promising_tickers.append(t)
                        # Special Case: Ultra tight consolidation even if trend is just starting
                        elif range_crude < 2.5:
                            promising_tickers.append(t)
                except:
                    continue
                p_bar.progress((i + 1) / len(TICKERS))
            
            p_bar.empty()
            
            # PHASE 3: Tier 2 Deep Dive (Parallel for promising ones ONLY)
            if promising_tickers:
                total_technical = len(promising_tickers)
                st.info(f"Menemukan {total_technical} emiten potensial secara teknikal. Melakukan Quality Check...")
                final_results = []
                # Optimasi: Tingkatkan max_workers dari 15 ke 25
                with ThreadPoolExecutor(max_workers=25) as executor:
                    # Optimasi: Kirim data historis yang sudah ada (hist) ke analyze_stock
                    futures = {}
                    for t in promising_tickers:
                        # Safely extract historical data for this ticker
                        t_hist = None
                        if isinstance(all_hist, pd.DataFrame) and not all_hist.empty:
                            if hasattr(all_hist.columns, 'levels'):
                                if t in list(all_hist.columns.levels[0]):
                                    t_hist = all_hist[t]
                            elif t in all_hist.columns:
                                t_hist = all_hist[[t]]
                        
                        futures[executor.submit(analyze_stock, t, t_hist)] = t
                    
                    p_bar_deep = st.progress(0)
                    for idx, future in enumerate(futures):
                        res = future.result()
                        if res:
                            final_results.append(res)
                        
                        # Update overlay for deep analysis
                        prog_deep = int((idx + 1) / len(promising_tickers) * 100)
                        loading_placeholder.markdown(custom_loading_overlay(f"DEEP ANALYSIS {idx+1}/{len(promising_tickers)}", progress=prog_deep), unsafe_allow_html=True)
                        p_bar_deep.progress((idx + 1) / len(promising_tickers))
                    p_bar_deep.empty()
                results = final_results
            
            if results:
                st.session_state.scan_results = pd.DataFrame(results)
                st.session_state.last_update = time.strftime("%H:%M WIB")
                
                # Hitung hasil akhir vs filter teknikal
                final_df = st.session_state.scan_results
                high_quality_count = len(final_df[final_df['Status'] != 'HOLD'])
                filtered_out = total_technical - high_quality_count
                
                # Save to cache
                save_cached_results(st.session_state.scan_results, st.session_state.last_update)
                
                msg = f"Scan Completed. Found {high_quality_count} High-Quality assets."
                if filtered_out > 0:
                    msg += f" ({filtered_out} assets filtered by Quality Check)"
                st.success(msg)
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
        
        # --- NEW: RESULT SEARCH FILTER (WITH SUBMIT BUTTON) ---
        st.markdown("### Filter Hasil")
        
        # Use form to prevent auto-filtering on every keystroke
        with st.form(key="search_form", clear_on_submit=False):
            col1, col2 = st.columns([5, 1])
            with col1:
                result_search = st.text_input(
                    "search_input",
                    placeholder="Ketik kode saham", 
                    label_visibility="collapsed",
                    key="search_query"
                )
            with col2:
                search_submitted = st.form_submit_button("Cari", use_container_width=True)
        
        # Only filter if form is submitted or search query exists
        if result_search and (search_submitted or result_search):
            # Filter DataFrame
            search_term = result_search.lower()
            df = df[
                df['Ticker'].str.lower().str.contains(search_term) | 
                df['Status'].str.lower().str.contains(search_term) |
                df['Analysis'].str.lower().str.contains(search_term)
            ]
            st.caption(f"Menampilkan {len(df)} hasil pencarian untuk '{result_search}'.")
        
        # Prepare filtered lists to get counts - ACCURATE MATH
        watchlist_list = [r for i, r in df.iterrows() if 'WATCHLIST' in r['Status']]
        exclusive_hot_list = [r for i, r in df.iterrows() if any(s in r['Status'] for s in ['STRONG BUY', 'WHALE', 'BIG PLAYER', 'HIGH RISK'])]
        hold_list = [r for i, r in df.iterrows() if r['Status'] == 'HOLD']
        
        total_potential = len(watchlist_list) + len(exclusive_hot_list)
        
        # Tabs for Result View - Using radio for persistence
        result_tab_options = [
            f"All ({total_potential})", 
            f"Watchlist ({len(watchlist_list)})", 
            f"Top Picks ({len(exclusive_hot_list)})"
        ]
        
        # Sync current tab with potentially new labels
        if 'active_result_tab' not in st.session_state:
            st.session_state.active_result_tab = result_tab_options[0]
        else:
            # Try to keep the same tab category even if count changes
            current_category = st.session_state.active_result_tab.split(' (')[0]
            if current_category == "All Potential": current_category = "All"
            new_tab_match = [opt for opt in result_tab_options if opt.startswith(current_category)]
            if new_tab_match:
                st.session_state.active_result_tab = new_tab_match[0]
            else:
                st.session_state.active_result_tab = result_tab_options[0]

        # Tab selector with radio buttons
        st.markdown("---")
        active_tab = st.radio(
            "Pilih Tampilan:",
            result_tab_options,
            horizontal=True,
            key="active_result_tab",
            label_visibility="collapsed"
        )
        
        def render_stock_grid(rows, key_prefix):
            if not rows:
                st.info("Belum ada emiten yang memenuhi kriteria ini.")
                return
            
            cols = st.columns(3)
            for idx, row in enumerate(rows):
                with cols[idx % 3]:
                    # Add unique ID for anchor navigation
                    st.markdown(f'<div id="card-{row["Ticker"]}"></div>', unsafe_allow_html=True)
                    
                    with st.container(border=True):
                        # 1. Header: Ticker & Price (Minimalist)
                        h_col1, h_col2 = st.columns([2, 1])
                        with h_col1:
                            ticker_clean = row['Ticker'].replace('.JK', '')
                            # Add Logo next to ticker
                            logo_url = f"https://assets.stockbit.com/logos/companies/{ticker_clean}.png"
                            st.markdown(f"""
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <div style="width:24px; height:24px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.05);">
                                        <img src="{logo_url}" style="width:100%; height:100%; object-fit:contain;">
                                    </div>
                                    <div>
                                        <div style="font-weight: 700; font-size: 14px; color: #e0e0e0; line-height: 1;">{ticker_clean}</div>
                                        <div style="font-size: 10px; color: #848e9c; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px;">{row.get('Name', '')}</div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            st.markdown(f"<span style='font-size: 18px; font-weight: 800; color: #fff;'>Rp {row['Price']:,}</span>", unsafe_allow_html=True)
                        with h_col2:
                            # Status (Plain Text)
                            st.markdown(f"<div style='text-align: right; font-size: 11px; font-weight: 700; color: #848e9c; margin-top: 5px;'>{row['Status']}</div>", unsafe_allow_html=True)

                        # 2. Key Metrics Card (Responsive Grid)
                        st.markdown(f"""
                            <div class="metrics-grid">
                                <div class="metric-item">
                                    <span class="metric-label">Trend</span>
                                    <span class="metric-value">{row['MA Trend']}</span>
                                </div>
                                <div class="metric-item">
                                    <span class="metric-label">Vol</span>
                                    <span class="metric-value">{row['Raw Vol Ratio']:.1f}x</span>
                                </div>
                                <div class="metric-item">
                                    <span class="metric-label">PBV</span>
                                    <span class="metric-value">{row['Raw PBV']:.2f}x</span>
                                </div>
                                <div class="metric-item">
                                    <span class="metric-label">ROE</span>
                                    <span class="metric-value">{row.get('ROE', 0):.1f}%</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                        # 3. Pulse Indicators (Text Only)
                        st.markdown(f"""
                            <div style="display: flex; gap: 15px; margin-top: 10px; margin-bottom: 5px;">
                                <div style="font-size: 10px; color: #848e9c;">MEDIA PULSE: <span style="color:#00c853;">{row['News Score']}%</span></div>
                                <div style="font-size: 10px; color: #848e9c;">SOCIAL BUZZ: <span style="color:#2962ff;">{row['Social Buzz']}%</span></div>
                            </div>
                        """, unsafe_allow_html=True)

                        # 4. Summary & Progressive Disclosure
                        analysis_title = row['Analysis'].split('\n')[0] if row['Analysis'] else "Analysis"
                        st.markdown(f"<div style='margin-top: 15px; font-weight: 700; color: #e0e0e0;'>{analysis_title}</div>", unsafe_allow_html=True)
                        
                        with st.expander("Detail Riset & Berita"):
                            # The full detailed bullet points
                            st.markdown(row['Analysis'])
                            st.markdown("---")
                            if row['News List']:
                                for news in row['News List']:
                                    st.markdown(f"**{news.get('date', 'Baru')}** | {news.get('source')}")
                                    st.markdown(f"[{news.get('title')}]({news.get('link', '#')})")
                                    st.markdown("---")
                            else: st.caption("Tidak ada berita spesifik hari ini.")
                        
                        st.button(f"Load Chart", key=f"btn_{key_prefix}_{idx}", on_click=set_ticker, args=(row['Ticker'],), use_container_width=True)


        # Render content based on active tab
        if active_tab.startswith("All"):
            render_stock_grid(watchlist_list + exclusive_hot_list, "all")
            
            # --- PROFESSIONAL TABLE UX IN ALL TAB ---
            st.markdown("---")
            st.markdown("### 📊 Tabel Detail Semua Emiten")
            st.markdown("""
            <style>
                /* Dataframe header styling */
                [data-testid="stDataFrameResizable"] th {
                    background-color: #2a2e39 !important;
                    color: #848e9c !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                df[df['Status'] != 'HOLD'], 
                use_container_width=True,
                column_order=["Ticker", "Status", "Price", "Change %", "Raw Vol Ratio", "News Score", "Social Buzz", "Headline"],
                column_config={
                    "Ticker": st.column_config.TextColumn(
                        "Ticker", 
                        width="small",
                        help="Kode Saham Emiten"
                    ),
                    "Status": st.column_config.TextColumn(
                        "Signal Status", 
                        width="medium",
                        help="Hasil Analisis Algoritma"
                    ),
                    "Price": st.column_config.NumberColumn(
                        "Price (IDR)", 
                        format="Rp %d",
                        help="Harga Terakhir"
                    ),
                    "Change %": st.column_config.NumberColumn(
                        "Change", 
                        format="%.2f%%",
                        help="Perubahan Harian"
                    ),
                    "Raw Vol Ratio": st.column_config.NumberColumn(
                        "Vol Ratio", 
                        format="%.1fx",
                        help="Rasio Volume vs Rata-rata 20 Hari"
                    ),
                    "News Score": st.column_config.ProgressColumn(
                        "Media Sentiment", 
                        min_value=0, 
                        max_value=100, 
                        format="%d",
                        help="Sentimen Berita (0-100)"
                    ),
                    "Social Buzz": st.column_config.ProgressColumn(
                        "Social Buzz", 
                        min_value=0, 
                        max_value=100, 
                        format="%d",
                        help="Intensitas Pembicaraan Publik (0-100)"
                    ),
                    "Headline": st.column_config.TextColumn(
                        "Latest News", 
                        width="large"
                    ),
                },
                hide_index=True,
                height=600
            )

        elif active_tab.startswith("Watchlist"):
            render_stock_grid(watchlist_list, "watchlist")

        elif active_tab.startswith("Top Picks"):
            render_stock_grid(exclusive_hot_list, "picks")

elif main_active_tab == "Financial statement":
    st.markdown("## Laporan Keuangan")
    st.markdown("---")
    
    try:
        yf_ticker = yf.Ticker(current_symbol + ".JK")
        info = yf_ticker.info
        
        # Company Info Header
        col_info1, col_info2 = st.columns([2, 1])
        with col_info1:
            st.markdown(f"### {info.get('longName', current_symbol)}")
            st.caption(f"**Sektor:** {info.get('sector', 'N/A')} | **Industri:** {info.get('industry', 'N/A')}")
        with col_info2:
            market_cap = info.get('marketCap', 0)
            if market_cap > 0:
                if market_cap >= 1e12:
                    market_cap_str = f"Rp {market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    market_cap_str = f"Rp {market_cap/1e9:.2f}B"
                else:
                    market_cap_str = f"Rp {market_cap/1e6:.2f}M"
                st.metric("Market Cap", market_cap_str)
        
        st.markdown("---")
        
        # Key Financial Metrics
        st.markdown("### Metrik Keuangan Utama")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            previous_close = info.get('previousClose', 0)
            change_pct = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
            st.metric(
                "Harga Saham",
                f"Rp {current_price:,.0f}",
                f"{change_pct:+.2f}%"
            )
        
        with col2:
            pe_ratio = info.get('trailingPE', 0)
            st.metric(
                "P/E Ratio",
                f"{pe_ratio:.2f}x" if pe_ratio > 0 else "N/A",
                help="Price to Earnings Ratio"
            )
        
        with col3:
            pbv = info.get('priceToBook', 0)
            st.metric(
                "P/BV Ratio",
                f"{pbv:.2f}x" if pbv > 0 else "N/A",
                help="Price to Book Value Ratio"
            )
        
        with col4:
            dividend_yield = info.get('dividendYield', 0)
            st.metric(
                "Dividend Yield",
                f"{dividend_yield*100:.2f}%" if dividend_yield > 0 else "N/A"
            )
        
        st.markdown("---")
        
        # Profitability Metrics
        st.markdown("### Profitabilitas")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            roe = info.get('returnOnEquity', 0)
            roe_color = "normal" if roe <= 0 else ("inverse" if roe < 0.10 else "off")
            st.metric(
                "ROE",
                f"{roe*100:.2f}%" if roe > 0 else "N/A",
                help="Return on Equity - Efisiensi menghasilkan profit dari ekuitas",
                delta_color=roe_color
            )
        
        with col2:
            roa = info.get('returnOnAssets', 0)
            st.metric(
                "ROA",
                f"{roa*100:.2f}%" if roa > 0 else "N/A",
                help="Return on Assets - Efisiensi menghasilkan profit dari aset"
            )
        
        with col3:
            profit_margin = info.get('profitMargins', 0)
            st.metric(
                "Profit Margin",
                f"{profit_margin*100:.2f}%" if profit_margin > 0 else "N/A",
                help="Net Profit Margin"
            )
        
        with col4:
            operating_margin = info.get('operatingMargins', 0)
            st.metric(
                "Operating Margin",
                f"{operating_margin*100:.2f}%" if operating_margin > 0 else "N/A"
            )
        
        st.markdown("---")
        
        # Financial Health
        st.markdown("### Kesehatan Keuangan")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_ratio = info.get('currentRatio', 0)
            st.metric(
                "Current Ratio",
                f"{current_ratio:.2f}x" if current_ratio > 0 else "N/A",
                help="Kemampuan membayar kewajiban jangka pendek"
            )
        
        with col2:
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity and debt_to_equity > 0:
                debt_to_equity = debt_to_equity / 100
            st.metric(
                "Debt to Equity",
                f"{debt_to_equity:.2f}x" if debt_to_equity > 0 else "N/A",
                help="Rasio utang terhadap ekuitas"
            )
        
        with col3:
            quick_ratio = info.get('quickRatio', 0)
            st.metric(
                "Quick Ratio",
                f"{quick_ratio:.2f}x" if quick_ratio > 0 else "N/A",
                help="Kemampuan membayar kewajiban tanpa menjual inventori"
            )
        
        with col4:
            total_cash = info.get('totalCash', 0)
            if total_cash > 0:
                if total_cash >= 1e12:
                    cash_str = f"Rp {total_cash/1e12:.2f}T"
                elif total_cash >= 1e9:
                    cash_str = f"Rp {total_cash/1e9:.2f}B"
                else:
                    cash_str = f"Rp {total_cash/1e6:.2f}M"
                st.metric("Total Cash", cash_str)
            else:
                st.metric("Total Cash", "N/A")
        
        st.markdown("---")
        
        # Revenue & Earnings
        st.markdown("### Pendapatan & Laba")
        
        col1, col2 = st.columns(2)
        
        with col1:
            total_revenue = info.get('totalRevenue', 0)
            revenue_growth = info.get('revenueGrowth', 0)
            if total_revenue > 0:
                if total_revenue >= 1e12:
                    revenue_str = f"Rp {total_revenue/1e12:.2f}T"
                elif total_revenue >= 1e9:
                    revenue_str = f"Rp {total_revenue/1e9:.2f}B"
                else:
                    revenue_str = f"Rp {total_revenue/1e6:.2f}M"
                st.metric(
                    "Total Revenue (TTM)",
                    revenue_str,
                    f"{revenue_growth*100:+.2f}%" if revenue_growth != 0 else None
                )
            else:
                st.metric("Total Revenue (TTM)", "N/A")
        
        with col2:
            net_income = info.get('netIncomeToCommon', 0)
            earnings_growth = info.get('earningsGrowth', 0)
            if net_income > 0:
                if net_income >= 1e12:
                    income_str = f"Rp {net_income/1e12:.2f}T"
                elif net_income >= 1e9:
                    income_str = f"Rp {net_income/1e9:.2f}B"
                else:
                    income_str = f"Rp {net_income/1e6:.2f}M"
                st.metric(
                    "Net Income (TTM)",
                    income_str,
                    f"{earnings_growth*100:+.2f}%" if earnings_growth != 0 else None
                )
            else:
                st.metric("Net Income (TTM)", "N/A")
        
        st.markdown("---")
        
        # Additional Info
        st.markdown("### Informasi Tambahan")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Karyawan:**")
            employees = info.get('fullTimeEmployees', 'N/A')
            st.write(f"{employees:,}" if isinstance(employees, int) else employees)
            
            st.markdown("**Alamat:**")
            address = info.get('address1', 'N/A')
            city = info.get('city', '')
            country = info.get('country', '')
            st.write(f"{address}, {city}, {country}")
        
        with col2:
            st.markdown("**Kontak:**")
            phone = info.get('phone', 'N/A')
            st.write(phone)
            
            st.markdown("**Website:**")
            website = info.get('website', 'N/A')
            if website != 'N/A':
                st.markdown(f"[{website}]({website})")
            else:
                st.write(website)
        
        # Business Summary
        st.markdown("---")
        st.markdown("### Deskripsi Bisnis")
        business_summary = info.get('longBusinessSummary', 'Tidak ada deskripsi tersedia.')
        st.write(business_summary)
        
    except Exception as e:
        st.error(f"Gagal memuat data keuangan: {str(e)}")
        st.info("Tip: Pastikan kode saham yang dipilih valid dan memiliki data keuangan yang tersedia.")

elif main_active_tab == "Professional Analyst Advisor":
    st.markdown(f"## Penasehat Analis Professional")
    st.caption("Tanyakan apapun tentang saham dan dapatkan penjelasan berdasarkan analisis teknikal & fundamental.")
    st.markdown("---")
    
    # Initialize chat history
    if 'advisor_chat_history' not in st.session_state:
        st.session_state.advisor_chat_history = []
    
    # Query Input - Compact Layout
    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        query = st.text_input(
            "Cari Kode Saham (contoh: BBCA, IHSG)", 
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
            if not ticker_query.endswith(".JK") and not ticker_query.startswith("^"):
                ticker_query += ".JK"
                
            with st.spinner(f"Menganalisis {ticker_query}..."):
                data = analyze_stock(ticker_query)
                
                if data:
                    # Store in chat history
                    st.session_state.advisor_chat_history.append({
                        'type': 'ticker_analysis',
                        'query': query,
                        'data': data
                    })
                    
                    st.markdown(f"### Analisis Untuk: {data['Name']} ({data['Ticker'].replace('.JK', '')})")
                    
                    # Get stock data for detailed analysis
                    try:
                        yf_ticker = yf.Ticker(ticker_query)
                        hist = yf_ticker.history(period="3mo")
                        info = yf_ticker.info
                        
                        # Calculate technical indicators
                        current_price = data['Price']
                        ma5 = hist['Close'].tail(5).mean()
                        ma20 = hist['Close'].tail(20).mean()
                        ma50 = hist['Close'].tail(50).mean() if len(hist) >= 50 else ma20
                        
                        # RSI calculation (simplified)
                        delta = hist['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
                        
                        # Volume analysis
                        avg_volume = hist['Volume'].mean()
                        current_volume = hist['Volume'].iloc[-1]
                        volume_ratio = current_volume / avg_volume
                        
                        # Price change
                        price_change_1d = ((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100) if len(hist) >= 2 else 0
                        price_change_1w = ((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5] * 100) if len(hist) >= 5 else 0
                        price_change_1m = ((current_price - hist['Close'].iloc[-20]) / hist['Close'].iloc[-20] * 100) if len(hist) >= 20 else 0
                        
                    except:
                        current_rsi = 50
                        volume_ratio = 1.0
                        price_change_1d = 0
                        price_change_1w = 0
                        price_change_1m = 0
                        ma5 = current_price
                        ma20 = current_price
                        ma50 = current_price
                    
                    # Recommendation Logic
                    score = data['News Score']
                    status = data['Status']
                    
                    recommendation = "LAYAK BELI" if "BUY" in status or "WHALE" in status else ("PANTAU (WATCHLIST)" if "WATCHLIST" in status else "TUNGGU (HOLD)")
                    rec_color = "#00c853" if "LAYAK" in recommendation else ("#2962ff" if "PANTAU" in recommendation else "#ff5252")
                    
                    # Display Recommendation
                    st.markdown(f"""
                    <div style="background: {rec_color}22; border: 1px solid {rec_color}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <div style="font-size: 14px; color: #848e9c; font-weight: 600;">REKOMENDASI ANALIS:</div>
                        <div style="font-size: 28px; font-weight: 800; color: {rec_color};">{recommendation}</div>
                        <div style="font-size: 14px; color: #d1d4dc; margin-top: 10px;">Status Sistem: <b>{status}</b></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Technical Analysis Section
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("#### 📈 Analisis Teknikal")
                        
                        # Trend Analysis
                        trend = "BULLISH ↗️" if ma5 > ma20 > ma50 else ("BEARISH ↘️" if ma5 < ma20 < ma50 else "SIDEWAYS ↔️")
                        trend_color = "#00c853" if "BULLISH" in trend else ("#ff5252" if "BEARISH" in trend else "#ffa726")
                        
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-size: 11px; color: #848e9c;">Trend:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {trend_color};">{trend}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # RSI
                        rsi_status = "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Netral")
                        rsi_color = "#ff5252" if current_rsi > 70 else ("#00c853" if current_rsi < 30 else "#ffa726")
                        
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-size: 11px; color: #848e9c;">RSI (14):</div>
                            <div style="font-size: 16px; font-weight: 700; color: {rsi_color};">{current_rsi:.1f} - {rsi_status}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Volume
                        vol_status = "Tinggi" if volume_ratio > 1.5 else ("Normal" if volume_ratio > 0.8 else "Rendah")
                        vol_color = "#00c853" if volume_ratio > 1.5 else ("#ffa726" if volume_ratio > 0.8 else "#ff5252")
                        
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px;">
                            <div style="font-size: 11px; color: #848e9c;">Volume:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {vol_color};">{volume_ratio:.2f}x - {vol_status}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("#### 💰 Analisis Fundamental")
                        
                        # PBV
                        pbv = data.get('Raw PBV', 0)
                        pbv_status = "Undervalued" if pbv < 1.5 else ("Fair" if pbv < 3.0 else "Overvalued")
                        pbv_color = "#00c853" if pbv < 1.5 else ("#ffa726" if pbv < 3.0 else "#ff5252")
                        
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-size: 11px; color: #848e9c;">PBV:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {pbv_color};">{pbv:.2f}x - {pbv_status}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ROE
                        roe = data.get('ROE', 0)
                        roe_status = "Excellent" if roe > 15 else ("Good" if roe > 10 else "Weak")
                        roe_color = "#00c853" if roe > 15 else ("#ffa726" if roe > 10 else "#ff5252")
                        
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-size: 11px; color: #848e9c;">ROE:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {roe_color};">{roe:.1f}% - {roe_status}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Sentiment
                        sentiment_score = data.get('News Score', 0)
                        sentiment_status = "Positif" if sentiment_score > 60 else ("Netral" if sentiment_score > 40 else "Negatif")
                        sentiment_color = "#00c853" if sentiment_score > 60 else ("#ffa726" if sentiment_score > 40 else "#ff5252")
                        
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px;">
                            <div style="font-size: 11px; color: #848e9c;">Sentimen Berita:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {sentiment_color};">{sentiment_score}% - {sentiment_status}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown("#### 📊 Performa Harga")
                        
                        # 1 Day Change
                        change_1d_color = "#00c853" if price_change_1d > 0 else "#ff5252"
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-size: 11px; color: #848e9c;">1 Hari:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {change_1d_color};">{price_change_1d:+.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 1 Week Change
                        change_1w_color = "#00c853" if price_change_1w > 0 else "#ff5252"
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-size: 11px; color: #848e9c;">1 Minggu:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {change_1w_color};">{price_change_1w:+.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 1 Month Change
                        change_1m_color = "#00c853" if price_change_1m > 0 else "#ff5252"
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 12px; border-radius: 6px;">
                            <div style="font-size: 11px; color: #848e9c;">1 Bulan:</div>
                            <div style="font-size: 16px; font-weight: 700; color: {change_1m_color};">{price_change_1m:+.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Detailed Analysis
                    with st.container(border=True):
                        st.markdown("#### 📝 Penjelasan Lengkap")
                        
                        # Generate comprehensive explanation
                        explanation = f"""
**Analisis Teknikal:**

{data['Ticker'].replace('.JK', '')} saat ini berada dalam trend **{trend}**. Harga bergerak {'di atas' if current_price > ma20 else 'di bawah'} MA20 (Rp {ma20:,.0f}), yang menunjukkan {'momentum positif' if current_price > ma20 else 'tekanan jual'}.

RSI berada di level **{current_rsi:.1f}** yang mengindikasikan kondisi **{rsi_status}**. {'Ini bisa menjadi peluang beli karena harga sudah oversold.' if current_rsi < 30 else ('Hati-hati, saham ini sudah overbought dan berpotensi koreksi.' if current_rsi > 70 else 'Kondisi masih normal dan belum jenuh.')}

Volume trading saat ini **{volume_ratio:.2f}x** dari rata-rata, menunjukkan {'akumulasi yang kuat dari big players' if volume_ratio > 1.5 else ('aktivitas normal' if volume_ratio > 0.8 else 'minat beli yang lemah')}.

**Analisis Fundamental:**

Dari sisi valuasi, PBV sebesar **{pbv:.2f}x** menunjukkan saham ini **{pbv_status}**. {'Ini adalah valuasi yang menarik untuk entry.' if pbv < 1.5 else ('Valuasi masih wajar.' if pbv < 3.0 else 'Valuasi sudah cukup tinggi, perlu hati-hati.')}

ROE sebesar **{roe:.1f}%** menggambarkan {'efisiensi manajemen yang sangat baik dalam menghasilkan profit' if roe > 15 else ('kinerja yang cukup baik' if roe > 10 else 'kinerja yang perlu diperbaiki')}.

**Sentimen Pasar:**

Sentimen berita menunjukkan skor **{sentiment_score}%** yang tergolong **{sentiment_status}**. {data['Analysis']}

**Kesimpulan:**

{'Saham ini layak untuk dipertimbangkan sebagai kandidat beli dengan catatan perhatikan level support dan resistance.' if 'BUY' in status or 'WHALE' in status else ('Saham ini bisa dimasukkan watchlist untuk dipantau perkembangannya.' if 'WATCHLIST' in status else 'Sebaiknya tunggu konfirmasi sinyal yang lebih kuat sebelum masuk.')}
                        """
                        
                        st.markdown(explanation)
                    
                    # Price Targets
                    st.markdown("#### 🎯 Target Harga & Risk Management")
                    
                    # Calculate targets based on technical levels
                    resistance_1 = current_price * 1.08
                    resistance_2 = current_price * 1.15
                    support = current_price * 0.92
                    
                    col_t1, col_t2 = st.columns(2)
                    
                    with col_t1:
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 15px; border-radius: 4px; border: 1px solid #2a2e39;">
                            <div style="font-size: 12px; color: #848e9c; margin-bottom: 12px; font-weight: 600;">📈 TARGET PROFIT:</div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Target 1 (Konservatif):</span> <span style="color:#00c853; font-weight:700;">Rp {int(resistance_1):,}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Target 2 (Agresif):</span> <span style="color:#00c853; font-weight:700;">Rp {int(resistance_2):,}</span>
                            </div>
                            <div style="font-size: 10px; color: #848e9c; margin-top: 8px;">
                                💡 Disarankan ambil profit bertahap di setiap target
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_t2:
                        st.markdown(f"""
                        <div style="background: #1e222d; padding: 15px; border-radius: 4px; border: 1px solid #2a2e39;">
                            <div style="font-size: 12px; color: #848e9c; margin-bottom: 12px; font-weight: 600;">🛡️ RISK MANAGEMENT:</div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Stop Loss:</span> <span style="color:#ff5252; font-weight:700;">Rp {int(support):,}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="color: #d1d4dc;">Risk/Reward Ratio:</span> <span style="color:#ffa726; font-weight:700;">1:2</span>
                            </div>
                            <div style="font-size: 10px; color: #848e9c; margin-top: 8px;">
                                ⚠️ Selalu gunakan stop loss untuk proteksi modal
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Update ticker for chart and collapse sidebar on mobile
                    chart_tk = ticker_query.replace('.JK', '')
                    if chart_tk == "^JKSE": chart_tk = "COMPOSITE"
                    st.session_state.advisor_ticker = chart_tk
                    st.session_state.collapse_sidebar = True
                    
                else:
                    st.error("Emiten tidak ditemukan atau data tidak mencukupi. Pastikan kode saham benar (misal: ZINC, BBCA).")
        
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
            
            elif any(word in query_lower for word in ['pbv', 'price to book']):
                response = """
**Apa itu PBV (Price to Book Value)?**

PBV adalah rasio yang membandingkan harga saham dengan nilai buku per saham. Ini menunjukkan berapa kali pasar menghargai nilai buku perusahaan.

**Cara Menghitung:**
PBV = Harga Saham / Nilai Buku per Saham

**Interpretasi:**
- **PBV < 1**: Undervalued - Saham diperdagangkan di bawah nilai bukunya (Potensi Bargain)
- **PBV 1-3**: Fair Value - Valuasi wajar
- **PBV > 3**: Overvalued - Saham mungkin sudah mahal

**Catatan Penting:**
- PBV rendah tidak selalu berarti saham bagus, bisa jadi ada masalah fundamental
- Bandingkan PBV dengan kompetitor di sektor yang sama
- Cocok untuk saham sektor perbankan dan properti
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

**Mengapa ROE Penting:**
1. Menunjukkan kemampuan perusahaan menghasilkan profit
2. Membandingkan efisiensi antar perusahaan sejenis
3. ROE konsisten tinggi = manajemen berkualitas

**Tips:** Cari saham dengan ROE konsisten di atas 15% selama 3-5 tahun terakhir.
                """
            
            elif any(word in query_lower for word in ['volume', 'vol']):
                response = """
**Mengapa Volume Trading Penting?**

Volume menunjukkan jumlah saham yang diperdagangkan dalam periode tertentu. Volume adalah konfirmasi dari pergerakan harga.

**Prinsip Dasar:**
- **Volume Tinggi + Harga Naik** = Trend naik kuat (Bullish)
- **Volume Tinggi + Harga Turun** = Trend turun kuat (Bearish)
- **Volume Rendah** = Pergerakan tidak terkonfirmasi, bisa false signal

**Volume Ratio:**
- **> 1.5x**: Akumulasi kuat, big players masuk
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
**Kapan Waktu Terbaik untuk Beli/Jual Saham?**

**Waktu Terbaik Beli:**
1. **Saat Koreksi Pasar** - Beli saat pasar turun tapi fundamental masih bagus
2. **Breakout dengan Volume** - Harga break resistance dengan volume tinggi
3. **RSI Oversold** - RSI < 30 dan mulai rebound
4. **Golden Cross** - MA50 potong MA200 ke atas
5. **Berita Positif** - Kinerja keuangan bagus, kontrak baru, dll

**Waktu Terbaik Jual:**
1. **Target Profit Tercapai** - Sudah naik 10-20% dari entry
2. **RSI Overbought** - RSI > 70 dan mulai turun
3. **Break Support** - Harga break support penting
4. **Death Cross** - MA50 potong MA200 ke bawah
5. **Berita Negatif** - Kinerja buruk, masalah hukum, dll

**Tips:** Jangan serakah, ambil profit bertahap. Gunakan stop loss untuk proteksi.
                """
            
            elif any(word in query_lower for word in ['diversifikasi', 'portofolio']):
                response = """
**Pentingnya Diversifikasi Portofolio**

**Apa itu Diversifikasi?**
Menyebar investasi ke berbagai aset untuk mengurangi risiko.

**Prinsip Diversifikasi:**
1. **Jangan Taruh Semua Telur di Satu Keranjang**
2. **Alokasi Ideal:**
   - 40% Saham Blue Chip (BBCA, BBRI, TLKM)
   - 30% Saham Growth (Teknologi, Konsumer)
   - 20% Saham Value (Undervalued)
   - 10% Cash untuk peluang

**Diversifikasi Sektor:**
- Perbankan
- Konsumer
- Infrastruktur
- Teknologi
- Kesehatan
- Energi

**Berapa Banyak Saham?**
- Pemula: 5-8 saham
- Intermediate: 8-12 saham
- Advanced: 12-20 saham

**Tips:** Review portofolio setiap 3 bulan, rebalance jika ada sektor yang terlalu dominan.
                """
            
            else:
                response = f"""
**Pertanyaan Anda: "{query}"**

Maaf, saya belum memiliki informasi spesifik untuk pertanyaan ini. Namun, saya bisa membantu Anda dengan:

**Topik yang Bisa Ditanyakan:**
- Analisis saham tertentu (ketik kode saham seperti BBCA, ZINC)
- Indikator teknikal (RSI, MA, Volume, Support/Resistance)
- Analisis fundamental (PBV, ROE, PER)
- Strategi trading dan timing
- Diversifikasi portofolio
- Risk management

**Contoh Pertanyaan:**
- "BBCA" - Untuk analisis lengkap BBCA
- "Apa itu RSI?" - Penjelasan indikator RSI
- "Kapan waktu terbaik beli saham?" - Tips timing
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
        st.session_state.advisor_ticker = "COMPOSITE"
    
    st.markdown("---")
    st.markdown(f"### 📈 Live Chart Forecast: {st.session_state.advisor_ticker}")
    tv_symbol = f"IDX:{st.session_state.advisor_ticker}"
    
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


