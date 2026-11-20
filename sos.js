// ElderSOS - SOS Emergency Alert Controller
// Handles 5-second countdown, cancel, geolocation fallback, fail-safe calling

let countdownInterval = null;
let countdownRemaining = 5;
let isDispatching = false;

// Audio beep using Web Audio API for tactile feedback
function playBeep(freq = 600, duration = 0.15) {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) {
    // AudioContext not supported or restricted; silently ignore
  }
}

function initSOSButton() {
  const triggerBtn = document.getElementById('sos-trigger-btn');
  const overlay = document.getElementById('sos-countdown-overlay');
  const timerDisplay = document.getElementById('sos-timer-count');
  const cancelBtn = document.getElementById('sos-cancel-btn');
  const resultsCard = document.getElementById('sos-results-card');
  const resultsContent = document.getElementById('sos-results-content');
  const failSafeBox = document.getElementById('sos-failsafe-box');

  if (!triggerBtn) return;

  triggerBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (isDispatching) return;
    startCountdown();
  });

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      cancelCountdown();
    });
  }

  function startCountdown() {
    countdownRemaining = 5;
    if (timerDisplay) timerDisplay.textContent = countdownRemaining;
    if (overlay) overlay.style.display = 'flex';
    if (resultsCard) resultsCard.style.display = 'none';
    if (failSafeBox) failSafeBox.style.display = 'none';

    playBeep(700, 0.2);

    countdownInterval = setInterval(() => {
      countdownRemaining -= 1;
      if (timerDisplay) timerDisplay.textContent = countdownRemaining;
      playBeep(700, 0.15);

      if (countdownRemaining <= 0) {
        clearInterval(countdownInterval);
        countdownInterval = null;
        if (overlay) overlay.style.display = 'none';
        executeSOSDispatch();
      }
    }, 1000);
  }

  function cancelCountdown() {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
    if (overlay) overlay.style.display = 'none';
    playBeep(400, 0.25);
    alert('SOS alert was cancelled. No emergency message was sent.');
  }

  function executeSOSDispatch() {
    isDispatching = true;
    triggerBtn.disabled = true;
    triggerBtn.style.opacity = '0.6';

    const statusMsg = document.getElementById('sos-status-feedback');
    if (statusMsg) {
      statusMsg.style.display = 'block';
      statusMsg.textContent = 'Acquiring GPS location and dispatching emergency alerts...';
    }

    // Attempt geolocation with 3500ms timeout
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          sendSOSRequest(position.coords.latitude, position.coords.longitude, 'available');
        },
        (error) => {
          let status = 'unavailable';
          if (error.code === error.PERMISSION_DENIED) status = 'denied';
          else if (error.code === error.TIMEOUT) status = 'timeout';
          sendSOSRequest(null, null, status);
        },
        { enableHighAccuracy: true, timeout: 3500, maximumAge: 0 }
      );
    } else {
      sendSOSRequest(null, null, 'unavailable');
    }
  }

  function sendSOSRequest(lat, lng, location_status) {
    const csrfToken = getCSRFToken();

    fetch('/api/sos', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        lat: lat,
        lng: lng,
        location_status: location_status
      })
    })
    .then(async (response) => {
      const data = await response.json();
      isDispatching = false;
      triggerBtn.disabled = false;
      triggerBtn.style.opacity = '1';

      const statusMsg = document.getElementById('sos-status-feedback');
      if (statusMsg) statusMsg.style.display = 'none';

      renderSOSResults(data, response.ok);
    })
    .catch((networkError) => {
      console.error('[ElderSOS] Network SOS failed:', networkError);
      isDispatching = false;
      triggerBtn.disabled = false;
      triggerBtn.style.opacity = '1';

      const statusMsg = document.getElementById('sos-status-feedback');
      if (statusMsg) statusMsg.style.display = 'none';

      renderNetworkFailure();
    });
  }

  function renderSOSResults(data, isOk) {
    if (!resultsCard || !resultsContent) return;
    resultsCard.style.display = 'block';
    resultsCard.scrollIntoView({ behavior: 'smooth' });

    let isSuccess = data.overall_status === 'sent';
    let isPartial = data.overall_status === 'partial';
    let isFailed = data.overall_status === 'failed';

    let html = '';

    if (data.mode === 'test') {
      html += `
        <div class="alert-banner info" style="font-size: 1.15rem; font-weight: 800; border-width: 3px;">
          🧪 TEST MODE ALERT RECORDED (Safe Simulation - No real charges or external SMS)
        </div>
      `;
    }

    if (isSuccess) {
      html += `
        <div class="alert-banner success" style="font-size: 1.25rem; font-weight: 800;">
          ✅ Emergency Alert Confirmed & Sent to All Contacts!
        </div>
      `;
    } else if (isPartial) {
      html += `
        <div class="alert-banner warning" style="font-size: 1.2rem; font-weight: 800;">
          ⚠️ Alert Partially Sent: Some contacts received the message, but others failed.
        </div>
      `;
    } else {
      html += `
        <div class="alert-banner danger" style="font-size: 1.25rem; font-weight: 800;">
          ❌ EMERGENCY ALERT NOT SENT: ${data.error_summary || 'Delivery to contacts failed.'}
        </div>
      `;
    }

    // GPS Status note
    html += `
      <div style="margin: 16px 0; font-size: 1.05rem; padding: 12px; background: #f8fafc; border-radius: 8px; border: 1px solid #cbd5e1;">
        <div>📍 <strong>GPS Location:</strong> ${data.location_status === 'available' ? 'Exact Coordinates Attached' : 'Location ' + data.location_status}</div>
        ${data.maps_link ? `<div>🗺️ <a href="${data.maps_link}" target="_blank" rel="noopener" style="color: var(--color-primary); font-weight: 700; text-decoration: underline;">View Emergency Map Pin</a></div>` : ''}
      </div>
    `;

    // Per-contact honest delivery table
    if (data.deliveries && data.deliveries.length > 0) {
      html += `
        <h3 style="font-size: 1.25rem; font-weight: 800; margin: 18px 0 10px;">Contact Notification Status:</h3>
        <div style="display: flex; flex-direction: column; gap: 12px;">
      `;

      data.deliveries.forEach((d) => {
        const sent = d.status === 'sent';
        html += `
          <div style="border: 2px solid ${sent ? 'var(--color-success)' : 'var(--color-emergency)'}; background: ${sent ? 'var(--color-success-light)' : 'var(--color-emergency-light)'}; padding: 14px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
              <div style="font-size: 1.15rem; font-weight: 800; color: var(--color-text-main);">
                ${d.contact_name} (${d.phone})
              </div>
              <div style="font-size: 0.95rem; margin-top: 4px;">
                Channel: <strong>${d.provider.toUpperCase()}</strong> | Status: <strong>${sent ? 'SENT ✅' : 'FAILED ❌'}</strong>
                ${d.provider_ref ? ` (Ref: <code>${d.provider_ref}</code>)` : ''}
              </div>
              ${d.error ? `<div style="color: var(--color-emergency); font-size: 0.95rem; font-weight: 700; margin-top: 4px;">Reason: ${d.error}</div>` : ''}
            </div>
            <a href="tel:${d.phone}" class="btn btn-secondary" style="font-size: 1rem; padding: 8px 16px;">
              📞 Call ${d.contact_name.split(' ')[0]}
            </a>
          </div>
        `;
      });

      html += `</div>`;
    }

    // Fail-safe direct dialing buttons if any failure or emergency
    if (isFailed || isPartial) {
      html += `
        <div class="failsafe-box" style="margin-top: 24px;">
          <h3 style="font-size: 1.4rem; font-weight: 900; color: var(--color-emergency); margin-bottom: 8px;">
            🚨 Immediate Fallback Phone Numbers
          </h3>
          <p style="font-size: 1.1rem; color: #102a43; margin-bottom: 16px;">
            Please tap below to place an immediate phone call using your mobile keypad:
          </p>
          <div class="failsafe-buttons">
            <a href="tel:112" class="btn btn-emergency btn-block" style="font-size: 1.35rem; padding: 16px;">
              🚨 Dial 112 (National Emergency)
            </a>
            ${data.primary_contact ? `
              <a href="tel:${data.primary_contact.phone}" class="btn btn-success btn-block" style="font-size: 1.35rem; padding: 16px;">
                📞 Call Primary: ${data.primary_contact.name} (${data.primary_contact.phone})
              </a>
            ` : ''}
          </div>
        </div>
      `;
    }

    resultsContent.innerHTML = html;
  }

  function renderNetworkFailure() {
    if (!resultsCard || !resultsContent) return;
    resultsCard.style.display = 'block';
    resultsCard.scrollIntoView({ behavior: 'smooth' });

    resultsContent.innerHTML = `
      <div class="alert-banner danger" style="font-size: 1.3rem; font-weight: 900;">
        ⚠️ ALERT NOT SENT: Device could not reach the server! Check your Wi-Fi or Mobile Data.
      </div>
      <div class="failsafe-box">
        <h3 style="font-size: 1.4rem; font-weight: 900; color: var(--color-emergency); margin-bottom: 8px;">
          🚨 Direct Emergency Calling (Works without Internet)
        </h3>
        <p style="font-size: 1.15rem; color: #102a43; margin-bottom: 16px;">
          Tap below to place a direct phone call immediately:
        </p>
        <div class="failsafe-buttons">
          <a href="tel:112" class="btn btn-emergency btn-block" style="font-size: 1.4rem; padding: 16px;">
            🚨 Call 112 (National Emergency Police / Ambulance)
          </a>
        </div>
      </div>
    `;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initSOSButton();
});
