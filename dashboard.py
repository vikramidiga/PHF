import streamlit as st
import pandas as pd
import requests
import altair as alt

# Set page config
st.set_page_config(page_title="PHF Auction Season 1 - Player Stats Dashboard", layout="wide")

# CSS to inject for specific styling if needed
st.markdown("""
<style>
    /* Force center alignment for all dataframe cells - multiple selectors for maximum coverage */
    .stDataFrame th,
    .stDataFrame td,
    div[data-testid="stDataFrame"] table tbody tr td,
    div[data-testid="stDataFrame"] table thead tr th,
    div[data-testid="stDataFrame"] td,
    div[data-testid="stDataFrame"] th,
    .dataframe td,
    .dataframe th,
    table td,
    table th {
        text-align: center !important;
    }
    
    /* Additional specific targeting for styled dataframes */
    .row_heading,
    .col_heading {
        text-align: center !important;
    }
    
    /* Award box styling */
    .award-box {
        background: linear-gradient(135deg, rgba(255, 75, 75, 0.1) 0%, rgba(255, 75, 75, 0.05) 100%);
        border: 2px solid rgba(255, 75, 75, 0.3);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .award-icon {
        font-size: 48px;
        margin-bottom: 10px;
    }
    
    .award-title {
        font-size: 14px;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 5px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .award-count {
        font-size: 36px;
        font-weight: bold;
        color: #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🏏 Player Stats Dashboard")

# Load the dataset
@st.cache_data
def load_data():
    file_path = "1503_PHFT20_players_with_stats_enhanced.xlsx"
    try:
        df = pd.read_excel(file_path)
        # Clean up name column
        if 'name' in df.columns:
            df['name'] = df['name'].astype(str).str.strip()
        
        # Fix types for Arrow compatibility
        if 'cricheroes' in df.columns:
            df['cricheroes'] = df['cricheroes'].astype(str)
        if 'extracted_id' in df.columns:
            df['extracted_id'] = df['extracted_id'].astype(str)
            
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

df = load_data()

def clean_and_convert_numeric(df):
    # List of columns that must be numeric
    # Batting
    bat_cols = ['Overall_Batting_Runs', 'Overall_Batting_Avg', 'Overall_Batting_SR', 
                'Overall_Batting_Mat', 'Overall_Batting_4s', 'Overall_Batting_6s']
    # Bowling
    bowl_cols = ['Overall_Bowling_Wkts', 'Overall_Bowling_Eco', 'Overall_Bowling_Avg', 
                 'Overall_Bowling_SR', 'Overall_Bowling_Mat', 'Overall_Bowling_Overs']
    
    # Specific cleanup for High Score (remove *)
    if 'Overall_Batting_HS' in df.columns:
        df['Overall_Batting_HS'] = df['Overall_Batting_HS'].astype(str).str.replace('*', '', regex=False)
        df['Overall_Batting_HS'] = pd.to_numeric(df['Overall_Batting_HS'], errors='coerce').fillna(0)

    all_numeric = bat_cols + bowl_cols
    for col in all_numeric:
        if col in df.columns:
            # Force numeric, turning non-parseable things (like '-') into NaN then 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

df = clean_and_convert_numeric(df)

# --- feature: Auction Metrics ---
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def calculate_derived_metrics(df):
    if df.empty: return df
    
    # helper for safe division
    def safe_div(n, d):
        return n / d if d > 0 else 0.0

    # 1. Calculate Wickets Per Inning (Global)
    # Use 'Overall_Bowling_Inns' if available, else 'Overall_Bowling_Mat'
    df['Overall_Bowling_WPI'] = df.apply(lambda r: safe_div(r.get('Overall_Bowling_Wkts', 0), r.get('Overall_Bowling_Inns', 0)), axis=1)

    # 2. Statistics for normalization (Median, ignoring zeros)
    # Batting
    bat_avg_series = df[df['Overall_Batting_Avg'] > 0]['Overall_Batting_Avg']
    bat_sr_series = df[df['Overall_Batting_SR'] > 0]['Overall_Batting_SR']
    bat_inn_series = df[df['Overall_Batting_Inns'] > 0]['Overall_Batting_Inns']
    
    pop_avg = bat_avg_series.median() if not bat_avg_series.empty else 20.0
    pop_sr = bat_sr_series.median() if not bat_sr_series.empty else 100.0
    pop_bat_inns = bat_inn_series.median() if not bat_inn_series.empty else 5.0
    
    # Bowling
    bowl_wpi_series = df[df['Overall_Bowling_WPI'] > 0]['Overall_Bowling_WPI']
    bowl_eco_series = df[df['Overall_Bowling_Eco'] > 0]['Overall_Bowling_Eco']
    bowl_inn_series = df[df['Overall_Bowling_Inns'] > 0]['Overall_Bowling_Inns']
    
    pop_wpi = bowl_wpi_series.median() if not bowl_wpi_series.empty else 1.0
    pop_eco = bowl_eco_series.median() if not bowl_eco_series.empty else 7.0
    pop_bowl_inns = bowl_inn_series.median() if not bowl_inn_series.empty else 5.0

    mvp_scores = []
    roles = []
    
    for _, row in df.iterrows():
        # Batting Components
        avg = row.get('Overall_Batting_Avg', 0)
        sr = row.get('Overall_Batting_SR', 0)
        bat_inn = row.get('Overall_Batting_Inns', 0)
        
        # Batting Performance Score
        # (Quality * Quality) * Normalized Volume
        bat_factor = (avg / pop_avg) * (sr / pop_sr)
        bat_score = bat_factor * (0.5 if bat_inn < 5 else (1 if bat_inn < 10 else (1.2 if bat_inn < 50 else 1.5)))
        
        # Bowling Components
        wpi = row.get('Overall_Bowling_WPI', 0)
        eco = row.get('Overall_Bowling_Eco', 0)
        bowl_inn = row.get('Overall_Bowling_Inns', 0)
        
        # Bowling Performance Score
        # For Economy, lower is better: Med_Eco / Eco
        eco_factor = 0
        if eco > 0:
            eco_factor = pop_eco / eco
        elif bowl_inn > 0:
            # If innings > 0 but eco is 0, it means perfect bowling (maiden?) or data issue.
            # Assign a strong multiplier (e.g., 2x median performance)
            eco_factor = 2.0 
            
        bowl_factor = (wpi / pop_wpi) * eco_factor
        bowl_score = bowl_factor * (0.5 if bowl_inn < 5 else (1 if bowl_inn < 10 else (1.2 if bowl_inn < 50 else 1.5)))
        
        # Total MVP
        # Additive to reward specialists as well as all-rounders
        # Scale factor (e.g. * 100) to make numbers readable
        total_mvp = (bat_score + bowl_score) * 100
        mvp_scores.append(total_mvp)
        
        # Role Inference
        runs = row.get('Overall_Batting_Runs', 0)
        wickets = row.get('Overall_Bowling_Wkts', 0)
        is_bowler = wickets > 9
        is_batter = runs > 200
        
        if is_bowler and is_batter:
            role = 'All-Rounder'
        elif is_bowler:
            role = 'Bowler'
        elif is_batter:
            role = 'Batter'
        else:
            role = 'Newcomer' 
            
        roles.append(role)
        
    df['MVP_Points'] = mvp_scores
    df['Inferred_Role'] = roles
    return df

df = calculate_derived_metrics(df)

# Helper to normalize stats
def normalize_stats(row, category, stat_type):
    stats = {}
    prefix = f"{category}_{stat_type}"
    
    if stat_type == 'Batting':
        mapping = {
            'Matches': f'{prefix}_Mat',
            'Innings': f'{prefix}_Inns',
            'Not Out': f'{prefix}_NO',
            'Runs': f'{prefix}_Runs',
            'High Score': f'{prefix}_HS',
            'Avg': f'{prefix}_Avg',
            'SR': f'{prefix}_SR',
            '100s': f'{prefix}_100s',
            '50s': f'{prefix}_50s',
            '30s': f'{prefix}_30s',
            '4s': f'{prefix}_4s',
            '6s': f'{prefix}_6s',
            'Ducks': f'{prefix}_Ducks'
        }
    else: # Bowling
        mapping = {
            'Matches': f'{prefix}_Mat',
            'Innings': f'{prefix}_Inns',
            'Overs': f'{prefix}_Overs',
            'Maidens': f'{prefix}_Maidens',
            'Runs': f'{prefix}_Runs',
            'Wickets': f'{prefix}_Wkts',
            'Best': f'{prefix}_BB',
            'Avg': f'{prefix}_Avg',
            'Eco': f'{prefix}_Eco',
            'SR': f'{prefix}_SR',
            '3w': f'{prefix}_3 Wkts',
            '5w': f'{prefix}_5 Wkts',
            'Wides': f'{prefix}_WD',
            'NB': f'{prefix}_NB'
        }

    for standard_col, raw_col in mapping.items():
        val = row.get(raw_col, 0)
        # Handle NaN
        if pd.isna(val) or str(val) == 'nan':
             val = 0
        stats[standard_col] = val
        
    return stats

def safe_int(val):
    try:
        f = float(val)
        if f.is_integer():
            return int(f)
        return f
    except:
        return val

def format_value(val, key):
    # Formatting rules
    # Float columns: Avg, SR, Eco
    # Float columns: Avg, SR, Eco, Overs
    float_cols = ['Avg', 'SR', 'Eco', 'Overs']
    if any(x in key for x in float_cols):
        try:
            val_str = str(val).replace('*', '') # Handle 12.34* if any
            if val_str == '-' or val_str == '': return val
            return "{:.2f}".format(float(val_str))
        except:
            return val
    
    # High Score should be string to handle 50 and 50* consistently without Arrow errors
    if 'HS' in key or 'High Score' in key:
        return str(val)
            
    # Integer columns: everything else usually
    # But check if it's strictly numeric
    try:
        f = float(val)
        if f.is_integer():
            return int(f)
        return f # Return float if not integer
    except:
        return val # Return string (e.g. "5/20")

if df.empty:
    st.error("Could not load data.")
else:
    # Main Tab Navigation
    st.markdown("""
    <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
             background-color: rgba(255, 255, 255, 0.05);
             border-bottom: 2px solid #FF4B4B;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Define Tabs
    tab_auction, tab_profile , tab_compare = st.tabs([
        "🔨 Auction Dashboard",
        "👤 Individual Profile", 
        "⚖️ Player Comparison"
       
    ])

    # --- 1. Individual Profile ---
    with tab_profile:
        st.markdown("### Individual Profile Search")
        if 'name' in df.columns:
            players_list = sorted(df['name'].unique().tolist())
            selected_player = st.selectbox(
                "Choose a player", 
                options=players_list,
                placeholder="Search..."
            )
            
            if selected_player:
                player_row = df[df['name'] == selected_player].iloc[0]
                
                # --- Reuse existing profile layout logic ---
                
                st.subheader(f"Player Profile: {selected_player}", divider='red')
                
                # Extract CricHeroes Info
                ch_raw = str(player_row.get('cricheroes', ''))
                
                # Format extracted_id as int if possible
                eid = player_row.get('extracted_id', pd.NA)
                ch_display = "N/A"
                if pd.notna(eid):
                    try:
                        ch_display = str(int(eid))
                    except:
                        ch_display = str(eid)

                ch_link = None
                if ch_raw and ch_raw.lower() != 'nan' and 'cricheroes' in ch_raw.lower():
                    ch_link = ch_raw
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**CricHeroes Profile ID:** {ch_display}")
                    if ch_link:
                        st.markdown(f"🔗 [View Profile]({ch_link})", unsafe_allow_html=True)
                with col2:
                    st.info(f"**Player Type:** {player_row.get('playertype', 'N/A')}")
                with col3:
                    st.info(f"**Team Owner:** {player_row.get('Team Owner', 'N/A')}")
                
                # Batting
                t_bat = normalize_stats(player_row, 'Tennis', 'Batting')
                l_bat = normalize_stats(player_row, 'Leather', 'Batting')
                o_bat = normalize_stats(player_row, 'Overall', 'Batting')
                
                bat_data = [t_bat, l_bat, o_bat]
                df_bat_prof = pd.DataFrame(bat_data, index=['Tennis', 'Leather', 'Overall'])
                
                # Force High Score 'HS' to string to avoid Arrow mixed-type error
                # Check for likely names from normalize_stats
                for col in df_bat_prof.columns:
                     if 'HS' in col or 'High Score' in col:
                         df_bat_prof[col] = df_bat_prof[col].astype(str)

                for col in df_bat_prof.columns:
                    df_bat_prof[col] = df_bat_prof[col].apply(lambda x: format_value(x, col))

                # Bowling
                t_bowl = normalize_stats(player_row, 'Tennis', 'Bowling')
                l_bowl = normalize_stats(player_row, 'Leather', 'Bowling')
                o_bowl = normalize_stats(player_row, 'Overall', 'Bowling')
                
                bowl_data = [t_bowl, l_bowl, o_bowl]
                df_bowl_prof = pd.DataFrame(bowl_data, index=['Tennis', 'Leather', 'Overall'])
                for col in df_bowl_prof.columns:
                    df_bowl_prof[col] = df_bowl_prof[col].apply(lambda x: format_value(x, col))
                
                st.markdown("#### Batting Stats")
                st.dataframe(df_bat_prof.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
                
                st.markdown("#### Bowling Stats")
                st.dataframe(df_bowl_prof.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
                
                # Awards Section
                st.markdown("#### Awards")
                
                # Get award counts
                best_batter = int(player_row.get('BEST BATTER', 0)) if pd.notna(player_row.get('BEST BATTER', 0)) else 0
                best_bowler = int(player_row.get('BEST BOWLER', 0)) if pd.notna(player_row.get('BEST BOWLER', 0)) else 0
                potm = int(player_row.get('PLAYER OF THE MATCH', 0)) if pd.notna(player_row.get('PLAYER OF THE MATCH', 0)) else 0
                
                award_col1, award_col2, award_col3 = st.columns(3)
                with award_col1:
                    st.markdown(f"""
                    <div class="award-box">
                        <div class="award-icon">🏏</div>
                        <div class="award-title">Best Batter</div>
                        <div class="award-count">{best_batter}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with award_col2:
                    st.markdown(f"""
                    <div class="award-box">
                        <div class="award-icon">🥎</div>
                        <div class="award-title">Best Bowler</div>
                        <div class="award-count">{best_bowler}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with award_col3:
                    st.markdown(f"""
                    <div class="award-box">
                        <div class="award-icon">🏆</div>
                        <div class="award-title">Player of the Match</div>
                        <div class="award-count">{potm}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.error("Name column missing.")

    # --- 2. Player Comparison ---
    with tab_compare:
        st.markdown("### Player Comparison")
        players_to_compare = st.multiselect("Select Players to Compare", options=sorted(df['name'].unique()), max_selections=4)
        
        if players_to_compare:
            df_comp = df[df['name'].isin(players_to_compare)]
            
            # Helper for metrics
            def safe_metric_fmt(val, is_int=False):
                # Handle NaN, None, and empty values
                if pd.isna(val) or val is None or str(val).lower() == 'nan':
                    return "0" if is_int else "0.00"
                try:
                    f = float(str(val).replace('*', ''))
                    if is_int:
                        return f"{int(f)}"
                    return f"{f:.2f}"
                except:
                    return "0" if is_int else "0.00"

            cols = st.columns(len(players_to_compare))
            for idx, player in enumerate(players_to_compare):
                p_data = df_comp[df_comp['name'] == player].iloc[0]
                with cols[idx]:
                    st.success(f"**{player}**")
                    st.metric("MVP Score", safe_metric_fmt(p_data.get('MVP_Points', 0), is_int=False))
                    st.markdown("---")
                    st.metric("Runs", safe_metric_fmt(p_data.get('Overall_Batting_Runs', 0), is_int=True))
                    st.metric("Bat Avg", safe_metric_fmt(p_data.get('Overall_Batting_Avg', 0), is_int=False))
                    st.metric("Bat SR", safe_metric_fmt(p_data.get('Overall_Batting_SR', 0), is_int=False))
                    st.markdown("---")
                    st.metric("Wickets", safe_metric_fmt(p_data.get('Overall_Bowling_Wkts', 0), is_int=True))
                    st.metric("Bowl Eco", safe_metric_fmt(p_data.get('Overall_Bowling_Eco', 0), is_int=False))
                    st.metric("Bowl Avg", safe_metric_fmt(p_data.get('Overall_Bowling_Avg', 0), is_int=False))
                    st.markdown("---")
                    st.metric("🏏 Best Batter", safe_metric_fmt(p_data.get('BEST BATTER', 0), is_int=True))
                    st.metric("🥎 Best Bowler", safe_metric_fmt(p_data.get('BEST BOWLER', 0), is_int=True))
                    st.metric("🏆 POTM", safe_metric_fmt(p_data.get('PLAYER OF THE MATCH', 0), is_int=True))

    # --- 3. Auction Dashboard ---
    with tab_auction:
        st.markdown("### Auction Data Pool")
        
        # Sub-tabs for roles
        subtab_bat, subtab_bowl, subtab_ar = st.tabs(["🏏 Batters", "🥎 Bowlers", "🌟 All-Rounders"])
        
        with subtab_bat:
            st.markdown("#### Top Batsmen")
            # Filter cols
            bat_cols = ['name', 'Overall_Batting_Runs', 'Overall_Batting_Avg', 'Overall_Batting_SR', 'Overall_Batting_Mat', 'Overall_Batting_HS', 'Overall_Batting_4s', 'Overall_Batting_6s', 'BEST BATTER', 'MVP_Points']
            # Rename for display
            bat_disp_map = {
                'name': 'Name', 'Overall_Batting_Runs': 'Runs', 'Overall_Batting_Avg': 'Avg', 
                'Overall_Batting_SR': 'SR', 'Overall_Batting_Mat': 'Mat', 'Overall_Batting_HS': 'HS',
                'Overall_Batting_4s': '4s', 'Overall_Batting_6s': '6s', 'BEST BATTER': '🏏 Awards', 'MVP_Points': 'MVP'
            }
            
            df_bat = df[bat_cols].copy()
            df_bat.rename(columns=bat_disp_map, inplace=True)
            
            # Ensure numeric for formatting
            numeric_cols = ['Runs', 'Avg', 'SR', 'MVP', 'Mat', '4s', '6s', '🏏 Awards']
            for col in numeric_cols:
                df_bat[col] = pd.to_numeric(df_bat[col], errors='coerce').fillna(0)
            
            # Interactive Dataframe
            styled_df = df_bat.style.format({
                'Avg': "{:.2f}", 
                'SR': "{:.2f}", 
                'MVP': "{:.0f}",
                'Runs': "{:.0f}",
                'Mat': "{:.0f}",
                'HS': "{:.0f}",
                '4s': "{:.0f}",
                '6s': "{:.0f}",
                '🏏 Awards': "{:.0f}"
            }).background_gradient(subset=['Runs', 'SR', 'MVP'], cmap='Greens')
            
            # Apply center alignment using set_table_styles
            styled_df = styled_df.set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center')]},
                {'selector': 'td', 'props': [('text-align', 'center')]}
            ])
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=500
            )
            
            # Scatter Plot with Percentile Lines
            st.markdown("##### 📊 Aggression vs Consistency")
            
            # Base Chart
            base_bat = alt.Chart(df).mark_circle(size=60).encode(
                x=alt.X('Overall_Batting_SR', title='Strike Rate'),
                y=alt.Y('Overall_Batting_Avg', title='Average'),
                color=alt.Color('Inferred_Role', legend=alt.Legend(title="Role", titleColor='white', labelColor='white')),
                size=alt.Size('MVP_Points', legend=alt.Legend(title="MVP", titleColor='white', labelColor='white', symbolFillColor='lightgray')),
                tooltip=['name', 'Overall_Batting_Runs', 'Overall_Batting_Avg', 'Overall_Batting_SR', 'MVP_Points']
            ).interactive()
            
            # Percentile Lines (Ignoring Zeros)
            sr_series = df[df['Overall_Batting_SR'] > 0]['Overall_Batting_SR']
            avg_series = df[df['Overall_Batting_Avg'] > 0]['Overall_Batting_Avg']
            
            x_quantiles = sr_series.quantile([0.25, 0.50, 0.75]).tolist() if not sr_series.empty else []
            y_quantiles = avg_series.quantile([0.25, 0.50, 0.75]).tolist() if not avg_series.empty else []
            
            rules_x = alt.Chart(pd.DataFrame({'x': x_quantiles})).mark_rule(color='#FFD700', strokeDash=[5,5], opacity=0.8).encode(x='x')
            rules_y = alt.Chart(pd.DataFrame({'y': y_quantiles})).mark_rule(color='#FFD700', strokeDash=[5,5], opacity=0.8).encode(y='y')
            
            final_chart_bat = (base_bat + rules_x + rules_y)
            
            st.altair_chart(final_chart_bat, use_container_width=True)

        with subtab_bowl:
            st.markdown("#### Top Bowlers")
            bowl_cols = ['name', 'Overall_Bowling_Wkts', 'Overall_Bowling_Eco', 'Overall_Bowling_Avg', 'Overall_Bowling_SR', 'Overall_Bowling_Mat', 'Overall_Bowling_BB', 'BEST BOWLER', 'MVP_Points']
            bowl_disp_map = {
                'name': 'Name', 'Overall_Bowling_Wkts': 'Wickets', 'Overall_Bowling_Eco': 'Eco',
                'Overall_Bowling_Avg': 'Avg', 'Overall_Bowling_SR': 'SR', 'Overall_Bowling_Mat': 'Mat',
                'Overall_Bowling_BB': 'Best', 'BEST BOWLER': '🥎 Awards', 'MVP_Points': 'MVP'
            }
            
            df_bowl = df[bowl_cols].copy()
            df_bowl.rename(columns=bowl_disp_map, inplace=True)
            
            # Ensure numeric for formatting
            numeric_cols_bowl = ['Wickets', 'Eco', 'Avg', 'SR', 'MVP', 'Mat', '🥎 Awards']
            for col in numeric_cols_bowl:
                df_bowl[col] = pd.to_numeric(df_bowl[col], errors='coerce').fillna(0)
            
            # Interactive Dataframe
            styled_df_bowl = df_bowl.style.format({
                'Eco': "{:.2f}", 
                'Avg': "{:.2f}", 
                'SR': "{:.2f}", 
                'MVP': "{:.0f}",
                'Wickets': "{:.0f}",
                'Mat': "{:.0f}",
                '🥎 Awards': "{:.0f}"
            }).background_gradient(subset=['Wickets', 'Eco', 'MVP'], cmap='Blues')
            
            # Apply center alignment using set_table_styles
            styled_df_bowl = styled_df_bowl.set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center')]},
                {'selector': 'td', 'props': [('text-align', 'center')]}
            ])
            
            st.dataframe(
                styled_df_bowl,
                use_container_width=True,
                height=500
            )
            
            st.markdown("##### 🎯 Economy vs Wickets per Inning")
            
            # Base Chart
            base_bowl = alt.Chart(df).mark_circle(size=60).encode(
                x=alt.X('Overall_Bowling_Eco', title='Economy'),
                y=alt.Y('Overall_Bowling_WPI', title='Wickets / Inning'),
                color=alt.Color('Inferred_Role', legend=alt.Legend(title="Role", titleColor='white', labelColor='white')),
                size=alt.Size('MVP_Points', legend=alt.Legend(title="MVP", titleColor='white', labelColor='white', symbolFillColor='lightgray')),
                tooltip=['name', 'Overall_Bowling_Wkts', 'Overall_Bowling_WPI', 'Overall_Bowling_Eco', 'MVP_Points']
            ).interactive()
            
            # Percentile Lines (Ignoring Zeros)
            eco_series = df[df['Overall_Bowling_Eco'] > 0]['Overall_Bowling_Eco']
            wpi_series = df[df['Overall_Bowling_WPI'] > 0]['Overall_Bowling_WPI']
            
            x_metrics_bowl = eco_series.quantile([0.25, 0.50, 0.75]).tolist() if not eco_series.empty else []
            y_metrics_bowl = wpi_series.quantile([0.25, 0.50, 0.75]).tolist() if not wpi_series.empty else []
            
            rules_x_bowl = alt.Chart(pd.DataFrame({'x': x_metrics_bowl})).mark_rule(color='#FFD700', strokeDash=[5,5], opacity=0.8).encode(x='x')
            rules_y_bowl = alt.Chart(pd.DataFrame({'y': y_metrics_bowl})).mark_rule(color='#FFD700', strokeDash=[5,5], opacity=0.8).encode(y='y')
            
            final_chart_bowl = (base_bowl + rules_x_bowl + rules_y_bowl)
            
            st.altair_chart(final_chart_bowl, use_container_width=True)

        with subtab_ar:
            st.markdown("#### All-Rounders & MVP Leaderboard")
            # Filter for All-Rounders
            df_ar = df[df['Inferred_Role'] == 'All-Rounder'].copy()
            
            ar_cols = ['name', 'MVP_Points', 'Overall_Batting_Runs', 'Overall_Bowling_Wkts', 'Overall_Batting_SR', 'Overall_Bowling_Eco', 'BEST BATTER', 'BEST BOWLER', 'PLAYER OF THE MATCH']
            ar_disp_map = {
                'name': 'Name', 'MVP_Points': 'MVP Score', 
                'Overall_Batting_Runs': 'Runs', 'Overall_Bowling_Wkts': 'Wickets',
                'Overall_Batting_SR': 'Bat SR', 'Overall_Bowling_Eco': 'Bowl Eco',
                'BEST BATTER': '🏏 Bat Awards', 'BEST BOWLER': '🥎 Bowl Awards', 'PLAYER OF THE MATCH': '🏆 POTM'
            }
            
            df_ar_view = df_ar[ar_cols].copy().rename(columns=ar_disp_map)
            
            # Ensure numeric
            numeric_cols_ar = ['MVP Score', 'Bat SR', 'Bowl Eco', 'Runs', 'Wickets', '🏏 Bat Awards', '🥎 Bowl Awards', '🏆 POTM']
            for col in numeric_cols_ar:
                df_ar_view[col] = pd.to_numeric(df_ar_view[col], errors='coerce').fillna(0)
            
            # Default Sort Descending by MVP Score
            df_ar_view = df_ar_view.sort_values(by='MVP Score', ascending=False)
            
            
            styled_df_ar = df_ar_view.style.format({
                'MVP Score': "{:.0f}", 
                'Bat SR': "{:.2f}", 
                'Bowl Eco': "{:.2f}",
                'Runs': "{:.0f}",
                'Wickets': "{:.0f}",
                '🏏 Bat Awards': "{:.0f}",
                '🥎 Bowl Awards': "{:.0f}",
                '🏆 POTM': "{:.0f}"
            }).highlight_max(subset=['MVP Score'], color='lightgreen', axis=0)
            
            # Apply center alignment using set_table_styles
            styled_df_ar = styled_df_ar.set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center')]},
                {'selector': 'td', 'props': [('text-align', 'center')]}
            ])
            
            st.dataframe(
                styled_df_ar,
                use_container_width=True,
                height=800
            )
            
            # st.markdown("##### ⚖️ Balance of Play")
