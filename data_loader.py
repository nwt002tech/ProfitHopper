import pandas as pd
import streamlit as st
from utils import normalize_column_name

@st.cache_data(ttl=3600)
def load_game_data():
    try:
        url = "https://raw.githubusercontent.com/nwt002tech/profit-hopper/main/extended_game_list.csv"
        df = pd.read_csv(url)
        
        df.columns = [normalize_column_name(col) for col in df.columns]
        
        col_map = {
            'rtp': ['rtp', 'expected_rtp'],
            'min_bet': ['min_bet', 'minbet', 'minimum_bet', 'min_bet_amount'],
            'advantage_play_potential': ['advantage_play_potential', 'app', 'advantage_potential'],
            'volatility': ['volatility', 'vol'],
            'bonus_frequency': ['bonus_frequency', 'bonus_freq', 'bonus_rate'],
            'game_name': ['game_name', 'name', 'title', 'game'],
            'type': ['type', 'game_type', 'category'],
            'tips': ['tips', 'tip', 'strategy']
        }
        
        for standard, variants in col_map.items():
            for variant in variants:
                if variant in df.columns:
                    df[standard] = df[variant]
                    break
        
        required_cols = ['rtp', 'min_bet']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"Missing required columns: {', '.join(missing)}")
            return pd.DataFrame()
        
        numeric_cols = ['rtp', 'min_bet', 'advantage_play_potential', 'volatility', 'bonus_frequency']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'advantage_play_potential' not in df.columns:
            df['advantage_play_potential'] = 3
        if 'volatility' not in df.columns:
            df['volatility'] = 3
        if 'bonus_frequency' not in df.columns:
            df['bonus_frequency'] = 0.2
            
        if 'game_name' not in df.columns:
            df['game_name'] = "Unknown Game"
        if 'type' not in df.columns:
            df['type'] = "Unknown"
        if 'tips' not in df.columns:
            df['tips'] = "No tips available"
        
        return df.dropna(subset=['rtp', 'min_bet'])
    except Exception as e:
        st.error(f"Error loading game data: {str(e)}")
        return pd.DataFrame()