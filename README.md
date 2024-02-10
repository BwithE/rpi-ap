# Raspberry Pi Access Point

This Bash script facilitates the setup of a Raspberry Pi as a WPA2 Access Point. It uses Python to host a webpage that can also change configuration settings. The script ensures that your Pi is up-to-date and applies all the necessary configurations to establish it as an access point. 

Beware, there is no login security from the webpage. I am currently working on a Captive Portal that will integrate fully into this project. Please check out https://github.com/BwithE/captiveportal

![image](https://github.com/BwithE/rpi-ap/assets/144924113/684a20f3-7087-4853-bbaf-2268d6ea3322)


## Usage:

Create a local copy of the script.

```git clone https://github.com/bwithe/rpi-ap```

Then run the script:

```sudo bash rpi-ap/rpi-ap.sh``` 

Once the script installs, it will reboot. This could take a few minnutes.

After the reboot, you should see "YOUR SSID" broadcasting.

Please connect to the ACCESS POINT with the credentials YOU created, then go to the following ```10.10.10.1```

You will then be able to see the "Reconfiguration Screen"

## Configuration:

The script prompts you for the following configuration options:

- **SSID:** Service Set Identifier for your access point.
- **Passphrase:** Password for the network.
- **Channel:** Configures the network to operate on either 2.4GHz or 5GHz.
- **Wireless Card:** Choose the wireless card to broadcast from (default is "wlan0").
- **Number of IPs:** Specify the number of users allowed to join the network (2-20).
- **VPN Configuration (Optional):** If desired, configure OPENVPN settings for VPN usage.

**Note:** Specify "wlan0" as your wireless card if you're not using a secondary external wireless card.

## Process Overview:

1. **User Input:**
   - Collects user-specified settings for the access point.

2. **VPN Configuration (Optional):**
   - If a VPN is chosen, the user is prompted to provide the VPN configuration file's full path.

3. **Channel Mode Determination:**
   - Determines the mode ("g" or "a") based on the user-specified channel.

4. **Display User Input:**
   - Displays a summary of the specified settings.

5. **Installation and Configuration:**
   - Updates and installs necessary applications for access point functionality.
   - Configures network interfaces, IP forwarding, and iptables rules for NAT.

6. **VPN Configuration (if specified):**
   - Applies additional configurations for VPN settings if specified.

7. **Service Start and System Reboot:**
   - Starts required services (hostapd, dnsmasq, ssh) and enables them to start on boot.
   - Initiates a system reboot after applying all configurations.

Upon completion, the Raspberry Pi will reboot and start broadcasting as an access point. Please review the script and its comments before execution, as it involves network configuration and system-level changes.
