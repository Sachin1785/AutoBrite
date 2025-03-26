from flask import Flask, request, jsonify
from flask_cors import CORS
from monitorcontrol import get_monitors
import logging
import csv
import os
import time

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)

CSV_FILE = 'settings.csv'

transition_in_progress = False

def get_current_brightness_and_contrast():
    try:
        monitors = get_monitors()
        for monitor in monitors:
            with monitor:
                current_brightness = monitor.get_luminance()
                current_contrast = monitor.get_contrast()
                return current_brightness, current_contrast
    except Exception as e:
        logging.error("Error getting current brightness and/or contrast: %s", e)
        return None, None

def gradual_transition(current_value, target_value, step=1, delay=0.005):
    global transition_in_progress
    if current_value is None or target_value is None:
        return target_value
    while current_value != target_value:
        if not transition_in_progress:
            return
        if current_value < target_value:
            current_value = min(current_value + step, target_value)
        else:
            current_value = max(current_value - step, target_value)
        yield current_value
        time.sleep(delay)

def set_brightness_and_contrast(brightness=None, contrast=None):
    global transition_in_progress
    transition_in_progress = False
    time.sleep(0.1)  # Wait for previous transition to finish
    transition_in_progress = True
    try:
        monitors = get_monitors()
        for monitor in monitors:
            with monitor:
                current_brightness, current_contrast = get_current_brightness_and_contrast()
                if brightness is not None:
                    for value in gradual_transition(current_brightness, brightness):
                        monitor.set_luminance(value)
                if contrast is not None:
                    for value in gradual_transition(current_contrast, contrast):
                        monitor.set_contrast(value)
        transition_in_progress = False
        return None
    except Exception as e:
        transition_in_progress = False
        logging.error("Error setting brightness and/or contrast: %s", e)
        return {"status": "error", "message": str(e)}

def save_settings_to_csv(website_url, brightness, contrast):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['website_url', 'brightness', 'contrast'])
        writer.writerow([website_url, brightness, contrast])

def normalize_url(url):
    return url.rstrip('/')

def get_settings_from_csv(website_url):
    website_url = normalize_url(website_url)
    if not os.path.isfile(CSV_FILE):
        return None, None
    
    default_brightness = None
    default_contrast = None
    
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Store default values when found
            if row['website_url'] == 'default':
                default_brightness = int(row['brightness'])
                default_contrast = int(row['contrast'])
                continue
                
            if normalize_url(row['website_url']) == website_url:
                brightness = int(row['brightness']) if row['brightness'] else default_brightness
                contrast = int(row['contrast']) if row['contrast'] else default_contrast
                return brightness, contrast
    
    return default_brightness, default_contrast

def update_default_settings(brightness, contrast):
    temp_file = CSV_FILE + '.tmp'
    with open(CSV_FILE, 'r') as file, open(temp_file, 'w', newline='') as temp:
        reader = csv.DictReader(file)
        writer = csv.DictWriter(temp, fieldnames=reader.fieldnames)
        writer.writeheader()
        
        for row in reader:
            if row['website_url'] == 'default':
                row['brightness'] = str(brightness)
                row['contrast'] = str(contrast)
            writer.writerow(row)
    
    os.replace(temp_file, CSV_FILE)

def get_default_settings():
    if not os.path.isfile(CSV_FILE):
        logging.debug("CSV file not found")
        return None, None
    
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['website_url'] == 'default':
                brightness = int(row['brightness'])
                contrast = int(row['contrast'])
                # logging.debug(f"Found default settings: brightness={brightness}, contrast={contrast}")
                return brightness, contrast
    logging.debug("No default settings found in CSV")
    return None, None

@app.route('/set_display', methods=['POST'])
def api_set_display():
    data = request.json
    brightness = data.get('brightness')
    contrast = data.get('contrast')
    set_default = data.get('setDefault', False)
    
    # logging.debug(f"Received request with brightness: {brightness}, contrast: {contrast}, setDefault: {set_default}")
    
    if brightness is not None or contrast is not None:
        if set_default:
            update_default_settings(brightness, contrast)
        
        result = set_brightness_and_contrast(brightness, contrast)
        if result and result.get("status") == "error":
            return jsonify(result), 500
        return jsonify({"status": "success", "brightness": brightness, "contrast": contrast}), 200
    else:
        return jsonify({"status": "error", "message": "Brightness or contrast value is required"}), 400

@app.route('/set_website', methods=['POST'])
def api_set_website():
    data = request.json
    website_url = data.get('website_url')
    logging.debug(f"Received request with website URL: {website_url}")
    if website_url:
        brightness, contrast = get_settings_from_csv(website_url)
        result = set_brightness_and_contrast(brightness, contrast)
        if result and result.get("status") == "error":
            return jsonify(result), 500
        return jsonify({"status": "success", "website_url": website_url, "brightness": brightness, "contrast": contrast}), 200
    else:
        return jsonify({"status": "error", "message": "Website URL is required"}), 400

@app.route('/get_current_settings', methods=['GET'])
def api_get_current_settings():
    try:
        current_brightness, current_contrast = get_current_brightness_and_contrast()
        default_brightness, default_contrast = get_default_settings()
        response = {
            "status": "success", 
            "brightness": current_brightness, 
            "contrast": current_contrast,
            "defaultBrightness": default_brightness,
            "defaultContrast": default_contrast
        }
        # logging.debug(f"Sending settings: {response}")
        return jsonify(response), 200
    except Exception as e:
        # logging.error("Error getting current brightness and/or contrast: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# Add this new route to get website settings
@app.route('/get_websites', methods=['GET'])
def api_get_websites():
    try:
        websites = []
        with open(CSV_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['website_url'] != 'default':
                    websites.append({
                        'url': row['website_url'],
                        'brightness': row['brightness'],
                        'contrast': row['contrast']
                    })
        return jsonify({"status": "success", "websites": websites}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update_website', methods=['POST'])
def api_update_website():
    data = request.json
    url = data.get('url')
    brightness = data.get('brightness')
    contrast = data.get('contrast')

    if not all([url, brightness, contrast]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        temp_file = CSV_FILE + '.tmp'
        with open(CSV_FILE, 'r') as file, open(temp_file, 'w', newline='') as temp:
            reader = csv.DictReader(file)
            writer = csv.DictWriter(temp, fieldnames=reader.fieldnames)
            writer.writeheader()
            
            for row in reader:
                if row['website_url'] == url:
                    row['brightness'] = str(brightness)
                    row['contrast'] = str(contrast)
                writer.writerow(row)
        
        os.replace(temp_file, CSV_FILE)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_website', methods=['POST'])
def api_add_website():
    data = request.json
    url = data.get('url')
    brightness = data.get('brightness')
    contrast = data.get('contrast')

    if not all([url, brightness, contrast]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        with open(CSV_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([url, brightness, contrast])
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_website', methods=['POST'])
def api_delete_website():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"status": "error", "message": "URL is required"}), 400

    try:
        temp_file = CSV_FILE + '.tmp'
        with open(CSV_FILE, 'r') as file, open(temp_file, 'w', newline='') as temp:
            reader = csv.DictReader(file)
            writer = csv.DictWriter(temp, fieldnames=reader.fieldnames)
            writer.writeheader()
            
            for row in reader:
                if row['website_url'] != url:
                    writer.writerow(row)
        
        os.replace(temp_file, CSV_FILE)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1204, debug=True)
