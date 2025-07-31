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
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="color: #4e89ae; margin-bottom: 0;">Profit Hopper Casino Manager</h1>
        <p style="color: #43658b; margin-top: 5px;">Maximize your casino profits with data-driven strategies</p>
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

def trip_info_box(trip_id, casino, starting_bankroll, current_bankroll):
    profit = current_bankroll - starting_bankroll
    profit_class = "positive-profit" if profit >= 0 else "negative-profit"
    
    return f"""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 15px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin:0;">Trip #{trip_id}</h3>
                <p style="margin:0;"><strong>Casino:</strong> {casino}</p>
            </div>
            <div style="text-align: right;">
                <p style="margin:0;"><strong>Starting Bankroll:</strong> ${starting_bankroll:,.2f}</p>
                <p style="margin:0;"><strong>Current Bankroll:</strong> ${current_bankroll:,.2f}</p>
                <p style="margin:0;"><span class="{profit_class}">Profit/Loss: ${profit:+,.2f}</span></p>
            </div>
        </div>
    </div>
    """