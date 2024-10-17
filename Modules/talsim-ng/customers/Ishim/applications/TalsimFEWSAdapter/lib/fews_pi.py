"""
---------------------------------------------------------
Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
This file may not be copied, modified and/or distributed
without the express permission of SYDRO Consult GmbH
---------------------------------------------------------

TALSIM FEWS Model Adapter

Module for reading/writing FEWS PI XML files

Docs: https://publicwiki.deltares.nl/display/FEWSDOC/Delft-FEWS+Published+interface+-+PI
"""
from dataclasses import dataclass
import datetime
import logging
import os
import xml.etree.ElementTree as ET

from .timeseries import Timeseries

logger = logging.getLogger(__name__)


def read_timeseries(file: str) -> dict:
    """
    Reads timeseries from a FEWS PI Timeseries XML file

    Schema: http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd
    
    :param file: path to xml input file
    :return: dict of timeseries {location_id: {parameter_id: Timeseries, ...}, ...}
    """
    return Timeseries.read_fews(file)


@dataclass
class ModelParameter:
    """
    Represents a model parameter as defined in a FEWS PI Parameters XML file

    NOTE: so far only supports boolean values
    """
    parameter_id: str
    parameter_name: str
    value: bool


def read_modelparameters(file: str) -> list[ModelParameter]:
    """
    Reads information from a FEWS PI Parameters XML file

    Schema: http://www.wldelft.nl/fews/PI http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_modelparameters.xsd

    NOTE: so far only supports boolean values
    
    :param file: path to xml input file
    :return: list of model parameters
    """

    logger.info(f"Reading model parameter file {os.path.basename(file)}...")

    parameters = []

    try:
        ns = {"PI": "http://www.wldelft.nl/fews/PI"}
        tree = ET.parse(file)
        root = tree.getroot()
        group = root.find("PI:group", ns)
        for parameter in group.findall("PI:parameter", ns):
            parameter_id = parameter.attrib['id']
            parameter_name = parameter.attrib['name']
            booltext = parameter.find("PI:boolValue", ns).text
            if booltext == 'true':
                boolvalue = True
            elif booltext == 'false':
                boolvalue = False
            else:
                 raise ValueError(f"Unexpected boolValue {booltext}!")
            
            parameters.append(ModelParameter(parameter_id, parameter_name, boolvalue))
        
    except Exception as e:
        logger.error(f"Error while reading model parameter file: {e}")
            
    return parameters


def read_runinfo(file_xml) -> tuple[datetime.datetime, datetime.datetime]:
    """
    Reads information from a FEWS PI Run XML file

    Schema: http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_run.xsd
    
    :param file: path to xml input file
    :return: tuple of (startDateTime, endDateTime)
    """
    logger.info(f"Reading file {os.path.basename(file_xml)}...")
    
    try:
        ns = {"PI": "http://www.wldelft.nl/fews/PI"}
        tree = ET.parse(file_xml)
        root = tree.getroot()

        startdatetime = root.find("PI:startDateTime", ns)
        date = startdatetime.attrib["date"]
        time = startdatetime.attrib["time"]
        startdate = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")

        enddatetime = root.find("PI:endDateTime", ns)
        date = enddatetime.attrib["date"]
        time = enddatetime.attrib["time"]
        enddate = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        logger.error(f"Error while reading run file!")
        logger.error(e)
            
    return (startdate, enddate)


def write_timeseries(file_xml: str, ts_dict: dict) -> None:
    """
    Writes timeseries from a FEWS PI Timeseries XML file

    Schema: http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd

    :param file_xml: path to XML file to write
    :param ts_dict: dict of timeseries to write {location_id: {parameter_id: Timeseries, ...}, ...}
    """
    return Timeseries.write_fews(file_xml, ts_dict)

