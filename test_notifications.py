#!/usr/bin/env python3
"""
Test script for the notification system
"""
import streamlit as st
from datetime import datetime
from src.utils.notifications import notification_service

st.set_page_config(
    page_title="Notification Test",
    page_icon="🔔",
    layout="wide"
)

st.title("🔔 Push Notification Test")
st.markdown("Use this page to test the push notification system")

# Current time info
current_time = datetime.now()
current_minute = current_time.minute
minutes_mod_5 = current_minute % 5
should_trigger = minutes_mod_5 == 0

st.info(f"""
**Current Time:** {current_time.strftime('%H:%M:%S')}  
**Current Minute:** {current_minute}  
**Minutes % 5:** {minutes_mod_5}  
**Should Trigger Alert:** {'✅ Yes' if should_trigger else '❌ No'}

The alert system triggers when the current minute is divisible by 5 (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55).
""")

# Notification controls
st.header("🧪 Test Controls")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔐 Request Permission"):
        notification_service.request_permission()
        st.success("Permission request sent to browser")

with col2:
    if st.button("🔔 Test Notification"):
        notification_service.send_test_notification()
        st.success("Test notification sent!")
        st.info("👀 Check browser console (F12 → Console) for debug info")

with col3:
    if st.button("📈 Sample Trend Alert"):
        notification_service.send_trend_alert("Bitcoin", 75.0, 12.5)
        st.success("Sample trend alert sent!")

# Auto-refresh to show time updates
if st.checkbox("Auto-refresh (5 seconds)", value=False):
    import time
    time.sleep(5)
    st.rerun()

st.markdown("---")
st.markdown("**Instructions:**")
st.markdown("1. Click 'Request Permission' to allow browser notifications")
st.markdown("2. Click 'Test Notification' to send a test notification")
st.markdown("3. Wait for a time when the minute is divisible by 5 (like 16:50, 16:55, etc.) to see automatic alerts")
st.markdown("4. Check your browser's notification settings if notifications don't appear")

st.markdown("---")
st.markdown("**Troubleshooting:**")
st.markdown("- **Open browser console** (F12 → Console tab) to see debug messages")
st.markdown("- **Chrome/Edge**: Check notification permissions in Settings → Privacy → Site Settings → Notifications")
st.markdown("- **Firefox**: Check permissions by clicking the lock icon next to the URL")
st.markdown("- **Safari**: Check Preferences → Websites → Notifications")
st.markdown("- **Make sure your browser supports notifications** (most modern browsers do)")
st.markdown("- **Disable 'Do Not Disturb' mode** on your system")
st.markdown("- **Some browsers block notifications on localhost** - try on a proper domain if issues persist")