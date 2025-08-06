def get_css():
    return """
    <style>
    .ph-sticky-header {
        position: sticky;
        top: 0;
        background: white;
        z-index: 100;
        padding: 0 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Compact summary styles */
    .compact-summary {
        display: grid;
        grid-template-columns: repeat(1, 1fr);
        gap: 8px;
        margin-bottom: 20px;
    }
    
    .summary-card {
        background: white;
        border-radius: 8px;
        padding: 8px 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        transition: all 0.2s;
    }
    
    /* Strategy colors as thin left borders */
    .strategy-conservative {
        border-left: 3px solid #28a745;
    }
    
    .strategy-moderate {
        border-left: 3px solid #17a2b8;
    }
    
    .strategy-standard {
        border-left: 3px solid #ffc107;
    }
    
    .strategy-aggressive {
        border-left: 3px solid #dc3545;
    }
    
    .stop-loss {
        border-left: 3px solid #e74c3c;
    }
    
    .swipe-button {
        background-color: #ff6b6b;
        color: white;
        border: none;
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 10px auto;
        width: 100%;
    }
    
    .swipe-button:hover {
        background-color: #ff5252;
        transform: translateX(-5px);
    }
    
    .swipe-button:active {
        transform: translateX(-10px);
    }
    
    .swipe-button span {
        margin-right: 8px;
    }
    
    @media (max-width: 768px) {
        .compact-summary {
            grid-template-columns: 1fr;
        }
    }
    
    .ph-game-card {
        padding: 15px;
        margin: 15px 0;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        background-color: #f8f9fa;
        border-left: 4px solid #4e89ae;
        position: relative;
    }
    
    .ph-game-title {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 8px;
        color: #2c3e50;
    }
    
    .ph-game-score {
        font-size: 0.9rem;
        color: #27ae60;
        margin-top: -5px;
        margin-bottom: 8px;
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
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 8px;
        background-color: #f8f9fa;
        border-left: 4px solid #3498db;
    }
    
    .trip-card {
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
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
        border-radius: 4极;
        border: none;
    }
    
    .trip-info-box {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid #4caf50;
    }
    
    .trip-id-badge {
        background-color: #1976d2;
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
    """

def get_header():
    return """
    <div style="text-align:center; padding:20px 0; background:linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d); border-radius:10px; margin-bottom:30px;">
        <h1 style="color:white; margin:0;">🏆 Profit Hopper Casino Manager</h1>
        <p style="color:white; margin:0;">Smart Bankroll Management & Game Recommendations</p>
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