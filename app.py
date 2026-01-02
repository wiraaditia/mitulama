import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
import time

# --- CONFIG DASHBOARD ---
st.set_page_config(page_title="EmitScan Indonesia", page_icon="favicon.png", layout="wide")

# --- CUSTOM CSS TERMINAL STYLE ---
st.markdown("""
<style>
    /* Global Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Share Tech Mono', monospace;
        background-color: #050505;
        color: #e0e0e0;
    }
    
    /* Neon Title */
    .neon-title {
        font-family: 'Share Tech Mono', monospace;
        font-size: 60px;
        text-align: center;
        color: #000;
        -webkit-text-stroke: 1.5px #00f3ff;
        text-shadow: 0 0 10px #00f3ff, 0 0 20px #00f3ff;
        margin-bottom: 0px;
    }
    
    .neon-subtitle {
        font-size: 20px;
        text-align: center;
        color: #00ff41;
        text-shadow: 0 0 5px #00ff41;
        margin-top: -10px;
        margin-bottom: 30px;
        letter-spacing: 2px;
    }
    
    /* Metric Boxes */
    div[data-testid="stMetric"] {
        background-color: #0a0a0a;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 0 5px rgba(0, 243, 255, 0.2);
        text-align: center;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #888 !important;
        font-size: 14px !important;
    }
    
    div[data-testid="stMetricValue"] {
        color: #00f3ff !important;
        font-size: 24px !important;
        text-shadow: 0 0 5px #00f3ff;
    }
    
    div[data-testid="stMetricDelta"] {
        color: #00ff41 !important;
    }

    /* Table Styling */
    .stDataFrame {
        border: 1px solid #333;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #000;
        color: #00ff41;
        border: 1px solid #00ff41;
        border-radius: 0;
        width: 100%;
        text-transform: uppercase;
        font-family: 'Share Tech Mono', monospace;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #00ff41;
        color: #000;
        box-shadow: 0 0 15px #00ff41;
    }
    
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown('<h1 class="neon-title">EMITSCAN INDONESIA</h1>', unsafe_allow_html=True)
st.markdown('<p class="neon-subtitle">>> SYSTEM SCREENING SAHAM INDONESIA <<< <br> [Volume Spike] [Media Sentimen] [Big Player]</p>', unsafe_allow_html=True)

# --- METRIC SECTION (Top) ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Market Status", "BULLISH", "+0.5%")
with col2:
    # Placeholder value, will update after screening
    st.metric("Potential Stocks", "WAITING...", "Scanning")
with col3:
    st.metric("Last Update", time.strftime("%H:%M:%S WIB"))

st.markdown("---")

# --- DATABASE EMITEN ---
# Sektor: Perbankan, Properti, Energi, Consumer
TICKERS = ['BBTN.JK', 'BMRI.JK', 'BBCA.JK', 'BSDE.JK', 'PWON.JK', 'ADRO.JK', 'PTBA.JK', 'UNVR.JK', 'ICBP.JK']



# --- FUNGSI UTAMA ---

@st.cache_data(ttl=600) # Cache data selama 10 menit
def get_stock_data(ticker):
    """Mengambil data historis dan fundamental"""
    stock = yf.Ticker(ticker)
    
    # Ambil data historis 1 bulan terakhir untuk perhitungan MA dan Volume
    hist = stock.history(period="1mo")
    
    if len(hist) < 20:
        return None # Data tidak cukup
        
    # Data Fundamental (PBV)
    try:
        pbv = stock.info.get('priceToBook', 0)
    except:
        pbv = 0
            
    return hist, pbv

def get_news_sentiment(ticker):
    """Scrape berita dari CNBC Indonesia (Pencarian Sederhana)"""
    try:
        clean_ticker = ticker.replace('.JK', '')
        # Gunakan CNBC Indonesia Search
        url = f"https://www.cnbcindonesia.com/search?query={clean_ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Coba ambil artikel pertama
        articles = soup.find_all('article')
        if not articles:
            return "NEUTRAL", "Tidak ada berita terbaru"
            
        first_article = articles[0]
        headline_tag = first_article.find('h2')
        
        if not headline_tag:
            return "NEUTRAL", "Judul tidak ditemukan"
            
        headline = headline_tag.get_text().strip()
        
        # Analisa Sentiment Sederhana
        positive_keywords = ['laba', 'naik', 'ekspansi', 'dividen', 'borong', 'untung', 'tumbuh']
        
        if any(word in headline.lower() for word in positive_keywords):
            return "POSITIVE", headline
        else:
            return "NEUTRAL", headline
            
    except Exception as e:
        return "NEUTRAL", f"Error: {str(e)}"

def analyze_stock(ticker):
    hist, pbv = get_stock_data(ticker)
    if hist is None:
        return None
        
    # --- HITUNG INDIKATOR ---
    current_price = hist['Close'].iloc[-1]
    prev_close = hist['Close'].iloc[-2]
    price_change_pct = ((current_price - prev_close) / prev_close) * 100
    
    current_vol = hist['Volume'].iloc[-1]
    avg_vol_20 = hist['Volume'].mean()
    
    ma5 = hist['Close'].tail(5).mean()
    ma20 = hist['Close'].tail(20).mean()
    
    sentiment, headline = get_news_sentiment(ticker)
    
    # --- LOGIKA 5 PILAR ---
    
    # 1. Volume & Value (Vol > 1.5x Avg20 AND PBV < 1.1)
    cond_vol_pbv = (current_vol > 1.5 * avg_vol_20) and (pbv < 1.1)
    
    # 2. Media Sentiment
    cond_sentiment = (sentiment == "POSITIVE")
    
    # 3. Big Player Flow (Vol > 1.8x Avg20 AND Price Stable < 3%)
    cond_big_player = (current_vol > 1.8 * avg_vol_20) and (abs(price_change_pct) < 3)
    big_player_status = "Akumulasi Bandar" if cond_big_player else "-"
    
    # 4. Analisa 3-7 Hari (MA5 > MA20)
    cond_trend = (ma5 > ma20)
    
    # --- KEPUTUSAN FINAL ---
    # Strong Buy: Semua terpenuhi (Vol/PBV + Sentiment + BigPlayer + Trend)
    # Note: Syarat "Semua Indikator" bisa sangat ketat. 
    # Kita sesuaikan sedikit: Minimal Technical/Fundamental kuat.
    
    status = "HOLD"
    color = "white"
    
    # Logic Evaluasi
    # STRONG BUY: Technical Trend Confirm + Undervalued/High Vol + Sentiment Positif
    if cond_trend and cond_vol_pbv and cond_sentiment:
        status = "🔥 STRONG BUY"
        color = "green"
    # WATCHLIST: Technical/Fundamental Oke, tapi berita netral/big player belum jelas
    elif cond_trend and (cond_vol_pbv or cond_big_player):
        status = "✅ WATCHLIST"
        color = "yellow"
    
    return {
        "Ticker": ticker,
        "Price": f"Rp {current_price:,.0f}",
        "Change": f"{price_change_pct:.2f}%",
        "Volume Ratio": f"{current_vol/avg_vol_20:.1f}x",
        "PBV": f"{pbv:.2f}x",
        "Trend (MA5>MA20)": "Bullish" if cond_trend else "Bearish",
        "Big Player": big_player_status,
        "Sentiment": sentiment,
        "Headline": headline,
        "Status": status
    }

# --- MAIN APP LOGIC ---

if st.button("🔴 EXECUTE SCAN SYSTEM"):
    with st.spinner('Accessing Market Data Feed...'):
        results = []
        progress_text = "Scanning Tickers..."
        my_bar = st.progress(0, text=progress_text)
        
        for i, ticker in enumerate(TICKERS):
            res = analyze_stock(ticker)
            if res:
                results.append(res)
            time.sleep(0.1) # Efek scanning visual
            my_bar.progress((i + 1) / len(TICKERS), text=f"Scanning {ticker}...")
            
        my_bar.empty()
        
        if results:
            df_results = pd.DataFrame(results)
            
            # Update Metrics
            with col2:
                st.metric("Potential Stocks", f"{len(df_results)} EMITEN", "Done")

            # Layout: Left (Table), Right (News/Feed) - Simulating the image layout
            # Streamlit columns for layout
            main_col, side_col = st.columns([3, 1])
            
            with main_col:
                st.markdown("### ⊕ Hasil Screening Potensial (3-7 Hari Ke Depan)")
                
                # Custom Styling for Dataframe
                def styled_dataframe(df):
                    def color_status(val):
                        if 'STRONG BUY' in val:
                            return 'color: #000; background-color: #00ff41; font-weight: bold;'
                        elif 'WATCHLIST' in val:
                            return 'color: #000; background-color: #ffff00; font-weight: bold;'
                        return ''
                        
                    return df.style.map(color_status, subset=['Status'])\
                        .format({'Price': '{}', 'PBV': '{}', 'Volume Ratio': '{}'})\
                        .set_properties(**{'background-color': '#050505', 'color': '#e0e0e0', 'border-color': '#333'})

                st.dataframe(
                    styled_dataframe(df_results), 
                    use_container_width=True, 
                    column_config={
                        "Headline": st.column_config.TextColumn("Latest News", help="Berita Terkini", width="large"),
                        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    },
                    hide_index=True
                )

            with side_col:
                st.markdown("### Latest News Feed")
                with st.container(border=True):
                    for _, row in df_results.iterrows():
                        if row['Headline'] != "Tidak ada berita terbaru":
                            color = "#00ff41" if row['Sentiment'] == "POSITIVE" else "#888"
                            st.markdown(f"""
                            <div style="margin-bottom: 10px; border-bottom: 1px dashed #333; padding-bottom: 5px;">
                                <strong style="color: {color};">[{row['Ticker']}]</strong>
                                <span style="font-size: 0.8em;">{row['Sentiment']}</span><br>
                                <span style="font-size: 0.9em; color: #ccc;">{row['Headline']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
            st.success("SCAN COMPLETED SUCCESSFULLY.")
            
        else:
            st.warning("No stocks matched criteria.")
else:
    st.info("System Ready. Click EXECUTE to start scanning.")

st.markdown("""
<br>
<center>
    <small style='color: #444;'>
        © 2026 EmitScan Indonesia | All Data Real-time Delayed 15min <br>
        Developed by <strong style='color: #00ff41;'>Wira Aditia</strong> | 
        <a href='https://www.instagram.com/wiirak_/?hl=ar' target='_blank' style='color: #00f3ff; text-decoration: none;'>@wiirak_</a>
    </small>
</center>
""", unsafe_allow_html=True)
