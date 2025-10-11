/**
 * Popup script for extension settings
 */

const API_BASE = 'http://localhost:5000';

// Check backend status
async function checkBackendStatus() {
    const statusDiv = document.getElementById('status');

    try {
        const response = await fetch(`${API_BASE}/api/feeds`, { timeout: 3000 });

        if (response.ok) {
            statusDiv.className = 'status connected';
            statusDiv.innerHTML = '✅ Backend: Connected';
        } else {
            statusDiv.className = 'status disconnected';
            statusDiv.innerHTML = '⚠️ Backend: Error';
        }
    } catch (error) {
        statusDiv.className = 'status disconnected';
        statusDiv.innerHTML = '❌ Backend: Not Running';
    }
}

// Load settings
function loadSettings() {
    chrome.storage.sync.get(['exchangeRate'], (result) => {
        if (result.exchangeRate) {
            document.getElementById('exchangeRate').value = result.exchangeRate;
        }
    });
}

// Save settings
function saveSettings() {
    const exchangeRate = parseFloat(document.getElementById('exchangeRate').value);

    chrome.storage.sync.set({ exchangeRate }, () => {
        const btn = document.getElementById('saveBtn');
        btn.textContent = '✓ Saved!';
        setTimeout(() => {
            btn.textContent = 'Save Settings';
        }, 2000);
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    checkBackendStatus();

    document.getElementById('saveBtn').addEventListener('click', saveSettings);
});
