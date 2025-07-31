from utils import map_advantage, map_volatility, map_bonus_freq

def get_css():
    return """
    <style>
    /* Base styles */
    :root {
        --primary: #4e89ae;
        --secondary: #43658b;
        --accent: #ed6663;
        --light: #f0f2f6;
        --dark: #2e3b4e;
        --success: #27ae60;
        --danger: #e74c3c;
    }
    
    /* Sticky header */
    .ph-sticky-header {
        position: sticky;
        top: 0;
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        z-index: 100;
        margin-bottom: 20px;
    }
    
    .ph-stop-loss {
        color: var(--danger);
        font-weight: bold;
    }
    
    /* Game grid */
    .ph-game-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }
    
    .game-card {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 15px;
        transition: transform 0.3s ease;
    }
    
    .game-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .game-card h3 {
        color: var(--primary);
        margin-top: 0;
    }
    
    .positive-profit {
        color: var(--success);
        font-weight: bold;
    }
    
    .negative-profit {
        color: var(--danger);
        font-weight: bold;
    }
    
    /* Session card */
    .session-card {
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        padding: 15px;
        margin-bottom: 15px;
    }
    
    /* Add styling for filter expander */
    .filter-expander .st-emotion-cache-1j9s6t8 {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-left: 4px solid #4e89ae;
    }
    .filter-expander .st-emotion-cache-1j9s6t8:hover {
        background-color: #e6e9ef;
    }
    </style>
    """

def get_header():
    return """
    <div style="display:flex; align-items:center; margin-bottom:20px;">
        <h1 style="margin:0; color:#4e89ae;">Profit Hopper Casino Manager</h1>
        <img src="https://via.placeholder.com/100" style="margin-left:20px; border-radius:8px;">
    </div>
    """

def game_card(row):
    return f"""
    <div class="game-card">
        <h3>{row['game_name']}</h3>
        <p><strong>Type:</strong> {row['type']}</p>
        <p><strong>RTP:</strong> {row['rtp']}%</p>
        <p><strong>Min Bet:</strong> ${row['min_bet']:,.2f}</p>
        <p><strong>Volatility:</strong> {map_volatility(row['volatility'])}</p>
        <p><strong>Advantage Play:</strong> {map_advantage(row['advantage_play_potential'])}</p>
        <p><strong>Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}</p>
        <p><strong>Tips:</strong> {row['tips']}</p>
    </div>
    """