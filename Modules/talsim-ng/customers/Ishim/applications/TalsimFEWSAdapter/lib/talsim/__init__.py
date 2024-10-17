# -*- coding: utf-8 -*-
"""
---------------------------------------------------------
Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
This file may not be copied, modified and/or distributed
without the express permission of SYDRO Consult GmbH
---------------------------------------------------------

Package talsim

This package contains the following classes:
* `TalsimDataset` for handling and manipulating a Talsim ASCII dataset
* `TalsimEngine` for carrying out simulations with Talsim-NG
* `TalsimNGSrv` for communicating with a Talsim-NG server
"""

__version__ = "1.1.0"

from .talsimdataset import TalsimDataset
from .talsimengine import TalsimEngine
from .talsimsrv import TalsimNGSrv
