# -*- coding: utf-8 -*-
"""
---------------------------------------------------------
Copyright (C) SYDRO Consult GmbH, <mail@sydro.de>
This file may not be copied, modified and/or distributed
without the express permission of SYDRO Consult GmbH
---------------------------------------------------------

Package talsim
"""
import logging
from pathlib import Path
import re
import subprocess

from .talsimdataset import TalsimDataset

logger = logging.getLogger(__name__)

FILENAME_EXE = "talsimw64.exe"
FILENAME_CHANGELOG = "TALSIM.CHANGELOG"

class TalsimEngine:
    """
    Class for carrying out simulations with Talsim-NG
    """
    def __init__(self, path: Path|str):
        """
        Instantiate a new TalsimEngine instance

        :param path: path to directory containing the engine executable
        """
        self.path = Path(path)

        # check executable exists
        if not self.exe_file.exists():
            raise Exception(f"Talsim executable {self.exe_file} not found!")

    @property
    def exe_file(self) -> Path:
        """
        Returns the path to the executable
        """
        return self.path / FILENAME_EXE
    
    @property
    def version(self) -> str:
        """
        Returns the Talsim engine version number
        """
        changelog = self.path / FILENAME_CHANGELOG

        if not changelog.exists():
            raise Exception(f"Changelog {changelog} not found!")

        with open(changelog, "r") as f:
            for line in f:
                m = re.match(r"Version (.+)", line)
                if m:
                    return m.group(1)
            else:
                raise Exception("Unable to read version number from changelog")

    def simulate(self, dataset: TalsimDataset, variation_id: int = 0, language: str = "de") -> bool:
        """
        Carries out a simulation
        
        :param dataset: dataset instance to simulate
        :param variation_id: optional Variation ID (default: 0)
        :param language: optional language (default: "de")
        :return: boolean success
        """

        # prepare runfile
        runfile = self.path / "talsim.run"
        with open(runfile, "w") as f:
            f.write("[TALSIM]\n")
            f.write(f"Path={dataset.path.resolve()}\\\n")
            f.write(f"System={dataset.name}\n")
            f.write("ExecMode=0\n")
            f.write(f"VariationId={variation_id}\n")
            f.write(f"Language={language}\n")

        # run talsim
        logger.info(f"Launching Talsim-NG v{self.version}...")
        args = [self.exe_file.resolve(), runfile.name]
        proc = subprocess.Popen(args, cwd=self.path.resolve())
        retcode = proc.wait()

        # check for warnings file
        file_wrn = dataset.path / f"{dataset.name}.wrn"
        if file_wrn.exists():
            logger.warning(f"Simulation produced warnings! See Talsim warning file: {file_wrn}")

        if retcode != 0:
            # simulation error
            # check for error file
            file_err = dataset.path / f"{dataset.name}.err"
            if file_err.exists():
                logger.error(f"Simulation ended with errors! See Talsim error file: {file_err}")
            else:
                logger.error(f"Simulation aborted without error message!")
            return False
        else:
            # simulation successful
            logger.info("Simulation successful!")
            return True
    
    def __repr__(self) -> str:
        return f"TalsimEngine in {self.path}"