# Rick Mur - Maverick.Solutions - (c) 2016
import yaml
import json
import logging
import syslog
import requests
import os
from netaddr import IPAddress, IPNetwork
from logging.handlers import RotatingFileHandler

print ("--------------------------------------------")
print ("Maverick.Solutions - CloudFlare DNS Updater")
print ("--------------------------------------------")

__author__ = "Rick Mur"
__version__ = "2.0"
syslogYes = False
IPv4 = False
IPv6 = False


def update_records(dns_record, records_config, the_ip, zone_id, zone_name):
    # Get Records list to verify if records exist that want an update
    my_records_get = requests.get(
        "https://api.cloudflare.com/client/v4/zones/" + zone_id + "/dns_records?type=" + dns_record, headers=CFheaders)

    # Check if HTTP status is OK and response is received
    if not my_records_get.ok:
        msg = "HTTP error: " + my_records_get.reason
        log.error(msg)
        if syslogYes:
            syslog.syslog(syslog.LOG_ERR, msg)
        my_records_get.raise_for_status()

    # Lookup records in zone list and match against config
    my_cf_records = my_records_get.json()

    # Go through records found under zone
    for cfrecord in my_cf_records["result"]:
        record = str(cfrecord["name"])
        if record == zone_name:
            # If domain name is DNS entry, then use it as root in config
            record = "root"
        else:
            # Remove the domain name from the record
            record = record.split(".")[0]

        # Update all records that are
        if record in records_config:
            # When IPv6 is used, the IP may need to be changed
            if dns_record == "AAAA":
                # If dynamic entry is used, use the IPv6 address of the current system
                if records_config[record].lower() == "dynamic":
                    setip = str(the_ip.ip)
                else:
                    # Otherwise use the ISP prefix and the address as requested
                    setip = str(the_ip.network)[:-2] + records_config[record]

                    # Make sure the entry is an actual IPv6 address
                    try:
                        testip = IPAddress(setip)
                    except:
                        raise Exception("IPv6 address: " + records_config[
                            record] + " at " + record + "." + zone_name + " is invalid!")
            else:
                setip = str(the_ip)

            if cfrecord["content"].lower() == setip.lower():
                # IP is still the same so no update
                log.info("\tNo update necessary for " + cfrecord["name"])
            else:
                # Update record with new IP
                cfrecord["content"] = setip

                # Send updated record back to CloudFlare, don't forget to format the dictionary as JSON
                update_record = requests.put(
                    "https://api.cloudflare.com/client/v4/zones/" + zone_id + "/dns_records/" + cfrecord["id"],
                    data=json.dumps(cfrecord), headers=CFheaders)

                # Check if HTTP status is OK and response is received
                if not my_records_get.ok:
                    msg = "HTTP error: " + my_records_get.reason
                    log.error(msg)
                    if syslogYes:
                        syslog.syslog(syslog.LOG_ERR, msg)
                    update_record.raise_for_status()

                # Check if CloudFlare response is Success or not
                update_records_json = update_record.json()
                if bool(update_records_json["success"]):
                    log.info("\tUpdating " + cfrecord["name"] + " completed successfully")
                else:
                    msg = "\t Updating " + cfrecord["name"] + " failed!"
                    log.error(msg)
                    if syslogYes:
                        syslog.syslog(syslog.LOG_ERR, msg)
                    msg = "\tCloudFlare ERROR: " + str(update_records_json["errors"][0]["message"])
                    log.error(msg)
                    if syslogYes:
                        syslog.syslog(syslog.LOG_ERR, msg)


try:
    # Setup logging, set 'requests' logging to WARNING instead of INFO
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    log = logging.getLogger("CFupdater")
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Load settings files and verify if YAML contents are found
    configFile = os.path.realpath(os.path.dirname(__file__)) + "/CFupdater.conf"
    myConfig = yaml.load(open(configFile).read())
    if not myConfig:
        raise Exception

    # Check if logging to file is wanted and setup logging and same for syslog
    logFile = ""
    try:
        myFile = myConfig["logging"]["file"]
        if myFile.startswith("/") or myFile.startswith("./"):
            logFile = os.path.realpath(myFile)
        else:
            logFile = os.path.realpath(os.path.dirname(__file__)) + "/" + myFile
    except:
        pass

    try:
        syslogYes = bool(myConfig["logging"]["syslog"])
    except:
        pass

    if logFile:
        handler = RotatingFileHandler(logFile, maxBytes=256000, backupCount=1)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s-%(name)s-%(levelname)s: %(message)s"))
        log.addHandler(handler)

    # Check if IPv4 is required to be updated in settings
    try:
        if myConfig["zones"]:
            IPv4 = True
    except:
        IPv4 = False

    # Check if IPv6 is required to be updated in settings
    try:
        if myConfig["zones_v6"]:
            IPv6 = True
    except:
        IPv6 = False

    if IPv4:
        # Get WAN (External) IP address from 2 sources, if first fails, fail-over
        try:
            getIP = requests.get("http://whatismyip.akamai.com/")
        except:
            msg = "Primary IP check website unavailable, failover"
            log.warning(msg)
            if syslogYes:
                syslog.syslog(syslog.LOG_WARNING, msg)
            getIP = requests.get("http://myip.dnsomatic.com")
        
        # Check if HTTP status is OK and response is received
        if not getIP.ok:
            msg = "HTTP error: " + getIP.reason
            log.error(msg)
            if syslogYes:
                syslog.syslog(syslog.LOG_ERR, msg)
            getIP.raise_for_status()

        # Format received IP in IPAddress type to verify contents
        myIP = IPAddress(getIP.text)
        # Check if getIP is really IPv4
        if not myIP.version == 4:
            msg = "This IP is not IPv4 which was expected, using IPv6 only?"
            raise Exception(msg)
        else:
            log.info("WAN IPv4: " + str(myIP))

    if IPv6:
        # Try to get prefixlength from config file, if not existent assume /64
        try:
            prefixlength = str(myConfig["zones_v6"]["isp_prefixlength"])
        except:
            prefixlength = "/64"

        # Get WAN (External) IPv6 address from 2 sources, if first fails, failover
        try:
            getIPv6 = requests.get("http://ipv6-test.com/api/myip.php")
        except requests.ConnectionError:
            msg = "Primary IPv6 check website unavailable, failover"
            log.warning(msg)
            if syslogYes:
                syslog.syslog(syslog.LOG_WARNING, msg)
            getIPv6 = requests.get("http://v6.ident.me/")

        # Check if HTTP status is OK and response is received
        if not getIPv6.ok:
            msg = "HTTP error: " + getIPv6.reason
            log.error(msg)
            if syslogYes:
                syslog.syslog(syslog.LOG_ERR, msg)
            getIPv6.raise_for_status()

        # Format received IP in IPAddress type to verify contents and check if valid
        try:
            msg = "No IPv6 address found, but IPv6 zones are configured, check IPv6 Internet connection"
            myIPv6 = IPNetwork(getIPv6.text + prefixlength)
            if not myIPv6.version == 6:
                raise Exception(msg)
            else:
                log.info("WAN IPv6: " + str(myIPv6))
        except:
            raise Exception(msg)

    # Build headers for REST call and get zone list
    CFheaders = {
        "X-Auth-Email": myConfig["cloudflareEmail"],
        "X-Auth-Key": myConfig["cloudflareAuthKey"],
        "Content-Type": "application/json"
    }
    myZonesGet = requests.get("https://api.cloudflare.com/client/v4/zones?status=active", headers=CFheaders)

    # Check if HTTP status is OK and response is received
    if not myZonesGet.ok:
        msg = "HTTP error: " + myZonesGet.reason
        log.error(msg)
        if syslogYes:
            syslog.syslog(syslog.LOG_ERR, msg)
        myZonesGet.raise_for_status()

    # Lookup zone identifier in zone list and match against config
    myCFzones = myZonesGet.json()
    for CFzone in myCFzones["result"]:
        zoneName = CFzone["name"]
        zoneID = CFzone["id"]

        if IPv4:
            if CFzone["name"] in myConfig["zones"].keys():
                recordsConfig = myConfig["zones"][zoneName]
                log.info("IPv4: Found zone " + zoneName)

                # Call UpdateRecords function to update A records
                update_records("A", recordsConfig, myIP, zoneID, zoneName)

        if IPv6:
            if CFzone["name"] in myConfig["zones_v6"].keys():
                recordsConfig = myConfig["zones_v6"][zoneName]
                log.info("IPv6: Found zone " + zoneName)

                # Call UpdateRecords function to update AAAA records
                update_records("AAAA", recordsConfig, myIPv6, zoneID, zoneName)

    log.info("All done! Thank you!")
except requests.ConnectionError:
    msg = "Connection failed, please check Internet connection"
    log.error(msg)
    if syslogYes:
        syslog.syslog(syslog.LOG_ERR, msg)
except requests.HTTPError:
    msg = "Unexpected data received, check authentication settings"
    log.error(msg)
    if syslogYes:
        syslog.syslog(syslog.LOG_ERR, msg)
except Exception as e:
    msg = "Something went wrong: " + str(e.message)
    log.error(msg)
    if syslogYes:
        syslog.syslog(syslog.LOG_ERR, msg)
