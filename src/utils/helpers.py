def map_advantage(value):
    mapping = {
        5: "⭐️⭐️⭐️⭐️⭐️ Excellent advantage opportunities",
        4: "⭐️⭐极️⭐️⭐️ Strong potential for skilled players",
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