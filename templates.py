from utils import map_advantage, map_volatility, map_bonus_freq

def get_css():
    return """
    <style>
    /* ... existing CSS ... */
    </style>
    """

def get_header():
    return """
    <div style="text-align:center; padding:20px 0; background:linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d); border-radius:10px; margin-bottom:30px;">
        <h1 style="color:white; margin:0;">🏆 Profit Hopper Casino Manager</h1>
        <p style="color:white; margin:0;">Smart Bankroll Management & Game Recommendations</p>
    </div>
    """

def game_card(row):
    # Add score if available, otherwise show N/A
    score = f"{row['Score']:.1f}/10" if 'Score' in row else "N/A"
    
    return f"""
    <div class="ph-game-card">
        <div class="ph-game-title">🎰 {row['game_name']} <span style="font-size:0.9rem; color:#27ae60;">⭐ Score: {score}</span></div>
        <div class="ph-game-detail">
            <strong>🗂️ Type:</strong> {row['type']}
        </div>
        <div class="ph-game-detail">
            <strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}
        </div>
        <div class="ph-game-detail">
            <strong>🧠 Advantage Play:</strong> {map_advantage(int(row['advantage_play_potential']))}
        </div>
        <div class="ph-game-detail">
            <strong>🎲 Volatility:</strong> {map_volatility(int(row['volatility']))}
        </div>
        <div class="ph-game-detail">
            <strong>🎁 Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}
        </div>
        <div class="ph-game-detail">
            <strong>🔢 RTP:</strong> {row['rtp']:.2f}%
        </div>
        <div class="ph-game-detail">
            <strong>💡 Tips:</极客
            <strong>💡 Tips:</strong> {row['tips']}
        </div>
    </div>
    """

def trip_info_box(trip_id, casino, starting_bankroll, current_bankroll):
    profit = current_bankroll - starting_bankroll
    profit_class = "positive-profit" if profit >= 0 else "negative-profit"
    
    return f"""
    <div class="trip-info-box">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <div><strong>Current Trip:</strong> #{trip_id}</div>
            <div><strong>Casino:</strong> {casino}</div>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <div><strong>Starting Bankroll:</strong> ${starting_bankroll:,.2f}</div>
            <div><strong>Current Bankroll:</strong> ${current_bankroll:,.2f}</div>
        </div>
        <div style="margin-top:10px; text-align:center;">
            <span class="{profit_class}">Profit/Loss: ${profit:+,.2f}</span>
        </div>
    </div>
    """