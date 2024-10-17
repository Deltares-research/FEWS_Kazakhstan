"""
---------------------------------------------------------
Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
This file may not be copied, modified and/or distributed
without the express permission of SYDRO Consult GmbH
---------------------------------------------------------

TALSIM FEWS Model Adapter

Config class
"""

import logging
import configparser
import pandas as pd
from pathlib import Path
import re

logger = logging.getLogger(__name__)

DIR_CONFIG = Path(r"config")
DIR_DATASETS = Path(r"..\..\projectData\fews\dataSets")
DIR_ZRE = Path(r"..\..\projectData\fews\dataBase\fews_zre")
DIR_INPUT = Path(r"..\..\projectData\fews\extern\FEWStoTALSIM")
DIR_OUTPUT = Path(r"..\..\projectData\fews\extern\TALSIMtoFEWS")

class Config:

    def __init__(self, file_config: str):
        """
        Reads the config.ini file and validates it

        :param file_config: config ini filename
        :raises FileNotFoundError: if file_config not found
        """
        logger.info(f"Using config file {file_config}")

        # required values
        self.timeseries_files = []
        self.timeseries_mapping = {} # {locationId: {parameterId: zreId, ...}, ...}
        self.dataset_folder = None
        self.dataset_name = None
        self.variation_id = 0
        self.output_file = None

        # optional values
        self.parameters_file = None
        self.state_input_files = []
        self.runinfo_file = None
        self.var_mapping = None
        self.output_mapping = None
        self.result_variables = []

        # check if config file exists
        file_config = DIR_CONFIG / file_config
        if not Path(file_config).exists():
            raise FileNotFoundError(f"Unable to find config file {file_config}")
        
        # read config
        configp = configparser.ConfigParser(inline_comment_prefixes=["#"])
        configp.read(file_config)

        # validate config
        self._validate(configp)

    def _validate(self, configp: configparser.ConfigParser):
        """
        Validates the config and stores the config values as instance attributes
        """
        required = {
            "input": ["timeseries_files", "timeseries_mapping"],
            "simulation": ["dataset_folder", "dataset_name"],
            "output": ["output_file"]
        }

        optional = {
            "input": ["variables_file", "state_input_files", "runinfo_file"],
            "simulation": ["variation_id"],
            "output": ["result_variables", "var_mapping", "output_mapping"]
        }

        # check all required sections and values are present
        for section, varlist in required.items():
            if section not in configp:
                raise Exception(f"Missing section [{section}] in config file!")
            for var in varlist:
                if var not in configp[section]:
                    raise Exception("Missing value '{var}' in section [{section}] of config file!")

        # read required config values

        # timeseries_files
        self.timeseries_files = [x.strip() for x in re.split(r",|\r\n", configp["input"]["timeseries_files"]) if len(x.strip()) > 0]
        # validate paths
        self.timeseries_files = [self._validate_path(DIR_INPUT / file.strip()) for file in self.timeseries_files]

        # timeseries_mapping 
        timeseries_mapping_file = self._validate_path(DIR_CONFIG / configp["input"]["timeseries_mapping"])
        # read csv to DataFrame
        df_mapping = pd.read_csv(timeseries_mapping_file, sep="\t")
        # check required columns
        required_cols = ["zreId", "locationId", "parameterId"]
        for col in required_cols:
            if col not in df_mapping.columns:
                raise Exception(f"Missing required column '{col}' in {timeseries_mapping_file}!")
        # store mapping as dictionary
        for row in df_mapping.itertuples():
            zre_id = row.zreId
            location_id = row.locationId
            parameter_id = row.parameterId
            if location_id not in self.timeseries_mapping:
                self.timeseries_mapping[location_id] = {}
            self.timeseries_mapping[location_id][parameter_id] = zre_id

        # dataset_folder
        self.dataset_folder = self._validate_path(DIR_DATASETS / configp["simulation"]["dataset_folder"])
        
        # dataset_name
        self.dataset_name = configp["simulation"]["dataset_name"]

        # output_file
        self.output_file = DIR_OUTPUT / configp["output"]["output_file"]

        # read optional config values

        # parameters_file
        if "parameters_file" in configp["input"]: 
            if configp["input"]["parameters_file"] != "":
                self.parameters_file = self._validate_path(DIR_INPUT / configp["input"]["parameters_file"])

        # runinfo_file
        if "runinfo_file" in configp["input"]: 
            if configp["input"]["runinfo_file"] != "":
                self.runinfo_file = self._validate_path(DIR_INPUT / configp["input"]["runinfo_file"])

        # state_input_files
        if "state_input_files" in configp["input"]: 
            if configp["input"]["state_input_files"] != "":
                filenames = [x.strip() for x in re.split(r",|\r\n", configp["input"]["state_input_files"]) if len(x.strip()) > 0]
                self.state_input_files = [self._validate_path(DIR_INPUT / file.strip()) for file in filenames]

        # var_mapping_file
        if "var_mapping" in configp["input"]:
            self.var_mapping = self._validate_path(DIR_CONFIG / configp["input"]["var_mapping"])

        # var_mapping file is required if there are state_input_files!
        #TODO: or should we allow state_input_files alone?
        if len(self.state_input_files) > 0 and not self.var_mapping:
            raise Exception(f"A value for the parameter 'var_mapping' is required if 'state_input_files' are provided!")

        # variation_id
        if "variation_id" in configp["simulation"]:
            if configp["simulation"]["variation_id"] != "":
                self.variation_id = int(configp["simulation"]["variation_id"])

        # output_mapping_file
        if "output_mapping" in configp["output"]:
            if configp["output"]["output_mapping"] != "":
                self.output_mapping = self._validate_path(DIR_CONFIG / configp["output"]["output_mapping"])

        # result_variables
        if "result_variables" in configp["output"]:
            if configp["output"]["result_variables"] != "":
                self.result_variables = [x.strip() for x in re.split(r"[,\r\n]", configp["output"]["result_variables"]) if len(x.strip()) > 0]

        return


    def _validate_path(self, path: str) -> Path:
        """
        Validates a path string
        and converts it to a Path object

        :param path: path to folder or file
        :return: Path object
        """
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        return path