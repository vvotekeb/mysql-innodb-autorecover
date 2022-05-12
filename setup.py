import subprocess
from setuptools import setup, find_packages, Command
from mysql_innodb_autorecover import APPNAME, APPVSN

SYS_DEPS = [
         ('node', '--version', '12.11.0')
         ]

class SysDeps(Command):
     """A Command class that runs system commands and checks for required dependencies"""

     user_options = []

     def initialize_options(self):
         pass

     def finalize_options(self):
         pass

     def RunSysCommand(self, dep):
         print('Running command: [%s]' % dep[0])
         p = subprocess.Popen(" ".join(dep[0:2]),
         stdin=subprocess.PIPE,
         stdout=subprocess.PIPE,
         stderr=subprocess.STDOUT,
         shell=True,
         text=True)
         stdout_data, _ = p.communicate()
         print('Command output: %s' % stdout_data)
         if p.returncode != 0:
           raise RuntimeError(
               'Command %s failed: exit code: %s' % (dep[0], p.returncode))

     def run(self):
         for dep in SYS_DEPS:
             self.announce('Running system dependencies check for %s' % dep[0])
             self.RunSysCommand(dep)

def get_requirements() -> list:
    with open('requirements.txt', 'r') as f:
        return f.readlines()


setup(
    name=APPNAME,
    version=APPVSN,
    packages=find_packages(),
    install_requires=get_requirements(), 
    include_package_data=True,
    package_data={'mysql_innodb_autorecover': ['resources/*']},
    description='MySQL Innodb recovery tool',
    url='https://github.com/VanagaS/mysql-innodb-autorecover',
    entry_points={
        'console_scripts': [
            'mysql_innodb_autorecover=mysql_innodb_autorecover.__main__:main'
        ]
    },
    classifiers=[
        'Intended Audience :: System/DB Admins',
    ],
    cmdclass={
        'sysdeps': SysDeps,
    },
)
