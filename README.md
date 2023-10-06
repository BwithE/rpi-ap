# Raspberry Pi - WPA2 Access Point
The script will get the latest updates and apply all necessary configs for your Pi to act as an access point.

You will be prompted for SSID, Passphrase, Channel (which will configure 2.4 or 5), wireless card to broadcast from, and how many IP's to lease.

You need to specify "wlan0" as your wireless card if you're not using a secondary external wireless card.

Once you've specified all the necessary options, the machine will apply those options into the necessary conf files.

After all the settings have been configured, the Raspberry Pi will reboot and will start broadcasting as an access point.


**_FIRST: Create a local copy of the script._**


```wget https://raw.githubusercontent.com/BwithE/rpi-wpa2/main/rpi-ap.sh```

**_Make the script executable:_**

```sudo chmod +x rpi-ap.sh```

**_Then run the script:_**

```sudo ./rpi-ap.sh``` 

**_or_**

```sudo bash rpi-ap.sh```


