# -*- coding: utf-8 -*-
"""
---------------------------------------------------------
Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
This file may not be copied, modified and/or distributed
without the express permission of SYDRO Consult GmbH
---------------------------------------------------------

"""
# core modules
import logging
import datetime
import collections
import xml.etree.ElementTree as ET
import json

# third party modules
import requests
import numpy as np

# own modules
from lib.timeseries import Timeseries

logger = logging.getLogger(__name__)

class TalsimNGSrv:
    """
    Wrapper class for reading and writing timeseries from and to a Talsim-NG server
    """

    port_HttpDataSrv = 8090
    port_HttpZreSrv = 8092

    path_requestZreDirectories = "/TalsimNGServer/HttpDataSrv/requestZreDirectories/"  # TODO: switch to ZreDirectories once that endpoint is live
    path_requestZreFiles = "/TalsimNGServer/HttpDataSrv/requestZreFiles/"

    path_requestSydroTimeSeries = "/TalsimNGServer/HttpZreSrv/requestSydroTimeSeries/"
    path_SydroTimeSeries = "/TalsimNGServer/HttpZreSrv/SydroTimeSeries/"

    TimeSeriesInfo = collections.namedtuple("TimeSeriesInfo", "id, name, station_id, type, unit")

    def __init__(self, server, timeout=1.):
        """
        Constructor

        Args:
            server (str): the server address of the Talsim-NG server (e.g. "10.0.0.5")
            timeout (float): the time in seconds to wait for a server response before a timeout
        """
        self.server = server
        self.timeout = timeout

        self.response = ""  # raw xml/json response
        self.success = False
        self.resultmsg = ""

        return

    def get_timeseries_class(self, customer, id, user):
        """
        Gets the timeseries class from the server

        Args:
            customer (str): the customer from which to get the time series
            id (int): the ID of the time series
            user (str): the user used for making the request

        Returns:
            str: timeseries class as string, e.g. "Flagged"
        """
        # construct the url
        url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpZreSrv) + TalsimNGSrv.path_SydroTimeSeries
        url += "class/%s,%s,%i" % (customer, user, id)

        # make the request
        try:
            logger.debug("GET request: %s" % url)
            self.success = False
            r = requests.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return False
            else:
                self.response = r.text
                # logger.debug("Response:", r.text)
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get contents of the ResultMsg tag
                self.resultmsg = xmlroot.find("{http://www.sydro.de}ResultMsg").text
                ts_class = self.resultmsg
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return ts_class

    def get_timeseries(self, customer, id, user, flag=0):
        """
        Gets a time series from the server and returns it as a Timeseries object

        Args:
            customer (str): the customer from which to get the time series
            id (int): the ID of the time series
            user (str): the user used for making the request
            flag (int): (optional) the flag for the request, defaults to 0

        Returns:
            Timeseries: Timeseries instance or False if unsuccessful
        """
        # determine time series class
        ts_class = self.get_timeseries_class(customer, id, user)

        # construct the url
        if ts_class == "Flagged":
            url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpZreSrv) + TalsimNGSrv.path_SydroTimeSeries
            url += "%s,%s,%i,0,0,%i" % (customer, user, id, flag)
        else:
            url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpZreSrv) + TalsimNGSrv.path_SydroTimeSeries
            url += "%s,%s,%i" % (customer, user, id)
        #TODO: handle class ForecastTimeSeries

        # make the request
        try:
            logger.debug("GET request: %s" % url)
            self.success = False
            r = requests.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return False
            else:
                #TODO: check HasError tag
                self.response = r.text
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get contents of the ResultMsg tag
                self.resultmsg = xmlroot.find("{http://www.sydro.de}ResultMsg").text
                # get flag
                flag = int(xmlroot.find("{http://www.sydro.de}Attribute").text)
                # get metadata
                metadata = xmlroot.find("{http://www.sydro.de}Metadata")
                name = metadata.find("{http://www.sydro.de}Name").text
                if name == None:
                    name = ""
                lat = float(metadata.find("{http://www.sydro.de}Lat").text)
                lon = float(metadata.find("{http://www.sydro.de}Lon").text)
                station_id = int(metadata.find("{http://www.sydro.de}StationId").text)
                unit = metadata.find("{http://www.sydro.de}Unit").text
                err_value = metadata.find("{http://www.sydro.de}ErrorValue").text
                ts_class = int(metadata.find("{http://www.sydro.de}TSClass").text)
                # convert to a time series object
                ts = Timeseries(name)
                ts.station_id = station_id
                ts.unit = unit
                ts.lat = lat
                ts.lon = lon
                # get csv string
                csv = xmlroot.find("{http://www.sydro.de}TimeSeriesString").text
                # parse csv
                # TODO: use DateValuePairSeparator and Separator from response xml?
                if csv != None:
                    for line in csv.split("#"):
                        if len(line.strip()) > 0:
                            parts = line.split(",")
                            date_str = parts[0]
                            value_str = parts[1]
                            date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            if value_str in [err_value, "-9999.999"]: # SydroDEV issue #125: server-api responses can sometimes also contain -9999.999 as an error value!
                                value = np.nan
                            else:
                                value = float(value_str)
                            ts[date] = value
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return ts

    def get_timeseries_old(self, customer, id, user):
        """
        Gets a time series from the server and returns it as a Timeseries object
        Uses the old requestSydroTimeSeries endpoint

        Args:
            customer (str): the customer from which to get the time series
            id (int): the ID of the time series
            user (str): the user used for making the request

        Returns:
            Timeseries: Timeseries instance or False if unsuccessful
        """
        # construct the url
        url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpZreSrv) + TalsimNGSrv.path_requestSydroTimeSeries
        url += "CSV/%s,%s,%i,0,0,comma" % (customer, user, id)

        # make the request
        try:
            logger.debug("GET request: %s" % url)
            self.success = False
            r = requests.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return False
            else:
                self.response = r.text
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get contents of the ResultMsg tag
                self.resultmsg = xmlroot.find("{http://www.sydro.de}ResultMsg").text
                # get other tag contents of interest
                csv = xmlroot.find("{http://www.sydro.de}TimeSeriesString").text
                name = xmlroot.find("{http://www.sydro.de}Name").text
                station_id = int(xmlroot.find("{http://www.sydro.de}StationId").text)
                unit = xmlroot.find("{http://www.sydro.de}Unit").text
                err_value = xmlroot.find("{http://www.sydro.de}ErrorValue").text
                # convert csv to a time series
                ts = Timeseries(name)
                ts.station_id = station_id
                ts.unit = unit
                # parse csv
                # TODO: use DateValuePairSeparator and Separator from response xml?
                for line in csv.split("#"):
                    if len(line.strip()) > 0:
                        date_str, value_str = line.split(",")
                        date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        if value_str == err_value:
                            value = np.nan
                        else:
                            value = float(value_str)
                        ts[date] = value
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return ts
    
    def create_timeseries(self, ts, customer, id, user, ts_class=0, flag=0, flag_description="Default", T0=None):
        """
        Creates a new time series on the server

        Args:
            ts (Timeseries): the time series to create
            customer (str): the customer to which the time series belongs
            id (int): the ID of the time series
            user (str): the user used for making the request
            ts_class (int): (optional) the time series class (default: 0)
            flag (int): (optional) the flag under which to store the timeseries values (default: 0)
            flag_description (int): (optional) the flag description (default: "Default")
            T0 (datetime): (optional) used only if ts_class == 2 (default: None)

        Returns:
            bool: success
            
        TODO: allow optional ID = 0 and return the new ID
        """
        return self.post_timeseries(ts, customer, id, user, ts_class, flag, flag_description, create_new=True, replace=False, T0=T0)
        
    def update_timeseries(self, ts, customer, id, user, ts_class=0, flag=0, flag_description="Default", T0=None):
        """
        Updates an existing time series on the server
        Existing nodes are replaced!

        Args:
            ts (Timeseries): the updated time series
            customer (str): the customer to which the time series belongs
            id (int): the ID of the time series
            user (str): the user used for making the request
            ts_class (int): (optional) the time series class (default: 0)
            flag (int): (optional) the flag under which to store the timeseries values (default: 0)
            flag_description (int): (optional) the flag description (default: "Default")
            T0 (datetime): (optional) used only if ts_class == 2 (default: None)

        Returns:
            bool: success
        """
        return self.post_timeseries(ts, customer, id, user, ts_class, flag, flag_description, create_new=False, replace=True, T0=T0)
        
    def append_timeseries(self, ts, customer, id, user, ts_class=0, flag=0, flag_description="Default", T0=None):
        """
        Appends data to an existing time series on the server

        Args:
            ts (Timeseries): the updated time series
            customer (str): the customer to which the time series belongs
            id (int): the ID of the time series
            user (str): the user used for making the request
            ts_class (int): (optional) the time series class (default: 0)
            flag (int): (optional) the flag under which to store the timeseries values (default: 0)
            flag_description (int): (optional) the flag description (default: "Default")
            T0 (datetime): (optional) used only if ts_class == 2 (default: None)

        Returns:
            bool: success
        """
        return self.post_timeseries(ts, customer, id, user, ts_class, flag, flag_description, False, False, T0)
        
    def post_timeseries(self, ts, customer, id, user, ts_class=0, flag=0, flag_description="Default", create_new=False, replace=False, T0=None):
        """
        Posts a time series to the server

        Args:
            ts (Timeseries): the time series to post
            customer (str): the customer to which the time series belongs
            id (int): the ID of the time series
            user (str): the user used for making the request
            ts_class (int): (optional) the time series class (default: 0)
            flag (int): (optional) the flag under which to store the timeseries values (default: 0)
            flag_description (int): (optional) the flag description (default: "Default")
            create_new (bool): (optional) if True attempts to create a new timeseries (default: False)
            replace (bool): (optional) if True replaces existing nodes between beginning and end of the time series (default: False)
            T0 (datetime): (optional) used only if ts_class == 2 (default: None)

        Returns:
            bool: success
        """
        # construct the url
        url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpZreSrv) + TalsimNGSrv.path_SydroTimeSeries + "new"

        # convert the time series to xml
        xml = TalsimNGSrv.timeseries_to_xml(ts, customer, id, user, ts_class, flag, flag_description, create_new, replace, T0)
        
        # DEBUG
        with open("tmp.xml", "wb") as f:
           f.write(xml)

        # make the request
        try:
            logger.debug("POST request: %s" % url)
            self.success = False
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            r = requests.post(url, data=xml, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return False
            else:
                self.response = r.text
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get contents of the ResultMsg tag
                self.resultmsg = xmlroot.find("{http://www.sydro.de}ResultMsg").text
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return True

    def delete_records(self, customer, id, user, start, end, flag=0):
        """
        Deletes records between start and end from a time series

        Args:
            customer (str): the customer to which the time series belongs
            id (int): the ID of the time series
            user (str): the user used for making the request
            flag (int): (optional) the flag of the records to be deleted (default: 0)
            start (datetime): start of period for deleting records (inclusively)
            end (datetime): end of period for deleting records (inclusively)

        Returns:
            bool: success
        """
        # construct the url
        url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpZreSrv) + TalsimNGSrv.path_SydroTimeSeries + "/deleteRecords/"
        url += "%s,%s,%i,%s,%s,%i" % (customer, user, id, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), flag)
        
        # make the request
        try:
            logger.debug("GET request: %s" % url)
            self.success = False
            r = requests.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return False
            else:
                self.response = r.text
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get contents of the ResultMsg tag
                self.resultmsg = xmlroot.find("{http://www.sydro.de}ResultMsg").text
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return True

    def query_stations(self, customer):
        """
        Gets a dict of stations available for the given customer

        Args:
            customer (str): the customer for which time series should be queried

        Returns:
            dict: dictionary of time series {id: name, ...} or False if unsuccessful
        """
        # construct the url
        url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpDataSrv) + TalsimNGSrv.path_requestZreDirectories
        url += customer + ",|"

        station_dict = {}

        # make the request
        try:
            logger.debug("GET request: %s" % url)
            self.success = False
            r = requests.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return None
            else:
                self.response = r.text
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get all TalsimZreDir tags
                for zredir in xmlroot.findall(".//{http://www.sydro.de}TalsimZreDir"):
                    id = int(zredir.find("{http://www.sydro.de}ZreDirId").text)
                    name = zredir.find("{http://www.sydro.de}ShortName").text
                    station_dict[id] = name

                self.resultmsg = "Server returned %i stations" % len(station_dict)
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return station_dict

    def query_timeseries(self, customer, user, station_id=0):
        """
        Gets a list of timeseries available for the given customer and station id

        Args:
            customer (str): the customer for which time series should be queried
            user (str): the user making the request
            station_id (int): (optional) the station id for which time series should be queried.
                Default: 0, i.e. all time series of the customer will be returned

        Returns:
            list: list of TimeSeriesInfo named-tuples or False if unsuccessful
        """
        # construct the url
        url = "http://" + self.server + ":" + str(TalsimNGSrv.port_HttpDataSrv) + TalsimNGSrv.path_requestZreFiles
        url += "%s,%s,%i" % (customer, user, station_id)

        ts_list = []

        # make the request
        try:
            logger.debug("GET request: %s" % url)
            self.success = False
            r = requests.get(url, timeout=self.timeout)
            if r.status_code != 200:
                self.resultmsg = "Server returned status code %i\nResponse text:\n%s" % (r.status_code, r.text)
                return False
            else:
                self.response = r.text
                # parse the response xml
                xmlroot = ET.fromstring(r.text)
                # get all TalsimZreFile tags
                for zrefile in xmlroot.findall(".//{http://www.sydro.de}TalsimZreFile"):
                    id = int(zrefile.find("{http://www.sydro.de}ZreFileId").text)
                    name = zrefile.find("{http://www.sydro.de}ShortName").text
                    station_id = int(zrefile.find("{http://www.sydro.de}ZreDirId").text)
                    type = int(zrefile.find("{http://www.sydro.de}TSTypeId").text)  # TODO: change to TsClass
                    unit = zrefile.find("{http://www.sydro.de}UnitText").text

                    # construct a TimeSeriesInfo object
                    info = TalsimNGSrv.TimeSeriesInfo(
                        id=id,
                        name=name,
                        station_id=station_id,
                        type=type,
                        unit=unit
                    )

                    ts_list.append(info)

                self.resultmsg = "Server returned %i time series" % len(ts_list)
                self.success = True

        except requests.exceptions.Timeout:
            self.resultmsg = "Request timed out!"
            return False

        return ts_list

    @staticmethod
    def timeseries_to_xml(ts, customer, id, user, ts_class=0, flag=0, flag_description="Default", create_new=False, replace=False, T0=None):
        """
        Converts a time series to xml format as accepted by a Talsim-NG server

        Args:
            ts (Timeseries): the time series to convert
            customer (str): the customer to which the time series belongs
            id (int): the ID of the time series
            user (str): the user making the request
            ts_class (int): (optional) the time series class (default: 0)
            flag (int): (optional) the flag under which to store the timeseries values (default: 0)
            flag_description (int): (optional) the flag description (default: "Default")
            create_new (bool): if True attempts to create a new time series
            replace (bool): (optional) if True replaces existing nodes between beginning and end of the time series (default: False)
            T0 (datetime): (optional) used only if ts_class == 2 (default: None)

        Returns:
            str: xml string
        """
        # convert the time series data to a string
        dateformat = "%Y-%m-%d %H:%M:%S"
        timeseriesString = ""
        for date, value in ts:
            if np.isnan(value):
                value = "NaN"
            if ts_class == 2:
                # forecast time series: T0,T1,fc_length,value
                fc_length = round((date - datetime.datetime(T0.year, T0.month, 1)).days / 30.0) # in months!
                timeseriesString += "%s,%s,%i,%s#\n" % (T0.strftime(dateformat), date.strftime(dateformat), fc_length, value)
            else:
                # other time series: T,value
                timeseriesString += "%s,%s#\n" % (date.strftime(dateformat), value)

        # build an xml tree structure
        xmlroot = ET.Element("SydroTimeSeries")
        xmlcustomer = ET.SubElement(xmlroot, "Customer")
        xmlcustomer.text = customer
        xmlAttribute = ET.SubElement(xmlroot, "Attribute")
        xmlAttribute.text = str(flag)
        if create_new:
            # this is required when creating a new time series
            xmlEnforceId = ET.SubElement(xmlroot, "EnforceID")
            xmlEnforceId.text = "true" 
        xmlDeleteBeforeInsert = ET.SubElement(xmlroot, "DeleteBeforeInsert")
        if replace:
            xmlDeleteBeforeInsert.text = "true"
        else:
            xmlDeleteBeforeInsert.text = "false"
        xmlLength = ET.SubElement(xmlroot, "Length")
        xmlLength.text = str(len(ts.nodes))
        xmlUser = ET.SubElement(xmlroot, "User")
        xmlUser.text = user
        # metadata
        xmlSaveMetadata = ET.SubElement(xmlroot, "SaveMetadata")
        xmlSaveMetadata.text = "true"
        xmlMetadata = ET.SubElement(xmlroot, "Metadata")
        xmlId = ET.SubElement(xmlMetadata, "Id")
        xmlId.text = str(id)
        xmlName = ET.SubElement(xmlMetadata, "Name")
        xmlName.text = ts.title
        xmlStationId = ET.SubElement(xmlMetadata, "StationId")
        xmlStationId.text = str(ts.station_id)
        xmlUnit = ET.SubElement(xmlMetadata, "Unit")
        xmlUnit.text = ts.unit
        xmlAttributeDescription = ET.SubElement(xmlMetadata, "AttributeDescription")
        xmlAttributeDescription.text = flag_description
        xmlErrorValue = ET.SubElement(xmlMetadata, "ErrorValue")
        xmlErrorValue.text = "NaN"
        xmlTSClass = ET.SubElement(xmlMetadata, "TSClass")
        xmlTSClass.text = str(ts_class)
        # csv data
        xmlTimeSeriesString = ET.SubElement(xmlroot, "TimeSeriesString")
        xmlTimeSeriesString.text = timeseriesString

        xml = ET.tostring(xmlroot, encoding="UTF-8")

        return xml


if __name__ == "__main__":
    pass
