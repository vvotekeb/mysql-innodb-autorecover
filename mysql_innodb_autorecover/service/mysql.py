import logging
import os


class MySQLUtil:
     logger = logging.getLogger(__module__)

     def __init__(self, host=None, user=None, password=None, **kwargs) -> None:
         super().__init__()
         self._host = host
         self._user = user
         self._pass = password

     def check_access(self):
         print("Check access successfull!")
