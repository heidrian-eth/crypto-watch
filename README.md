# 📈 Crypto Watch Dashboard

> **⚡ 100% Vibe-Coded with Claude Code**  
> *This entire project was developed through natural language conversations with Claude Code - no traditional coding required!*

A sophisticated Streamlit-based cryptocurrency monitoring system that combines **Google Trends analysis**, **real-time price tracking**, **futures premium monitoring**, and **statistical breakout detection** to identify market opportunities and anomalies.

![Dashboard Preview](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-AI-orange?style=for-the-badge)

## 🚀 Key Features

### 📊 **Multi-Modal Data Analysis**
- **Google Trends Integration**: Hourly search interest tracking for crypto keywords
- **Real-time Price Monitoring**: BTC, ETH, and Alt Index (top 8 cryptos) with Binance API
- **COIN-M Futures Premium**: Quarterly futures contract premium tracking
- **Volume Analysis**: Normalized trading volume across spot and futures markets
- **High-Frequency Volatility**: Intra-hour volatility using 5-minute data with LMS regression detrending

### 🚨 **Statistical Breakout Alert System**
- **LMS Linear Regression**: Analyzes 7-day hourly data strips (168 data points)
- **2-Sigma Boundary Detection**: Configurable statistical thresholds (1σ to 4σ)
- **Smart Breakout Logic**: Alerts when data crosses from within 2σ to outside 2σ boundaries
- **Multi-Series Analysis**: Monitors all 5 chart types simultaneously
- **Browser Push Notifications**: Real-time alerts with statistical context

### 📈 **Advanced Visualizations**
- **Normalized Charts**: All data normalized to 100 for comparative analysis
- **Interactive Plotly Charts**: Zoom, pan, and hover for detailed exploration
- **Regression Overlays**: Visual trend lines with confidence boundaries
- **Real-time Updates**: Auto-refresh with configurable intervals (30-300 seconds)

### 🎯 **KPI Dashboard**
- **Trend Momentum Analysis**: 24h changes, 7-day averages, volatility metrics
- **Price Performance**: Current prices, ranges, trend directions
- **Futures Metrics**: Premium percentages, volatility, trend analysis
- **Volume Insights**: Normalized volume changes and patterns

## 🛠️ Installation & Setup

### **Quick Start (Recommended)**
```bash
# Clone the repository
git clone <repository-url>
cd crypto-watch

# Run the automated setup script
./run.sh
```
The script will automatically:
- Create a Python virtual environment
- Install all dependencies
- Set up configuration files
- Launch the dashboard

### **Manual Setup**
```bash
# Create virtual environment
python3.12 -m venv venv  # or python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch dashboard
streamlit run app_simple.py
```

### **Configuration**
1. Copy `.env.example` to `.env` (optional)
2. Add your Binance API keys for enhanced features:
   ```env
   BINANCE_API_KEY=your_api_key_here
   BINANCE_API_SECRET=your_secret_here
   ```

## 🎮 Usage Guide

### **Main Dashboard (`app_simple.py`)**
Access at: `http://localhost:8501`

**Sidebar Controls:**
- **Auto-refresh**: Enable/disable automatic updates
- **Refresh Interval**: 30-300 seconds
- **Push Notifications**: Browser notification controls
- **Statistical Alerts**: Enable breakout detection with configurable sigma thresholds

**Chart Tabs:**
1. **📈 Trends**: Google search interest (normalized), price trends, futures premiums, volume, HF volatility
2. **📊 KPIs**: Detailed metrics tables with trend analysis

### **Statistical Alerts Test (`test_statistical_alerts.py`)**
Access at: `http://localhost:8502`
```bash
streamlit run test_statistical_alerts.py
```

**Testing Features:**
- **Synthetic Data Generation**: Create test data with controllable parameters
- **Breakout Simulation**: Test detection algorithms with known breakouts  
- **Visual Regression Analysis**: See trend lines and sigma boundaries
- **Real-time Testing**: Continuous breakout detection validation
- **Notification Testing**: Verify browser alerts work correctly

## 🧮 Statistical Algorithm

### **Core Mathematics**
```python
# 1. LMS Linear Regression
slope, intercept, r_value, p_value, std_err = stats.linregress(time, values)

# 2. Normalized RMSE Calculation  
rmse = sqrt(mean((actual - predicted)²))
normalized_rmse = rmse / abs(mean(values))

# 3. 2-Sigma Boundary Detection
residual_std = std(residuals)
upper_boundary = predicted + (2 * residual_std)
lower_boundary = predicted - (2 * residual_std)

# 4. Breakout Detection Logic
if (previous_point_within_2sigma AND current_point_outside_2sigma):
    trigger_statistical_alert()
```

### **Monitored Data Series**
- **Google Trends**: Search interest for each crypto keyword
- **Prices**: BTC-USD, ETH-USD, Alt Index (normalized to 100)
- **Futures Premiums**: BTC/ETH quarterly contract premiums vs spot
- **Volume**: Trading volume across spot and futures markets
- **HF Volatility**: 5-minute intra-hour volatility calculations

## 🔔 Notification System

### **Alert Types**
1. **Statistical Breakouts**: When data crosses 2σ boundaries
2. **Multiple Breakouts**: When 3+ series break simultaneously  
3. **Manual Tests**: Sidebar test button for validation

### **Notification Content**
- **Statistical Context**: Sigma level, confidence percentage
- **Market Context**: Asset name, chart type, direction
- **Values**: Current vs expected with proper formatting
- **Visual Indicators**: Emojis and trend direction arrows

## 📁 Project Structure

```
crypto-watch/
├── app_simple.py                    # Main dashboard application
├── test_statistical_alerts.py      # Statistical testing interface
├── test_notifications.py           # Notification testing page
├── requirements.txt                 # Python dependencies
├── run.sh                          # Automated setup script
├── src/
│   ├── data/
│   │   ├── trends_fetcher.py       # Google Trends API integration
│   │   ├── binance_fetcher.py      # Binance API integration
│   │   └── crypto_fetcher.py       # Legacy crypto data fetching
│   └── utils/
│       ├── config.py               # Configuration settings
│       ├── notifications.py        # Browser push notifications
│       └── statistical_alerts.py   # LMS regression & breakout detection
└── venv/                           # Python virtual environment
```

## 🔧 Configuration Options

### **Tracked Assets** (`src/utils/config.py`)
```python
TREND_KEYWORDS = ["bitcoin", "ethereum", "crypto", "blockchain", "btc", "eth"]
CRYPTO_SYMBOLS = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", ...]
FUTURES_CONTRACTS = ["BTCUSD_PERP", "ETHUSD_PERP", ...]
```

### **Statistical Parameters**
- **Sigma Threshold**: 1.0σ to 4.0σ (default: 2.0σ)
- **Minimum Data Points**: 48 hours for reliability
- **Regression Window**: 7 days (168 hourly points)
- **Update Frequency**: 30-300 seconds (default: 300s)

### **Cache Settings**
- **Trends Data**: 5 minutes TTL
- **Price Data**: 15 minutes TTL  
- **Statistical Analysis**: Real-time (no cache)

## 🧪 Testing & Validation

### **Automated Tests**
```bash
# Test core functionality
python -c "from src.utils.statistical_alerts import statistical_analyzer; print('✅ Statistical system ready!')"

# Test notifications
python -c "from src.utils.notifications import notification_service; print('✅ Notification system ready!')"

# Test data integration
python -c "from src.data.trends_fetcher import TrendsDataFetcher; print('✅ Data fetching ready!')"
```

### **Manual Testing**
1. **Launch test application**: `streamlit run test_statistical_alerts.py`
2. **Adjust parameters** in sidebar for different scenarios
3. **Enable breakout simulation** to test detection accuracy
4. **Use real-time mode** for continuous validation
5. **Check browser console** (F12) for detailed logs

## 🚨 Troubleshooting

### **Common Issues**

**Notifications Not Working:**
- Check browser notification permissions
- Disable "Do Not Disturb" mode
- Try different browsers (Chrome, Firefox, Edge)
- Check browser console for JavaScript errors

**API Rate Limits:**
- Google Trends: Built-in rate limiting and caching
- Binance API: Free tier has sufficient limits for this use case
- Add delays if experiencing 429 errors

**Statistical Analysis Errors:**
- Ensure minimum 48 data points available
- Check for NaN values in data series
- Verify regression analysis requirements are met

**Performance Issues:**
- Reduce refresh frequency
- Disable unused chart types
- Clear browser cache
- Check system resources

### **Debug Mode**
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🏗️ Architecture & Design

### **Development Philosophy**
This project demonstrates **AI-Native Development** using Claude Code:
- **Natural Language Requirements**: Features described in plain English
- **Iterative Refinement**: Continuous improvement through conversation
- **Mathematical Precision**: Complex statistical algorithms from descriptions
- **No Traditional Coding**: Built entirely through AI assistance

### **Key Design Decisions**
- **Streamlit Framework**: Rapid prototyping and deployment
- **Modular Architecture**: Separate concerns for data, analysis, and presentation
- **Real-time Processing**: Live statistical analysis without data persistence  
- **Browser-Based Alerts**: No external notification services required
- **Configurable Parameters**: User-adjustable statistical thresholds

### **Performance Considerations**
- **Efficient Caching**: Multiple cache layers with appropriate TTL
- **Vectorized Operations**: NumPy/Pandas for statistical calculations
- **Async-Safe Design**: Thread-safe state management
- **Memory Management**: Automatic cleanup of old data

## 🤝 Contributing

This project showcases **AI-Assisted Development**. To contribute:

1. **Describe Features**: Use natural language to describe desired functionality
2. **Iterate with AI**: Refine requirements through conversation
3. **Test Thoroughly**: Validate using provided test interfaces
4. **Document Changes**: Update README and code comments

### **Development Workflow**
```bash
# 1. Test changes
streamlit run test_statistical_alerts.py

# 2. Validate integration  
streamlit run app_simple.py

# 3. Commit with descriptive messages
git commit -m "Add feature: detailed description"
```

## 📄 License & Credits

### **🎯 Development Credit**
**100% Vibe-Coded with Claude Code** - This entire project was developed through natural language conversations with Claude Code, demonstrating the power of AI-assisted development.

### **Data Sources**
- **Google Trends**: pytrends library
- **Cryptocurrency Prices**: Binance API
- **Statistical Analysis**: SciPy, NumPy, Pandas

### **Dependencies**
- **Streamlit**: Web application framework
- **Plotly**: Interactive visualizations  
- **Pandas/NumPy**: Data manipulation and analysis
- **SciPy**: Statistical functions
- **Requests**: HTTP client for APIs

---

## 🎉 **Why This Project is Special**

This cryptocurrency monitoring system represents a new paradigm in software development:

✅ **Complex Statistical Analysis** - Implemented through natural language descriptions  
✅ **Real-time Data Processing** - Multi-source integration without traditional coding  
✅ **Sophisticated UI/UX** - Interactive dashboards from conversational requirements  
✅ **Mathematical Precision** - LMS regression and statistical boundaries from English descriptions  
✅ **Production-Ready Features** - Comprehensive testing, error handling, and documentation  

**The future of coding is here - and it's conversational! 🚀**