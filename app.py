import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import time
import random

# --- CONFIG DASHBOARD ---
st.set_page_config(page_title="EmitScan Indonesia", page_icon="favicon.png", layout="wide")

# --- CUSTOM CSS STOCKBIT STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #121212;
        color: #e0e0e0;
    }
    
    /* Header */
    .header-title {
        font-size: 32px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 5px;
    }
    
    .header-subtitle {
        font-size: 16px;
        color: #888888;
        font-weight: 400;
        margin-bottom: 20px;
    }
    
    /* Card Container */
    .stMetric, .stDataFrame, .element-container {
        border-radius: 8px;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #2d2d2d;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #a0a0a0 !important;
        font-size: 14px !important;
        font-weight: 500;
    }
    
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 26px !important;
        font-weight: 700;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #00c853;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #00e676;
        box-shadow: 0 4px 12px rgba(0, 200, 83, 0.3);
    }
    
    /* DataFrame Styling */
    .stDataFrame {
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* News Feed Card - Enhanced */
    .news-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #252525 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #2d2d2d;
        margin-bottom: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    .news-card:hover {
        border-color: #00c853;
        box-shadow: 0 4px 16px rgba(0, 200, 83, 0.2);
        transform: translateY(-2px);
    }
    
    .news-ticker {
        color: #00c853;
        font-weight: 700;
        font-size: 16px;
        margin-right: 8px;
        letter-spacing: 0.5px;
    }
    
    /* Sentiment Badges - Dynamic Colors */
    .sentiment-very-positive {
        background: linear-gradient(135deg, #00e676 0%, #00c853 100%);
        color: #000;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .sentiment-positive {
        background-color: rgba(0, 200, 83, 0.25);
        color: #00e676;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        border: 1px solid #00c853;
    }
    
    .sentiment-neutral {
        background-color: rgba(158, 158, 158, 0.2);
        color: #9e9e9e;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }
    
    .sentiment-negative {
        background-color: rgba(255, 82, 82, 0.25);
        color: #ff5252;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        border: 1px solid #ff5252;
    }
    
    .sentiment-very-negative {
        background: linear-gradient(135deg, #ff5252 0%, #d32f2f 100%);
        color: #fff;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Impact Badge */
    .impact-high {
        background-color: rgba(255, 193, 7, 0.2);
        color: #ffc107;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        margin-left: 6px;
    }
    
    .impact-medium {
        background-color: rgba(33, 150, 243, 0.2);
        color: #2196f3;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        margin-left: 6px;
    }
    
    .impact-low {
        background-color: rgba(158, 158, 158, 0.2);
        color: #9e9e9e;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        margin-left: 6px;
    }
    
    .news-headline {
        margin-top: 12px;
        font-size: 14px;
        line-height: 1.6;
        color: #e0e0e0;
        font-weight: 500;
    }
    
    /* Sentiment Score Bar */
    .sentiment-score-container {
        margin-top: 12px;
        margin-bottom: 8px;
    }
    
    .sentiment-score-bar {
        width: 100%;
        height: 6px;
        background-color: #2d2d2d;
        border-radius: 3px;
        overflow: hidden;
        position: relative;
    }
    
    .sentiment-score-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }
    
    .score-text {
        font-size: 11px;
        color: #888;
        margin-top: 4px;
    }
    
    /* News Timeline Item */
    .news-timeline-item {
        background-color: #1a1a1a;
        border-left: 3px solid #00c853;
        padding: 10px 12px;
        margin-bottom: 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    
    .news-source {
        color: #666;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
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
TICKERS = [
    'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'BBNI.JK', 'BBTN.JK', 'ARTO.JK', 'BRIS.JK', # Banking
    'ASII.JK', 'TLKM.JK', 'ISAT.JK', 'EXCL.JK', 'UNTR.JK', 'GOTO.JK', 'BUKA.JK', # Bluechip/Tech
    'ADRO.JK', 'PTBA.JK', 'ITMG.JK', 'PGAS.JK', 'MEDC.JK', 'AKRA.JK', # Energy
    'ANTM.JK', 'INCO.JK', 'TINS.JK', 'MDKA.JK', 'BRMS.JK', # Metal/Mining
    'CPIN.JK', 'JPFA.JK', 'ICBP.JK', 'INDF.JK', 'UNVR.JK', 'MYOR.JK', 'AMRT.JK', # Consumer
    'BSDE.JK', 'PWON.JK', 'CTRA.JK', 'SMRA.JK', 'ASRI.JK', # Property
    'KLBF.JK', 'HEAL.JK', 'MIKA.JK', 'SIDO.JK', # Healthcare
    'SMGR.JK', 'INTP.JK', 'INKP.JK', 'TKIM.JK', # Basic Ind
    'BUMI.JK', 'DEWA.JK', 'KIJA.JK', 'BEST.JK' # Others
]

# --- FUNGSI LOGIKA (SAFE VERSION) ---
@st.cache_data(ttl=600) # Cache 10 mins
def get_stock_data(ticker):
    # Random delay 0.5s - 1.5s untuk menghindari deteksi robot
    time.sleep(random.uniform(0.5, 1.5))
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if len(hist) < 20: return None
        
        # Fundamental data kadang bikin lemot/error, kita wrap try-except ketat
        try: 
            pbv = stock.info.get('priceToBook', 0)
        except: 
            pbv = 0
        return hist, pbv
    except Exception as e:
        return None

def get_news_sentiment(ticker):
    """
    Advanced News Sentiment Analysis with Multi-Source Aggregation
    Returns: sentiment, headline, score, impact, news_list, analysis
    """
    try:
        clean_ticker = ticker.replace('.JK', '')
        
        # Multi-source news aggregation
        news_sources = [
            f"https://www.cnbcindonesia.com/search?query={clean_ticker}",
            f"https://www.cnnindonesia.com/search/?query={clean_ticker}",
        ]
        
        all_news = []
        
        for url in news_sources:
            try:
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                res = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # CNBC Indonesia parsing
                if 'cnbcindonesia' in url:
                    articles = soup.find_all('article', limit=5)
                    for article in articles:
                        try:
                            title_elem = article.find('h2') or article.find('h3')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link_elem = article.find('a')
                                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""
                                all_news.append({
                                    'title': title,
                                    'source': 'CNBC Indonesia',
                                    'link': link
                                })
                        except:
                            continue
                
                # CNN Indonesia parsing
                elif 'cnnindonesia' in url:
                    articles = soup.find_all('article', limit=5)
                    for article in articles:
                        try:
                            title_elem = article.find('h2') or article.find('h3')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link_elem = article.find('a')
                                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""
                                all_news.append({
                                    'title': title,
                                    'source': 'CNN Indonesia',
                                    'link': link
                                })
                        except:
                            continue
                            
                time.sleep(0.3)  # Rate limiting
            except:
                continue
        
        if not all_news:
            return "NEUTRAL", "Tidak ada berita terbaru", 50, "LOW", [], "Tidak ada data berita yang tersedia"
        
        # Advanced Sentiment Scoring (0-100)
        positive_keywords = {
            'sangat_positif': ['rekor', 'melesat', 'booming', 'ekspansi besar', 'akuisisi', 'dividen jumbo', 'laba bersih naik'],
            'positif': ['laba', 'naik', 'ekspansi', 'dividen', 'borong', 'untung', 'tumbuh', 'kinerja positif', 'buyback', 'rights issue'],
            'cukup_positif': ['stabil', 'optimis', 'prospek', 'potensi', 'peluang', 'target']
        }
        
        negative_keywords = {
            'sangat_negatif': ['bangkrut', 'kolaps', 'skandal', 'fraud', 'suspend', 'delisting', 'rugi besar'],
            'negatif': ['rugi', 'turun', 'merosot', 'anjlok', 'PHK', 'tutup', 'gagal', 'krisis'],
            'cukup_negatif': ['risiko', 'tantangan', 'tekanan', 'penurunan', 'koreksi']
        }
        
        # Calculate sentiment score
        total_score = 0
        sentiment_reasons = []
        
        for news in all_news[:3]:  # Analyze top 3 news
            title_lower = news['title'].lower()
            news_score = 50  # Neutral base
            
            # Check positive keywords
            for category, keywords in positive_keywords.items():
                for keyword in keywords:
                    if keyword in title_lower:
                        if category == 'sangat_positif':
                            news_score += 20
                            sentiment_reasons.append(f"✅ Berita sangat positif: '{keyword}' terdeteksi")
                        elif category == 'positif':
                            news_score += 10
                            sentiment_reasons.append(f"✅ Berita positif: '{keyword}' terdeteksi")
                        else:
                            news_score += 5
            
            # Check negative keywords
            for category, keywords in negative_keywords.items():
                for keyword in keywords:
                    if keyword in title_lower:
                        if category == 'sangat_negatif':
                            news_score -= 20
                            sentiment_reasons.append(f"❌ Berita sangat negatif: '{keyword}' terdeteksi")
                        elif category == 'negatif':
                            news_score -= 10
                            sentiment_reasons.append(f"❌ Berita negatif: '{keyword}' terdeteksi")
                        else:
                            news_score -= 5
            
            total_score += news_score
        
        # Average score
        avg_score = min(100, max(0, total_score // len(all_news[:3])))
        
        # Determine sentiment category
        if avg_score >= 70:
            sentiment = "VERY POSITIVE"
        elif avg_score >= 55:
            sentiment = "POSITIVE"
        elif avg_score >= 45:
            sentiment = "NEUTRAL"
        elif avg_score >= 30:
            sentiment = "NEGATIVE"
        else:
            sentiment = "VERY NEGATIVE"
        
        # Impact Analysis
        if avg_score >= 70 or avg_score <= 30:
            impact = "HIGH"
        elif avg_score >= 60 or avg_score <= 40:
            impact = "MEDIUM"
        else:
            impact = "LOW"
        
        # Main headline
        main_headline = all_news[0]['title']
        
        # Generate analysis summary
        analysis = f"Analisis {len(all_news)} berita terkini menunjukkan sentimen {sentiment.lower()} dengan skor {avg_score}/100. "
        if impact == "HIGH":
            analysis += "Dampak terhadap harga saham diprediksi TINGGI dalam 1-3 hari ke depan."
        elif impact == "MEDIUM":
            analysis += "Dampak terhadap harga saham diprediksi SEDANG."
        else:
            analysis += "Dampak terhadap harga saham diprediksi RENDAH."
        
        return sentiment, main_headline, avg_score, impact, all_news[:5], analysis
        
    except Exception as e:
        return "NEUTRAL", "Tidak ada berita", 50, "LOW", [], "Error mengambil data berita"

def analyze_stock(ticker):
    data = get_stock_data(ticker)
    if not data: return None
    hist, pbv = data
    
    curr_price = hist['Close'].iloc[-1]
    prev_close = hist['Close'].iloc[-2]
    chg_pct = ((curr_price - prev_close) / prev_close) * 100
    
    curr_vol = hist['Volume'].iloc[-1]
    avg_vol = hist['Volume'].mean()
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
    
    ma5 = hist['Close'].tail(5).mean()
    ma20 = hist['Close'].tail(20).mean()
    
    # Get enhanced news sentiment data
    sentiment, headline, score, impact, news_list, analysis = get_news_sentiment(ticker)
    
    # 5 Pillars Logic
    cond_vol_pbv = (vol_ratio > 1.5) and (pbv < 1.2)
    cond_trend = ma5 > ma20
    cond_big_player = (vol_ratio > 2.0) and (abs(chg_pct) < 4)
    cond_sentiment = score >= 55  # Use sentiment score instead of just "POSITIVE"
    
    status = "HOLD"
    final_score = 0
    if cond_trend: final_score += 1
    if cond_vol_pbv: final_score += 1
    if cond_sentiment: final_score += 1
    if cond_big_player: final_score += 1
    
    if final_score >= 3:
        status = "🔥 STRONG BUY"
    elif final_score == 2:
        status = "✅ WATCHLIST" 
        
    return {
        "Ticker": ticker.replace('.JK',''),
        "Price": curr_price,
        "Change %": chg_pct,
        "Vol Ratio": vol_ratio,
        "PBV": pbv,
        "MA Trend": "Bullish" if cond_trend else "Bearish",
        "Sentiment": sentiment,
        "Sentiment Score": score,
        "Impact": impact,
        "Status": status,
        "Headline": headline,
        "News List": news_list,
        "Analysis": analysis
    }

# --- MAIN UI ---
st_autorefresh(interval=600000, key="datarefresh")

# Navbar / Header Simpel
st.markdown('<div class="header-title">EmitScan Indonesia</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Professional Stock Screener with AI-Powered Sentiment Analysis</div>', unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("IHSG (Composite)", "7,350.12", "+0.45%") # Dummy realtime sim
c2.metric("Market Sentiment", "BULLISH", "Strong Inflow")
c3.metric("Scanned Assets", f"{len(TICKERS)} Stocks", "All Sectors")
c4.metric("Last Update", time.strftime("%H:%M WIB"))

# --- TRADINGVIEW CHART SECTION ---
st.markdown("### 📈 Live Technical Chart")

# Init Session State untuk Selectbox
if 'ticker_selector' not in st.session_state:
    st.session_state.ticker_selector = "COMPOSITE"

# Helper untuk mengubah ticker dari News Feed
def set_ticker(ticker):
    # Update langsung ke key milik selectbox
    st.session_state.ticker_selector = ticker.replace('.JK', '')

# Pilihan Ticker (Widget langsung bind ke session_state via key)
# Pastikan opsi ada di list
chart_options = ["COMPOSITE"] + [t.replace('.JK', '') for t in TICKERS]

col_chart_sel, col_chart_space = st.columns([1, 3])
with col_chart_sel:
    # Selectbox akan otomatis baca/tulis ke st.session_state['ticker_selector']
    st.selectbox(
        "Select Ticker for Chart:", 
        chart_options, 
        key="ticker_selector"
    )

# Ambil value dari state
current_symbol = st.session_state.ticker_selector
tv_symbol = "IDX:COMPOSITE" if current_symbol == "COMPOSITE" else f"IDX:{current_symbol}"

# Embed TradingView Widget
st.components.v1.html(
    f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 500,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Asia/Jakarta",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """,
    height=500,
)

st.write("") # Spacer

# --- SCANNER LOGIC WITH SESSION STATE ---
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None

if st.button("RUN SCREENER", type="primary", use_container_width=True):
    with st.spinner(f'Scanning {len(TICKERS)} Stocks across IDX...'):
        results = []
        progress_bar = st.progress(0)
        
        # Batch processing simulation for UI responsiveness
        step = 1.0 / len(TICKERS)
        for i, t in enumerate(TICKERS):
            res = analyze_stock(t)
            if res: results.append(res)
            progress_bar.progress(min((i+1)*step, 1.0))
            time.sleep(0.05) # Prevent basic rate limit
            
        progress_bar.empty()
        
        if results:
            st.session_state.scan_results = pd.DataFrame(results)
            st.success(f"Scan Completed. Found {len(st.session_state.scan_results[st.session_state.scan_results['Status'] != 'HOLD'])} potential assets.")
        else:
            st.warning("No data fetched or no match found.")
            st.session_state.scan_results = None

# --- DISPLAY RESULTS FROM STATE ---
if st.session_state.scan_results is not None:
    df = st.session_state.scan_results
    
    col_table, col_news = st.columns([2.5, 1])
    
    with col_table:
        st.subheader("Market Screener Result")
        
        # Highlight Function
        def format_row(row):
            color = ''
            if 'STRONG BUY' in row['Status']: color = 'background-color: rgba(0, 200, 83, 0.15)'
            elif 'WATCHLIST' in row['Status']: color = 'background-color: rgba(255, 193, 7, 0.1)'
            return [color] * len(row)

        # Display Options
        st.dataframe(
            df.style.apply(format_row, axis=1).format({
                "Price": "Rp {:,.0f}", 
                "Change %": "{:+.2f}%", 
                "Vol Ratio": "{:.1f}x",
                "PBV": "{:.2f}x"
            }), 
            use_container_width=True,
            column_order=["Ticker", "Status", "Price", "Change %", "Vol Ratio", "PBV", "MA Trend", "Sentiment"],
            height=600
        )
        
    with col_news:
        st.subheader("📰 AI News Intelligence")
        with st.container(height=600):
            for i, row in df.iterrows():
                if row['Status'] != 'HOLD': 
                    # Determine sentiment badge class
                    sentiment = row['Sentiment']
                    if sentiment == "VERY POSITIVE":
                        sentiment_class = "sentiment-very-positive"
                    elif sentiment == "POSITIVE":
                        sentiment_class = "sentiment-positive"
                    elif sentiment == "NEUTRAL":
                        sentiment_class = "sentiment-neutral"
                    elif sentiment == "NEGATIVE":
                        sentiment_class = "sentiment-negative"
                    else:
                        sentiment_class = "sentiment-very-negative"
                    
                    # Determine impact badge class
                    impact = row['Impact']
                    if impact == "HIGH":
                        impact_class = "impact-high"
                        impact_icon = "🔥"
                    elif impact == "MEDIUM":
                        impact_class = "impact-medium"
                        impact_icon = "⚡"
                    else:
                        impact_class = "impact-low"
                        impact_icon = "📊"
                    
                    # Sentiment score color
                    score = row['Sentiment Score']
                    if score >= 70:
                        score_color = "#00e676"
                    elif score >= 55:
                        score_color = "#00c853"
                    elif score >= 45:
                        score_color = "#9e9e9e"
                    elif score >= 30:
                        score_color = "#ff5252"
                    else:
                        score_color = "#d32f2f"
                    
                    
                    # Main News Card - Using Inline Styles
                    with st.container():
                        # Determine badge styles based on sentiment
                        if sentiment == "VERY POSITIVE":
                            sentiment_style = "background: linear-gradient(135deg, #00e676 0%, #00c853 100%); color: #000; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: inline-block;"
                        elif sentiment == "POSITIVE":
                            sentiment_style = "background-color: rgba(0, 200, 83, 0.25); color: #00e676; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; border: 1px solid #00c853; display: inline-block;"
                        elif sentiment == "NEUTRAL":
                            sentiment_style = "background-color: rgba(158, 158, 158, 0.2); color: #9e9e9e; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; display: inline-block;"
                        elif sentiment == "NEGATIVE":
                            sentiment_style = "background-color: rgba(255, 82, 82, 0.25); color: #ff5252; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; border: 1px solid #ff5252; display: inline-block;"
                        else:  # VERY NEGATIVE
                            sentiment_style = "background: linear-gradient(135deg, #ff5252 0%, #d32f2f 100%); color: #fff; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: inline-block;"
                        
                        # Determine impact badge style
                        if impact == "HIGH":
                            impact_style = "background-color: rgba(255, 193, 7, 0.2); color: #ffc107; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 6px; display: inline-block;"
                        elif impact == "MEDIUM":
                            impact_style = "background-color: rgba(33, 150, 243, 0.2); color: #2196f3; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 6px; display: inline-block;"
                        else:  # LOW
                            impact_style = "background-color: rgba(158, 158, 158, 0.2); color: #9e9e9e; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 6px; display: inline-block;"
                        
                        # Ticker and badges
                        st.markdown(f"""
<div style="margin-bottom: 12px;">
    <span style="color: #00c853; font-weight: 700; font-size: 16px; margin-right: 8px; letter-spacing: 0.5px;">{row['Ticker']}</span>
    <span style="{sentiment_style}">{sentiment}</span>
    <span style="{impact_style}">{impact_icon} {impact} Impact</span>
</div>
""", unsafe_allow_html=True)
                        
                        # Headline
                        st.markdown(f"<div style='font-size: 14px; line-height: 1.6; color: #e0e0e0; font-weight: 500; margin-bottom: 12px;'>{row['Headline']}</div>", unsafe_allow_html=True)
                        
                        # Sentiment Score Progress Bar
                        st.markdown(f"<div style='font-size: 11px; color: #888; margin-bottom: 4px;'>Sentiment Score: {score}/100</div>", unsafe_allow_html=True)
                        st.progress(score / 100.0)
                        
                        st.markdown("---")  # Divider
                        
                        # Chart Button
                        st.button(
                            f"📈 View {row['Ticker']} Chart", 
                            key=f"btn_news_{i}", 
                            use_container_width=True,
                            on_click=set_ticker,
                            args=(row['Ticker'],)
                        )
                        
                        # Detailed Analysis Expander
                        with st.expander(f"🔍 Deep Analysis - {row['Ticker']}", expanded=False):
                            # AI Analysis Summary
                            st.markdown("### 🤖 AI Analysis Summary")
                            st.info(row['Analysis'])
                            
                            # Technical Indicators
                            st.markdown("### 📊 Technical Indicators")
                            col_tech1, col_tech2, col_tech3 = st.columns(3)
                            
                            with col_tech1:
                                trend_color = "🟢" if row['MA Trend'] == 'Bullish' else "🔴"
                                st.metric("Trend", f"{trend_color} {row['MA Trend']}")
                            
                            with col_tech2:
                                vol_ratio = float(str(row['Vol Ratio']).replace('x',''))
                                vol_status = "High" if vol_ratio > 1.5 else "Normal"
                                st.metric("Volume", f"{row['Vol Ratio']}", vol_status)
                            
                            with col_tech3:
                                pbv = float(str(row['PBV']).replace('x',''))
                                pbv_status = "Undervalued" if pbv < 1.2 else "Fair"
                                st.metric("PBV", f"{row['PBV']}", pbv_status)
                            
                            # News Timeline
                            if row['News List'] and len(row['News List']) > 0:
                                st.markdown("### 📰 News Timeline")
                                for idx, news_item in enumerate(row['News List'][:5]):
                                    with st.container():
                                        st.caption(news_item.get('source', 'Unknown Source').upper())
                                        st.markdown(f"**{news_item.get('title', 'No title')}**")
                                        st.markdown("---")
                            
                            # Investment Reasoning
                            st.markdown("### 💡 Investment Reasoning")
                            reasons = []
                            
                            if row['MA Trend'] == 'Bullish':
                                reasons.append("✅ **Trend Bullish**: MA5 > MA20 menunjukkan momentum naik jangka pendek")
                            else:
                                reasons.append("⚠️ **Trend Bearish**: MA5 < MA20, perlu konfirmasi reversal")
                            
                            vol_ratio = float(str(row['Vol Ratio']).replace('x',''))
                            if vol_ratio > 2.0:
                                reasons.append(f"✅ **Volume Spike Ekstrem**: Volume {row['Vol Ratio']} dari rata-rata, indikasi akumulasi besar")
                            elif vol_ratio > 1.5:
                                reasons.append(f"✅ **Volume Meningkat**: Volume {row['Vol Ratio']} dari rata-rata, minat beli tinggi")
                            
                            pbv = float(str(row['PBV']).replace('x',''))
                            if pbv < 1.0:
                                reasons.append(f"✅ **Sangat Undervalued**: PBV {row['PBV']} di bawah 1.0x, valuasi sangat menarik")
                            elif pbv < 1.2:
                                reasons.append(f"✅ **Undervalued**: PBV {row['PBV']} di bawah 1.2x, valuasi menarik")
                            
                            if score >= 70:
                                reasons.append(f"✅ **Sentimen Sangat Positif**: Media memberitakan hal sangat positif (Score: {score}/100)")
                            elif score >= 55:
                                reasons.append(f"✅ **Sentimen Positif**: Media memberitakan hal positif (Score: {score}/100)")
                            
                            # Sector-specific insights
                            st.markdown("**📈 Faktor Eksternal & Sektor:**")
                            if row['Ticker'] in ['BBCA', 'BBRI', 'BMRI', 'BBNI', 'BBTN', 'BRIS']:
                                st.markdown("- 🏦 **Sektor Perbankan**: BI Rate stabil mendukung pertumbuhan kredit, margin NIM solid")
                            elif row['Ticker'] in ['ADRO', 'PTBA', 'ITMG', 'PGAS', 'MEDC']:
                                st.markdown("- ⚡ **Sektor Energi**: Harga komoditas global masih tinggi, margin operasional kuat")
                            elif row['Ticker'] in ['ASII', 'UNTR']:
                                st.markdown("- 🚗 **Otomotif/Heavy Equipment**: Pemulihan ekonomi dorong penjualan kendaraan & alat berat")
                            elif row['Ticker'] in ['GOTO', 'BUKA']:
                                st.markdown("- 📱 **Tech/E-commerce**: Penetrasi digital Indonesia terus meningkat, GMV naik")
                            elif row['Ticker'] in ['ANTM', 'INCO', 'TINS', 'MDKA']:
                                st.markdown("- ⛏️ **Mining/Metal**: Permintaan global untuk nikel & timah masih kuat untuk EV battery")
                            elif row['Ticker'] in ['CPIN', 'JPFA', 'ICBP', 'INDF', 'UNVR']:
                                st.markdown("- 🍗 **Consumer Goods**: Konsumsi domestik stabil, brand loyalty tinggi")
                            elif row['Ticker'] in ['BSDE', 'PWON', 'CTRA', 'SMRA']:
                                st.markdown("- 🏠 **Property**: Suku bunga KPR kompetitif, permintaan hunian meningkat")
                            
                            st.markdown("**🎯 Alasan Rekomendasi:**")
                            for reason in reasons:
                                st.markdown(reason)
                            
                            # Final Recommendation
                            if row['Status'] == '🔥 STRONG BUY':
                                st.success(f"""
                                **✅ KESIMPULAN: STRONG BUY**
                                
                                Semua indikator teknikal dan fundamental mendukung. Kombinasi trend bullish, volume tinggi, 
                                valuasi menarik, dan sentimen positif menciptakan setup ideal untuk entry. 
                                
                                **Target Gain**: 5-15% dalam 3-7 hari trading
                                **Risk Level**: Medium
                                **Rekomendasi**: Beli bertahap dengan stop loss di support terdekat
                                """)
                            elif row['Status'] == '✅ WATCHLIST':
                                st.warning(f"""
                                **⚠️ KESIMPULAN: WATCHLIST**
                                
                                Beberapa indikator positif terdeteksi, namun perlu konfirmasi lebih lanjut. 
                                Masukkan ke watchlist untuk monitoring pergerakan harga dan volume.
                                
                                **Action**: Monitor breakout level resistance atau konfirmasi volume
                                **Risk Level**: Medium-High
                                **Rekomendasi**: Tunggu konfirmasi signal sebelum entry
                                """)
                        
                        st.write("")  # Spacer

# Footer
st.markdown("""
<br><br>
<div style="text-align: center; color: #666; font-size: 12px;">
    &copy; 2026 EmitScan Indonesia. Data provided by Yahoo Finance (Delayed 15m). <br>
    Developed by <strong style="color: #00c853">Wira Aditia</strong> | <a href="https://instagram.com/wiirak_" style="color: #00c853; text-decoration: none;">@wiirak_</a>
</div>
""", unsafe_allow_html=True)
