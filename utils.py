import re
import base64
import pandas as pd
import urllib.parse

def map_advantage(value):
    mapping = {
        5: "⭐️⭐️⭐️⭐️⭐️ Excellent advantage opportunities",
        4: "⭐️⭐️⭐️⭐️ Strong potential for skilled players",
        3: "⭐️⭐️⭐️ Moderate advantage play value",
        2: "⭐️⭐️ Low advantage value",
        1: "⭐️ Minimal advantage potential"
    }
    return mapping.get(value, "Unknown")

def map_volatility(value):
    mapping = {
        1: "📈 Very low volatility (frequent small wins)",
        2: "📈 Low volatility",
        3: "📊 Medium volatility",
        4: "📉 High volatility",
        5: "📉 Very high volatility (rare big wins)"
    }
    return mapping.get(value, "Unknown")

def map_bonus_freq(value):
    if value >= 0.4:
        return "🎁🎁🎁 Very frequent bonuses"
    elif value >= 0.3:
        return "🎁🎁 Frequent bonus features"
    elif value >= 0.2:
        return "🎁 Occasional bonuses"
    elif value >= 0.1:
        return "🎁 Rare bonuses"
    else:
        return "🎁 Very rare bonuses"

def normalize_column_name(name):
    return re.sub(r'\W+', '_', name.lower().strip())

def get_csv_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'

def get_game_image_url(game_name, default_image=None):
    """Generate a Google image search URL for the game"""
    if default_image and not pd.isna(default_image):
        return default_image
    query = f"{game_name} slot machine"
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?tbm=isch&q={encoded_query}"