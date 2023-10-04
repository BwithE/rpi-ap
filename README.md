# Raspberry Pi - WPA2 Access Point
The script will get the latest updates and apply all necessary configs for your Pi to act as an access point.

You will be prompted for SSID, Passphrase, Channel (which will also choose the mode), wireless card to broadcast from, and how many IP's to lease.
You need to specify "wlan0" as your wireless card if you're not using a secondary external wireless card.

If you use "wlan0", after the reboot boot, the pi will no longer be associated to the previous network it was setup on.
You will have to connect to the new access point you created, and ssh into the raspberry pi to modify any settings.
BEFORE CREATING THE ACCESS POINT, I RECOMMEND TURNING ON SSH.
AT ANYPOINT THAT YOU CAN'T CONFIGURE THE ACCESS POINT SETTINGS, YOU WILL NEED TO SSH INTO THE PI/ROUTER TO MODIFY THE CONFIGS.

Once you've specified all the necessary options, the machine will apply those options into the necessary conf files.
After all the settings have been configured, the Raspberry Pi will reboot and will start broadcasting as an access point.

Create a local copy of the script.
```wget https://raw.githubusercontent.com/BwithE/rpi-wpa2/main/rpi-ap.sh```

Make the script executable: ```sudo chmod +x rpi-ap.sh```
Then run the script: ```sudo ./rpi-ap.sh``` or ```sudo bash rpi-ap.sh```


