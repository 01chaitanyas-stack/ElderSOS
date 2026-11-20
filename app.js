// ElderSOS Core Application Script
document.addEventListener('DOMContentLoaded', () => {
  // 1. Register Service Worker for PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        console.log('[ElderSOS PWA] Service worker registered with scope:', reg.scope);
      })
      .catch((err) => {
        console.warn('[ElderSOS PWA] Service worker registration failed:', err);
      });
  }

  // 2. Online/Offline Network Monitoring for Seniors
  function updateOnlineStatus() {
    const isOnline = navigator.onLine;
    let banner = document.getElementById('offline-network-banner');
    if (!isOnline) {
      if (!banner) {
        banner = document.createElement('div');
        banner.id = 'offline-network-banner';
        banner.className = 'alert-banner danger';
        banner.style.position = 'sticky';
        banner.style.top = '72px';
        banner.style.zIndex = '999';
        banner.innerHTML = `
          <span>⚠️ <strong>Device Offline:</strong> Internet connection lost. For emergencies, please call <a href="tel:112" style="color: inherit; text-decoration: underline; font-weight: 800;">112</a> directly.</span>
        `;
        const main = document.getElementById('main-content');
        if (main) main.insertBefore(banner, main.firstChild);
      }
    } else if (banner) {
      banner.remove();
    }
  }

  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);
  updateOnlineStatus();
});

// Helper to fetch CSRF token from meta tag
function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}
