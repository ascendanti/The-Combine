// Translation mapping: unedited English -> corrected English
let translationMap = {};

// DOM elements
const sheetUrlInput = document.getElementById('sheetUrl');
const csvDataInput = document.getElementById('csvData');
const loadSheetBtn = document.getElementById('loadSheet');
const loadCsvBtn = document.getElementById('loadCsv');
const fillCurrentBtn = document.getElementById('fillCurrent');
const autoFillAllBtn = document.getElementById('autoFillAll');
const statusDiv = document.getElementById('status');
const dataCountDiv = document.getElementById('dataCount');

// Pre-fill with user's sheet
sheetUrlInput.value = '1i8WjmwSuQPeengiDYLwQX1HLosGKBJKyLtp5v_FYBhw';

// Load saved data on popup open
chrome.storage.local.get(['translationMap'], (result) => {
  if (result.translationMap) {
    translationMap = result.translationMap;
    updateDataCount();
  }
});

function showStatus(message, type = 'info') {
  statusDiv.className = `status ${type}`;
  statusDiv.textContent = message;
}

function updateDataCount() {
  const count = Object.keys(translationMap).length;
  dataCountDiv.textContent = `${count} translations loaded`;
}

function extractSheetId(input) {
  // If it's already just an ID
  if (/^[a-zA-Z0-9_-]+$/.test(input) && !input.includes('/')) {
    return input;
  }
  // Extract from URL
  const match = input.match(/\/d\/([a-zA-Z0-9_-]+)/);
  return match ? match[1] : input;
}

// Load from Google Sheets
loadSheetBtn.addEventListener('click', async () => {
  const input = sheetUrlInput.value.trim();
  if (!input) {
    showStatus('Please enter a Sheet URL or ID', 'error');
    return;
  }

  const sheetId = extractSheetId(input);
  showStatus('Loading sheet...', 'info');

  try {
    // Try to fetch as CSV (works for publicly accessible sheets)
    const gid = '1696073450'; // The specific sheet tab
    const csvUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=csv&gid=${gid}`;

    const response = await fetch(csvUrl);
    if (!response.ok) {
      throw new Error('Could not access sheet. Make sure it is shared publicly or "Anyone with link can view"');
    }

    const csvText = await response.text();
    parseCSV(csvText);
  } catch (error) {
    showStatus(`Error: ${error.message}`, 'error');
  }
});

// Parse CSV data
function parseCSV(csvText) {
  const lines = csvText.split('\n');
  translationMap = {};

  // Skip header row
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Parse CSV properly (handle quoted fields)
    const fields = parseCSVLine(line);

    // Columns: Order, Arabic, English, Corrected_English, Note
    // Index:   0,     1,      2,       3,                  4
    if (fields.length >= 4) {
      const original = fields[2].trim();
      const corrected = fields[3].trim();

      if (original && corrected) {
        translationMap[original] = corrected;
      }
    }
  }

  // Save to storage
  chrome.storage.local.set({ translationMap });
  updateDataCount();
  showStatus(`Loaded ${Object.keys(translationMap).length} translations`, 'success');
}

// Parse a single CSV line handling quoted fields
function parseCSVLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"' && !inQuotes) {
      inQuotes = true;
    } else if (char === '"' && inQuotes) {
      if (nextChar === '"') {
        current += '"';
        i++; // Skip escaped quote
      } else {
        inQuotes = false;
      }
    } else if (char === ',' && !inQuotes) {
      fields.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current);

  return fields;
}

// Load from pasted CSV
loadCsvBtn.addEventListener('click', () => {
  const csvText = csvDataInput.value.trim();
  if (!csvText) {
    showStatus('Please paste CSV data', 'error');
    return;
  }

  translationMap = {};
  const lines = csvText.split('\n');

  for (const line of lines) {
    const parts = line.split(',');
    if (parts.length >= 2) {
      const original = parts[0].trim();
      const corrected = parts.slice(1).join(',').trim(); // In case corrected has commas
      if (original && corrected) {
        translationMap[original] = corrected;
      }
    }
  }

  chrome.storage.local.set({ translationMap });
  updateDataCount();
  showStatus(`Loaded ${Object.keys(translationMap).length} translations`, 'success');
});

// Send message to content script to fill current row
fillCurrentBtn.addEventListener('click', async () => {
  if (Object.keys(translationMap).length === 0) {
    showStatus('No translations loaded', 'error');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.tabs.sendMessage(tab.id, {
    action: 'fillCurrent',
    translations: translationMap
  }, (response) => {
    if (response?.success) {
      showStatus(response.message, 'success');
    } else {
      showStatus(response?.message || 'Could not fill row', 'error');
    }
  });
});

// Auto-fill all matching rows
autoFillAllBtn.addEventListener('click', async () => {
  if (Object.keys(translationMap).length === 0) {
    showStatus('No translations loaded', 'error');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.tabs.sendMessage(tab.id, {
    action: 'autoFillAll',
    translations: translationMap
  }, (response) => {
    if (response?.success) {
      showStatus(response.message, 'success');
    } else {
      showStatus(response?.message || 'Could not auto-fill', 'error');
    }
  });
});
