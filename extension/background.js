/**
 * Background service worker for Reading Backlog extension.
 */

const API_BASE = 'http://127.0.0.1:5123/api';

/**
 * Send article to the backend API.
 */
async function saveArticle(data) {
  const response = await fetch(`${API_BASE}/articles`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save article');
  }

  return response.json();
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'saveArticle') {
    saveArticle(message.data)
      .then(article => sendResponse({ success: true, article }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
});
