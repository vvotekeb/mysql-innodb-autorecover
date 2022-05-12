"""
 Recover lost rows from innodb pages
 Usage:
   mysql_innodb_autorecover [-l LEVEL] (-u USERNAME) (-p PASSWORD) (-s HOSTNAME)
   mysql_innodb_autorecover -v | --version
   mysql_innodb_autorecover -h | --help

 Options:
   -h --help                          show this help message and exit
   -v --version                       print version and exit
   -l LEVEL --log-level LEVEL         set log level. Options: debug, info, warning, error, critical [default: info]
   -u USERNAME                        MySQL username
   -p PASSWORD                        MySQL password
   -s HOSTNAME                        MySQL hostname
"""
import logging, coloredlogs, verboselogs

from colorama import init
from docopt import docopt, DocoptExit
from pkg_resources import Requirement, resource_filename
from colorama import Fore, Back, Style

from mysql_innodb_autorecover import APPVSN
from mysql_innodb_autorecover.service.mysql import MySQLUtil
from mysql_innodb_autorecover.service.yum import Yum
from mysql_innodb_autorecover.percona.app import Percona

init()


def main(args=None):
    try:
        arguments = docopt(__doc__, argv=args, version=APPVSN)
    except DocoptExit as usage:
        print(usage)
        sys.exit(1)

    coloredlogs.install(fmt='%(asctime)s - %(levelname)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
    verboselogs.install()
    logging.basicConfig(level=arguments['--log-level'].upper())

    mysql_util = MySQLUtil(host=arguments['-s'],
                           user=arguments['-u'],
                           password=arguments['-p'])
    mysql_util.check_access()

    yumutil = Yum()
    yumutil.setup_requirements()

    tool = Percona()
