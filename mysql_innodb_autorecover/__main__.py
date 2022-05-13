"""
 Recover lost rows from innodb pages
 Usage:
   mysql_innodb_autorecover [-l LEVEL] (-u USERNAME) [-p PASSWORD] (-H HOSTNAME) [-P PORT] (-D DATABASE) [-t TABLES] [-T TEMPDIR] (-d DATADIR)
   mysql_innodb_autorecover -v | --version
   mysql_innodb_autorecover -h | --help

 Options:
   -h --help                          show this help message and exit
   -v --version                       print version and exit
   -l LEVEL                           set log level. Options: debug, info, warning, error, critical [default: info]
   -u USERNAME                        MySQL username
   -p PASSWORD                        MySQL password - If not provided, enter when prompted
   -H HOSTNAME                        MySQL hostname
   -P PORT                            MySQL port
   -D DATABASE                        MySQL database
   -d DATADIR                         path to MySQL data directory or a copy of it (ex: /var/lib/mysql) 
   -t TABLES                          (optional) mySQL tables to recover. If left out all the tables from the database are considered for recovering). Comma-separated list of tables, or a filename prepended with @, for ex: @/tmp/tables.txt
   -T TEMPDIR                         (optional) path to a directory where percona tool is downloaded and compiled. If not specified a temporary directory is created and deleted automatically when the process stops
"""
import sys
import logging, coloredlogs, verboselogs

from colorama import init
from docopt import docopt, DocoptExit
from pkg_resources import Requirement, resource_filename
from colorama import Fore, Back, Style

from mysql_innodb_autorecover import APPVSN, APPNAME
from mysql_innodb_autorecover.mysql.mysql import MySQLUtil
from mysql_innodb_autorecover.service.yum import Yum
from mysql_innodb_autorecover.percona.app import Percona
from mysql_innodb_autorecover.service.recover import Recover

init()

def main(args=None):
    try:
        arguments = docopt(__doc__, argv=args, version=APPVSN)
    except DocoptExit as usage:
        print(usage)
        sys.exit(1)

    coloredlogs.install(fmt='%(asctime)s - %(levelname)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
    verboselogs.install()
    logger = logging.getLogger(__name__)

    yumutil = Yum()
    yumutil.setup_requirements()

    mysql = MySQLUtil(
                host=arguments['-H'],
                port=arguments['-P'],
                user=arguments['-u'],
                password=arguments['-p'],
                database=arguments['-D'],
                tables=arguments['-t']
            )

    percona = Percona(target=arguments['-T'], datadir=arguments['-d'])
    recover = Recover(mysql, percona)
    recover.recover()

