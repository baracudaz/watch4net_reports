# Watch4net ReportPack CLI Management Utility

The purpose of the `manage-reports.py` utility as the name reveals is to allow Watch4net reports management over the CLI. The Watch4net comes with comprehesive UI to manage and edit the reports. However as reports get complex there is a need to export the reports into CM system in order to tract the changes.

## Prerequisites
Make sure to install the prerequsites from the `requirements.txt` file using well known `pip` command.
```
$ pip install -r requirements.txt
```

## Basic Usage
The utility displays a help message when started with `-h` CLI option.
```
$ ./manage-reports.py --help
usage: manage-reports.py [-h] [-d DEBUG] [-c CONF]
                         {list,pinned,get,put,build,remove} ...

Watch4net ReportPack CLI Management Utility

positional arguments:
  {list,pinned,get,put,build,remove}
    list                Show all ReportPacks
    pinned              Show the currently pinned ReportPacks
    get                 Download the specified ReportPack
    put                 Upload the specified ReportPack or APR file
    build               Build the ReportPack into a ARP file
    remove              Delete the specified ReportPack

optional arguments:
  -h, --help            show this help message and exit
  -d DEBUG, --debug DEBUG
                        Debugging level (default is info)

Credentials stored in config file:
  -c CONF, --conf CONF  Config file with credentials (default is config.ini)
```  

## Configuation
The configuration file `config.ini` contains the Watch4net user credentials and the hostname. 
```
$ cat config.ini 
# Watch4net credentials
[credentials]
hostname = localhost
username = admin
password = changeme
# ReportPack parameters
[reports]
```
The following two ports (or URLs) are expected for connecting to the Watch4net host:
* **APG_URL** = http://localhost:58080/APG/
* **WSGW_URL** = https://localhost:48443/

If your Watch4net happends to run behing firewall you can tunel the two required ports to localhost using the SSH:
```
ssh w4n-host -L 48443:w4n-host:48443 -L 58080:w4n-host:58080
```

## Listing the ReportPacks
You can get a list of ReportPacks with the **list** option. Additionally the **pinned** provides the list of currently active RPs.
```
$ ./manage-reports.py list
  id  name
----  -----------------------------
  72  EMC Smarts
  93  Traffic Flows
 166  Cisco NBAR
 213  Swisscom Development
 217  Cisco VoIP CUCM
 468  Oracle Palladion VoIP
 469  Oracle Palladion VoIP
 643  EMC Smarts
 661  Cisco QoS
 669  Cisco VoIP CUCM
 680  Cisco UCS
 706  Cisco MDS Nexus
 725  Default ReportPack
 734  Traffic Flows
 741  Traffic Flows
```
## Exporting the ReportPacks
Downloading the ReportPack from Watch4net can be done with **get** option and providing the report ID. This will download the specified RP as ARP file and the option **-x** with extract it. As a result we will get a bunch of **XML** files.
```
$ ./manage-reports.py get -id 661 -x
INFO: Downloading the ReportPack 'Cisco QoS' to the file 'reports/Cisco QoS.arp'
INFO: Unzipping ReportPack file 'reports/Cisco QoS.arp' to 'reports/Cisco QoS'
```
As you can see the RP is a bunch of XMLs that can be even put into a git repository for detailed tracking.
```
$ find reports/Cisco\ QoS -type f
reports/Cisco QoS/META-INF/MANIFEST.MF
reports/Cisco QoS/Cisco QoS/template.xml
```

## Importing the ReportPacks
Uploading the the RP is pretty easy too with **put** option. Just provide the name of RP or directly APR file.
```
$ ./manage-reports.py put -name "Cisco QoS"
INFO: Creating ReportPack from 'reports/Cisco QoS' to file 'reports/Cisco QoS.arp'
INFO: ReportPack 'Cisco QoS' ID '827' succesfully uploaded

$ ./manage-reports.py put -file reports/Cisco\ QoS.arp 
INFO: ReportPack 'Cisco QoS' ID '828' succesfully uploaded
```