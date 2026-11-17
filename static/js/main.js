/**
 * Finora AI — main.js
 * Common utilities, sidebar toggle, nav highlighting, fetch wrapper.
 */

'use strict';

// ============================================================
// 1. Currency & Date Formatters
// ============================================================

/**
 * Format a number as Indian Rupee string.
 * @param {number|string} amount
 * @param {number} [decimals=2]
 * @returns {string}  e.g. "₹1,23,456.78"
 */
function formatCurrency(amount, decimals = 2) {
  const num = parseFloat(amount);
  if (isNaN(num)) return '₹0.00';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
}

/**
 * Format an ISO date string or Date object to a human-readable string.
 * @param {string|Date} dateInput
 * @param {'short'|'medium'|'long'} [style='medium']
 * @returns {string}
 */
function formatDate(dateInput, style = 'medium') {
  if (!dateInput) return '—';
  const d = new Date(dateInput);
  if (isNaN(d.getTime())) return String(dateInput);

  const options = {
    short:  { day: '2-digit', month: 'short' },
    medium: { day: '2-digit', month: 'short', year: 'numeric' },
    long:   { weekday: 'short', day: '2-digit', month: 'long', year: 'numeric' },
  };
  return d.toLocaleDateString('en-IN', options[style] || options.medium);
}

/**
 * Returns "today", "yesterday", or a formatted date string.
 * @param {string|Date} dateInput
 */
function relativeDate(dateInput) {
  if (!dateInput) return '—';
  const d = new Date(dateInput);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  d.setHours(0, 0, 0, 0);
  const diff = (today - d) / 86400000;
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Yesterday';
  return formatDate(dateInput);
}

// ============================================================
// 2. Alert / Toast System
// ============================================================

/** @type {HTMLElement|null} */
let _alertContainer = null;

function _getAlertContainer() {
  if (_alertContainer) return _alertContainer;
  _alertContainer = document.getElementById('alert-container');
  if (!_alertContainer) {
    _alertContainer = document.createElement('div');
    _alertContainer.id = 'alert-container';
    _alertContainer.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:10px;min-width:300px;max-width:420px;';
    document.body.appendChild(_alertContainer);
  }
  return _alertContainer;
}

/**
 * Show a toast alert.
 * @param {string} message
 * @param {'success'|'danger'|'info'|'warning'} [type='info']
 * @param {number} [duration=4000]  milliseconds before auto-dismiss (0 = no auto-dismiss)
 */
function showAlert(message, type = 'info', duration = 4000) {
  const container = _getAlertContainer();
  const icons = { success: '✅', danger: '❌', info: 'ℹ️', warning: '⚠️' };

  const el = document.createElement('div');
  el.className = `alert alert-${type} animate-fade-in`;
  el.innerHTML = `
    <span>${icons[type] || 'ℹ️'}</span>
    <span style="flex:1">${message}</span>
    <button class="alert-close" aria-label="Close">✕</button>
  `;

  const closeBtn = el.querySelector('.alert-close');
  closeBtn.addEventListener('click', () => _dismissAlert(el));

  container.appendChild(el);

  if (duration > 0) {
    setTimeout(() => _dismissAlert(el), duration);
  }
  return el;
}

function _dismissAlert(el) {
  el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  el.style.opacity = '0';
  el.style.transform = 'translateX(20px)';
  setTimeout(() => el.remove(), 300);
}

// ============================================================
// 3. Confirm Delete Dialog
// ============================================================

/**
 * Show a confirmation modal before deleting a resource.
 * @param {string} [itemName='this item']
 * @returns {Promise<boolean>}
 */
function confirmDelete(itemName = 'this item') {
  return new Promise((resolve) => {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3 class="modal-title">🗑️ Confirm Delete</h3>
          <button class="modal-close" aria-label="Close">✕</button>
        </div>
        <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:0">
          Are you sure you want to delete <strong style="color:var(--text-primary)">${itemName}</strong>?<br>
          This action <span style="color:var(--red)">cannot be undone</span>.
        </p>
        <div class="modal-footer">
          <button class="btn btn-ghost cancel-btn">Cancel</button>
          <button class="btn btn-danger confirm-btn">Delete</button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    const close  = backdrop.querySelector('.modal-close');
    const cancel = backdrop.querySelector('.cancel-btn');
    const confirm = backdrop.querySelector('.confirm-btn');

    function cleanup(result) {
      backdrop.remove();
      resolve(result);
    }

    close.addEventListener('click',   () => cleanup(false));
    cancel.addEventListener('click',  () => cleanup(false));
    confirm.addEventListener('click', () => cleanup(true));
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) cleanup(false);
    });
  });
}

// ============================================================
// 4. Fetch Wrapper (JSON, error handling, session-safe)
// ============================================================

/**
 * Wrapper around fetch() that:
 *  - Sets Content-Type: application/json for POST/PUT/PATCH
 *  - Handles 401 → redirects to /login
 *  - Throws on non-ok responses with parsed error message
 * @param {string} url
 * @param {RequestInit} [options={}]
 * @returns {Promise<any>}  parsed JSON body
 */
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };

  const merged = {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) },
  };

  // If body is a plain object, stringify it
  if (merged.body && typeof merged.body === 'object' && !(merged.body instanceof FormData)) {
    merged.body = JSON.stringify(merged.body);
  }

  // Don't set Content-Type for FormData (browser sets multipart boundary)
  if (options.body instanceof FormData) {
    delete merged.headers['Content-Type'];
  }

  const response = await fetch(url, merged);

  if (response.status === 401) {
    window.location.href = '/login';
    return;
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = { error: response.statusText };
  }

  if (!response.ok) {
    throw new Error(data?.error || `HTTP ${response.status}`);
  }

  return data;
}

// ============================================================
// 5. Sidebar Toggle (mobile)
// ============================================================

function initSidebar() {
  const sidebar  = document.querySelector('.sidebar');
  const toggle   = document.querySelector('.sidebar-toggle');
  const overlay  = document.querySelector('.sidebar-overlay');

  if (!sidebar || !toggle) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  if (overlay) overlay.addEventListener('click', closeSidebar);

  // Close on resize back to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) closeSidebar();
  });
}

// ============================================================
// 6. Active Nav Link Highlighting
// ============================================================

function highlightActiveNav() {
  const links = document.querySelectorAll('.nav-item[href]');
  const path  = window.location.pathname;

  links.forEach((link) => {
    link.classList.remove('active');
    const href = link.getAttribute('href');
    if (href && href !== '/' && path.startsWith(href)) {
      link.classList.add('active');
    } else if (href === '/' && path === '/') {
      link.classList.add('active');
    }
  });
}

// ============================================================
// 7. Auto-dismiss flash messages
// ============================================================

function initFlashMessages() {
  document.querySelectorAll('.alert .alert-close').forEach((btn) => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) _dismissAlert(alert);
    });
  });

  // Auto-dismiss after 5s
  document.querySelectorAll('.alert').forEach((el, i) => {
    setTimeout(() => _dismissAlert(el), 5000 + i * 500);
  });
}

// ============================================================
// 8. Misc Helpers
// ============================================================

/** Capitalise the first letter of a string. */
function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/** Truncate a string to `max` characters with an ellipsis. */
function truncate(str, max = 40) {
  if (!str || str.length <= max) return str || '';
  return str.slice(0, max - 1) + '…';
}

/**
 * Debounce a function.
 * @param {Function} fn
 * @param {number} delay
 */
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/** Return the current month/year as { month, year }. */
function currentMonthYear() {
  const d = new Date();
  return { month: d.getMonth() + 1, year: d.getFullYear() };
}

/** Build a category colour map from an array of { name, color } objects. */
function buildColorMap(categories) {
  const map = {};
  categories.forEach((c) => { map[c.name] = c.color; });
  return map;
}

// ============================================================
// 9. Init on DOMContentLoaded
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  highlightActiveNav();
  initFlashMessages();
});
