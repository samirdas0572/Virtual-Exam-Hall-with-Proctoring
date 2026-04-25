/**
 * Main JavaScript - Common utilities and UI interactions
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeAlerts();
    initializeNavbar();
});

function initializeNavbar() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 20);
    });
    const menuToggle = document.getElementById('menuToggle');
    const navLinks = document.getElementById('navLinks');
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            menuToggle.classList.toggle('active');
        });
    }
}

function initializeAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.animation = 'slideOut 0.4s ease forwards';
            setTimeout(() => alert.remove(), 400);
        }, 4000);
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.animation = 'slideOut 0.4s ease forwards';
                setTimeout(() => alert.remove(), 400);
            });
        }
    });
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ'}</span><span>${message}</span>`;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function confirmAction(message) {
    return confirm(message);
}

function showLoading(el) {
    if (!el) return;
    el.dataset.originalText = el.innerHTML;
    el.innerHTML = '<span class="spinner"></span> Loading...';
    el.disabled = true;
}
function hideLoading(el) {
    if (!el) return;
    el.innerHTML = el.dataset.originalText || el.innerHTML;
    el.disabled = false;
}
