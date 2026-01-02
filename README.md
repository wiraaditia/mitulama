# 📊 EmitScan Indonesia

**Professional Stock Screener with AI-Powered Sentiment Analysis**

EmitScan Indonesia adalah platform analisis saham Indonesia yang powerful, menggabungkan analisis teknikal, fundamental, dan AI-powered sentiment analysis dari berbagai sumber berita terpercaya.

![EmitScan Indonesia](https://img.shields.io/badge/version-2.0-green) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.31+-red)

---

## ✨ Fitur Utama

### 🤖 AI News Intelligence
- **Multi-Source News Aggregation**: Mengambil berita dari CNBC Indonesia, CNN Indonesia, dan sumber terpercaya lainnya
- **Advanced Sentiment Scoring**: Sistem scoring 0-100 dengan 5 kategori (VERY POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, VERY NEGATIVE)
- **Impact Prediction**: Prediksi dampak berita terhadap harga saham (HIGH/MEDIUM/LOW)
- **News Timeline**: Timeline berita terkini dengan source attribution
- **Deep Analysis**: Analisis mendalam dengan AI-generated insights

### 📈 Technical Analysis
- **Moving Average Trend**: MA5 vs MA20 untuk identifikasi trend
- **Volume Analysis**: Deteksi volume spike dan akumulasi big players
- **Valuation Metrics**: PBV analysis untuk identifikasi undervalued stocks

### 🎯 Smart Screener
- **50+ Emiten**: Coverage saham-saham populer dan aktif di IDX
- **5 Pillars Logic**: Kombinasi trend, volume, valuation, sentiment, dan big player activity
- **Auto-Refresh**: Data ter-update setiap 10 menit
- **Real-time Scanning**: Progress bar untuk monitoring scan process

### 📰 Professional UI
- **Stockbit-Style Design**: Dark mode dengan gradient effects
- **Interactive Charts**: TradingView integration untuk technical analysis
- **Responsive Layout**: Optimized untuk desktop dan mobile
- **Dynamic Badges**: Color-coded sentiment dan impact indicators
- **Progress Bars**: Visual sentiment score representation

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 atau lebih tinggi
- pip (Python package manager)

### Installation

1. **Clone repository**
```bash
git clone https://github.com/wiraaditia/emitscanindonesia.git
cd emitscanindonesia
```

2. **Create virtual environment** (recommended)
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# atau
source .venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run application**
```bash
streamlit run app.py
```

5. **Open browser**
```
http://localhost:8501
```

---

## 📦 Dependencies

- `streamlit` - Web framework
- `yfinance` - Stock data provider
- `pandas` - Data manipulation
- `requests` - HTTP requests
- `beautifulsoup4` - Web scraping
- `streamlit-autorefresh` - Auto-refresh functionality

---

## 🎯 Usage

### 1. Run Screener
Klik tombol **"RUN SCREENER"** untuk memulai scanning 50+ emiten di IDX.

### 2. View Results
- **Left Panel**: Market Screener Result (tabel lengkap)
- **Right Panel**: AI News Intelligence (news cards)

### 3. Explore Analysis
- Klik **"View Chart"** untuk melihat TradingView chart
- Expand **"Deep Analysis"** untuk insight mendalam:
  - AI Analysis Summary
  - Technical Indicators
  - News Timeline
  - Investment Reasoning
  - Final Recommendation

### 4. Interpret Signals
- 🔥 **STRONG BUY**: 3+ indikator positif, high conviction
- ✅ **WATCHLIST**: 2 indikator positif, perlu monitoring
- **HOLD**: Kurang dari 2 indikator positif

---

## 🧠 How It Works

### Sentiment Scoring Algorithm

```python
# Keyword-based scoring
VERY POSITIVE (+20): rekor, melesat, booming, akuisisi, dividen jumbo
POSITIVE (+10): laba, naik, ekspansi, dividen, tumbuh
NEUTRAL (0): baseline
NEGATIVE (-10): rugi, turun, anjlok, PHK, gagal
VERY NEGATIVE (-20): bangkrut, skandal, fraud, suspend
```

### Impact Analysis
```python
if score >= 70 or score <= 30:
    impact = "HIGH"  # Dampak tinggi dalam 1-3 hari
elif score >= 60 or score <= 40:
    impact = "MEDIUM"  # Dampak sedang
else:
    impact = "LOW"  # Dampak rendah
```

### 5 Pillars Logic
1. **Trend**: MA5 > MA20 (Bullish momentum)
2. **Volume**: Volume ratio > 1.5x (High interest)
3. **Valuation**: PBV < 1.2x (Undervalued)
4. **Sentiment**: Score >= 55 (Positive news)
5. **Big Player**: Volume spike + low volatility (Accumulation)

---

## 📊 Features Breakdown

### Multi-Source News Aggregation
- Scraping otomatis dari 2+ sumber media
- Error handling untuk setiap source
- Rate limiting untuk anti-blocking
- User-Agent rotation

### Advanced Sentiment Analysis
- 5 kategori sentiment dengan scoring 0-100
- Keyword detection dengan weighted scoring
- Context-aware analysis
- Source credibility weighting

### Professional UI Components
- Gradient news cards dengan hover effects
- Dynamic sentiment badges (5 colors)
- Impact indicators dengan icons
- Progress bars untuk sentiment scores
- Smooth animations dan transitions

---

## 🎨 Design Philosophy

EmitScan Indonesia mengadopsi design philosophy dari platform trading profesional seperti Stockbit dan TradingView:

- **Dark Mode First**: Mengurangi eye strain untuk monitoring jangka panjang
- **Information Density**: Maksimalkan informasi tanpa overwhelming user
- **Visual Hierarchy**: Color coding untuk quick decision making
- **Responsive Design**: Seamless experience across devices
- **Performance**: Caching dan optimization untuk fast loading

---

## 🔒 Data Sources

- **Stock Data**: Yahoo Finance (yfinance)
- **News**: CNBC Indonesia, CNN Indonesia
- **Charts**: TradingView Widget
- **Market Data**: IDX (Indonesia Stock Exchange)

**Disclaimer**: Data delayed 15 minutes. Untuk trading decisions, gunakan data real-time dari broker.

---

## 📈 Roadmap

### Version 2.1 (Coming Soon)
- [ ] More news sources (Detik Finance, Kontan, Bisnis.com)
- [ ] Historical sentiment tracking
- [ ] Sentiment vs Price correlation analysis
- [ ] Email/Telegram alerts
- [ ] Portfolio tracking

### Version 3.0 (Future)
- [ ] GPT-4 integration untuk advanced NLP
- [ ] Machine learning untuk price prediction
- [ ] Social media sentiment (Twitter, Reddit)
- [ ] Insider trading detection
- [ ] Sector rotation analysis

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👨‍💻 Developer

**Wira Aditia**
- Instagram: [@wiirak_](https://instagram.com/wiirak_)
- GitHub: [@wiraaditia](https://github.com/wiraaditia)

---

## ⚠️ Disclaimer

EmitScan Indonesia adalah tools untuk **edukasi dan research purposes only**. Bukan merupakan rekomendasi investasi. Selalu lakukan due diligence sendiri dan konsultasi dengan financial advisor sebelum membuat keputusan investasi.

**Investasi mengandung risiko. Past performance tidak menjamin future results.**

---

## 🙏 Acknowledgments

- Yahoo Finance untuk stock data API
- CNBC Indonesia & CNN Indonesia untuk news sources
- TradingView untuk charting widget
- Streamlit team untuk amazing framework
- Indonesian trading community untuk feedback dan support

---

## 📞 Support

Jika ada pertanyaan atau issues, silakan:
- Open an issue di GitHub
- Contact via Instagram: [@wiirak_](https://instagram.com/wiirak_)

---

**Made with ❤️ for Indonesian Traders**

🇮🇩 **#IndonesiaTrading #StockAnalysis #AIpowered**
