// ElderSOS Senior Hydration & Daily Reminders Script

document.addEventListener('DOMContentLoaded', () => {
  initHydrationTracker();
  initNotificationPermission();
});

// Hydration Tracker with LocalStorage Persistence
function initHydrationTracker() {
  const container = document.getElementById('hydration-tracker-card');
  if (!container) return;

  const todayKey = 'eldersos_water_' + new Date().toISOString().split('T')[0];
  let glasses = parseInt(localStorage.getItem(todayKey) || '0', 10);
  const target = 8; // 8 glasses recommended for seniors (approx 2 Litres)

  const countDisplay = document.getElementById('water-count-display');
  const progressBar = document.getElementById('water-progress-fill');
  const logBtn = document.getElementById('btn-log-water');
  const resetBtn = document.getElementById('btn-reset-water');

  function updateUI() {
    if (countDisplay) {
      countDisplay.textContent = `${glasses} of ${target} Glasses`;
    }
    if (progressBar) {
      const pct = Math.min(100, Math.round((glasses / target) * 100));
      progressBar.style.width = `${pct}%`;
      progressBar.textContent = `${pct}%`;
      if (pct >= 100) {
        progressBar.style.backgroundColor = '#1b7a42';
      }
    }
  }

  if (logBtn) {
    logBtn.addEventListener('click', () => {
      glasses += 1;
      localStorage.setItem(todayKey, glasses.toString());
      updateUI();

      // Audio feedback chime
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(520, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(780, ctx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        osc.start();
        osc.stop(ctx.currentTime + 0.2);
      } catch (e) {}
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (confirm('Reset today\'s logged water count to 0?')) {
        glasses = 0;
        localStorage.setItem(todayKey, '0');
        updateUI();
      }
    });
  }

  updateUI();
}

// Browser notification permission request for senior hydration/meal alerts
function initNotificationPermission() {
  const permBtn = document.getElementById('btn-enable-notifications');
  if (!permBtn) return;

  if ('Notification' in window) {
    if (Notification.permission === 'granted') {
      permBtn.style.display = 'none';
    } else if (Notification.permission !== 'denied') {
      permBtn.addEventListener('click', () => {
        Notification.requestPermission().then((permission) => {
          if (permission === 'granted') {
            permBtn.textContent = '✅ Notifications Enabled';
            permBtn.disabled = true;
            new Notification('ElderSOS Reminders Active', {
              body: 'You will receive gentle hydration and mealtime reminders.',
              icon: '/static/icons/icon-192.png'
            });
          }
        });
      });
    } else {
      permBtn.style.display = 'none';
    }
  } else {
    permBtn.style.display = 'none';
  }
}
