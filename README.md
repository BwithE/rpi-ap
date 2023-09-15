# Raspberry Pi - WPA2 Access Point
The script will get the latest updates and apply all necessary configs for your Pi to act as an access point.

First, make sure your Raspberry Pi is connected to an ethernet connection if you are not using an external wireless card for an initial internet connection.
Run the following commands.

sudo apt install wget -y
wget github.com/BwithE/Pi/rpi-ap.sh

To run the script, run the following

sudo bash rpi-ap.sh
or
sudo chmod +x rpi-ap.sh
sudo ./rpi-ap.sh

You will be prompted for SSID, Passphrase, Channel, wireless card to broadcast from, and how many IP's to lease.
You need to specify "wlan0" as your wireless card if you're not using a secondary external wireless card.

Once you've specified all the necessary options, the machine will apply those options into the necessary conf files.
After all the settings have been configured, the Raspberry Pi will reboot and will start broadcasting as an access point.
