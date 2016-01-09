# Rick Mur - Maverick.Solutions - (c) 2016
__author__ = "Rick Mur"
__version__ = "1.0"

import yaml
import json
import logging
import syslog
import requests
import os
from netaddr import IPAddress

print ("--------------------------------------------")
print ("Maverick.Solutions - CloudFlare DNS Updater")
print ("--------------------------------------------")

try:

  # Setup logging, set 'requests' logging to WARNING instead of INFO
  logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
  log = logging.getLogger("CFupdater")
  logging.getLogger("requests").setLevel(logging.WARNING)

  # Load settings files and verify if YAML contents are found
  configFile = os.path.realpath(os.path.dirname(__file__)) + "/CFupdater.conf"
  myConfig = yaml.load(open(configFile).read())
  if (not myConfig):
    raise Exception

  # Check if logging to file is wanted and setup logging
  logFile = ""
  try:
    logFile = os.path.realpath(myConfig["logging"]["file"])
  except:
    pass

  if (logFile):
    handler = logging.FileHandler(logFile)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s-%(name)s-%(levelname)s: %(message)s"))
    log.addHandler(handler)

  # Get WAN (External) IP address from 2 sources, if first fails, failover
  try:
    getIP = requests.get("http://myip.dnsomatic.com")
  except ConnectionError:
    log.warning("WARNING: Primary IP check website unavailable, failover")
    getIP = requests.get("http://curlmyip.com")

  # Check if HTTP status is OK and response is received
  if (not getIP.ok):
    log.error ("HTTP error: " + getIP.reason)
    getIP.raise_for_status()

  # Format received IP in IPAddress type to verify contents
  myIP = IPAddress(getIP.text)
  log.info ("WAN IP: " + str(myIP))

  # Build headers for REST call and get zone list
  CFheaders = {
    "X-Auth-Email": myConfig["cloudflareEmail"],
    "X-Auth-Key": myConfig["cloudflareAuthKey"],
    "Content-Type": "application/json"
  }
  myZonesGet = requests.get("https://api.cloudflare.com/client/v4/zones?status=active", headers=CFheaders)

  # Check if HTTP status is OK and response is received
  if (not myZonesGet.ok):
    log.error ("HTTP error: " + myZonesGet.reason)
    myZonesGet.raise_for_status()

  # Lookup zone identifier in zone list and match against config
  myCFzones = myZonesGet.json()
  for CFzone in myCFzones["result"]:
    if CFzone["name"] in myConfig["zones"].keys():
      zoneName = CFzone["name"]
      zoneID = CFzone["id"]
      recordsConfig = myConfig["zones"][zoneName]
      log.info("Found zone " + zoneName)

      # Get Records list to verify if records exist that want an update
      myRecordsGet = requests.get("https://api.cloudflare.com/client/v4/zones/" + zoneID + "/dns_records?type=A", headers=CFheaders)

      # Check if HTTP status is OK and response is received
      if (not myRecordsGet.ok):
        log.error ("HTTP error: " + myRecordsGet.reason)
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
            log.info ("\tNo update necessary for " + CFrecord["name"])
          else:
            # Update record with new IP
            CFrecord["content"] = str(myIP)

            # Send updated record back to CloudFlare, don't forget to format the dictionary as JSON
            updateRecord = requests.put("https://api.cloudflare.com/client/v4/zones/" + zoneID + "/dns_records/" + CFrecord["id"], data=json.dumps(CFrecord), headers=CFheaders)

            # Check if HTTP status is OK and response is received
            if (not myRecordsGet.ok):
              log.error ("HTTP error: " + myRecordsGet.reason)
              updateRecord.raise_for_status()

            # Check if CloudFlare response is Success or not
            updateRecordJson = updateRecord.json()
            if (bool(updateRecordJson["success"])):
              log.info ("\tUpdating " + CFrecord["name"] + " completed successfully")
            else:
              log.error ("\tERROR: Updating " + CFrecord["name"] + " failed!")
              log.error ("\tCloudFlare ERROR: " + str(updateRecordJson["errors"][0]["message"]))

  log.info("All done! Thank you!")
except requests.ConnectionError:
  log.error ("ERROR: Connection failed, please check Internet connection")
except requests.HTTPError:
  log.error ("ERROR: Unexpected data received, check authentication settings")
except Exception as e:
  log.exception("ERROR: Something went wrong with the following error:")
  syslog.syslog(syslog.LOG_ERR, "ERROR: Something went wrong with the following error:" + str(e))
