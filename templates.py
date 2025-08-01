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
            <strong>💡 Tips:</strong> {row['tips']}
        </div>
    </div>
    """