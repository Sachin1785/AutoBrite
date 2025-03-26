document.addEventListener('DOMContentLoaded', function() {
  const brightnessSlider = document.getElementById('brightnessSlider');
  const contrastSlider = document.getElementById('contrastSlider');
  const brightnessValue = document.getElementById('currentBrightness');
  const contrastValue = document.getElementById('currentContrast');

  // Debounce function to limit API calls
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Update display settings
  const updateSettings = debounce((brightness, contrast, setDefault = false) => {
    const endpoint = setDefault ? '/set_display' : '/set_display';
    fetch(`http://localhost:1108${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        brightness: parseInt(brightness),
        contrast: parseInt(contrast),
        setDefault: setDefault
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status !== 'success') {
        console.error('Error:', data.message);
      }
    })
    .catch(error => console.error('Error:', error));
  }, 100);

  // Handle slider changes - only update current values
  brightnessSlider.addEventListener('input', function() {
    brightnessValue.textContent = `${this.value}%`;
    updateSettings(this.value, contrastSlider.value, false);
  });

  contrastSlider.addEventListener('input', function() {
    contrastValue.textContent = `${this.value}%`;
    updateSettings(brightnessSlider.value, this.value, false);
  });

  // Add default settings handler - explicitly for defaults only
  document.getElementById('saveDefaults').addEventListener('click', function() {
    const defaultBrightness = parseInt(document.getElementById('defaultBrightness').value);
    const defaultContrast = parseInt(document.getElementById('defaultContrast').value);
    
    if (isNaN(defaultBrightness) || isNaN(defaultContrast)) {
      console.error('Invalid default values');
      return;
    }
    
    updateSettings(defaultBrightness, defaultContrast, true);
  });

  // Replace useDefault with resetToDefault handler
  document.getElementById('resetToDefault').addEventListener('click', function() {
    // Disable auto mode
    chrome.storage.sync.set({ autoEnabled: false });
    autoToggle.checked = false;
    
    // Get default values
    fetch('http://localhost:1108/get_current_settings')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.status === 'success' && data.defaultBrightness !== null && data.defaultContrast !== null) {
          // Apply default settings
          updateSettings(data.defaultBrightness, data.defaultContrast);
          
          // Update UI elements
          brightnessSlider.value = data.defaultBrightness;
          contrastSlider.value = data.defaultContrast;
          brightnessValue.textContent = `${data.defaultBrightness}%`;
          contrastValue.textContent = `${data.defaultContrast}%`;
        } else {
          console.error('No default settings available');
        }
      })
      .catch(error => {
        console.error('Error resetting to defaults:', error);
      });
  });

  // Get initial settings
  fetch('http://localhost:1108/get_current_settings')
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        brightnessSlider.value = data.brightness;
        contrastSlider.value = data.contrast;
        brightnessValue.textContent = `${data.brightness}%`;
        contrastValue.textContent = `${data.contrast}%`;
        
        // Set default values in input fields with fallback to current values
        const defaultBrightnessInput = document.getElementById('defaultBrightness');
        const defaultContrastInput = document.getElementById('defaultContrast');
        
        defaultBrightnessInput.value = data.defaultBrightness !== null ? 
          data.defaultBrightness : data.brightness;
        defaultContrastInput.value = data.defaultContrast !== null ? 
          data.defaultContrast : data.contrast;
        
        console.log('Received settings:', data); // Debug log
      } else {
        console.error('Error:', data.message);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      brightnessValue.textContent = 'Error';
      contrastValue.textContent = 'Error';
    });

  // Handle toggle state
  const autoToggle = document.getElementById('autoToggle');
  
  chrome.storage.sync.get(['autoEnabled'], function(result) {
    autoToggle.checked = result.autoEnabled !== undefined ? result.autoEnabled : true;
  });

  autoToggle.addEventListener('change', function() {
    const isEnabled = this.checked;
    chrome.storage.sync.set({ autoEnabled: isEnabled }, function() {
      console.log('Auto mode set to:', isEnabled);
      
      if (isEnabled) {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
          if (tabs[0] && tabs[0].url) {
            console.log('Sending current URL:', tabs[0].url);
            chrome.runtime.sendMessage({
              type: 'updateCurrentTab',
              url: tabs[0].url
            });
          } else {
            console.log('No active tab URL found');
          }
        });
      }
    });
  });
});