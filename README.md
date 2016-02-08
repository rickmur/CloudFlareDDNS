# CloudFlare DNS Updating tool
*Simple Dynamic DNS client for CloudFlare written in Python*

This is a simple script to update a CloudFlare DNS record with your WAN IP. CloudFlare by default doesn't support Dynamic DNS updates from other platforms than its default program (ddclient). I wrote this script to run on my Synology NAS.

This has been an exercise to get familier with Python, so any comments and improvements regarding my code are welcome!

If you encounter a problem, please file a Github issue.

##How to get started
1. Download the files on your system using `git clone https://github.com/rickmur/CloudFlareDDNS.git`. Any further updates are downloaded using `git pull` from the new directory
2. Install required libraries with `pip install -r requirements.txt`. If your Synology doesn't have pip installed yet, follow the steps in the next section
3. Copy `CFupdater.default` to `CFupdater.conf` with `cp CFupdater.default CPupdater.conf`
4. Edit `CFupdater.conf` to include your CloudFlare username (e-mail), API key (found in Settings panel) and your domainnames (zones) and records as per the example below
5. Run `crontab -e` or on Synology platforms `vi /etc/crontab` and append a line to enable recurring updates as per the example below

#####Install PIP on Synology
1. Set-up SSH to your Synology NAS
2. Enter `wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py`
3. Run `python get-pip.py`

#####Sample crontab job
The following line should be appended to your crontab file (edited either with `crontab -e` or on Synology with `vi /etc/crontab`. This line will execute the script every hour on every day on minute 0 of each hour.

    0       *       *       *       *       root    python /PATH_TO_FILES/CFupdater.py

##Sample configuration
- Please be careful with sharing the CloudFlare API key and E-mail, treat it as a username/password.
- There is **no** limit on the amount of zones and records per zone
- If you want to update the **root** A-record of your zone (known as **@** in Cloudlare) like `example.com`, use **root** as the record name
- If you want to enable logging, use the `file` setting to set all logging to output to a file in the same directory.
- If you want to enable syslog which will output to your system default logfile use the `syslog` setting and set to `true` or `false` to enable or disable
- When all logging settings are removed, only text output is shown when running the script
```YAML
# List of DNS zones to check
# Use the keyword 'root' to match the A-record of the domain itself, like 'example.com'
---
cloudflareEmail: yourEmailToLogin
cloudflareAuthKey: yourAPIkey

zones:
    example.com:
        - root
        - home
    example2.net:
        - www
        - myhost

# Put a file name with full path (or without in case you want to use the CFupdater.py directory)
# Syslog logs to your systems default log file, use True or False to enable/disable
logging:
    file: CFupdater.log
    syslog: true
```

##License
This software is licensed under the MIT License

Copyright (c) 2016 - Maverick.Solutions - Rick Mur
