import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import requests
import time
from datetime import datetime
import scipy.stats as stats

# Page configuration
st.set_page_config(
    page_title="Real-time Sensor Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for real-time features
st.markdown("""
<style>
    .realtime-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 0.5rem;
        border-left: 4px solid #3498db;
    }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background: #00ff00;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# API base URL
API_BASE = "http://localhost:3000/api"

class RealTimeDashboard:
    def __init__(self):
        self.data = None
        self.realtime_data = []
        self.current_data = None
        self.max_realtime_points = 50
        self.load_data()
    
    def load_data(self):
        """Load all data from the API"""
        try:
            response = requests.get(f"{API_BASE}/all-data")
            if response.status_code == 200:
                self.data = response.json()
                self.df = pd.DataFrame(self.data)
                st.success(f"✅ Loaded {len(self.data)} complete records")
            else:
                st.error("❌ Failed to load data from API")
        except Exception as e:
            st.error(f"❌ Error connecting to API: {e}")
    
    def get_current_data(self):
        """Get current real-time data"""
        try:
            response = requests.get(f"{API_BASE}/current-data")
            if response.status_code == 200:
                return response.json()
        except:
            return None
    
    def update_realtime_data(self, data):
        """Update real-time data buffer"""
        if data:
            data['timestamp'] = datetime.now()
            self.realtime_data.append(data)
            
            # Keep only recent data
            if len(self.realtime_data) > self.max_realtime_points:
                self.realtime_data.pop(0)
            
            self.current_data = data
    
    def create_realtime_header(self):
        """Create real-time status header"""
        st.markdown("""
        <div style="text-align: center;">
            <h1>📊 Real-time Sensor Analytics</h1>
            <p><span class="live-indicator"></span> Live data streaming from your sensors</p>
        </div>
        """, unsafe_allow_html=True)
    
    def create_realtime_metrics(self):
        """Create real-time metrics dashboard"""
        st.subheader("📈 Live Dashboard")
        
        if not self.current_data:
            st.info("📡 Waiting for real-time data...")
            return
        
        # Current values in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🌡️ Temperature</h3>
                <div style="font-size: 2.5rem; font-weight: bold; color: #e74c3c;">
                    {self.current_data['temperature']:.1f}°C
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💧 Humidity</h3>
                <div style="font-size: 2.5rem; font-weight: bold; color: #3498db;">
                    {self.current_data['humidity']:.1f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🔋 Battery</h3>
                <div style="font-size: 2.5rem; font-weight: bold; color: #27ae60;">
                    {self.current_data['battery_voltage']:.2f}V
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            motion_color = "#e67e22" if self.current_data['motion'] > 0 else "#95a5a6"
            motion_text = "ACTIVE" if self.current_data['motion'] > 0 else "INACTIVE"
            st.markdown(f"""
            <div class="metric-card">
                <h3>🚶 Motion</h3>
                <div style="font-size: 2.5rem; font-weight: bold; color: {motion_color};">
                    {motion_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def create_realtime_charts(self):
        """Create real-time charts"""
        if len(self.realtime_data) < 2:
            st.info("📡 Collecting real-time data...")
            return
        
        # Convert to DataFrame for easier manipulation
        realtime_df = pd.DataFrame(self.realtime_data)
        realtime_df['time_index'] = range(len(realtime_df))
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Real-time Temperature & Humidity
            fig_temp_hum = go.Figure()
            fig_temp_hum.add_trace(go.Scatter(
                x=realtime_df['time_index'],
                y=realtime_df['temperature'],
                name='Temperature',
                line=dict(color='#e74c3c', width=3),
                mode='lines+markers'
            ))
            fig_temp_hum.add_trace(go.Scatter(
                x=realtime_df['time_index'],
                y=realtime_df['humidity'],
                name='Humidity',
                line=dict(color='#3498db', width=3),
                mode='lines+markers'
            ))
            fig_temp_hum.update_layout(
                title="Real-time Temperature & Humidity",
                xaxis_title="Time Index",
                yaxis_title="Values",
                height=400
            )
            st.plotly_chart(fig_temp_hum, use_container_width=True)
        
        with col2:
            # Real-time Battery & Motion
            fig_battery_motion = go.Figure()
            fig_battery_motion.add_trace(go.Scatter(
                x=realtime_df['time_index'],
                y=realtime_df['battery_voltage'],
                name='Battery Voltage',
                line=dict(color='#27ae60', width=3),
                mode='lines+markers'
            ))
            # Add motion as bars
            fig_battery_motion.add_trace(go.Bar(
                x=realtime_df['time_index'],
                y=realtime_df['motion'],
                name='Motion',
                marker_color='#e67e22',
                opacity=0.6
            ))
            fig_battery_motion.update_layout(
                title="Real-time Battery & Motion",
                xaxis_title="Time Index",
                yaxis_title="Values",
                height=400
            )
            st.plotly_chart(fig_battery_motion, use_container_width=True)
        
        # Real-time combined chart
        fig_combined = go.Figure()
        fig_combined.add_trace(go.Scatter(
            x=realtime_df['time_index'],
            y=realtime_df['temperature'],
            name='Temperature',
            line=dict(color='#e74c3c', width=2)
        ))
        fig_combined.add_trace(go.Scatter(
            x=realtime_df['time_index'],
            y=realtime_df['humidity'],
            name='Humidity',
            line=dict(color='#3498db', width=2)
        ))
        fig_combined.add_trace(go.Scatter(
            x=realtime_df['time_index'],
            y=realtime_df['battery_voltage'],
            name='Battery',
            line=dict(color='#27ae60', width=2)
        ))
        fig_combined.update_layout(
            title="Real-time Combined Sensor Data",
            xaxis_title="Time Index",
            yaxis_title="Values",
            height=500
        )
        st.plotly_chart(fig_combined, use_container_width=True)
    
    def create_historical_analysis(self):
        """Create historical analysis section"""
        st.header("📊 Historical Analysis")
        
        if self.data is None:
            st.warning("No historical data available")
            return
        
        tab1, tab2, tab3 = st.tabs(["Time Series", "Distributions", "Correlations"])
        
        with tab1:
            self.create_time_series_analysis()
        
        with tab2:
            self.create_distribution_analysis()
        
        with tab3:
            self.create_correlation_analysis()
    
    def create_time_series_analysis(self):
        """Time series analysis"""
        if self.df is None or len(self.df) == 0:
            st.warning("No data available for time series analysis")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature over time
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=list(range(len(self.df))),
                y=self.df['temperature'],
                name='Temperature',
                line=dict(color='#e74c3c', width=2)
            ))
            fig_temp.update_layout(
                title='Temperature Over Time',
                xaxis_title='Time Index',
                yaxis_title='Temperature (°C)',
                height=400
            )
            st.plotly_chart(fig_temp, use_container_width=True)
        
        with col2:
            # Humidity over time
            fig_hum = go.Figure()
            fig_hum.add_trace(go.Scatter(
                x=list(range(len(self.df))),
                y=self.df['humidity'],
                name='Humidity',
                line=dict(color='#3498db', width=2)
            ))
            fig_hum.update_layout(
                title='Humidity Over Time',
                xaxis_title='Time Index',
                yaxis_title='Humidity (%)',
                height=400
            )
            st.plotly_chart(fig_hum, use_container_width=True)
        
        # Battery and Motion over time
        col3, col4 = st.columns(2)
        
        with col3:
            fig_batt = go.Figure()
            fig_batt.add_trace(go.Scatter(
                x=list(range(len(self.df))),
                y=self.df['battery_voltage'],
                name='Battery Voltage',
                line=dict(color='#27ae60', width=2)
            ))
            fig_batt.update_layout(
                title='Battery Voltage Over Time',
                xaxis_title='Time Index',
                yaxis_title='Voltage (V)',
                height=400
            )
            st.plotly_chart(fig_batt, use_container_width=True)
        
        with col4:
            fig_motion = go.Figure()
            fig_motion.add_trace(go.Scatter(
                x=list(range(len(self.df))),
                y=self.df['motion'],
                name='Motion',
                line=dict(color='#e67e22', width=1),
                mode='markers'
            ))
            fig_motion.update_layout(
                title='Motion Detection Over Time',
                xaxis_title='Time Index',
                yaxis_title='Motion Detected',
                height=400
            )
            st.plotly_chart(fig_motion, use_container_width=True)
    
    def create_distribution_analysis(self):
        """Distribution analysis"""
        if self.df is None or len(self.df) == 0:
            st.warning("No data available for distribution analysis")
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Temperature distribution
            fig_temp_dist = go.Figure()
            fig_temp_dist.add_trace(go.Histogram(
                x=self.df['temperature'],
                name='Temperature',
                marker_color='#e74c3c',
                opacity=0.7
            ))
            fig_temp_dist.update_layout(
                title='Temperature Distribution',
                xaxis_title='Temperature (°C)',
                yaxis_title='Frequency',
                height=400
            )
            st.plotly_chart(fig_temp_dist, use_container_width=True)
        
        with col2:
            # Humidity distribution
            fig_hum_dist = go.Figure()
            fig_hum_dist.add_trace(go.Histogram(
                x=self.df['humidity'],
                name='Humidity',
                marker_color='#3498db',
                opacity=0.7
            ))
            fig_hum_dist.update_layout(
                title='Humidity Distribution',
                xaxis_title='Humidity (%)',
                yaxis_title='Frequency',
                height=400
            )
            st.plotly_chart(fig_hum_dist, use_container_width=True)
        
        with col3:
            # Battery distribution
            fig_batt_dist = go.Figure()
            fig_batt_dist.add_trace(go.Histogram(
                x=self.df['battery_voltage'],
                name='Battery Voltage',
                marker_color='#27ae60',
                opacity=0.7
            ))
            fig_batt_dist.update_layout(
                title='Battery Voltage Distribution',
                xaxis_title='Voltage (V)',
                yaxis_title='Frequency',
                height=400
            )
            st.plotly_chart(fig_batt_dist, use_container_width=True)
        
        # Box plots for all sensors
        st.subheader("Statistical Summary")
        fig_box = go.Figure()
        fig_box.add_trace(go.Box(y=self.df['temperature'], name='Temperature', marker_color='#e74c3c'))
        fig_box.add_trace(go.Box(y=self.df['humidity'], name='Humidity', marker_color='#3498db'))
        fig_box.add_trace(go.Box(y=self.df['battery_voltage'], name='Battery', marker_color='#27ae60'))
        fig_box.update_layout(
            title="Sensor Data Distributions",
            height=400
        )
        st.plotly_chart(fig_box, use_container_width=True)
    
    def create_correlation_analysis(self):
        """Correlation analysis without statsmodels"""
        if self.df is None or len(self.df) == 0:
            st.warning("No data available for correlation analysis")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature vs Humidity scatter plot
            fig_corr1 = px.scatter(
                self.df, 
                x='temperature', 
                y='humidity',
                title='Temperature vs Humidity',
                color_discrete_sequence=['#3498db']
            )
            # Add manual trend line
            if len(self.df) > 1:
                z = np.polyfit(self.df['temperature'], self.df['humidity'], 1)
                p = np.poly1d(z)
                fig_corr1.add_trace(go.Scatter(
                    x=self.df['temperature'],
                    y=p(self.df['temperature']),
                    name='Trend',
                    line=dict(color='red', dash='dash')
                ))
            st.plotly_chart(fig_corr1, use_container_width=True)
        
        with col2:
            # Temperature vs Battery scatter plot
            fig_corr2 = px.scatter(
                self.df, 
                x='temperature', 
                y='battery_voltage',
                title='Temperature vs Battery Voltage',
                color_discrete_sequence=['#27ae60']
            )
            # Add manual trend line
            if len(self.df) > 1:
                z = np.polyfit(self.df['temperature'], self.df['battery_voltage'], 1)
                p = np.poly1d(z)
                fig_corr2.add_trace(go.Scatter(
                    x=self.df['temperature'],
                    y=p(self.df['temperature']),
                    name='Trend',
                    line=dict(color='red', dash='dash')
                ))
            st.plotly_chart(fig_corr2, use_container_width=True)
        
        # Correlation matrix
        st.subheader("Correlation Matrix")
        numeric_df = self.df[['temperature', 'humidity', 'battery_voltage']]
        correlation_matrix = numeric_df.corr()
        
        fig_corr_matrix = go.Figure(data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.columns,
            colorscale='Blues',
            text=correlation_matrix.round(3).values,
            texttemplate='%{text}',
            hoverinfo='z'
        ))
        
        fig_corr_matrix.update_layout(
            title="Sensor Correlation Matrix",
            height=400
        )
        st.plotly_chart(fig_corr_matrix, use_container_width=True)
        
        # Display correlation values
        st.write("**Correlation Coefficients:**")
        st.dataframe(correlation_matrix.round(3), use_container_width=True)
    
    def show_data_summary(self):
        """Show data summary"""
        st.header("📋 Data Summary")
        
        if self.df is not None and len(self.df) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", len(self.df))
                st.metric("Temperature Avg", f"{self.df['temperature'].mean():.1f}°C")
                
            with col2:
                st.metric("Humidity Avg", f"{self.df['humidity'].mean():.1f}%")
                st.metric("Battery Avg", f"{self.df['battery_voltage'].mean():.2f}V")
                
            with col3:
                motion_count = len(self.df[self.df['motion'] > 0])
                st.metric("Motion Detections", motion_count)
                detection_rate = (motion_count / len(self.df)) * 100
                st.metric("Detection Rate", f"{detection_rate:.1f}%")
                
            with col4:
                # Calculate correlation manually
                if len(self.df) > 1:
                    corr = np.corrcoef(self.df['temperature'], self.df['humidity'])[0,1]
                    st.metric("Temp-Humidity Correlation", f"{corr:.3f}")
            
            # Show raw data preview
            with st.expander("View Raw Data"):
                st.dataframe(self.df, use_container_width=True)

def main():
    # Initialize dashboard
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = RealTimeDashboard()
        st.session_state.last_update = datetime.now()
    
    dashboard = st.session_state.dashboard
    
    # Sidebar controls
    st.sidebar.title("🎮 Dashboard Controls")
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 2)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Actions")
    
    if st.sidebar.button("🔄 Refresh Data"):
        dashboard.load_data()
        st.rerun()
    
    if st.sidebar.button("📊 Show Data Summary"):
        dashboard.show_data_summary()
        st.rerun()
    
    # Real-time data update
    if auto_refresh:
        current_data = dashboard.get_current_data()
        if current_data:
            dashboard.update_realtime_data(current_data)
    
    # Display dashboard sections
    dashboard.create_realtime_header()
    dashboard.create_realtime_metrics()
    dashboard.create_realtime_charts()
    
    st.markdown("---")
    dashboard.create_historical_analysis()
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()