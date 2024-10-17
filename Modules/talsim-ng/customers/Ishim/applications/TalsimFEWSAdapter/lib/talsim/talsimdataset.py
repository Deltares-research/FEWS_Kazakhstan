# -*- coding: utf-8 -*-
"""
---------------------------------------------------------
Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
This file may not be copied, modified and/or distributed
without the express permission of SYDRO Consult GmbH
---------------------------------------------------------

Package talsim
"""
from __future__ import annotations
import datetime
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import re
import shutil
import xml.dom.minidom
import xml.etree.ElementTree as ET

from lib.timeseries import Timeseries

logger = logging.getLogger(__name__)

RESULT_EXTENSIONS = [".MAX", ".WMX", ".BLZ", ".SCO", ".WRN", ".ERR", ".LOG", ".WELINFO", ".WEL", ".WBL"]

class TalsimDataset():
    """
    Class for handling and manipulating a Talsim ASCII dataset
    """

    def __init__(self, path: Path|str, name: str):
        """
        Instantiates a new TalsimDataset instance

        :param path: path to directory containing the dataset
        :param name: name of the dataset
        """
        self.path = Path(path)
        self.name = name

    
    def copy(self, destination: Path|str, include_results: bool = False) -> TalsimDataset:
        """
        Copies the dataset to a destination directory, optionally including result files

        :param destination: destination directory
        :param include_results: if True, also copy result files (default: False)
        :return: the destination dataset
        """
        destination = Path(destination)

        if not destination.exists():
            destination.mkdir(parents=True)
            
        # collect dataset files
        files = []
        for file in self.path.glob(f"{self.name}.*"):
            if not include_results and file.suffix.upper() in RESULT_EXTENSIONS:
                # omit result files if not requested
                continue
            files.append(file)
        # add any *.var files (can have arbitrary filenames!)
        files.extend(self.path.glob("*.var"))

        # copy files
        for file in files:
            shutil.copy2(file, destination / file.name)

        return TalsimDataset(destination, self.name)


    def process_templates(self, variables: dict) -> None:
        """
        Processes template files in a Talsim dataset by replacing the appropriate parameter values

        NOTES:
        * Template files must be named like the original file but with an additional extension "template", e.g. "dataset.ALL.template" 
          and will replace the original file after variable substitution.
        * Template files must contain placeholders for variables enclosed with curly braces, e.g. {variable_name}
        * Standard Python string format specifiers (e.g. {variable_name:formatspec}) are allowed https://docs.python.org/3/library/string.html#format-specification-mini-language
          but behave slightly differently than the default:
          * floats: the given precision may be automatically reduced in order to fit the specified length
          * strings: strings may be cut to the specified length if too long
        
        :param variables: dict of variable names and values {name: value, ...}
        """

        logger.info(f"Processing templates in {self.path} ...")
            
        # find all *.template files
        templates = list(self.path.glob("*.template"))
        for template in templates:
            # replace variables
            logger.info(f"Replacing variables in template file {template.name}...")
            file = str(template).replace(".template", "")
            with open(template, "r") as fr:
                with open(file, "w") as fw:
                    for line in fr:
                        for m in re.finditer(r"\{(.+?)(\:(.+?))?\}", line):
                            if m:
                                pattern = m.group(0) 

                                varname = m.group(1)
                                if not varname in variables:
                                    raise Exception(f"Variable {varname} in template not found!")
                                
                                formatspec = m.group(3)
                                if not formatspec:
                                    formatspec = ""
                                    
                                value = variables[varname]

                                if isinstance(value, float):
                                    # if necessary, reduce precision of floats to suit specified length
                                    m = re.match(r"(\d+)\.(\d+)f", formatspec)
                                    if m:
                                        length = int(m.group(1))
                                        precision = int(m.group(2))
                                        length_int = len(str(int(value)))
                                        max_precision = length - length_int - 1
                                        if max_precision < 0:
                                            raise Exception(f"Variable {varname} with value of {value} can not fit in {length} characters!")
                                        if max_precision < precision:
                                            # reduce precision to max_precision
                                            formatspec = f"{length}.{max_precision}f"
                                
                                elif isinstance(value, str):
                                    # if necessary, cut strings to specified length
                                    m = re.match(r"((.)?([<>]))?(\d+)", formatspec)
                                    if m:
                                        length = int(m.group(4))
                                        if len(value) > length:
                                            # cut string to length
                                            value = value[:length]
        
                                line = line.replace(pattern, format(value, formatspec))

                        fw.write(line)


    def write_varfile(self, file_var: str, vars: dict[str: Timeseries|bool]) -> None:
        """
        Creates a Talsim VAR file containing the given variables

        :param file_var: filename of VAR file to write
        :param vars: dictionary with identifiers as keys and variables as values. Values may be of type Timeseries or bool.
        """

        logger.info(f"Writing file {file_var}...")

        nanvalue = "-9999.999"

        xmlroot = ET.Element('variation_para')
        for identifier, value in vars.items():

            section=ET.SubElement(xmlroot, "section")
            section.set("name", identifier)
            
            if isinstance(value, Timeseries):
                ts = value
                if len(ts.nodes) < 1:
                    # time series with zero length
                    # write one NaN value
                    text = (
                        f"\nValues=1\n"
                        f"{-1:>3}\t{nanvalue:>20}\n"
                    )
                else:
                    # write all time series values
                    text = f"\nValues={len(ts.nodes)}\n"
                    for v in ts.get_values():
                        if np.isnan(v):
                            v = nanvalue
                        text += f"{1:>3}\t{v:>20}\n"
            
            elif isinstance(value, bool):
                # write boolean value as integer
                text = (
                    f"\nValues=1\n"
                    f"{1:>3}\t{int(value):>20}\n"
                )
            
            else:
                raise ValueError(f"Unexpected type of variable: {type(value)}!")
            
            section.text = text

        xmlstring = ET.tostring(xmlroot, encoding="windows-1252", xml_declaration=True)
        xmlstring = xml.dom.minidom.parseString(xmlstring).toprettyxml()
        with open(self.path / file_var, "w", encoding="utf-8") as f:
            f.write(xmlstring)
        return


    @property
    def timeseries_result_files(self) -> list[Path]:
        """
        Returns a list of available timeseries result files
        """
        wel_files = list(self.path.glob("*.WEL"))
        wbl_files = list(self.path.glob("*.WBL"))
        return wel_files + wbl_files
    

    @property
    def warnings(self) -> str|None:
        """
        Returns the warnings from the last simulation run or None if none exist
        """
        file_wrn = self.path / f"{self.name}.WRN"
        if file_wrn.exists():
            with open(file_wrn, "r") as f:
                return f.read()
            
        return None
    

    @property
    def errors(self) -> str|None:
        """
        Returns the errors from the last simulation run or None if none exist
        """
        file_err = self.path / f"{self.name}.ERR"
        if file_err.exists():
            with open(file_err, "r") as f:
                return f.read()
            
        return None

    
    def copy_result_files(self, dir_dest: Path|str) -> None:
        """
        Copy all result files to a destination directory

        Copies all files with stem corresponding to the dataset name 
        and one of the extensions in `RESULT_EXTENSIONS`

        :param dir_dest: destination directory
        """
        dir_dest = Path(dir_dest)

        # collect result files
        files = []
        for ext in RESULT_EXTENSIONS:
            files += list(self.path.glob(f"{self.name}{ext}"))
        
        # create destination directory if necessary
        dir_dest.mkdir(parents=True, exist_ok=True)

        # copy all result files to destination
        for file in files:
            logger.info(f"Copying file {file.name}...")
            file_dest = dir_dest / file.name
            shutil.copy2(file, file_dest)
        return


    def file_to_dataframe(self, file: str) -> pd.DataFrame:
        """
        Reads a dataset file as a pandas DataFrame

        :param file: file to read: "BOA", "BOD", "EFL" or "EZG"
        :return: the contents of the file as a pandas DataFrame
        """

        file_path = self.path / f"{self.name}.{file}"
        if not file_path.exists():
            raise Exception(f"File {file_path} not found!")

        #create dictionary where the key is 'param file' and value is 'version number'
        file_versions = {
            "BOA": "2.0",
            "EFL": "1.2",
            "EZG": "1.7"
        }

        #read file
        with open(file_path, "r") as f:
            lines=f.readlines()

        #check if the user is using the correct version
        if file in file_versions:
            supported_version = file_versions[file]
            for line in lines:
                if line.startswith("VERSION="):
                    file_version = line.strip().split("=")[-1]
                    if file_version != supported_version:
                        raise Exception(f"Unsupported version {file_version} of file {file_path}! Please use version {supported_version}!")
                    break
            else:
                raise Exception(f"File {file_path} does not have a version number! Please use version {supported_version}!")


        # find the line with column information
        k=0
        for i in lines:
            if "<" in i:
                break
            else:
                k=k+1

        def find(str, ch):
            for i, ltr in enumerate(str):
                if ltr == ch:
                    yield i

        start_list = sorted(list(find(lines[k], "<"))+list(find(lines[k], "+")))
        
        end_list=list(np.asarray(sorted(list(find(lines[k], ">"))+list(find(lines[k], "+"))))+1)
        colspe=[]
        for i,val in enumerate(start_list):
            colspe.append(tuple([start_list[i],end_list[i]]))
        if file == "BOA":
            header_list=["ID", "Soil", "BD", "Typ","WP","FK","GPV","kf","maxInf","maxKap","Bemerkkung"]
        elif file == "BOD":
            header_list=["ID", "anzsch", "d1", "boa1","d2","boa2","d3","boa3","d4","boa4","d5","boa5","d6","boa6","Bemerkung"]
        elif file == "EFL":
            header_list=["EZG", "Gef", "Flaeche", "Bod","Lnz","CN","Typ","mi","xPos","yPos","Symbol"]
        elif file == "EZG":
            header_list=["Bez","KNG", "AUnit", "A","Vg","Ho","Hu","L","N_Datei","Evp_Kng","Evp_Sum","Evp_Datei","Evp_HYO","T_Kng","T_Tem","T_JGG","T_TGG","T_Datei","QBASIS_qB","QBASIS_JGG","PSI","SCS_CN","SCS_VorRg","BF0","Ret_R","Ret_K(VG)","Ret_K1","Ret_K2","Ret_Int","Ret_Bas","SCS_con","SCS_Expo","Beta1","Beta2","Opt_Muld","Opt_SCS","Opt_SCH","Opt_Int2_bool","Opt_Int2","Abl_QUrb","Abl_QNat","Abl_QInt","Abl_QIn2","Abl_QBas","Abl_QGWt","Grun_Bas2_bool","Grun_Bas2","Grun_Beta","Schn_Kng","Schn_Abgabe","Schn_WaEquiva","Scale_Precip","CWR_Demand_bool"]
        else:
            header_list=list(range(1, len(start_list)))   

        # read file to dataframe 
        df = pd.read_fwf(file_path, skipfooter=1, skiprows=k+1, colspecs=colspe, names=header_list, encoding='ANSI')

        return df


    def calculate_average_soil_properties(self) -> pd.DataFrame:
        """
        Calculates the average soil properties for soil types over all layers

        :return: pandas Dataframe
        """

        # read required file contents as dataframes
        df_bod = self.file_to_dataframe("BOD")
        df_boa = self.file_to_dataframe("BOA")

        #Create empty lists for results
        WP_Average_List=[]
        FK_Average_List=[]
        GPV_Average_List=[]

        #loop over BOD rows
        for index, row in df_bod.iterrows():
            soil_id=row["ID"]
            n_layer=row["anzsch"]

            #cols with depth
            depth=row[np.arange(2, 2+n_layer*2,2, dtype=int)].to_list()
            #cols with BOA No.
            type=row[np.arange(3, 3+n_layer*2,2, dtype=int)].to_list()

            df_depth_type=pd.DataFrame({'depth': depth,'type': type,})

            #empty Lists for soil props
            WP_mm_List=[]
            FK_mm_List=[]
            GPV_mm_List=[]

            #loop over each soil layer
            for index, row in df_depth_type.iterrows():
                #multiple prop with depth
                WP_mm_List.append(df_boa.loc[df_boa["ID"] == row["type"]]["WP"].values*row["depth"])
                FK_mm_List.append(df_boa.loc[df_boa["ID"] == row["type"]]["FK"].values*row["depth"])
                GPV_mm_List.append(df_boa.loc[df_boa["ID"] == row["type"]]["GPV"].values*row["depth"])

            #sum up lists and calculate avergae
            WP_Average=sum(WP_mm_List)/sum(depth)
            FK_Average=sum(FK_mm_List)/sum(depth)
            GPV_Average=sum(GPV_mm_List)/sum(depth)

            #append to result List
            WP_Average_List.append(*WP_Average)
            FK_Average_List.append(*FK_Average)
            GPV_Average_List.append(*GPV_Average)

        #create dataframe
        df_soil_avg = pd.DataFrame({'Bod': df_bod["ID"],'WP_Average': WP_Average_List,'FK_Average': FK_Average_List,'GPV_Average': GPV_Average_List},)

        return df_soil_avg


    @property
    def sim_start(self) -> datetime.datetime:
        """
        Returns the simulation start date as set in the ALL file
        """
        sim_options = self.get_sim_options()
        for option, value in sim_options.items():
            if option.lower() == "simstart":
                return datetime.datetime.strptime(value, "%d.%m.%Y %H:%M")
        else:
            raise Exception("Option 'SimStart' not found in ALL file!")


    @property
    def sim_end(self) -> datetime.datetime:
        """
        Returns the simulation end date as set in the ALL file
        """
        sim_options = self.get_sim_options()
        for option, value in sim_options.items():
            if option.lower() == "simend":
                return datetime.datetime.strptime(value, "%d.%m.%Y %H:%M")
        else:
            raise Exception("Option 'SimEnd' not found in ALL file!")


    def get_sim_options(self) -> dict:
        """
        Gets all options set in the ALL file

        :returns: dictionary of keys and values as strings
        """
        file_all = self.path / f"{self.name}.ALL"
        
        options = {}

        # read contents of ALL file
        with open(file_all, "r") as f:
            for line in f:
                if not line.startswith(("#", "*")) and "=" in line:
                    option, value = line.strip().split("=")
                    options[option] = value

        return options


    def set_sim_options(self, options: dict) -> None:
        """
        Sets new options in the ALL file

        :param options: dictionary of keys and values to set. Keys must correspond to existing options in the ALL file
        """
        file_all = self.path / f"{self.name}.ALL"

        # read contents of existing ALL file
        with open(file_all, "r") as f:
            lines = f.readlines()

        # modify applicable lines
        for option, value in options.items():
            for i, line in enumerate(lines):
                if not line.startswith(("#", "*")) and "=" in line:
                    option_existing = line.split("=")[0]
                    if option.lower() == option_existing.lower():
                        # set new value
                        if type(value) == datetime.datetime:
                            # convert datetime values to string
                            value = value.strftime("%d.%m.%Y %H:%M")
                        lines[i] = f"{option_existing}={value}\n"
                        break
            else:
                logger.warning(f"Option '{option}' was not found in ALL file and could not be set!")

        # write a new ALL file
        with open(file_all, "w") as f:
            f.writelines(lines)

        return

    def set_calibration_parameters(self, parameters: dict) -> None:
        """
        Sets calibration parameters in the KAL file

        :param parameters: dictionary of keys and values to set. Keys must correspond to existing parameters in the KAL file
        """
        file_kal = self.path / f"{self.name}.KAL"

        if not file_kal.exists():
            raise FileNotFoundError(f"File {file_kal.name} not found!")

        # read contents of existing KAL file
        with open(file_kal, "r") as f:
            lines = f.readlines()

        # modify applicable lines
        for param, value in parameters.items():
            for i, line in enumerate(lines):
                if not line.startswith("#") and "=" in line:
                    param_existing = line.split("=")[0]
                    if param.lower() == param_existing.lower():
                        # set new value
                        lines[i] = f"{param_existing}={value}\n"
                        break
            else:
                logger.warning(f"Parameter '{param}' was not found in KAL file and could not be set!")

        # write a new KAL file
        with open(file_kal, "w") as f:
            f.writelines(lines)

        return

    def __repr__(self) -> str:
        return f"TalsimDataset '{self.name}' in {self.path}"
