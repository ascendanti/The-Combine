// Cleverso AutoFill - Minimal Version
// Ctrl+Shift+F = Fill current field

let translationMap = {};

// Load translations from storage
chrome.storage.local.get(['translationMap'], (result) => {
  if (result.translationMap) {
    translationMap = result.translationMap;
    console.log('[AutoFill] Loaded', Object.keys(translationMap).length, 'translations');
  }
});

// Listen for storage changes
chrome.storage.onChanged.addListener((changes) => {
  if (changes.translationMap) {
    translationMap = changes.translationMap.newValue || {};
    console.log('[AutoFill] Updated:', Object.keys(translationMap).length);
  }
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.translations) {
    translationMap = request.translations;
  }
  if (request.action === 'fillCurrent') {
    sendResponse(fillCurrent());
  } else if (request.action === 'autoFillAll') {
    autoFillAll().then(sendResponse);
    return true;
  }
});

// Keyboard shortcut
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === 'F') {
    e.preventDefault();
    const result = fillCurrent();
    showToast(result.message, result.success ? 'success' : 'error');
  }
});

// Normalize text
function normalize(text) {
  if (!text) return '';
  return text.trim().replace(/\s+/g, ' ');
}

// Fill current field
function fillCurrent() {
  if (Object.keys(translationMap).length === 0) {
    return { success: false, message: 'No translations loaded' };
  }

  // Get the active/focused element
  const active = document.activeElement;

  // Try to get text from active element
  let fieldText = '';
  let targetField = null;

  if (active && active.contentEditable === 'true') {
    fieldText = active.innerText || active.textContent || '';
    targetField = active;
  } else if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {
    fieldText = active.value || '';
    targetField = active;
  }

  // If no direct field, look for segment structure
  if (!targetField || !fieldText) {
    const segment = active?.closest('[class*="segment"]') ||
                    document.querySelector('[class*="segment"][class*="focus"]') ||
                    document.querySelector('[class*="segment"][class*="active"]');

    if (segment) {
      const editable = segment.querySelector('[contenteditable="true"]');
      if (editable) {
        fieldText = editable.innerText || editable.textContent || '';
        targetField = editable;
      }
    }
  }

  if (!targetField) {
    return { success: false, message: 'Click on a text field first' };
  }

  if (!fieldText.trim()) {
    return { success: false, message: 'Field is empty' };
  }

  const normalizedField = normalize(fieldText);
  console.log('[AutoFill] Field text:', normalizedField.substring(0, 50));

  // Find exact match
  for (const [original, corrected] of Object.entries(translationMap)) {
    if (normalize(original) === normalizedField) {
      applyText(targetField, corrected);
      return { success: true, message: 'Filled!' };
    }
  }

  // Find partial match (one contains the other)
  for (const [original, corrected] of Object.entries(translationMap)) {
    const normOrig = normalize(original);
    if (normOrig.includes(normalizedField) || normalizedField.includes(normOrig)) {
      applyText(targetField, corrected);
      return { success: true, message: 'Filled!' };
    }
  }

  console.log('[AutoFill] No match. Sample translations:', Object.keys(translationMap).slice(0, 2).map(k => normalize(k).substring(0, 40)));
  return { success: false, message: 'No match found' };
}

// Apply text to field
function applyText(field, text) {
  if (field.contentEditable === 'true') {
    field.innerText = text;
  } else {
    field.value = text;
  }
  field.dispatchEvent(new Event('input', { bubbles: true }));
  field.dispatchEvent(new Event('change', { bubbles: true }));
  field.dispatchEvent(new Event('blur', { bubbles: true }));
}

// Auto-fill all
async function autoFillAll() {
  let filled = 0;
  const segments = document.querySelectorAll('[class*="segment"]');

  for (const segment of segments) {
    const editable = segment.querySelector('[contenteditable="true"]');
    if (!editable) continue;

    const text = normalize(editable.innerText || '');
    if (!text) continue;

    for (const [original, corrected] of Object.entries(translationMap)) {
      if (normalize(original) === text) {
        applyText(editable, corrected);
        filled++;
        await new Promise(r => setTimeout(r, 50));
        break;
      }
    }
  }

  return filled > 0
    ? { success: true, message: `Filled ${filled} rows` }
    : { success: false, message: 'No matches found' };
}

// Toast notification
function showToast(message, type) {
  const old = document.querySelector('.autofill-toast');
  if (old) old.remove();

  const toast = document.createElement('div');
  toast.className = 'autofill-toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed; top: 20px; right: 20px;
    padding: 12px 20px; border-radius: 6px;
    color: white; font-size: 14px; z-index: 999999;
    background: ${type === 'success' ? '#34a853' : '#ea4335'};
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}

console.log('[AutoFill] Ready. Ctrl+Shift+F to fill.');
