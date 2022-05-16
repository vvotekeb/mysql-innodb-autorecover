import os
import logging, verboselogs

from colorama import Fore, Style, Back
from getpass import getpass
from mysql.connector import cursor, pooling, Error

verboselogs.install()

class Recover:
    logger = logging.getLogger(__module__)

    def __init__(self, mysql=None, percona=None) -> None:
        super().__init__()
        self.mysql = mysql
        self.percona = percona

    def recover(self):
        for table in self.mysql.tables:
            Recover.logger.notice("Attempting to recover table %s%s%s%s" % (Style.BRIGHT, Fore.CYAN, table, Style.RESET_ALL))
            row_format = self.get_row_format(table)
            self.percona.generate_table_defs(table, self.mysql.host, self.mysql.port, self.mysql.user, self.mysql.password, self.mysql.database)
            self.percona.compile(alternate=True)
            if self.percona.extract_innodb_pages(self.mysql.database, table, row_format):
                self.percona.extract_data(table, row_format)
        self.percona.print_summary()
            
    def get_row_format(self, table) -> int:
        query = "SELECT ROW_FORMAT from information_schema.TABLES WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='%s';" % (self.mysql.database, table)
        Recover.logger.debug(query)
        row_format = self.mysql.row_format(self.mysql.fetch(query)[0])
        Recover.logger.debug("Format: %s" % row_format)
        return row_format

