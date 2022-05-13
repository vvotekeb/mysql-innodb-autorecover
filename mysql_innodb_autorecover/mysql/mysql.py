import logging, verboselogs
import os
import sys

from colorama import Fore, Style, Back
from getpass import getpass
from mysql.connector import cursor, pooling, Error

verboselogs.install()

class MySQLUtil:
    logger = logging.getLogger(__module__)

    def __init__(self, host=None, port=None, user=None, password=None, database=None, tables=None, **kwargs) -> None:
        super().__init__()
        self._host = host
        self._user = user
        self._database = database

        if port is None:
            self._port = 3306
        else:
            self._port = port

        if password is None:
            self._pass = getpass("%s%s%sEnter MySQL password for %s@%s:%s " % (Back.YELLOW, Style.NORMAL, Fore.RED, user, host, Style.RESET_ALL)) 
        else:
            self._pass = password
        
        self.check_access()
        self.setup_tables(tables)

    @property
    def user(self):
        return self._user

    @property
    def password(self):
        return self._pass

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def database(self):
        return self._database

    @property
    def tables(self):
        return self._tables

    @property
    def connection(self):
        return self.connection_pool.get_connection()

    def fetch(self, query) -> str:
        try:
            conn = self.connection_pool.get_connection()
            if conn.is_connected():
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchone()
        except Error as e:
            MySQLUtil.logger.critical(e)
            return None
        finally:
            cursor.close()
            conn.close()

    def row_format(self, _format) -> int:
        if _format.upper() == "REDUNDANT":
            return 4
        else:
            return 5 # COMPACT. Return the same for Dynamic as well

    def check_access(self):
        try:
            self.connection_pool = pooling.MySQLConnectionPool(
                    pool_name="recover",
                    pool_size=1,
                    pool_reset_session=True,
                    host=self._host,
                    user=self._user,
                    password=self._pass,
                    port=int(self._port),
                    database=self._database
            )
            MySQLUtil.logger.success("Successfully connected to database '%s' with '%s@%s'" % (self._database, self._user, self._host))
        except Error as e:
            MySQLUtil.logger.critical(e)
            sys.exit(-1)


    def setup_tables(self, tables):
        if tables is None or tables == "":
            self.fetch_tables()
        elif tables.startswith("@"):
            with open(tables[1:]) as tables_list:
                self._tables = [ table.strip() for table in filter(None, tables_list.read().splitlines()) ]
        else:
            self._tables = [table.strip() for table in tables.split(",")]

    def fetch_tables(self):
        try:
            conn = self.connection_pool.get_connection()
            if conn.is_connected():
                cursor = conn.cursor()
                cursor.execute("show tables;")
                self._tables = [ row[0] for row in cursor.fetchall() ]
                cursor.close()
                conn.close()
        except Error as e:
            MySQLUtil.logger.critical(e)
            sys.exit(-1)

