from utils import map_advantage, map_volatility, map_bonus_freq

def get_css():
    return """
    <style>
    .ph-sticky-header {
        position: sticky;
        top: 0;
        background: white;
        z-index: 100;
        padding: 10px 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .ph-game-card {
        padding: 15px;
        margin: 15px 0;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        background-color: #f8f9fa;
        border-left: 4px solid #4e89ae;
    }
    
    .ph-game-title {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 8px;
        color: #2c3e50;
    }
    
    .ph-game-detail {
        margin: 6px 0;
        padding-left: 25px;
        position: relative;
        font-size: 0.95rem;
    }
    
    .ph-game-detail::before {
        content: "•";
        position: absolute;
        left: 10px;
        color: #4e89ae;
        font-size: 1.2rem;
    }
    
    .ph-stop-loss {
        color: #e74c3c;
        font-weight: bold;
    }
    
    .ph-game-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
    }
    
    @media (max-width: 768px) {
        .ph-game-grid {
            grid-template-columns: 1fr;
        }
        .ph-game-card {
            padding: 12px;
            margin: 12px 0;
        }
        .ph-game-detail {
            padding-left: 20px;
        }
        .ph-game-detail::before {
            left: 5px;
        }
    }
    
    .session-card {
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        background-color: #f8f9fa;
        border-left: 4px solid #3498db;
    }
    
    .positive-profit {
        color: #27ae60;
        font-weight: bold;
    }
    
    .negative-profit {
        color: #e74c3c;
        font-weight: bold;
    }
    
    .download-button {
        background-color: #4CAF50;
        color: white;
        padding: 8px 16px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
        border: none;
    }
    </style>
    """

def game_card(row):
    return f"""
    <div class="ph-game-card">
        <div class="ph-game-title">🎰 {row['game_name']}</div>
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