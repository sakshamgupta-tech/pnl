import streamlit as st
import pandas as pd
import os
from io import BytesIO
import time

# Page config
st.set_page_config(
    page_title="Multi-Server Excel Merger",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem;}
    .success-box {background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #28a745;}
    .info-box {background-color: #cce5ff; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #17a2b8;}
    .stFileUploader > div > div > div {border: 2px dashed #1f77b4 !important;}
    .server-card {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;}
    .algo-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def process_excel_file(file_content, filename):
    """Process a single Excel file."""
    df_portfolios = pd.read_excel(BytesIO(file_content), sheet_name='Portfolios')
    df_users = pd.read_excel(BytesIO(file_content), sheet_name='Users')
    
    server_name = os.path.basename(filename).split(' ')[0]
    
    grouped_df = df_portfolios.groupby(['Portfolio Name', 'Strategy Tag'], as_index=False)[[
        'PNL', 'PNL Per Lot', 'CE PNL', 'PE PNL', 'Max PNL', 'Min PNL',
        'Underlying Price', 'Total Legs', 'Total Orders', 'Total Lots'
    ]].sum()
    
    grouped_df['Profit'] = grouped_df['PNL'].where(grouped_df['PNL'] > 0)
    grouped_df['Loss'] = grouped_df['PNL'].where(grouped_df['PNL'] < 0)
    grouped_df['Neutral'] = grouped_df['PNL'].where(grouped_df['PNL'] == 0)
    
    final_df = grouped_df[[
        'Portfolio Name', 'Strategy Tag', 'Profit', 'Loss', 'Neutral',
        'PNL Per Lot', 'CE PNL', 'PE PNL'
    ]].copy()
    
    final_df['SERVER'] = server_name
    
    users_filtered = df_users[df_users['SERVER'] == server_name][
        ['SERVER', 'ALGO', 'REMARK', 'OPERATOR', 'EXPIRY', 'DATE']
    ].drop_duplicates()
    
    final_df = final_df.merge(users_filtered, on='SERVER', how='left')
    
    return final_df

def create_server_summary(df):
    """Create server-wise summary with counts."""
    server_summary = df.groupby(['SERVER', 'ALGO']).agg({
        'Profit': ['sum', 'count'],
        'Loss': ['sum', 'count'],
        'Neutral': ['sum', 'count']
    }).round(2)
    
    server_summary.columns = ['Total_Profit', 'Profit_Count', 'Total_Loss', 'Loss_Count', 
                             'Total_Neutral', 'Neutral_Count']
    server_summary = server_summary.reset_index()
    
    # Calculate server totals
    server_totals = df.groupby('SERVER').agg({
        'Profit': 'sum',
        'Loss': 'sum',
        'Neutral': 'count'
    }).round(2)
    server_totals.columns = ['Server_Profit', 'Server_Loss', 'Server_Neutral_Count']
    server_totals = server_totals.reset_index()
    
    return server_summary, server_totals

def main():
    st.markdown('<h1 class="main-header">📊 Multi-Server Excel Merger</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.header("⚙️ Settings")
    max_files = st.sidebar.slider("Max Files to Upload", 1, 50, 10)
    
    # Main content
    st.markdown("### 🚀 Upload Your Excel Files")
    st.info("👉 Upload **multiple Excel files** (SUMMARY files) → **Auto-process** → **Download single CSV**")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose Excel files (SUMMARY format)",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        help="Upload multiple SUMMARY Excel files at once!"
    )
    
    if uploaded_files:
        if len(uploaded_files) > max_files:
            st.warning(f"⚠️ Maximum {max_files} files allowed. Please upload fewer files.")
            return
        
        st.success(f"✅ **{len(uploaded_files)} files uploaded successfully!**")
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_merged_data = []
        file_names = []
        
        # Process files
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            processed_df = process_excel_file(uploaded_file.read(), uploaded_file.name)
            all_merged_data.append(processed_df)
            file_names.append(uploaded_file.name)
            
            uploaded_file.seek(0)
            time.sleep(0.1)
        
        # Concatenate all dataframes
        final_merged_df = pd.concat(all_merged_data, ignore_index=True)
        
        # Create summaries
        server_summary, server_totals = create_server_summary(final_merged_df)
        
        progress_bar.progress(100)
        status_text.text(f"✅ **All {len(uploaded_files)} files processed!**")
        st.balloons()
        
        # === NEW SERVER-WISE SUMMARY SECTION ===
        st.markdown("---")
        st.markdown("## 🎯 **SERVER-WISE PROFIT/LOSS ANALYSIS**")
        
        # Server Cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="server-card">
                <h3>{len(server_totals)} Servers</h3>
                <h2>₹{server_totals['Server_Profit'].sum():,.0f}</h2>
                <p><strong>Total Profit</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="server-card">
                <h3>{len(server_summary)}</h3>
                <h2>₹{abs(server_totals['Server_Loss'].sum()):,.0f}</h2>
                <p><strong>Total Loss</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="server-card">
                <h3>{server_totals['Server_Neutral_Count'].sum()}</h3>
                <h2>{server_totals['Server_Neutral_Count'].sum()}</h2>
                <p><strong>Zero PNL Count</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        # Server-wise Detailed Table
        st.markdown("### 📊 **Server & Algo Breakdown**")
        st.dataframe(
            server_summary[['SERVER', 'ALGO', 'Total_Profit', 'Profit_Count', 
                          'Total_Loss', 'Loss_Count', 'Neutral_Count']],
            use_container_width=True,
            height=400,
            column_config={
                "Total_Profit": st.column_config.NumberColumn("💰 Profit", format="₹%.2f"),
                "Total_Loss": st.column_config.NumberColumn("📉 Loss", format="₹%.2f"),
                "Profit_Count": st.column_config.NumberColumn("✅ Profit Cnt"),
                "Loss_Count": st.column_config.NumberColumn("❌ Loss Cnt"),
                "Neutral_Count": st.column_config.NumberColumn("⭕ Zero Cnt")
            }
        )
        
        # Overall Summary Row
        st.markdown("### 📈 **SERVER TOTALS**")
        total_df = pd.DataFrame({
            'SERVER': ['🎯 ALL SERVERS'],
            'ALGO': ['TOTAL'],
            'Total_Profit': [server_summary['Total_Profit'].sum()],
            'Profit_Count': [server_summary['Profit_Count'].sum()],
            'Total_Loss': [server_summary['Total_Loss'].sum()],
            'Loss_Count': [server_summary['Loss_Count'].sum()],
            'Neutral_Count': [server_summary['Neutral_Count'].sum()]
        })
        st.dataframe(total_df, use_container_width=True)
        
        # === ORIGINAL SECTIONS (UNCHANGED) ===
        st.markdown("---")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### 📋 Summary")
            st.metric("Total Servers", len(set(final_merged_df['SERVER'].dropna())))
            st.metric("Total Portfolios", len(final_merged_df))
            st.metric("Total Profit", f"₹{final_merged_df['Profit'].sum():,.2f}")
            st.metric("Total Loss", f"₹{final_merged_df['Loss'].sum():,.2f}")
            
        with col2:
            st.markdown("### 👀 Preview Data")
            st.dataframe(
                final_merged_df.head(10),
                use_container_width=True,
                height=400
            )
        
        # Download section (UNCHANGED)
        st.markdown("---")
        st.markdown("### 💾 Download Your File")
        
        csv_buffer = BytesIO()
        final_merged_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ALL_SERVERS_MERGED_{timestamp}.csv"
        
        st.download_button(
            label="📥 Download Merged CSV",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv",
            help="Click to download the complete merged file!"
        )
        
        # ORIGINAL Processed Files Section (UNCHANGED)
        st.markdown("### ✅ Processed Files")
        for name in file_names:
            server = name.split(' ')[0]
            st.success(f"• **{server}** - {name}")
    
    else:
        st.markdown("""
        <div class="info-box">
        <strong>📝 Quick Start Guide:</strong><br>
        1. Click "Browse files" above<br>
        2. Select multiple SUMMARY Excel files<br>
        3. Wait for processing (auto)<br>
        4. See **Server-wise P&L breakdown**<br>
        5. Download single CSV file<br><br>
        <strong>💡 New Feature:</strong> **Server & Algo-wise Profit/Loss/Zero Count!**
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()