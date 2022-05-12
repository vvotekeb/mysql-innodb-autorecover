import os
import sys
import verboselogs
import tempfile
import requests
import tarfile
import fileinput
import subprocess

from os.path import join, basename, split
from mysql_innodb_autorecover import PERCONA_URL
from colorama import Fore, Back, Style
from tqdm import tqdm


class Percona:
    logger = verboselogs.VerboseLogger(__module__)

    def __init__(self) -> None:
        super().__init__()
        self.workdir = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.download_dir = join(self.tmpdir.name, "download")
        self.tool_dir = join(self.tmpdir.name, "tools")

        Percona.logger.info("Temporary working directory located at: %s", self.tmpdir.name)
        self.download()
        self.extract()
        #self.patch_makefile()
        self.compile()


    def download(self):
        os.mkdir(self.download_dir)
        self.archive = join(self.download_dir, "recovery-tool.tar.gz")

        Percona.logger.notice("Downloading Percona recovery tool from: %s%s%s", Style.DIM, PERCONA_URL, Style.RESET_ALL)
        data = requests.get(PERCONA_URL)
        with open(self.archive, 'wb') as file:
            for data in tqdm(data.iter_content()):
                file.write(data)

    def extract(self):
        if tarfile.is_tarfile(self.archive):
            tar = tarfile.open(self.archive, "r:gz")
            tar.extractall(path=self.tool_dir)
            self.source_dir = join(self.tool_dir, tar.getnames()[0])
            tar.close()
        else:
           Percona.logger.critical("Downloaded file is not a tar file: %s", self.archive)
           sys.exit(-1)

    def patch_makefile(self):
        makefile = join(self.source_dir, "Makefile")
        Percona.logger.info("Patching Makefile: %s", makefile)
        for line in fileinput.input(makefile, inplace=1):
            if line.startswith("CFLAGS="):
                line = line.replace("-Wall -O3", "-Wall -O3 -fgnu89-inline")
            if "gcc $(INCLUDES)" in line:
                line = line.replace("gcc $(INCLUDES)", "gcc $(CFLAGS) $(INCLUDES)")
            if "gcc  -o" in line:
                line = line.replace("gcc  -o", "gcc $(CFLAGS) $(INCLUDES) -o")
            if "constraints_parser innochecksum" in line:
                line = line.replace("constraints_parser innochecksum", "constraints_parser innochecksum ibdconnect")
            sys.stdout.write(line)

    def compile(self):
        Percona.logger.info("Compiling Percona tools %s", self.source_dir)
        os.chdir(self.source_dir)
        make = subprocess.Popen("make", stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return_code = make.wait()
        if return_code:
            Percona.logger.success("Compile failed! return code: %d", return_code)
            for line in iter(make.stderr.readline, ""):
                Percona.logger.critical(line.strip())
            raise subprocess.CalledProcessError(return_code, "make")
        Percona.logger.success("Compile successful!")


    def cleanup(self):
        self.tmpdir.cleanup()
