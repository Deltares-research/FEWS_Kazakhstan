# TalsimFEWSAdapter

## Changelog

### v0.12
* allow multiple values for one parameter in the config file to be split by either comma (",") or indented newlines

### v0.11
* remove config parameter `runfile` and added new optional parameter `variation_id` instead
* allow inline comments starting with "#" in config file
* improve handling of optional config parameters
* small improvements to FEWS PI Timeseries XML output
* set Talsim engine language to English
* if Talsim simulation is unsuccessful, abort run and output Talsim error message
* update talsim package to v1.1.0
* update timeseries module to v1.5.0 and use it for reading and writing FEWS PI Timeseries XML files