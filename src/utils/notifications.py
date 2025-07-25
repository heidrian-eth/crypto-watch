import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from typing import Optional, Literal
import json


class NotificationService:
    """Service for sending push notifications in Streamlit applications"""
    
    def __init__(self):
        self.is_enabled = True
        self.notification_permission = None
    
    def request_permission(self):
        """Request notification permission from the browser"""
        permission_js = """
        <script>
        if ('Notification' in window) {
            if (Notification.permission === 'default') {
                Notification.requestPermission().then(function (permission) {
                    if (permission === 'granted') {
                        console.log('Notification permission granted');
                        window.parent.postMessage({type: 'notification_permission', permission: 'granted'}, '*');
                    } else {
                        console.log('Notification permission denied');
                        window.parent.postMessage({type: 'notification_permission', permission: 'denied'}, '*');
                    }
                });
            } else {
                window.parent.postMessage({type: 'notification_permission', permission: Notification.permission}, '*');
            }
        } else {
            console.log('Notifications not supported');
            window.parent.postMessage({type: 'notification_permission', permission: 'not_supported'}, '*');
        }
        </script>
        """
        components.html(permission_js, height=0)
    
    def send_browser_notification(
        self,
        title: str,
        body: str,
        icon: Optional[str] = None,
        tag: Optional[str] = None,
        sound: bool = True,
        duration: int = 5000
    ):
        """Send a browser push notification"""
        if not self.is_enabled:
            return
        
        # Escape quotes in title and body more carefully
        title = title.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')
        body = body.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')
        
        # Default icon (crypto-related emoji as fallback)
        if not icon:
            icon = "data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3e%3ctext y='24' font-size='24'%3e📈%3c/text%3e%3c/svg%3e"
        
        notification_js = f"""
        <script>
        console.log('Starting notification script...');
        
        function sendNotification() {{
            console.log('sendNotification called');
            console.log('Notification support:', 'Notification' in window);
            console.log('Notification permission:', Notification.permission);
            
            if ('Notification' in window) {{
                if (Notification.permission === 'granted') {{
                    console.log('Permission granted, creating notification...');
                    try {{
                        const notification = new Notification('{title}', {{
                            body: '{body}',
                            icon: '{icon}',
                            tag: '{tag or "crypto_alert"}',
                            requireInteraction: false,
                            silent: {str(not sound).lower()}
                        }});
                        
                        console.log('Notification created successfully');
                        
                        // Auto-close notification after duration
                        setTimeout(() => {{
                            notification.close();
                            console.log('Notification auto-closed');
                        }}, {duration});
                        
                        notification.onclick = function() {{
                            console.log('Notification clicked');
                            window.focus();
                            notification.close();
                        }};
                        
                        notification.onshow = function() {{
                            console.log('Notification shown');
                        }};
                        
                        notification.onerror = function(error) {{
                            console.error('Notification error:', error);
                        }};
                        
                    }} catch (error) {{
                        console.error('Error creating notification:', error);
                    }}
                }} else if (Notification.permission === 'default') {{
                    console.log('Permission not granted, requesting...');
                    Notification.requestPermission().then(function (permission) {{
                        console.log('Permission response:', permission);
                        if (permission === 'granted') {{
                            sendNotification();
                        }}
                    }});
                }} else {{
                    console.log('Notification permission denied or not supported');
                }}
            }} else {{
                console.log('Notifications not supported by browser');
            }}
        }}
        
        // Execute immediately
        sendNotification();
        </script>
        """
        components.html(notification_js, height=0)
    
    def send_alert(
        self,
        message: str,
        alert_type: Literal["info", "success", "warning", "error"] = "info",
        show_notification: bool = True
    ):
        """Send both a Streamlit alert and browser notification"""
        # Send Streamlit alert
        if alert_type == "info":
            st.info(message)
        elif alert_type == "success":
            st.success(message)
        elif alert_type == "warning":
            st.warning(message)
        elif alert_type == "error":
            st.error(message)
        
        # Send browser notification if enabled
        if show_notification and self.is_enabled:
            title_map = {
                "info": "🔔 Crypto Alert",
                "success": "✅ Success",
                "warning": "⚠️ Warning",
                "error": "❌ Error"
            }
            
            self.send_browser_notification(
                title=title_map[alert_type],
                body=message,
                tag=f"crypto_{alert_type}"
            )
    
    def send_trend_alert(self, keyword: str, current_value: float, change_pct: float):
        """Send a specialized trend alert notification"""
        if abs(change_pct) > 50:  # Significant change threshold
            direction = "📈" if change_pct > 0 else "📉"
            title = f"{direction} {keyword} Alert"
            body = f"Search interest: {current_value:.0f} ({change_pct:+.1f}%)"
            
            self.send_browser_notification(
                title=title,
                body=body,
                tag=f"trend_{keyword.lower().replace(' ', '_')}"
            )
    
    def send_price_alert(self, symbol: str, current_price: float, change_pct: float):
        """Send a specialized price alert notification"""
        if abs(change_pct) > 5:  # 5% change threshold
            direction = "📈" if change_pct > 0 else "📉"
            title = f"{direction} {symbol} Price Alert"
            body = f"${current_price:,.2f} ({change_pct:+.1f}%)"
            
            self.send_browser_notification(
                title=title,
                body=body,
                tag=f"price_{symbol.lower().replace('-', '_')}"
            )
    
    def send_test_notification(self):
        """Send a test notification to verify the system is working"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Try a simpler notification first
        simple_js = f"""
        <script>
        console.log('=== TEST NOTIFICATION START ===');
        console.log('Time:', '{current_time}');
        
        if ('Notification' in window) {{
            console.log('Notification API available');
            console.log('Current permission:', Notification.permission);
            
            if (Notification.permission === 'granted') {{
                console.log('Creating test notification...');
                
                const notification = new Notification('🔔 Test Notification', {{
                    body: 'System working! Time: {current_time}',
                    icon: 'data:image/svg+xml,%3csvg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"%3e%3ctext y="24" font-size="24"%3e🔔%3c/text%3e%3c/svg%3e',
                    tag: 'test_notification'
                }});
                
                notification.onshow = () => console.log('Test notification shown!');
                notification.onerror = (e) => console.error('Test notification error:', e);
                notification.onclick = () => {{ 
                    console.log('Test notification clicked!');
                    notification.close();
                }};
                
                setTimeout(() => {{
                    notification.close();
                    console.log('Test notification closed');
                }}, 5000);
                
            }} else {{
                console.log('No notification permission');
                alert('No notification permission. Please click "Request Permission" first.');
            }}
        }} else {{
            console.log('Notification API not supported');
            alert('Notifications not supported by your browser');
        }}
        
        console.log('=== TEST NOTIFICATION END ===');
        </script>
        """
        
        components.html(simple_js, height=0)
    
    def enable(self):
        """Enable notifications"""
        self.is_enabled = True
    
    def disable(self):
        """Disable notifications"""
        self.is_enabled = False
    
    def is_notification_enabled(self) -> bool:
        """Check if notifications are enabled"""
        return self.is_enabled


# Global notification service instance
notification_service = NotificationService()