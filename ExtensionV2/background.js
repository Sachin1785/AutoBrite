let isAutoEnabled = true;

chrome.storage.sync.get(['autoEnabled'], function(result) {
  isAutoEnabled = result.autoEnabled !== undefined ? result.autoEnabled : true;
});

chrome.storage.onChanged.addListener(function(changes, namespace) {
  if (changes.autoEnabled) {
    isAutoEnabled = changes.autoEnabled.newValue;
    console.log("Auto brightness mode:", isAutoEnabled ? "enabled" : "disabled");
  }
});

function getMainUrl(url) {
  try {
    if (!url || !url.startsWith('http')) {
      return null;
    }
    const urlObj = new URL(url);
    return `${urlObj.protocol}//${urlObj.hostname}`;
  } catch (e) {
    console.error('Error parsing URL:', e);
    return null;
  }
}

function sendUrlToBackend(url) {
  if (!isAutoEnabled) {
    console.log("Auto brightness disabled, skipping update");
    return;
  }

  const mainUrl = getMainUrl(url);
  if (!mainUrl) {
    console.log("Invalid URL, skipping update");
    return;
  }

  console.log("Sending URL to backend:", mainUrl);
  fetch('http://localhost:1108/set_website', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ website_url: mainUrl })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    console.log('Success:', data);
    if (data.brightness === null || data.contrast === null) {
      console.log('No settings found for this website');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    // Disable auto mode only on connection errors
    if (error.message.includes('Failed to fetch')) {
      chrome.storage.sync.set({ autoEnabled: false });
    }
  });
}

chrome.runtime.onMessage.addListener(function(message) {
  if (message.type === 'updateCurrentTab') {
    sendUrlToBackend(message.url);
  }
});

chrome.tabs.onActivated.addListener(function(activeInfo) {
  chrome.tabs.get(activeInfo.tabId, function(tab) {
    console.log("Active tab URL:", tab.url);
    sendUrlToBackend(tab.url);
  });
});

chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
  if (changeInfo.status === 'complete' && tab.url) {
    console.log("Updated tab URL:", tab.url);
    sendUrlToBackend(tab.url);
  }
});