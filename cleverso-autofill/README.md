# Cleverso AutoFill Chrome Extension

Automatically fill Cleverso translation fields from your Google Sheet corrections.

## Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Select this `cleverso-autofill` folder
5. The extension icon will appear in your toolbar

## Setup

### First-time configuration:

1. Click the extension icon in Chrome toolbar
2. Your Google Sheet ID is pre-filled (`1i8WjmwSuQPeengiDYLwQX1HLosGKBJKyLtp5v_FYBhw`)
3. Click **Load Sheet** to fetch your translations
4. You should see "X translations loaded"

### Important: Sheet must be accessible
Make sure your Google Sheet is shared with "Anyone with the link can view"

## Usage

### Semi-Auto Mode (Recommended to start):
1. Navigate to Cleverso in Chrome
2. Click on a row to edit it
3. Press **Ctrl+Shift+F** to auto-fill the current row
4. Check the "done" circle
5. Move to next row and repeat

### Full-Auto Mode:
1. Load your sheet data via the extension popup
2. Navigate to Cleverso
3. Click **Auto-Fill All** in the extension popup
4. The extension will attempt to fill all matching rows

## How Matching Works

The extension:
1. Reads your sheet's **English** column (original/unedited)
2. Looks for matching text in Cleverso's English column
3. Replaces it with **Corrected_English** from your sheet

## Troubleshooting

### "No matching translation found"
- Make sure the text in Cleverso exactly matches your sheet's English column
- Extra spaces or special characters can cause mismatches

### "Could not access sheet"
- Ensure your Google Sheet is shared publicly (Anyone with link can view)

### Extension not working on Cleverso
- Check the Cleverso URL - update `manifest.json` if needed
- Open DevTools (F12) and check console for error messages

## Customizing for your Cleverso URL

Edit `manifest.json` and update the `content_scripts.matches` array with your actual Cleverso URL pattern:

```json
"content_scripts": [
  {
    "matches": ["https://your-cleverso-domain.com/*"],
    "js": ["content.js"],
    "css": ["content.css"]
  }
]
```

Then reload the extension in `chrome://extensions/`

## Keyboard Shortcuts

- **Ctrl+Shift+F** - Fill current row with matching translation
