/**
 * Popup script for Reading Backlog extension.
 */

const API_BASE = 'http://127.0.0.1:5123/api';

// DOM elements
const urlInput = document.getElementById('url');
const tagsInput = document.getElementById('tags');
const saveBtn = document.getElementById('save-btn');
const statusDiv = document.getElementById('status');
const contentDiv = document.getElementById('content');
const priorityBtns = document.querySelectorAll('.priority-btn');

let selectedPriority = 'medium';

// Get current tab URL
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]?.url) {
        urlInput.value = tabs[0].url;
    }
});

// Priority button handling
priorityBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        priorityBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedPriority = btn.dataset.value;
    });
});

// Show status message
function showStatus(type, message) {
    statusDiv.className = `status ${type}`;
    statusDiv.textContent = message;
    statusDiv.classList.remove('hidden');
}

// Hide status
function hideStatus() {
    statusDiv.classList.add('hidden');
}

// Save article
saveBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) {
        showStatus('error', 'No URL found');
        return;
    }

    // Get tags
    const tagsValue = tagsInput.value.trim();
    const tags = tagsValue ? tagsValue.split(',').map(t => t.trim()).filter(Boolean) : [];

    // Disable button and show loading
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    showStatus('loading', 'Fetching article metadata...');

    try {
        let response;
        try {
            response = await fetch(`${API_BASE}/articles`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    tags: tags,
                    priority: selectedPriority,
                }),
            });
        } catch (networkError) {
            throw new Error('Server not running. Start it with: python scripts/start_server.py');
        }

        if (!response.ok) {
            let errorMessage = 'Failed to save article';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (e) {
                // JSON parsing failed, use default message
            }
            throw new Error(errorMessage);
        }

        const article = await response.json();

        // Show success
        contentDiv.classList.add('hidden');
        showStatus('success', `Saved: ${article.title}`);

        // Close popup after delay
        setTimeout(() => window.close(), 1500);

    } catch (error) {
        const message = typeof error.message === 'string' ? error.message : 'An error occurred';
        showStatus('error', message);
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Article';
    }
});
