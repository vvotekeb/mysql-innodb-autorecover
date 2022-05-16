import os
import sys
import logging, verboselogs
import tempfile
import requests
import tarfile
import fileinput
import subprocess
import glob
import pathlib
import shutil
import re

from os.path import join, basename, split
from mysql_innodb_autorecover import PERCONA_URL
from colorama import Fore, Back, Style
from tqdm import tqdm
from alive_progress import alive_bar

verboselogs.install()

class Percona:
    logger                 = logging.getLogger(__module__)
    PAGE_PARSER_BIN        = "page_parser"
    CREATE_DEFS_BIN        = "create_defs.pl"
    CONSTRAINTS_PARSER_BIN = "constraints_parser"
    RECOVERED_TABLES       = set()
    TABLES                 = 0
    INDEXES                = 0
    RECOVERED_INDEXES      = 0
    LOAD_SQL_QUERIES       = []

    def __init__(self, datadir=None, target=None) -> None:
        super().__init__()
        self.workdir = os.getcwd()
        self.data_dir = datadir

        if target is None:
            self.tmpdir = tempfile.TemporaryDirectory().name
        else:
            os.makedirs(target, exist_ok=True)
            self.tmpdir = target
        self.download_dir = join(self.tmpdir, "download")
        self.tool_dir = join(self.tmpdir, "tools")
        self.tool_defs_dir = join(self.tool_dir, "defs")
        self.recovered_dir = join(self.tmpdir, "recovered")
        self.recovered_indexes_dir = join(self.recovered_dir, "indexes")

        Percona.logger.info("Temporary working directory located at: %s%s%s", Fore.YELLOW, self.tmpdir, Style.RESET_ALL)
        self.download()
        self.extract()
        self.patch_makefile()
        self.compile()

    def download(self):
        os.makedirs(self.download_dir, exist_ok=True)
        self.archive = join(self.download_dir, "recovery-tool.tar.gz")
        if os.path.exists(self.archive):
            return

        Percona.logger.notice("Downloading Percona recovery tool from: %s%s%s", Style.DIM, PERCONA_URL, Style.RESET_ALL)
        try:
            data = requests.get(PERCONA_URL)
            with open(self.archive, 'wb') as file:
                for data in tqdm(data.iter_content()):
                    file.write(data)
        except Exception as e:
            Percona.logger.critical("Failed downloading recovery tool: %s" % e)
            try:
                os.remove(self.archive)
            except:
                pass
            sys.exit(-1)

    def extract(self):
        if tarfile.is_tarfile(self.archive):
            tar = tarfile.open(self.archive, "r:gz")
            tar.extractall(path=self.tool_dir)
            self.source_dir = join(self.tool_dir, tar.getnames()[0])
            tar.close()
        else:
            Percona.logger.critical("Downloaded file is not a tar file: %s", self.archive)
            try:
                os.remove(self.archive)
            except:
                pass
            sys.exit(-1)

    def patch_makefile(self):
        makefile = join(self.source_dir, "Makefile")
        Percona.logger.info("Patching Makefile: %s%s%s", Fore.YELLOW, makefile, Style.RESET_ALL)
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


    def compile(self, alternate=False):
        src_dir = self.tool_defs_dir if alternate else self.source_dir
        counter = 71 if alternate else 1171

        Percona.logger.info("Compiling Percona tools %s%s%s", Fore.YELLOW, src_dir, Style.RESET_ALL)
        os.chdir(src_dir)
        make = subprocess.Popen("make", stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stderr = []
        with alive_bar(counter, title='Running make...', enrich_print=True, spinner="dots_reverse") as bar:
            bar.text("[%s%sRunning configure%s]"%(Style.BRIGHT, Fore.MAGENTA, Style.RESET_ALL))
            for line in iter(make.stdout.readline, ""):
                bar()
                if line.startswith("cd mysql-source/include && make my_config.h"):
                  bar.text("[%s%sCompiling%s]"%(Style.BRIGHT, Fore.CYAN, Style.RESET_ALL))
            for line in iter(make.stderr.readline, ""):
                bar()
        return_code = make.wait()
        if return_code:
            for line in stderr:
                Percona.logger.error(line.strip())
            Percona.logger.critical("Compile failed! Please check Makefile generated errors above and fix them before running this program again. Return code: %d", return_code)
            raise subprocess.CalledProcessError(return_code, "make")
        Percona.logger.notice("Compile successful!")
        if not alternate:
            Percona.logger.debug("Copying tools directory to %s for compiling per table defs"%self.tool_defs_dir)
            shutil.copytree(self.source_dir, self.tool_defs_dir, dirs_exist_ok=True)
        


    def find_ibd_file(self, database, table):
        ibd_file = join(self.data_dir, database, table + '.ibd')
        Percona.logger.notice("Looking for innodb table file %s%s.ibd%s", Fore.YELLOW, table, Style.RESET_ALL)
        if os.path.exists(ibd_file):
            Percona.logger.notice("Found %s.ibd at %s%s%s", table, Fore.YELLOW, ibd_file, Style.RESET_ALL)
            return ibd_file
        else:
            Percona.logger.warn("%s.ibd not found at %s", table, ibd_file)
            ibd_file = join(self.data_dir, table + '.ibd')
            if os.path.exists(ibd_file):
                Percona.logger.notice("Found %s.ibd at %s%s%s", table, Fore.YELLOW, ibd_file, Style.RESET_ALL)
                return ibd_file
            else:
                Percona.logger.critical("%s.ibd not found at %s. Giving up!", table, ibd_file)
                return None



    def extract_innodb_pages(self, database, table, row_format=5) -> bool:
        table_dir = join(self.recovered_indexes_dir, table)
        os.makedirs(table_dir, exist_ok=True)
        ibd_file = self.find_ibd_file(database, table)
        if ibd_file is None:
            return False
        self.page_parser(table_dir, table, row_format, ibd_file)
        return True


    def page_parser(self, table_dir, table, row_format, ibd_file):
        os.chdir(table_dir)
        binary = [join(self.source_dir, Percona.PAGE_PARSER_BIN), "-%d"%row_format, "-f", ibd_file]
        Percona.logger.info("Parsing deleted pages from %s%s.ibd%s: %s"%(Fore.YELLOW, table, Style.RESET_ALL, ibd_file))
        make = subprocess.Popen(binary, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return_code = make.wait()

    def generate_table_defs(self, table, host, port, user, password, db):
        include_dir = join(self.tool_defs_dir, "include")
        os.chdir(include_dir)
        defs_h = join(include_dir, "table_defs.h")
        os.remove(defs_h)
        binary = [join(self.source_dir, Percona.CREATE_DEFS_BIN), "--host", host, "--port", str(port), "--user", user, "--password", password, "--db", db, "--table", table]
        with open(defs_h, 'w') as table_defs:
            subprocess.Popen(binary, stdout=table_defs, universal_newlines=True)


    def extract_data(self, table, row_format):
        table_dir = join(self.recovered_indexes_dir, table)
        search = '**/FIL_PAGE_INDEX/*'
        extracted = pathlib.Path(table_dir).glob(search)
        os.chdir(table_dir)
        Percona.TABLES = Percona.TABLES + 1
        Percona.logger.info("Scanning for any deleted records from indexes: [%s%s%s%s]", Style.BRIGHT, Fore.BLUE, table_dir, Style.RESET_ALL)
        for item in extracted:
            if not str(item).endswith('FIL_PAGE_INDEX'):
                Percona.INDEXES = Percona.INDEXES + 1
                binary = [join(self.tool_defs_dir, Percona.CONSTRAINTS_PARSER_BIN), "-%d"%row_format, "-D", "-f", item]
                tsv_file = "%s%s.tsv"%(table,os.path.basename(item))
                with open(tsv_file, "w") as tsv:
                    make = subprocess.Popen(binary, stdout=tsv, stderr=subprocess.PIPE)
                _, stderr = make.communicate()
                if os.stat(tsv_file).st_size == 0:
                    Percona.logger.warn("[%s%s%s%s] - No deleted records found", Style.BRIGHT, Fore.BLUE, os.path.basename(item), Style.RESET_ALL)
                    os.remove(tsv_file)
                else:
                    Percona.logger.success("[%s%s%s%s] - Deleted records found%s", Style.BRIGHT, Fore.BLUE, os.path.basename(item), Fore.GREEN, Style.RESET_ALL)
                    # Create directory to save recovered data
                    recovered_tsv_dir = join(self.recovered_dir, table)
                    os.makedirs(recovered_tsv_dir, exist_ok=True)
                    recovered_data_file = join(recovered_tsv_dir, tsv_file)
                    os.rename(join(table_dir, tsv_file), recovered_data_file)

                    # Save load data sql query
                    default_dir = join(self.workdir, "dumps", "default", table)
                    stderr = re.sub(default_dir, recovered_data_file, stderr.decode('utf-8'))

                    # Save summary
                    Percona.LOAD_SQL_QUERIES.append(stderr)
                    Percona.RECOVERED_TABLES.add(table)
                    Percona.RECOVERED_INDEXES = Percona.RECOVERED_INDEXES + 1
        shutil.rmtree(table_dir)
        shutil.rmtree(self.recovered_indexes_dir)


    def print_summary(self):
        Percona.logger.info("===============================================")
        Percona.logger.info("                    SUMMARY                    ")
        Percona.logger.info("===============================================")
        Percona.logger.info("  Tables  Scanned: %s%d%s  ", Fore.CYAN, Percona.TABLES, Style.RESET_ALL)
        Percona.logger.info("  Indexes Scanned: %s%d%s  ", Fore.CYAN, Percona.INDEXES, Style.RESET_ALL)
        Percona.logger.info("-----------------------------------------------")
        Percona.logger.info("  Tables Recovered: %s%d%s  ", Fore.CYAN, len(Percona.RECOVERED_TABLES), Style.RESET_ALL)
        Percona.logger.info("  Indexes Recovered: %s%d%s  ", Fore.CYAN, Percona.RECOVERED_INDEXES, Style.RESET_ALL)
        if Percona.RECOVERED_INDEXES > 0:
            Percona.logger.info("  Recovered Rows from Tables:  ")
            for item in Percona.RECOVERED_TABLES:
                Percona.logger.info("  %s%s%s%s  ", Style.BRIGHT, Fore.MAGENTA, item, Style.RESET_ALL) 
        Percona.logger.info("")
        Percona.logger.info("Please go over the recovered data under %s%s<table-name>%s  and then execute the following SQL commands (if required)", Fore.RED, self.recovered_dir, Style.RESET_ALL)
        Percona.logger.info("If multiple files present under the same table name (directory), there might be conflicting rows,")
        Percona.logger.info("so, please go over the files, decide (and edit) each file before loading them into database")
        Percona.logger.info("%sTIP: When multiple files found under a table, prefer the one that has most entries%s", Fore.CYAN, Style.RESET_ALL)
        Percona.logger.info("%sQueries to load data into database: %s", Style.BRIGHT, Fore.CYAN)
        for item in Percona.LOAD_SQL_QUERIES:
            Percona.logger.warning("%s%s%s%s  ", Style.BRIGHT, Fore.BLUE, item, Style.RESET_ALL)
        Percona.logger.info("")
        Percona.logger.info("-----------------------------------------------")


