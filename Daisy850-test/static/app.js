/**
 * 850 Toolbox — Shared PWA Logic
 * Service Worker registration, auto-refresh, online/offline status,
 * install prompt, bottom nav active state.
 */

(function() {
  'use strict';

  // ── Service Worker Registration ──────────────────────────
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(function(reg) {
        console.log('[PWA] SW registered:', reg.scope);

        // Listen for updates
        reg.addEventListener('updatefound', function() {
          var newWorker = reg.installing;
          newWorker.addEventListener('statechange', function() {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('[PWA] New version available — will apply on reload');
            }
          });
        });
      })
      .catch(function(err) {
        console.warn('[PWA] SW registration failed:', err);
      });
  }

  // ── Auto-refresh (every 5 minutes when page is visible) ──
  var REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes
  var lastDataRefresh = Date.now();
  var refreshTimer = null;
  var visibilityTimer = null;

  function updateStatusDot() {
    var el = document.getElementById('live-status');
    if (!el) return;
    var seconds = Math.floor((Date.now() - lastDataRefresh) / 1000);
    if (seconds < 30) {
      el.textContent = '🟢 实时';
      el.className = 'live-dot live-on';
    } else if (seconds < 300) {
      el.textContent = '🟢 ' + Math.floor(seconds / 60) + '分前';
      el.className = 'live-dot live-on';
    } else if (seconds < 600) {
      el.textContent = '🟡 ' + Math.floor(seconds / 60) + '分前';
      el.className = 'live-dot live-stale';
    } else {
      el.textContent = '🔴 ' + Math.floor(seconds / 60) + '分前';
      el.className = 'live-dot live-old';
    }
  }

  function doRefresh() {
    lastDataRefresh = Date.now();
    updateStatusDot();
    // Call page-specific refresh if available
    if (typeof window._pageRefresh === 'function') {
      window._pageRefresh();
    }
  }

  function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(doRefresh, REFRESH_INTERVAL);

    // Only tick status when page is visible
    document.addEventListener('visibilitychange', function() {
      if (document.hidden) {
        if (visibilityTimer) clearInterval(visibilityTimer);
      } else {
        updateStatusDot();
        visibilityTimer = setInterval(updateStatusDot, 30000);
        // If been hidden for > REFRESH_INTERVAL, trigger refresh
        if (Date.now() - lastDataRefresh > REFRESH_INTERVAL) {
          doRefresh();
        }
      }
    });

    if (!document.hidden) {
      visibilityTimer = setInterval(updateStatusDot, 30000);
    }
  }

  // Expose for page scripts to call after data loads
  window._pwaMarkRefresh = function() {
    lastDataRefresh = Date.now();
    updateStatusDot();
  };

  window._pwaStartRefresh = startAutoRefresh;

  // ── Online / Offline detection ───────────────────────────
  function setOnline(state) {
    document.body.classList.toggle('is-offline', !state);
    var el = document.getElementById('live-status');
    if (!el) return;
    if (!state) {
      el.textContent = '🔴 离线';
      el.className = 'live-dot live-old';
    } else {
      updateStatusDot();
    }
  }

  window.addEventListener('online', function() {
    setOnline(true);
    doRefresh();
  });
  window.addEventListener('offline', function() { setOnline(false); });
  setOnline(navigator.onLine);

  // ── PWA Install Prompt ───────────────────────────────────
  var deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', function(e) {
    e.preventDefault();
    deferredPrompt = e;
    var btns = document.querySelectorAll('.pwa-install-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].style.display = '';
      btns[i].addEventListener('click', function() {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function(result) {
          if (result.outcome === 'accepted') {
            for (var j = 0; j < btns.length; j++) {
              btns[j].style.display = 'none';
            }
          }
        });
      });
    }
  });

  // Track if already installed
  window.addEventListener('appinstalled', function() {
    console.log('[PWA] App installed');
    deferredPrompt = null;
  });

  // ── Bottom Nav Active State ──────────────────────────────
  var currentPath = window.location.pathname;
  var navItems = document.querySelectorAll('.bn-item');
  for (var i = 0; i < navItems.length; i++) {
    var href = navItems[i].getAttribute('href');
    if (href === currentPath || (href === '/' && (currentPath === '/' || currentPath === '/index.html'))) {
      navItems[i].classList.add('active');
    }
  }

  // ── Start refresh cycle ──────────────────────────────────
  startAutoRefresh();
  updateStatusDot();
})();
