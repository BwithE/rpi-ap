from flask import Flask, render_template, request, redirect, url_for
import subprocess
import re

app = Flask(__name__, template_folder='templates')  # Explicitly set the templates folder

# Function to read the current configuration
def read_config():
    config = {}
    with open('/etc/hostapd/hostapd.conf', 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config[key.strip()] = value.strip()
    return config

# COMMENT THIS OUT WHEN TESTING
# Function to read the IP address from dhcpcd.conf
def read_ip_from_dhcpcd():
    with open('/etc/dhcpcd.conf', 'r') as f:
        for line in f:
            match = re.match(r'static ip_address=(\d+\.\d+\.\d+\.\d+)/\d+', line)
            if match:
                return match.group(1)
    return None

# Route for the root URL
@app.route('/')
def index():
    return render_template('index.html')

# Route for the settings page
@app.route('/wifi')
def settings():
    # Check if a message is passed in the query parameters
    message = request.args.get('message')
    return render_template('wifi.html', message=message)

# Route for configuring the Raspberry Pi Access Point
@app.route('/configure', methods=['POST'])
def configure():
    form_ssid = request.form['ssid']
    form_passphrase = request.form['pass']
    form_channel = request.form['channel']

    current_config = read_config()

    # Update fields if modified
    if form_ssid:
        current_config['ssid'] = form_ssid
    if form_passphrase:
        current_config['wpa_passphrase'] = form_passphrase
    if form_channel:
        current_config['channel'] = form_channel

    # Write updated configuration back to file
    with open('/etc/hostapd/hostapd.conf', 'w') as f:
        for key, value in current_config.items():
            f.write(f"{key}={value}\n")

    # Restart hostapd service
    subprocess.run(['sudo', 'systemctl', 'restart', 'hostapd'])

    # Redirect back to settings page with a success message
    return redirect(url_for('settings', message='Configuration saved successfully.'))


# USE THIS FOR TESTING LOCALLY
#if __name__ == '__main__':
#    ip_address = '127.0.0.1'  # Assign as a string
#    app.run(host=ip_address, port=80, debug=True)

# COMMENT THIS ONE OUT WHEN TESTING
if __name__ == '__main__':
    ip_address = read_ip_from_dhcpcd()
    if ip_address:
        app.run(host=ip_address, port=80, debug=True)
    else:
        print("Failed to read IP address from dhcpcd.conf. Please check the file.")
