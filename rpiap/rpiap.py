import os
from flask import Flask, render_template, request, redirect, url_for
import subprocess
import re

app = Flask(__name__, template_folder='templates')

# Define the directory paths for saving scan results
ARP_SCAN_DIR = os.path.join(os.getcwd(), 'arp')
NMAP_SCAN_DIR = os.path.join(os.getcwd(), 'nmap')

# Create the directories if they don't exist
os.makedirs(ARP_SCAN_DIR, exist_ok=True)
os.makedirs(NMAP_SCAN_DIR, exist_ok=True)

def read_config():
    config = {}
    with open('/etc/hostapd/hostapd.conf', 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config[key.strip()] = value.strip()
    return config

def read_ip_from_dhcpcd():
    with open('/etc/dhcpcd.conf', 'r') as f:
        for line in f:
            match = re.match(r'static ip_address=(\d+\.\d+\.\d+\.\d+)/\d+', line)
            if match:
                return match.group(1)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/wifi')
def settings():
    message = request.args.get('message')
    return render_template('wifi.html', message=message)

@app.route('/configure', methods=['POST'])
def configure():
    form_ssid = request.form['ssid']
    form_passphrase = request.form['pass']
    form_channel = request.form['channel']

    current_config = read_config()

    if form_ssid:
        current_config['ssid'] = form_ssid
    if form_passphrase:
        current_config['wpa_passphrase'] = form_passphrase
    if form_channel:
        current_config['channel'] = form_channel

    with open('/etc/hostapd/hostapd.conf', 'w') as f:
        for key, value in current_config.items():
            f.write(f"{key}={value}\n")

    subprocess.run(['sudo', 'systemctl', 'restart', 'hostapd'])

    return redirect(url_for('settings', message='Configuration saved successfully.'))

@app.route('/netenum', methods=['GET', 'POST'])
def netenum():
    if request.method == 'POST':
        scan_type = request.form['scan_type']
        interface = request.form['interface']
        network = request.form.get('network', '')

        if scan_type == 'arp':
            try:
                result = subprocess.check_output(['arp-scan', '-l', f'--interface={interface}']).decode()
                # Save the ARP scan results into a file in the 'arp' directory
                with open(os.path.join(ARP_SCAN_DIR, 'arp_scan_results.txt'), 'w') as f:
                    f.write(result)
            except subprocess.CalledProcessError as e:
                result = f"Error executing arp-scan: {e}"
        elif scan_type == 'nmap':
            try:
                result = subprocess.check_output(['nmap', '-p-', '-Pn', '-n', '-sV', "--open", f'{interface}', network]).decode()
                # Save the Nmap scan results into a file in the 'nmap' directory
                with open(os.path.join(NMAP_SCAN_DIR, 'nmap_scan_results.txt'), 'w') as f:
                    f.write(result)
            except subprocess.CalledProcessError as e:
                result = f"Error executing nmap: {e}"
        else:
            result = "Invalid scan type"

        # Redirect to the results page after saving the scan results
        return redirect(url_for('results'))

    return render_template('netenum.html', result=None)

@app.route('/results')
def results():
    # Read ARP scan results
    arp_scan_results = ''
    arp_scan_results_path = os.path.join(ARP_SCAN_DIR, 'arp_scan_results.txt')
    if os.path.exists(arp_scan_results_path):
        with open(arp_scan_results_path, 'r') as f:
            arp_scan_results = f.read()

    # Read Nmap scan results
    nmap_scan_results = ''
    nmap_scan_results_path = os.path.join(NMAP_SCAN_DIR, 'nmap_scan_results.txt')
    if os.path.exists(nmap_scan_results_path):
        with open(nmap_scan_results_path, 'r') as f:
            nmap_scan_results = f.read()

    return render_template('results.html', arp_scan_results=arp_scan_results, nmap_scan_results=nmap_scan_results)

if __name__ == '__main__':
    ip_address = read_ip_from_dhcpcd()
    if ip_address:
        app.run(host=ip_address, port=80, debug=True)
    else:
        print("Failed to read IP address from dhcpcd.conf. Please check the file.")
