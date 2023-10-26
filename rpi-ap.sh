#!/bin/bash

# This script creates a RASPBERRY PI ACCESS POINT
# With user specified settings

echo "
    ____        _       ___                            ____        _       __ 
   / __ \____  (_)     /   | _____________  __________/ __ \____  (_)___  / /_
  / /_/ / __ \/ /_____/ /| |/ ___/ ___/ _ \/ ___/ ___/ /_/ / __ \/ / __ \/ __/
 / _, _/ /_/ / /_____/ ___ / /__/ /__/  __(__  |__  ) ____/ /_/ / / / / / /_  
/_/ |_/ .___/_/     /_/  |_\___/\___/\___/____/____/_/    \____/_/_/ /_/\__/  
     /_/                                                                      
    "

read -p "What would you like the SSID to be?: " ssid
read -p "What would you like the passphrase to be?: " pass
read -p "What channel would you like your network to run on?: " channel
read -p "What network card would you like to use? (or press Enter for 'wlan0'): " wificard
read -p "How many user's would you like to be able to join this network? (ex: 2-50): " allowed_ips
read -p "Will this AP be used with a VPN? (yes or no): " cloud

# Use default value "wlan0" if the user presses Enter without typing anything
if [ -z "$wificard" ]; then
  wificard="wlan0"
fi

#  sets VPN settings based off users vpn cert location
if [ "$cloud" = "yes" ]; then
  read -p "Please specify full path for your VPN conf file. (/home/user/user.ovpn)" vpnconf
fi

# Based off user input, the channel specifies the mode
if [[ $channel -ge 1 && $channel -le 11 ]]; then
  mode="g"
elif [[ $channel -ge 36 && $channel -le 196 ]]; then
  mode="a"
else
  echo "Invalid channel number."
  exit 1
fi

clear

echo "This script is about to apply updates and install the necessary applications to make this machine an access point."
echo " "
echo "SSID: $ssid"
echo "Password: $pass"
echo "Wireless card: $wificard"
echo "Mode and Channel: $mode $channel"
if [ "$cloud" = "yes" ]; then
  echo "VPN conf location: $vpnconf"
fi
echo " "
echo "To modify Access Point settings, check the '/etc/hostapd/hostapd.conf'"
echo " "
read -n 1 -r -s -p $'Press enter to continue if the values above are correct. Otherwise "Ctrl + c" to reenter...\n'
clear

# Applies update then install required software for the application
sudo apt-get update -y 
sudo apt-get install hostapd dnsmasq -y
sudo DEBIAN_FRONTEND=noninteractive apt install -y netfilter-persistent iptables-persistent

#  installs openvpn
if [ "$cloud" = "yes" ]; then
  sudo apt install openvpn -y
fi

# writes settings to /etc/dhcpcd.conf
clear
sudo tee -a /etc/dhcpcd.conf << EOF
interface $wificard
static ip_address=10.10.10.1/24
nohook wpa_supplicant
EOF

# writes routing settings for wireless to eth0
clear
sudo tee -a /etc/sysctl.d/routed-ap.conf << EOF
net.ipv4.ip_forward=1
EOF

sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo netfilter-persistent save

# writes settings to /etc/network/interfaces
clear
sudo tee -a /etc/network/interfaces << EOF
auto lo
iface lo inet loopback

auto eth0
allow-hotplug eth0
iface eth0 inet dhcp

auto $wificard
allow-hotplug $wificard
iface $wificard inet static
address 10.10.10.1
netmask 255.255.255.0
EOF

# writes settings to /etc/dnsmasq.conf
clear
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.old
sudo tee -a /etc/dnsmasq.conf << EOF
interface=$wificard
dhcp-range=10.10.10.2,10.10.10.$allowed_ips,255.255.255.0,24h
domain=wlan
address=/rt.wlan/10.10.10.1
EOF

# Writes configs to "/etc/hostapd/hostapd.conf
clear
sudo tee -a /etc/hostapd/hostapd.conf << EOF
interface=$wificard
ssid=$ssid
hw_mode=$mode
channel=$channel
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$pass
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# new settings ###########################
# if any issues, delete between these hashes
# updates hostapd configurations
sudo sed -i 's/#DAEMON_CONF=""/DAEMON_CONF="\/etc\/hostapd\/hostapd.conf"/' /etc/default/hostapd

# enables IP forwarding
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
sudo sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf

# configures iptables to allow NAT
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"

# enable IP forwarding on boot
sudo sed -i '/^exit 0/ i iptables-restore < /etc/iptables.ipv4.nat' /etc/rc.local
##########################################


# Starts required services and then reboots the machine
clear
sudo systemctl start hostapd
sudo systemctl unmask hostapd.service
sudo systemctl enable hostapd
sudo systemctl start dnsmasq
sudo systemctl enable dnsmasq
sudo systemctl enable ssh

#  sets VPN settings for tun0
if [ "$cloud" = "yes" ]; then
   sudo openvpn $vpnconf &
   sudo ip route add default dev tun0
   sudo sysctl -w net.ipv4.ip_forward=1
   sudo iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE
   sudo netfilter-persistent save
   # echo "@reboot sudo openvpn $vpnconf" > /etc/cron.d/cronjob
fi

# After everythings done running, the PI will reboot
sudo reboot
