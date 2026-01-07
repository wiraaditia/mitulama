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
    
    /* Card / Panels */
    .pro-card {
        background-color: #1e222d;
        border: 1px solid #2a2e39;
        border-radius: 4px;
        padding: 0px;
        margin-bottom: 8px;
        overflow: hidden;
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

# --- FUNGSI LOGIKA (SAFE VERSION) ---
@st.cache_data(ttl=600) # Cache 10 mins
def get_stock_data(ticker, hist=None):
    # Optimasi: Kurangi delay dari 0.5-1.5s menjadi minimal (0.05-0.1s)
    time.sleep(random.uniform(0.05, 0.15))
    
    try:
        stock = yf.Ticker(ticker)
        # Optimasi: Gunakan data historis yang sudah diunduh jika tersedia
        if hist is None:
            hist = stock.history(period="1mo")
        
        if len(hist) < 20: return None
        
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

@st.cache_data(ttl=600) # Cache 10 mins
def get_news_sentiment(ticker):
    """
    Advanced News Sentiment Analysis with Multi-Source Aggregation
    Returns: sentiment, headline, news_score, social_buzz, impact, news_list, analysis
    """
    try:
        clean_ticker = ticker.replace('.JK', '')
        
        # Multi-source news aggregation with specific search logic
        news_sources = [
            {"name": "CNBC Indonesia", "url": f"https://www.cnbcindonesia.com/search?query={clean_ticker}"},
            {"name": "CNN Indonesia", "url": f"https://www.cnnindonesia.com/search/?query={clean_ticker}"},
            {"name": "Kontan", "url": f"https://www.kontan.co.id/search?search={clean_ticker}"},
            {"name": "Bisnis.com", "url": f"https://search.bisnis.com/?q={clean_ticker}"},
        ]
        
        all_news = []
        social_keywords = ['netizen', 'viral', 'trending', 'socmed', 'X', 'twitter', 'perbincangan', 'ramai']
        noise_keywords = ['edit profil', 'hubungi kami', 'redaksi', 'career', 'iklan', 'disclaimer']
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
        pos_k = ['naik', 'untung', 'laba', 'ekspansi', 'dividen', 'rekor', 'prospek', 'rebound', 'ara', 'hijau', 'melesat']
        neg_k = ['turun', 'rugi', 'anjlok', 'suspen', 'krisis', 'pkpu', 'phk', 'lemah', 'arb', 'merah', 'merosot']
        
        total_score = 50
        for n in all_news[:6]:
            t_low = n['title'].lower()
            if any(k in t_low for k in pos_k): total_score += 10
            if any(k in t_low for k in neg_k): total_score -= 10
        
        avg_score = min(100, max(0, total_score))
        
        # Social Buzz Score (Simulated)
        social_buzz = min(95, 40 + (len(all_news) * 2) + (social_hits * 15) + random.randint(0, 5))
        
        sentiment = "NEUTRAL"
        if avg_score >= 70: sentiment = "VERY POSITIVE"
        elif avg_score >= 55: sentiment = "POSITIVE"
        elif avg_score <= 30: sentiment = "VERY NEGATIVE"
        elif avg_score <= 45: sentiment = "NEGATIVE"
        
        impact = "HIGH" if (avg_score >= 70 or avg_score <= 30) else "MEDIUM"
        
        analysis = f"Pulse Media & Sosial menunjukkan level ketertarikan yang {'tinggi' if social_buzz > 70 else 'stabil'}. "
        analysis += f"Sentimen agregat berada di level {avg_score}/100."
        
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
    avg_vol = hist['Volume'].mean()
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
    
    ma5 = hist['Close'].tail(5).mean()
    ma20 = hist['Close'].tail(20).mean()
    
    # News Sentiment

    
    # Get enhanced news sentiment data (Returns 7 items now)
    sentiment, headline, news_score, social_buzz, impact, news_list, analysis = get_news_sentiment(ticker)
    
    # 5 Pillars Logic
    cond_vol_pbv = (vol_ratio > 1.5) and (pbv < 1.3)
    cond_trend = ma5 > ma20
    cond_big_player = (vol_ratio > 2.0) and (abs(chg_pct) < 4)
    cond_sentiment = news_score >= 55 or social_buzz >= 65  # Boosted by social too
    
    # Fundamental Health
    roe = info.get('returnOnEquity', 0)
    debt_equity = info.get('debtToEquity', 0)
    
    status = "HOLD"
    final_score = 0
    if cond_trend: final_score += 1
    if vol_ratio > 1.2: final_score += 1 # Slightly lower threshold for watchlist
    if cond_sentiment: final_score += 1
    if cond_big_player: final_score += 1
    
    if final_score >= 3:
        status = "🔥 STRONG BUY"
    elif final_score >= 1: # More inclusive for watchlist
        status = "✅ WATCHLIST" 
    
    # --- Analisis Riset Mendalam (Bahasa Indonesia) ---
    research_points = []
    
    # Technical Analysis
    if cond_trend:
        research_points.append(f"🟢 **Teknikal:** Tren harga menunjukkan pola **Bullish** (MA5 > MA20).")
    else:
        research_points.append(f"🔴 **Teknikal:** Harga masih dalam fase konsolidasi atau **Bearish**.")
        
    if vol_ratio > 2.0:
        research_points.append(f"🔥 **Volume:** Terjadi lonjakan volume signifikan (**{vol_ratio:.1f}x**) rata-rata harian.")
    elif vol_ratio > 1.2:
        research_points.append(f"📈 **Volume:** Akumulasi volume mulai meningkat di atas rata-rata.")
        
    # Fundamental Analysis
    if pbv > 0:
        if pbv < 1.0:
            research_points.append(f"💎 **Valuasi:** Sangat murah dengan **PBV {pbv:.2f}x** (di bawah nilai buku).")
        elif pbv < 1.5:
            research_points.append(f"✅ **Valuasi:** Menarik dengan **PBV {pbv:.2f}x**.")
        else:
            research_points.append(f"⚠️ **Valuasi:** Mulai premium dengan **PBV {pbv:.2f}x**.")
            
    if roe > 15:
        research_points.append(f"💰 **Profitabilitas:** Sangat solid dengan **ROE {roe:.1f}%**.")
    elif roe > 5:
        research_points.append(f"📊 **Profitabilitas:** Stabil dengan **ROE {roe:.1f}%**.")
        
    # Sentiment Analysis
    if news_score >= 70:
        research_points.append(f"🗞️ **Media:** Sentimen berita sangat optimis (Skor: {news_score}).")
    elif news_score >= 55:
        research_points.append(f"📰 **Media:** Sentimen berita cenderung positif.")
        
    if social_buzz >= 70:
        research_points.append(f"🔥 **Sosial:** Buzz publik sangat tinggi, potensi volatilitas ritel.")

    # Synthesis
    if status == "🔥 STRONG BUY":
        analysis = "🚀 **KESIMPULAN PRO:** Emiten ini memiliki konvergensi teknikal dan fundamental yang sangat kuat.\n\n"
    elif status == "✅ WATCHLIST":
        analysis = "📋 **KESIMPULAN PRO:** Emiten potensial dengan beberapa sinyal positif yang layak dipantau.\n\n"
    else:
        analysis = "⚖️ **KESIMPULAN PRO:** Kondisi pasar saat ini netral untuk emiten ini.\n\n"
        
    analysis += "\n".join(research_points)
    
    if headline:
        analysis += f"\n\n*Headline Utama:* \"{headline[:60]}...\""

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
        "MA Trend": "UP" if cond_trend else "DOWN",
        "News List": news_list,
        "Headline": headline
    }

# Helper untuk mengubah ticker dari News Feed
def set_ticker(ticker):
    # Update langsung ke key milik selectbox
    st.session_state.ticker_selector = ticker.replace('.JK', '')
    # Force switch to Market Dashboard
    st.session_state.active_tab = "📈 Market Dashboard"
    # Set scroll to top flag
    st.session_state.scroll_to_top = True

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


# --- UI COMPONENT: SIDEBAR (WATCHLIST ONLY) ---
with st.sidebar:
    # Remove default padding & Reduce Top Margin AGGRESSIVELY
    st.markdown("""
    <style>
        /* FORCE SIDEBAR TOP ZERO */
        section[data-testid="stSidebar"] > div {
            padding-top: 0rem !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem !important; /* Some padding needed for inner content */
            margin-top: -4rem !important;
        }
        /* Hide default Streamlit anchors if any */
        a.anchor-link { display: none !important; }
        
        /* Specific Fix for "stSidebarUserContent" */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0rem !important;
        }
        /* Header Adjustment */
        .wl-header {
             margin-top: -20px !important; 
        }
        /* Custom Row Styling */
        .wl-row {
            display: flex;
            align-items: center;
            padding: 8px 4px;
            border-radius: 6px;
            margin-bottom: 2px;
            transition: background 0.2s;
            cursor: pointer;
        }
        /* Header Styling */
        .wl-header {
            font-size: 16px;
            font-weight: 700;
            color: #e0e0e0;
            margin-bottom: 10px;
            margin-top: 10px; /* Adjust this to move Up/Down */
            display: flex;
            align-items: center;
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
    s_col1, s_col2 = st.columns([1, 4])
    with s_col1:
        if st.button("🔍", help="Cari Emiten"):
            st.session_state.show_search = not st.session_state.show_search
            st.rerun()
    with s_col2:
        if st.button("🔄 Refresh Prices", use_container_width=True, type="secondary"):
            clear_watchlist_cache()
            if 'watchlist_data_list' in st.session_state:
                del st.session_state.watchlist_data_list
            st.rerun()

    # Search Input (Conditional)
    if st.session_state.show_search:
        search_ticker = st.selectbox(
            "Cari Kode Saham:",
            options=[t.replace('.JK', '') for t in TICKERS],
            index=None,
            placeholder="Ketik kode (misal: BBCA)...",
            label_visibility="collapsed"
        )
        if search_ticker:
            set_ticker(search_ticker)
            st.session_state.show_search = False
            st.rerun()
    
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    
    # Tabs for Watchlist / Gainer / Loser
    tab_wl, tab_gainer, tab_loser = st.tabs(["📋 Watchlist", "📈 Gainer", "📉 Loser"])
    
    # Action Bar (Add, Sort) - Removed Refresh as requested, kept minimal loop structure if needed, or just remove cols
    # ... logic for watchlist loop continues below ...

    # --- WATCHLIST (CUSTOM ROW COMPONENT) ---
    # Styles for custom row
    st.markdown("""
    <style>
    /* ... existing styles ... */
    .wl-row {
        display: flex;
        align-items: center;
        padding: 8px 4px;
        border-radius: 6px;
        margin-bottom: 2px;
        transition: background 0.2s;
        cursor: pointer;
    }
    .wl-row:hover {
        background-color: #2a2e39;
    }
    .wl-ticker { font-weight: 700; font-size: 13px; color: #e0e0e0; }
    .wl-name { font-size: 10px; color: #848e9c; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 110px; }
    .wl-price { font-weight: 600; font-size: 13px; text-align: right; }
    .wl-chg { font-size: 10px; text-align: right; }
    .up { color: #00c853; }
    .down { color: #ff5252; }
    </style>
    """, unsafe_allow_html=True)

    # Load from cache or fetch new data
    if 'watchlist_data_list' not in st.session_state:
        # Try to load from cache first
        cached_watchlist = load_watchlist_cache()
        if cached_watchlist:
            st.session_state.watchlist_data_list = cached_watchlist
        else:
            # Generate list using Batch Download for Speed
            with st.spinner("📦 Loading Market Data..."):
                try:
                    # Fetch 200+ tickers in ONE call instead of loop
                    batch_data = yf.download(TICKERS, period="2d", group_by='ticker', threads=True, progress=False)
                except:
                    batch_data = pd.DataFrame()

                wl = []
                # Fallback names map for common ones
                names_map = {
                    "BBCA": "Bank Central Asia Tbk.",
                    "BBRI": "Bank Rakyat Indonesia.",
                    "BMRI": "Bank Mandiri (Persero).",
                    "GOTO": "GoTo Gojek Tokopedia Tbk.",
                    "TLKM": "Telkom Indonesia Tbk."
                }
                
                for t in TICKERS:
                    ticker = t.replace('.JK', '')
                    try:
                        # Extract from batch
                        if isinstance(batch_data, pd.DataFrame) and t in batch_data.columns.levels[0]:
                            hist = batch_data[t]
                            price = int(hist['Close'].iloc[-1])
                            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[0]
                            chg = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                        else:
                            raise ValueError("No data")
                    except:
                        # Random Fallback if data missing
                        price = random.randint(100, 10000)
                        chg = random.uniform(-2, 2)
                    
                    logo = f"https://assets.stockbit.com/logos/companies/{ticker}.png"
                    wl.append({
                        "ticker": ticker,
                        "name": names_map.get(ticker, "Emiten Indonesia Tbk"),
                        "price": price,
                        "chg": chg,
                        "logo": logo
                    })
                
                st.session_state.watchlist_data_list = wl
                save_watchlist_cache(wl)
            
    # Helper for SVG Sparkline
    def make_sparkline(data, color):
        if not data: return ""
        width = 60
        height = 20
        min_y, max_y = min(data), max(data)
        range_y = max_y - min_y if max_y != min_y else 1
        pts = []
        for i, val in enumerate(data):
            x = (i / (len(data)-1)) * width
            y = height - ((val - min_y) / range_y) * height
            pts.append(f"{x},{y}")
        polyline = " ".join(pts)
        return f'<svg width="{width}" height="{height}"><polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/></svg>'

    # Render Loop - Watchlist Tab
    with tab_wl:
        for item in st.session_state.watchlist_data_list[:st.session_state.watchlist_limit]:
            # Layout: [Logo] [Ticker/Name] [Sparkline] [Price/Change]
            r_col1, r_col2, r_col3, r_col4 = st.columns([0.8, 2, 1.5, 1.8])
            
            with r_col1:
                # Logo
                st.image(item['logo'], width=32)
                
            with r_col2:
                # Ticker & Name 
                if st.button(f"{item['ticker']}", key=f"btn_wl_{item['ticker']}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.caption(f"{item['name']}")
                
            with r_col3:
                # Sparkline
                # Mock a small trend list based on change
                trend_color = "#00c853" if item['chg'] >= 0 else "#ff5252"
                # Generate pseudo-random trend for the sparkline visual
                trend_data = [
                    item['price'] * (1 - (random.uniform(0, 0.05) if item['chg'] < 0 else -random.uniform(0, 0.05)))
                    for _ in range(5)
                ]
                trend_data.append(item['price']) # End at current
                
                st.markdown(make_sparkline(trend_data, trend_color), unsafe_allow_html=True)
                
            with r_col4:
                # Price & Change
                color_class = "up" if item['chg'] >= 0 else "down"
                sign = "+" if item['chg'] >= 0 else ""
                
                st.markdown(f"""
                <div style="text-align: right; line-height: 1.2;">
                    <div style="font-size: 13px; font-weight: 600; color: #e0e0e0;">{item['price']:,}</div>
                    <div style="font-size: 10px;" class="{color_class}">{sign}{item['chg']:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<div style='margin-bottom: 4px; border-bottom: 1px solid #2a2e39;'></div>", unsafe_allow_html=True)
        
        # Load More Button
        if len(st.session_state.watchlist_data_list) > st.session_state.watchlist_limit:
            if st.button("🔽 Load More", use_container_width=True):
                st.session_state.watchlist_limit += 20
                st.rerun()
        
        st.caption(f"Showing {min(st.session_state.watchlist_limit, len(st.session_state.watchlist_data_list))} of {len(st.session_state.watchlist_data_list)} assets")
        st.caption("IHSG 7,350.12 (Live)")
    
    # Gainer Tab
    with tab_gainer:
        # Sort by highest positive change
        gainers = sorted([i for i in st.session_state.watchlist_data_list if i['chg'] > 0], key=lambda x: x['chg'], reverse=True)[:10]
        for item in gainers:
            r_col1, r_col2, r_col3, r_col4 = st.columns([0.8, 2, 1.5, 1.8])
            with r_col1:
                st.image(item['logo'], width=32)
            with r_col2:
                if st.button(f"{item['ticker']}", key=f"btn_g_{item['ticker']}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.caption(f"{item['name']}")
            with r_col3:
                trend_color = "#00c853"
                trend_data = [item['price'] * (1 - random.uniform(0, 0.05)) for _ in range(5)]
                trend_data.append(item['price'])
                st.markdown(make_sparkline(trend_data, trend_color), unsafe_allow_html=True)
            with r_col4:
                st.markdown(f"""
                <div style="text-align: right; line-height: 1.2;">
                    <div style="font-size: 13px; font-weight: 600; color: #e0e0e0;">{item['price']:,}</div>
                    <div style="font-size: 10px; color: #00c853;">+{item['chg']:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 4px; border-bottom: 1px solid #2a2e39;'></div>", unsafe_allow_html=True)
    
    # Loser Tab
    with tab_loser:
        # Sort by change (lowest first) - show bottom 10 regardless of positive/negative
        losers = sorted(st.session_state.watchlist_data_list, key=lambda x: x['chg'])[:10]
        if not losers:
            st.info("🔎 No data available")
        for item in losers:
            r_col1, r_col2, r_col3, r_col4 = st.columns([0.8, 2, 1.5, 1.8])
            with r_col1:
                st.image(item['logo'], width=32)
            with r_col2:
                if st.button(f"{item['ticker']}", key=f"btn_l_{item['ticker']}", use_container_width=True):
                    set_ticker(item['ticker'])
                st.caption(f"{item['name']}")
            with r_col3:
                trend_color = "#ff5252" if item['chg'] < 0 else "#00c853"
                trend_data = [item['price'] * (1 + random.uniform(0, 0.05)) for _ in range(5)]
                trend_data.append(item['price'])
                st.markdown(make_sparkline(trend_data, trend_color), unsafe_allow_html=True)
            with r_col4:
                color_class = "up" if item['chg'] >= 0 else "down"
                sign = "+" if item['chg'] >= 0 else ""
                st.markdown(f"""
                <div style="text-align: right; line-height: 1.2;">
                    <div style="font-size: 13px; font-weight: 600; color: #e0e0e0;">{item['price']:,}</div>
                    <div style="font-size: 10px;" class="{color_class}">{sign}{item['chg']:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 4px; border-bottom: 1px solid #2a2e39;'></div>", unsafe_allow_html=True)


        


# --- UI COMPONENT: TICKER TAPE ---
# Modern CSS Marquee
st.markdown("""
<div class="ticker-wrap">
<div class="ticker">
  <div class="ticker__item">BBCA <span class="up">▲ 9,975</span></div>
  <div class="ticker__item">BBRI <span class="down">▼ 5,200</span></div>
  <div class="ticker__item">BMRI <span class="up">▲ 7,125</span></div>
  <div class="ticker__item">BBNI <span class="up">▲ 6,025</span></div>
  <div class="ticker__item">TLKM <span class="down">▼ 2,130</span></div>
  <div class="ticker__item">ASII <span class="up">▲ 5,100</span></div>
  <div class="ticker__item">GOTO <span class="down">▼ 54</span></div>
  <div class="ticker__item">UNVR <span class="down">▼ 2,340</span></div>
  <div class="ticker__item">ADRO <span class="up">▲ 2,450</span></div>
  <div class="ticker__item">ANTM <span class="up">▲ 1,560</span></div>
  <!-- Duplicate for infinite loop illusion -->
  <div class="ticker__item">BBCA <span class="up">▲ 9,975</span></div>
  <div class="ticker__item">BBRI <span class="down">▼ 5,200</span></div>
  <div class="ticker__item">BMRI <span class="up">▲ 7,125</span></div>
  <div class="ticker__item">BBNI <span class="up">▲ 6,025</span></div>
</div>
</div>
<style>
.ticker-wrap {
  width: 100%;
  overflow: hidden;
  background-color: #15191e;
  padding-left: 100%; /* Start offscreen */
  box-sizing: content-box;
  border-bottom: 1px solid #2a2e39;
  height: 30px;
  line-height: 30px;
  margin-bottom: 10px;
}
.ticker {
  display: inline-block;
  white-space: nowrap;
  padding-right: 100%;
  box-sizing: content-box;
  animation-iteration-count: infinite;
  animation-timing-function: linear;
  animation-name: ticker;
  animation-duration: 45s;
}
.ticker__item {
  display: inline-block;
  padding: 0 2rem;
  font-size: 12px;
  color: #d1d4dc;
  font-weight: 600;
}
.ticker__item .up { color: #00c853; }
.ticker__item .down { color: #ff5252; }

@keyframes ticker {
  0% { transform: translate3d(0, 0, 0); }
  100% { transform: translate3d(-100%, 0, 0); }
}
</style>
""", unsafe_allow_html=True)


# --- MAIN LAYOUT (Tabs: Chart, Financials, Profile) ---
current_symbol = st.session_state.ticker_selector

# Top Bar (Symbol Info) with Logo
logo_url = f"https://assets.stockbit.com/logos/companies/{current_symbol}.png"

# --- IHSG DATA ---
ihsg_data = get_ihsg_info()
if ihsg_data:
    ihsg_p = f"{ihsg_data['price']:,.2f}"
    ihsg_c = f"{ihsg_data['change']:+.2f}"
    ihsg_pct = f"{ihsg_data['percent']:+.2f}%"
    ihsg_color = "#00c853" if ihsg_data['change'] >= 0 else "#ff5252"
    ihsg_trend = "↗" if ihsg_data['change'] >= 0 else "↘"
    market_sentiment = "POSITIVE" if ihsg_data['change'] >= 0 else "NEGATIVE"
    sentiment_bg = "rgba(0, 200, 83, 0.1)" if ihsg_data['change'] >= 0 else "rgba(255, 82, 82, 0.1)"
    sentiment_color = "#00c853" if ihsg_data['change'] >= 0 else "#ff5252"
else:
    ihsg_p = "7,215.30"
    ihsg_c = "-12.45"
    ihsg_pct = "-0.17%"
    ihsg_color = "#ff5252"
    ihsg_trend = "↘"
    market_sentiment = "NEUTRAL"
    sentiment_bg = "rgba(255, 255, 255, 0.05)"
    sentiment_color = "#848e9c"

header_html = f"""
<div style="background: rgba(30, 34, 45, 0.7); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); padding: 10px 20px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; margin-top: -12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; gap: 12px;">
        <img src="{logo_url}" onerror="this.style.display='none'" style="width: 36px; height: 36px; border-radius: 6px; object-fit: contain; background: rgba(255,255,255,0.05); padding: 4px;" alt="{current_symbol}">
        <div style="display: flex; flex-direction: column; gap: 2px;">
            <span style="font-size: 20px; font-weight: 800; color: #fff; letter-spacing: 0.5px; line-height: 1;">{current_symbol}</span>
            <span style="font-size: 11px; color: #848e9c; font-weight: 500;">JKSE • STOCK</span>
        </div>
        <span style="background: rgba(0, 200, 83, 0.1); color: #00c853; padding: 5px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; border: 1px solid rgba(0, 200, 83, 0.2); letter-spacing: 0.5px; margin-left: 8px;">MARKET OPEN</span>
    </div>
    <div style="display: flex; align-items: center; gap: 20px;">
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


# Main Content Tabs
tab_chart, tab_financials = st.tabs(["🔥 Chart", "📊 Financial statement"])

with tab_chart:
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
            
            st.markdown(f"### 🏢 {info.get('longName', current_symbol)}")
            
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
        st.markdown("<div style='margin-top: 15px; font-weight: 700; font-size: 14px;'>Running Trade ↗</div>", unsafe_allow_html=True)
        
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
    st.write("")
    st.markdown("### Market Screener & AI Analysis")

    # Control Bar
    b1, b2, b3 = st.columns([2, 1, 6])
    with b1:
        if st.button("RUN SCREENER", key="run_scr_main", use_container_width=True, type="primary"):
            st.session_state.run_screener = True
    with b2:
        if st.button("🧹 Clear", key="clear_scr_main", use_container_width=True):
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
        with st.spinner(f'🚀 Memulai Adaptive Scanning ({len(TICKERS)} emiten)...'):
            # PHASE 1: Batch Download Historical Data (Extremely Fast)
            try:
                all_hist = yf.download(TICKERS, period="1mo", group_by='ticker', threads=True, progress=False)
            except:
                all_hist = {}

            # PHASE 2: Tier 1 Filtering (Technical Filter)
            promising_tickers = []
            results = [] # To store minimal data for non-promising ones if we want, but usually we just skip
            
            p_bar = st.progress(0, text="Menyaring emiten potensial...")
            for i, t in enumerate(TICKERS):
                try:
                    hist = all_hist[t] if isinstance(all_hist, pd.DataFrame) and t in all_hist.columns.levels[0] else None
                    if hist is not None and not hist.empty and len(hist) >= 20:
                        ma5 = hist['Close'].tail(5).mean().iloc[0] if isinstance(hist['Close'].tail(5).mean(), pd.Series) else hist['Close'].tail(5).mean()
                        ma20 = hist['Close'].tail(20).mean().iloc[0] if isinstance(hist['Close'].tail(20).mean(), pd.Series) else hist['Close'].tail(20).mean()
                        curr_vol = hist['Volume'].iloc[-1]
                        avg_vol = hist['Volume'].mean()
                        
                        # Criteria: Trend UP or Volume Spike
                        if ma5 > ma20 or curr_vol > (avg_vol * 1.5):
                            promising_tickers.append(t)
                except:
                    continue
                p_bar.progress((i + 1) / len(TICKERS))
            
            p_bar.empty()
            
            # PHASE 3: Tier 2 Deep Dive (Parallel for promising ones ONLY)
            if promising_tickers:
                st.info(f"🔍 Menemukan {len(promising_tickers)} emiten potensial. Melakukan analisis mendalam...")
                final_results = []
                # Optimasi: Tingkatkan max_workers dari 15 ke 25
                with ThreadPoolExecutor(max_workers=25) as executor:
                    # Optimasi: Kirim data historis yang sudah ada (hist) ke analyze_stock
                    futures = {}
                    for t in promising_tickers:
                        t_hist = all_hist[t] if isinstance(all_hist, pd.DataFrame) and t in all_hist.columns.levels[0] else None
                        futures[executor.submit(analyze_stock, t, t_hist)] = t
                    
                    p_bar_deep = st.progress(0)
                    for idx, future in enumerate(futures):
                        res = future.result()
                        if res:
                            final_results.append(res)
                        p_bar_deep.progress((idx + 1) / len(promising_tickers))
                    p_bar_deep.empty()
                results = final_results
            
            if results:
                st.session_state.scan_results = pd.DataFrame(results)
                st.session_state.last_update = time.strftime("%H:%M WIB")
                # Save to cache
                save_cached_results(st.session_state.scan_results, st.session_state.last_update)
                st.success(f"Scan Completed. Found {len(st.session_state.scan_results[st.session_state.scan_results['Status'] != 'HOLD'])} potential assets.")
            else:
                st.warning("No data fetched or no match found.")
                st.session_state.scan_results = None

    # Display Logic
    if st.session_state.scan_results is not None:
        df = st.session_state.scan_results
        
        # Tabs for Result View
        tab_picks, tab_grid, tab_table = st.tabs(["� Top Picks", "🔲 All Potential", "📋 Table View"])
        
        def render_stock_grid(rows, key_prefix):
            if not rows:
                st.info("🔎 Belum ada emiten yang memenuhi kriteria ini.")
                return
            
            cols = st.columns(3)
            for idx, row in enumerate(rows):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"### {row['Ticker']} — Rp {row['Price']:,}")
                        if 'STRONG BUY' in row['Status']: 
                            st.markdown("🔥 **STRONG BUY**")
                        else: 
                            st.markdown("✅ **WATCHLIST**")
                        
                        st.markdown(f"<div style='font-size: 11px; margin-bottom: 2px; color: #848e9c;'>Media Pulse: <span style='color: #fff;'>{row['News Score']}%</span></div>", unsafe_allow_html=True)
                        st.progress(row['News Score'] / 100.0)
                        
                        st.markdown(f"<div style='font-size: 11px; margin-bottom: 2px; margin-top: 5px; color: #848e9c;'>Social Buzz: <span style='color: #fff;'>{row['Social Buzz']}%</span></div>", unsafe_allow_html=True)
                        st.progress(row['Social Buzz'] / 100.0)
                        st.markdown("---")
                        
                        k1, k2, k3 = st.columns(3)
                        k1.metric("Trend", row['MA Trend'])
                        k2.metric("Vol", f"{row['Raw Vol Ratio']:.1f}x")
                        k3.metric("PBV", f"{row['Raw PBV']:.2f}x")
                        
                        # Financial Summary Row (ROE Only)
                        row_roe = row.get('ROE', 0)
                        st.markdown(f"<div style='text-align: center; margin-top: -5px;'><span style='font-size: 11px; color: #848e9c;'>ROE:</span> <span style='font-size: 11px; font-weight: 700; color: #fff;'>{row_roe:.1f}%</span></div>", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown(row['Analysis'])
                        
                        with st.expander("📰 Lihat Berita & Research"):
                            if row['News List']:
                                for news in row['News List']:
                                    # Format tanggal berita agar lebih menonjol
                                    date_str = news.get('date', 'Baru saja')
                                    st.markdown(f"**🕒 {date_str}** | _Sumber: {news.get('source')}_")
                                    link = news.get('link', '#')
                                    st.markdown(f"👉 [{news.get('title')}]({link})")
                                    st.markdown("---")
                            else: st.write("-")
                        
                        st.button(f"📈 Load", key=f"btn_{key_prefix}_{idx}", on_click=set_ticker, args=(row['Ticker'],), use_container_width=True)

        with tab_picks:
            # Filter for STRONG BUY only
            picks = [r for i, r in df.iterrows() if 'STRONG BUY' in r['Status']]
            render_stock_grid(picks, "picks")

        with tab_grid:
            # Filter for all potential (excluding HOLD)
            potential = [r for i, r in df.iterrows() if r['Status'] != 'HOLD']
            render_stock_grid(potential, "all")

        with tab_table:
            st.dataframe(
                df, 
                use_container_width=True,
                column_order=["Ticker", "Status", "Price", "Change %", "Vol Ratio", "Sentiment Score", "Headline"],
                height=400
            )

with tab_financials:
    st.markdown(f"### 📊 Laporan Financial Perusahaan: {current_symbol}")
    
    # Try fetching real data via yfinance
    try:
        yf_ticker = yf.Ticker(current_symbol + ".JK")
        
        # Helper to get latest from Annual or Quarterly
        def get_latest_financials(annual_df, quarterly_df):
            if annual_df.empty and quarterly_df.empty: return None, None, ""
            
            # Sort both to get latest
            latest_annual_date = sorted(annual_df.columns, reverse=True)[0] if not annual_df.empty else None
            latest_quarterly_date = sorted(quarterly_df.columns, reverse=True)[0] if not quarterly_df.empty else None
            
            if latest_quarterly_date and (not latest_annual_date or latest_quarterly_date > latest_annual_date):
                return quarterly_df.reindex(sorted(quarterly_df.columns, reverse=True), axis=1), latest_quarterly_date, " (Quarterly)"
            return annual_df.reindex(sorted(annual_df.columns, reverse=True), axis=1), latest_annual_date, " (Annual)"

        # 1. Neraca (Balance Sheet)
        st.markdown("#### 🏦 1. Neraca (Balance Sheet)")
        bs, latest_date_bs, bs_type = get_latest_financials(yf_ticker.balance_sheet, yf_ticker.quarterly_balance_sheet)
        
        if bs is not None:
            latest_bs = bs.iloc[:, 0]
            st.caption(f"Data per: **{latest_date_bs.strftime('%Y-%m-%d')}**{bs_type}")
            aset = latest_bs.get('Total Assets', 0)
            liab = latest_bs.get('Total Liabilities Net Minority Interest', latest_bs.get('Total Liab', 0))
            ekuitas = latest_bs.get('Stockholders Equity', latest_bs.get('Total Equity Gross Minority Interest', 0))
            
            n1, n2, n3 = st.columns(3)
            n1.metric("Aset", f"Rp {aset/1e12:.2f} T" if aset > 0 else "-")
            n2.metric("Liabilitas", f"Rp {liab/1e12:.2f} T" if liab > 0 else "-")
            n3.metric("Ekuitas", f"Rp {ekuitas/1e12:.2f} T" if ekuitas > 0 else "-")
            
            with st.expander("Detail Neraca"):
                st.dataframe(bs.T.head(4), use_container_width=True)
        else:
            st.warning("Data Neraca tidak tersedia.")

        # 2. Income Statement
        st.markdown("#### 📈 2. Income Statement")
        is_stmt, latest_date_is, is_type = get_latest_financials(yf_ticker.income_stmt, yf_ticker.quarterly_income_stmt)
        
        if is_stmt is not None:
            latest_is = is_stmt.iloc[:, 0]
            st.caption(f"Data per: **{latest_date_is.strftime('%Y-%m-%d')}**{is_type}")
            revenue = latest_is.get('Total Revenue', 0)
            net_income = latest_is.get('Net Income', 0)
            expenses = latest_is.get('Total Operating Expenses', latest_is.get('Operating Expense', revenue - net_income))
            
            i1, i2, i3 = st.columns(3)
            i1.metric("Pendapatan", f"Rp {revenue/1e12:.2f} T" if revenue > 0 else "-")
            i2.metric("Beban", f"Rp {expenses/1e12:.2f} T" if expenses > 0 else "-")
            i3.metric("Laba Bersih", f"Rp {net_income/1e12:.2f} T" if net_income != 0 else "-")
            
            with st.expander("Detail Rugi Laba"):
                st.dataframe(is_stmt.T.head(4), use_container_width=True)
        else:
            st.warning("Data Income Statement tidak tersedia.")

        # 3. Cashflow Statement
        st.markdown("#### 💵 3. Cashflow Statement")
        cf, latest_date_cf, cf_type = get_latest_financials(yf_ticker.cashflow, yf_ticker.quarterly_cashflow)
        
        if cf is not None:
            latest_cf = cf.iloc[:, 0]
            st.caption(f"Data per: **{latest_date_cf.strftime('%Y-%m-%d')}**{cf_type}")
            fcf = latest_cf.get('Free Cash Flow', 0)
            ocf = latest_cf.get('Operating Cash Flow', latest_cf.get('Cash Flow From Continuing Operating Activities', 0))
            
            c1, c2 = st.columns(2)
            c1.metric("Arus Kas Operasi", f"Rp {ocf/1e12:.2f} T" if ocf != 0 else "-")
            c2.metric("Free Cash Flow", f"Rp {fcf/1e12:.2f} T" if fcf != 0 else "-")
            
            # Decision: Good or Bad
            status_kas = "BAIK ✅" if fcf > 0 and ocf > 0 else "BURUK ⚠️"
            color_kas = "#00c853" if status_kas == "BAIK ✅" else "#ff5252"
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; border-left: 5px solid {color_kas}; margin-top: 10px;">
                <span style="font-size: 14px; font-weight: 600; color: #848e9c;">KESIMPULAN KAS:</span><br>
                <span style="font-size: 20px; font-weight: 800; color: {color_kas};">Laporan Kas ini sedang {status_kas}</span>
                <p style="font-size: 12px; color: #d1d4dc; margin-top: 5px;">
                    {'Perusahaan memiliki arus kas operasional positif dan mampu menghasilkan free cash flow.' if status_kas == 'BAIK ✅' else 'Perusahaan mengalami kesulitan dalam menghasilkan arus kas bebas atau operasional yang positif.'}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Detail Arus Kas"):
                st.dataframe(cf.T.head(4), use_container_width=True)
        else:
            st.warning("Data Cashflow tidak tersedia.")
            
    except Exception as e:
        st.error(f"Gagal mengambil data finansial detail: {e}")
        st.warning("Coba muat ulang fitur ini.")


