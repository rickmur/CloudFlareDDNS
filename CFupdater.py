# Rick Mur - Maverick.Solutions - (c) 2016
__author__ = "Rick Mur"
__version__ = "1.0"

import yaml
import json
import logging
import requests
import os
from netaddr import IPAddress

print ("--------------------------------------------")
print ("Maverick.Solutions - CloudFlare DNS Updater")
print ("--------------------------------------------")

try:
  # Load settings files and verify if YAML contents are found
  configFile = open(os.path.dirname(__file__) + "/CFupdater.conf").read()
  myConfig = yaml.load(configFile)
  if (not myConfig):
    raise Exception

  # Get WAN (External) IP address from 2 sources, if first fails, failover
  try:
    getIP = requests.get("http://myip.dnsomatic.com")
  except ConnectionError:
    print ("WARNING: Primary IP check website unavailable, failover")
    getIP = requests.get("http://curlmyip.com")

  # Check if HTTP status is OK and response is received
  if (not getIP.ok):
    print ("HTTP error: " + getIP.reason)
    getIP.raise_for_status()

  # Format received IP in IPAddress type to verify contents
  myIP = IPAddress(getIP.text)
  print ("WAN IP: " + str(myIP))

  # Build headers for REST call and get zone list
  CFheaders = {
    "X-Auth-Email": myConfig["cloudflareEmail"],
    "X-Auth-Key": myConfig["cloudflareAuthKey"],
    "Content-Type": "application/json"
  }
  myZonesGet = requests.get("https://api.cloudflare.com/client/v4/zones?status=active", headers=CFheaders)

  # Check if HTTP status is OK and response is received
  if (not myZonesGet.ok):
    print ("HTTP error: " + myZonesGet.reason)
    myZonesGet.raise_for_status()

  # Lookup zone identifier in zone list and match against config
  myCFzones = myZonesGet.json()
  for CFzone in myCFzones["result"]:
    if CFzone["name"] in myConfig["zones"].keys():
      zoneName = CFzone["name"]
      zoneID = CFzone["id"]
      recordsConfig = myConfig["zones"][zoneName]
      print ("Found zone " + zoneName)

      # Get Records list to verify if records exist that want an update
      myRecordsGet = requests.get("https://api.cloudflare.com/client/v4/zones/" + zoneID + "/dns_records?type=A", headers=CFheaders)

      # Check if HTTP status is OK and response is received
      if (not myRecordsGet.ok):
        print ("HTTP error: " + myRecordsGet.reason)
        myRecordsGet.raise_for_status()

      # Lookup records in zone list and match against config
      myCFrecords = myRecordsGet.json()

      # Go through records found under zone
      for CFrecord in myCFrecords["result"]:
        record = str(CFrecord["name"])
        if record == zoneName:
          # If domain name is DNS entry, then use it as root in config
          record = "root"
        else:
          # Remove the domain name from the record
          record = record.split(".")[0]

        # Update all records that are
        if record in recordsConfig:
          if CFrecord["content"] == str(myIP):
            # IP is still the same so no update
            print ("\tNo update necessary for " + CFrecord["name"])
          else:
            # Update record with new IP
            CFrecord["content"] = str(myIP)

            # Send updated record back to CloudFlare, don't forget to format the dictionary as JSON
            updateRecord = requests.put("https://api.cloudflare.com/client/v4/zones/" + zoneID + "/dns_records/" + CFrecord["id"], data=json.dumps(CFrecord), headers=CFheaders)

            # Check if HTTP status is OK and response is received
            if (not myRecordsGet.ok):
              print ("HTTP error: " + myRecordsGet.reason)
              updateRecord.raise_for_status()

            # Check if CloudFlare response is Success or not
            updateRecordJson = updateRecord.json()
            if (bool(updateRecordJson["success"])):
              print ("\tUpdating " + CFrecord["name"] + " completed successfully")
            else:
              print ("\tERROR: Updating " + CFrecord["name"] + " failed!")
              print ("\tCloudFlare ERROR: " + str(updateRecordJson["errors"][0]["message"]))

  print ("--------------------------------------------")
  print ("All done! Thank you!")
except requests.ConnectionError:
  print ("----------------------------------------------------")
  print ("ERROR: Connection failed, please check Internet connection")
except requests.HTTPError:
  print ("----------------------------------------------------")
  print ("ERROR: Unexpected data received, check authentication settings")
except Exception as e:
  print ("----------------------------------------------------")
  print ("ERROR: Something went wrong with the following error:")
  print (e)
