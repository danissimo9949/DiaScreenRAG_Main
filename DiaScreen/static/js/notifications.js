
class NotificationSystem {
    constructor() {
        this.pollInterval = 30000;
        this.lastCheckTime = null;
        this.processedNotifications = new Set();
        this.notificationContainer = null;
        this.init();
    }

    init() {
        this.createNotificationContainer();
        
        this.checkNotifications();
        
        setInterval(() => this.checkNotifications(), this.pollInterval);
    }

    createNotificationContainer() {

        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
        this.notificationContainer = container;
    }

    async checkNotifications() {
        try {
            const response = await fetch('/api/notifications/');
            if (!response.ok) {
                return;
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateNotificationBadge(data.unread_count);
                this.showNewNotifications(data.notifications);
            }
        } catch (error) {
            console.error('Помилка при отриманні сповіщень:', error);
        }
    }

    updateNotificationBadge(unreadCount) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    showNewNotifications(notifications) {
        notifications.forEach(notif => {
            if (!notif.is_read && !this.processedNotifications.has(notif.id)) {
                this.showNotification(notif);
                this.processedNotifications.add(notif.id);
            }
        });
    }

    showNotification(notification) {
        const notifElement = document.createElement('div');
        notifElement.className = `notification notification-${notification.type}`;
        notifElement.dataset.notificationId = notification.id;
        
        const icon = this.getIconForType(notification.type);
        
        notifElement.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">${icon}</div>
                <div class="notification-text">
                    <div class="notification-title">${this.escapeHtml(notification.title)}</div>
                    <div class="notification-message">${this.escapeHtml(notification.message)}</div>
                    <div class="notification-time">${notification.created_at}</div>
                </div>
                <button class="notification-close" onclick="notificationSystem.closeNotification(${notification.id})">×</button>
            </div>
        `;
        
        if (notification.link) {
            notifElement.style.cursor = 'pointer';
            notifElement.addEventListener('click', () => {
                window.location.href = notification.link;
            });
        }
        
        this.notificationContainer.appendChild(notifElement);
        
        setTimeout(() => {
            notifElement.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            this.closeNotification(notification.id);
        }, 5000);
    }

    getIconForType(type) {
        const icons = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'danger': '🔴',
            'success': '✅',
        };
        return icons[type] || 'ℹ️';
    }

    async closeNotification(notificationId) {
        const notifElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (notifElement) {
            notifElement.classList.remove('show');
            setTimeout(() => {
                notifElement.remove();
            }, 300);
            
            try {
                await fetch(`/api/notifications/${notificationId}/read/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                });
            } catch (error) {
                console.error('Ошибка при отметке уведомления:', error);
            }
        }
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

let notificationSystem;
document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;
    const isAuthenticated = body.dataset.userAuthenticated === 'true' || 
                           body.getAttribute('data-user-authenticated') === 'true';
    
    if (isAuthenticated) {
        notificationSystem = new NotificationSystem();
    }
});

