import requests
import json
import time

def get_market_data():
    print("Fetching global market data...")
    # Get global data for dominance/sectors if available, otherwise just top coins to infer
    
    # 1. Fetch Top 100 Coins to analyze sectors
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Simple Sector Inference (Hardcoded for top coins for MVP)
        # In a real app we'd use the categories endpoint or tags
        sectors = {
            'Layer 1': ['BTC', 'ETH', 'SOL', 'ADA', 'AVAX', 'DOT', 'TRX', 'NEAR', 'KAS', 'SUI', 'SEI', 'APT', 'ALGO', 'HBAR', 'XRP', 'BNB'],
            'DeFi': ['UNI', 'LINK', 'AAVE', 'MKR', 'SNX', 'CRV', 'COMP', 'RUNE', 'INJ', 'JUP', 'DYDX', 'LDO'],
            'AI & Big Data': ['TAO', 'FET', 'RNDR', 'NEAR', 'GRT', 'AGIX', 'WLD', 'OCEAN', 'JASMY', 'AKT'],
            'Meme': ['DOGE', 'SHIB', 'PEPE', 'WIF', 'BONK', 'FLOKI', 'MEME', 'BOME', 'BRETT', 'MOG'],
            'Gaming/Metaverse': ['ICP', 'IMX', 'SAND', 'MANA', 'AXS', 'GALA', 'BEAM', 'RON'],
            'Layer 2': ['MATIC', 'ARB', 'OP', 'MNT', 'STRK', 'BLAST', 'BASE'],
            'RWA': ['ONDO', 'POLYX', 'PENDLE']
        }
        
        sector_performance = {k: [] for k in sectors}
        sector_performance['Others'] = []
        
        top_picks = []
        
        print(f"Analyzing {len(data)} coins...")
        
        for coin in data:
            symbol = coin.get('symbol', '').upper()
            mcap = coin.get('market_cap') or 0
            price = coin.get('current_price') or 0
            chg_24h = coin.get('price_change_percentage_24h') or 0
            vol_24h = coin.get('total_volume') or 0
            
            # Formatting Mcap
            if mcap > 1e12: fmt_mcap = f"${mcap/1e12:.2f}T"
            elif mcap > 1e9: fmt_mcap = f"${mcap/1e9:.2f}B"
            elif mcap > 1e6: fmt_mcap = f"${mcap/1e6:.2f}M"
            else: fmt_mcap = f"${mcap:,.0f}"
            
            # Assign Sector
            assigned = False
            for sector, tickers in sectors.items():
                if symbol in tickers:
                    sector_performance[sector].append(chg_24h)
                    assigned = True
                    break
            if not assigned:
                sector_performance['Others'].append(chg_24h)
                
            # Pick potential (Volume > Mcap * 0.1 OR Surge > 5%)
            vol_ratio = vol_24h / (mcap if mcap else 1)
            if chg_24h > 5 or vol_ratio > 0.1:
                top_picks.append({
                    'Symbol': symbol,
                    'Price': price,
                    'Change': chg_24h,
                    'Mcap': fmt_mcap,
                    'Vol/Mcap': vol_ratio
                })
        
        # Calculate avg sector performance
        sector_stats = []
        for sector, changes in sector_performance.items():
            if changes:
                avg_chg = sum(changes) / len(changes)
                sector_stats.append((sector, avg_chg))
        
        sector_stats.sort(key=lambda x: x[1], reverse=True)
        
        print("\n--- SECTOR ANALYSIS (24h Avg Change) ---")
        for s, chg in sector_stats:
            print(f"{s:<20}: {chg:+.2f}%")
            
        print("\n--- POTENTIAL SECTORS FORWARD ---")
        top_sector = sector_stats[0][0]
        print(f"Top performing sector is {top_sector}. Watch for leaders in {top_sector}.")
        
        print("\n--- TOP PICK HIGHLIGHTS ---")
        # Sort by Vol/Mcap ratio (Whale activity proxy)
        top_picks.sort(key=lambda x: x['Vol/Mcap'], reverse=True)
        for p in top_picks[:10]:
            print(f"{p['Symbol']:<6} | ${p['Price']:.2f} | {p['Change']:+.2f}% | {p['Mcap']} | VolRatio: {p['Vol/Mcap']:.2f}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_market_data()
