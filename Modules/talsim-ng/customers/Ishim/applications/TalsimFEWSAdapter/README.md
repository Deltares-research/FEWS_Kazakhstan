# TalsimFEWSAdapter

TalsimFEWSAdapter is a model adapter for running [Talsim-NG](http://www.talsim.de) models under [Delft-FEWS](https://oss.deltares.nl/web/delft-fews).

It supports the following features:
* Read and process timeseries in FEWS PI Timeseries format
* Read and process model parameters in FEWS PI Parameters format
* Read and process state information in FEWS PI State format
* Read and process information in FEWS PI Run format
* Carry out a simulation with Talsim-NG
* Convert simulation results to FEWS PI Timeseries format

## Setup

TalsimFEWSAdapter requires the standard Talsim-NG folder structure:

```
+---talsim-ng
|   \---customers
|       \---<customername>                      # can be any name
|           +---applications
|           |   +---engine                      # directory with Talsim-NG executable
|           |   \---TalsimFEWSAdapter           # directory containing the TaslimFEWSAdapter itself
|           |       +---config                  # config directory
|           |       \---lib
|           |       \---log                     # log directory
|           \---projectData
|               \---fews
|                   +---dataBase
|                   |   \---fews_zre            # time series directory
|                   +---dataSets
|                   |   \---<dataset_folder>    # directory containing the Talsim dataset, can be any name
|                   +---extern
|                   |   +---FEWStoTALSIM        # data exchange from FEWS to Talsim
|                   |   \---TALSIMtoFEWS        # data exchange from Talsim to FEWS
```

## Configuration

TalsimFEWSAdapter is configured by creating an ini file in the directory `talsim-ng\customers\<customername>\applications\TaslimFEWSAdapter\config`, see `config_template.ini` for possible config values.

Whenever a config parameter needs to hold multiple values, these can be separated either by comma (",") or by indented newlines, i.e. the following two examples are equivalent:
```
parameterX = value1, value2
```
and
```
parameterX =
    value1
    value2
```

## Input time series
Input time series provided by FEWS need to be specified under `timeseries_files`. These need to be mapped to time series IDs used by Talsim.

For this, you need to specify and provide a `timeseries_mapping` file in tab-separated CSV format containing the following columns:
* `locationId`: FEWS locationId
* `parameterId`: FEWS parameterId
* `zreId`: Talsim time series ID

TalsimFEWSAdapter will convert each time series to a BIN file and save them in the folder `projectData\fews\dataBase\fews_zre`. 

The time series path in the EXT file of the Talsim dataset should be set to a relative path according to the folder structure:
```
PATHLocal=..\..\projectData\fews\dataBase\fews_zre\
```
The correct unit and interpretation of the time series must already be set in the EXT file according to what will be received from FEWS.

## Initial conditions

### State file
Talsim should read the state file provided by FEWS at the beginning of each simulation and write a new state file at the end of each simulation. This needs to be configured using an ABZ file as part of the dataset with the following settings:

```
[SETTINGS]
Name=<dataset_name>     ; Titel
Option=3                ; 0=nichts, 1=schreiben, 2=lesen, 3=lesen (SimBeginn) schreiben (SimEnde)
FilenameRead=..\..\projectData\fews\extern\FEWStoTalsim\<state_file>
FilenameWrite=..\..\projectData\fews\extern\TalsimToFEWS\<state_file>

[WRITE]
NDate=0                 ; Anzahl der Datumsangaben, zu denen der Zustand geschrieben werden soll

[READ]
Runoff=1                          ; Abflussbildung, 0=nicht gesetzt, 1=gesetzt
TimeofConcentration=1             ; Abflusskonzentration, 0=nicht gesetzt, 1=gesetzt
Transport=1                       ; Transportstrecken, 0=nicht gesetzt, 1=gesetzt
RainHistory=1                     ; Regen-Historie, 0=nicht gesetzt, 1=gesetzt
Snow=1                            ; Schnee-Historie, 0=nicht gesetzt, 1=gesetzt
InitVolume=1                      ; Anfangsinhalte, 0=nicht gesetzt, 1=gesetzt
Cntrl=1                           ; Systemzustände + Zustandsgruppen, 0=nicht gesetzt, 1=gesetzt
OrdinarySysState=1                ; sonstige Elementezustände, 0=nicht gesetzt, 1=gesetzt

[READWRITE]
SimEndOffset=1
```

The value of 1 for `SimEndOffset` is important in order for FEWS to correctly interpret the timestamp for which the state file is valid.

### Additional states
In addition to the state file provided by FEWS, additional initial conditions, which can overwrite the values in the state file, can be provided in two ways:
* **State timeseries** can be provided as PI XML time series and must be specified under `state_input_files`
* **Model parameters** can be provided as PI XML model parameters sepcified under `parameters_file`. 

These will be converted to corresponding VAR files for Talsim. An UPD-file telling Talsim how to use these VAR file(s) must be provided as part of the dataset. Also, the `variation_id` must be set accordingly in the TalsimFEWSAdapter config.

#### State timeseries
To map the contents of the time series specified under `state_input_files` to Talsim element states, you have to also specify and provide a `var_mapping` file as a tab-separated CSV file with the following columns:
* `locationId`: FEWS locationId
* `parameterId`: FEWS parameterId
* `elementKey`: Talsim element key to map to (e.g. A001)
* `AreaFactor`: scaling factor 
* `Area`: division factor
* `UnitFactor`: scaling factor

The last three columns can be used to scale the values provided by FEWS. If no scaling is necessary, set them all to 1.

For each unique `parameterId` in the `var_mapping` file, TalsimFEWSAdapter will create a corresponding VAR file named `<dataset_name>_<parameterId>.var` containing the corresponding values for each mapped Talsim element, using the combination of `<element_key>_<parameterId>` as identifiers. 

#### Model parameters
A model parameter file specified under `parameters_file` will be converted to a single VAR file named `<dataset_name>_parameters.var`, using the combination of `<parameter_id>_<parameter_name>` as identifiers. So far only boolean model parameters are supported.

## Talsim dataset templates
Any file of the Talsim dataset can be used as a template with placeholders for values provided by FEWS. For this, create a copy of the file, add the additional file extension "template" to the filename, e.g. `<dataset_name>.EZG.template`, and then add placeholders with the variable name in curly braces, e.g. `{variable_name}`, at the relevant locations in the file.

Possible variables can come from different sources:
* `parameters_file` (FEWS PI parameters XML file): all parameter id and name combinations in this file can be used as placeholders in template dataset files (`{<parameter_id>_<parameter_name>}`).

Standard [Python string format specifiers](https://docs.python.org/3/library/string.html#format-specification-mini-language) (in the form `{variable_name:formatspec}`) can be used to define how variable values are formatted (e.g. regarding their length, number of decimal places) but behave slightly differently than the default:
* floats: if necessary, the given precision will be automatically reduced in order to fit the specified length
* strings: if necessary, strings will be cut to the specified length if too long

### Simulation start and end dates
If FEWS exports a runinfo XML file, then set the config value `runinfo_file` to the filename of this file and the adapter will read the start and end dates from the `<startDateTime>` and `<endDateTime>` elements.

If there is no runinfo file, or the config value `runinfo_file` is not set, the adapter will use the first and last date of the last input time series as simulation start and end dates.

## Output time series
Talsim simulation results (WEL file) will be converted to FEWS PI XML time series file with the filename specified under `output_file`. Only the time series that are specified under `result_variables` will be converted.

Additionally, it is possible to perform some postprocessing and output custom time series by specifiying an `output_mapping` file. Using the information in this file, Talsim results are mapped to FEWS locationIds that are then added to the XML output file. Multiple entries for one combination of locationId and parameterId in the mapping file cause the individual time series to be added together to form the output time series. The column `AreaFactor` in the mapping file can be used to scale values.
