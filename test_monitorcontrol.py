from monitorcontrol import get_monitors

def test_brightness(value):
    try:
        monitors = get_monitors()
        for monitor in monitors:
            with monitor:
                monitor.set_luminance(value)
        print("Brightness set to", value)
    except Exception as e:
        print("Error setting brightness:", e)

def test_contrast(value):
    try:
        monitors = get_monitors()
        for monitor in monitors:
            with monitor:
                monitor.set_contrast(value)
        print("Contrast set to", value)
    except Exception as e:
        print("Error setting contrast:", e)

# Test setting brightness and contrast
test_brightness(20)
test_contrast(50)
