/* ========================================
   BASE.JS — Notification system + panel navigation
   Used in base.html
======================================== */

// ── Notification System ──
function showNotification(message, type = 'success', duration = 5000) {
    const container = document.getElementById('notificationContainer');
    if (!container) return;

    // Icon mapping
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const icon = icons[type] || icons.info;

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.innerHTML = `
        <span class="alert-icon"><i class="fas ${icon}"></i></span>
        <span class="alert-msg">${message}</span>
        <button class="alert-close" onclick="dismissNotification(this.parentElement)">
            <i class="fas fa-times"></i>
        </button>
        <div class="alert-progress"></div>
    `;

    // Add to container
    container.appendChild(notification);

    // Auto-dismiss after duration
    const timeoutId = setTimeout(() => {
        dismissNotification(notification);
    }, duration);

    // Store timeout ID for cleanup
    notification.dataset.timeoutId = timeoutId;

    return notification;
}

function dismissNotification(notification) {
    if (!notification) return;

    // Clear the auto-dismiss timeout
    if (notification.dataset.timeoutId) {
        clearTimeout(parseInt(notification.dataset.timeoutId));
    }

    // Add hiding animation
    notification.classList.add('hiding');

    // Remove after animation completes
    setTimeout(() => {
        if (notification.parentElement) {
            notification.parentElement.removeChild(notification);
        }
    }, 300);
}

// ── Panel navigation ──
const PANEL_META = {
    dashboard: { title: 'Dashboard',     sub: 'Overview of your payment activity' },
    upload:    { title: 'Upload File',   sub: 'Convert an Excel file to bank-ready CSV' },
    history:   { title: 'History',       sub: 'All your past processing jobs' },
    detail:    { title: 'Job Detail',    sub: 'Full details for this processing job' },
};

function showPanel(name) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));

    const panel = document.getElementById('panel-' + name);
    if (panel) panel.classList.add('active');

    const navEl = document.getElementById('nav-' + name);
    if (navEl) navEl.classList.add('active');

    const meta = PANEL_META[name] || {};
    const titleEl = document.getElementById('topbar-title');
    const subEl = document.getElementById('topbar-sub');
    
    if (titleEl) titleEl.textContent = meta.title || '';
    if (subEl) subEl.textContent = meta.sub || '';

    return false;
}

// ── Parse Django messages ──
function parseDjangoMessages(messages) {
    // messages is expected to be an array of {text, type}
    messages.forEach(function(msg) {
        let type = 'info';
        if (msg.type === 'success') type = 'success';
        else if (msg.type === 'error') type = 'error';
        else if (msg.type === 'warning') type = 'warning';
        else if (msg.type === 'info') type = 'info';
        
        showNotification(msg.text, type);
    });
}

// ── Expose functions globally ──
window.showNotification = showNotification;
window.dismissNotification = dismissNotification;
window.showPanel = showPanel;
window.parseDjangoMessages = parseDjangoMessages;