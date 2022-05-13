import sys
import logging, verboselogs
import subprocess
from pkg_resources import Requirement, resource_filename
from mysql_innodb_autorecover import APPNAME
from colorama import Fore, Back, Style

verboselogs.install()

class Yum:
    logger = logging.getLogger(__module__)

    def __init__(self) -> None:
        super().__init__()

    def setup_requirements(self):
        packages = resource_filename(Requirement.parse(APPNAME),
                   '{}/resources/{}'.format(APPNAME, 'system-dependencies-yum.txt'))
        with open(packages, 'r') as source:
            Yum.logger.info("Checking for installed packages...")
            installed = subprocess.Popen(
                          ['yum', 'list', 'installed'],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE
                      )
            packages = installed.stdout.read()
            for package in source.readlines():
                if package.strip() and not package.startswith('#'):
                  process = subprocess.run(['grep', package.strip()], input=packages.decode('utf-8'), encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                  return_code = process.returncode
                  if return_code is not None:
                      if return_code != 0:
                          Yum.logger.critical('%s -- not installed' % (package.strip()))
                          sys.exit(-1)
                      else:
                          Yum.logger.success('%s -- installed' % (package.strip()))
