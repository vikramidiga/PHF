# PHF Auction Dashboard

A comprehensive Streamlit-based analytics dashboard designed for the PHF Cricket Auction. This tool provides in-depth insights into player performance, helping teams make data-driven decisions during the auction process.

## 🚀 Features

### 1. Auction Dashboard
The central hub for analyzing the entire player pool.
- **Role-Based Views**: Dedicated tabs for **Batters**, **Bowlers**, and **All-Rounders**.
- **Interactive Visualizations**: 
    - **Aggression vs Consistency (Batting)**: A scatter plot comparing Strike Rate vs Average.
    - **Economy vs Wickets/Inning (Bowling)**: A scatter plot comparing Economy Rate vs Wickets per Inning.
    - **Quadrants**: All charts feature 25th, 50th, and 75th percentile lines (gold dashed lines) to easily identify top-tier performers (Top-Right for Batters, Top-Left for Bowlers).
    - **Bubble Size**: The size of the bubbles represents the player's **MVP Score**.
- **All-Rounders Leaderboard**: A consolidated table of top all-rounders sorted by MVP score.

### 2. Individual Profile
Detailed drill-down into a specific player's statistics.
- **Multi-Format Analysis**: View stats separated by **Tennis Ball**, **Leather Ball**, and **Overall**.
- **Key Metrics**: A card-based layout showing Runs, Wickets, Average, Strike Rate, and more.

### 3. Player Comparison
Head-to-head comparison tool.
- Select two players to compare their stats side-by-side.
- Visual bar charts for quick metric comparison.

## 🏆 MVP Calculation Logic

The Dashboard uses an advanced, **Median-based** scoring model to calculate an MVP Points score. This ensures fairness across different roles and rewards consistent performance over volume alone.

The formula normalizes a player's stats against the pool's **Median** (ignoring zero values) and scales it by **Innings Played**.

### Batting Score
```
Bat_Score = (Player_Avg / Median_Avg) * (Player_SR / Median_SR) * (0.5 if bat_inn < 5 else (1 if bat_inn < 10 else (1.2 if bat_inn < 50 else 1.5)))
```
*   Rewards players who score faster and more consistently than the median peer.
*   Heavily weighted by the number of innings to prove consistency.

### Bowling Score
```
Bowl_Score = (Player_WPI / Median_WPI) * (Median_Eco / Player_Eco) 
*(0.5 if bowl_inn < 5 else (1 if bowl_inn < 10 else (1.2 if bowl_inn < 50 else 1.5)))
```
*   **WPI**: Wickets Per Inning.
*   Rewards players who take more wickets per game and have a lower economy rate than the median peer.

### Total MVP Score
```
Total MVP = (Bat_Score + Bowl_Score) * 100
```
*   The final score is additive, allowing pure Batters and pure Bowlers to compete with All-Rounders on a single leaderboard.

## 🛠️ Setup & Running

1.  **Prerequisites**: Ensure you have Python installed.
2.  **Install Dependencies**:
    ```bash
    pip install streamlit pandas altair openpyxl requests
    ```
3.  **Run the Dashboard**:
    ```bash
    streamlit run dashboard.py
    ```
4.  **Data Source**: The app expects `1503_PHFT20_players_with_stats_enhanced.xlsx` in the root directory.

## 📂 File Structure

- `dashboard.py`: Main Streamlit application and UI logic.
- `process_player_stats.py`: Helper script for fetching and processing player data from external APIs (CricHeroes).
- `1503_PHFT20_players_with_stats_enhanced.xlsx`: The master dataset containing all player statistics.
