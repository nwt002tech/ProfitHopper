def get_css():
    return """
    <style>
    /* ... existing styles ... */
    
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
    
    /* ... existing styles ... */
    </style>
    """