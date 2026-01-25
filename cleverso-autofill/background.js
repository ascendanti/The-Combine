// Background service worker for Cleverso AutoFill

// Register keyboard shortcut command
chrome.commands?.onCommand?.addListener((command) => {
  if (command === 'fill-current') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'fillCurrent' });
      }
    });
  }
});

// Handle extension install/update
chrome.runtime.onInstalled.addListener(() => {
  console.log('Cleverso AutoFill extension installed');
});
