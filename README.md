# mysql-innodb-autorecover
Automate recovery from Innodb pages

# Requirements
- RedHat Linux (for now, tested)
- Python 3.8+
- Build Tools (sudo yum groupinstall 'Development Tools')
- MySQL installed and running with full schema (with or without data, can be a different server)
- Git

# Install
```
git clone https://github.com/VanagaS/mysql-innodb-autorecover.git
cd mysql-innodb-autorecover
pip install -e . 
```
`pip should be running with python 3.8. On some systems, it could be pip3 or pip3.8 etc`

unless run with `sudo` pip would install binary `mysql_innodb_autorecover` under `$HOME/.local/bin/`. Make sure the PATH variable has this directory, else do
```
export PATH=$HOME/.local/bin:$PATH
```


# Run
```
mysql_innodb_autorecover -u <Username> -H <Hostname> -D <DB Name> -r /tmp/recovered -d /var/lib/mysql 
```

- `-r /tmp/recovered`: Whatever recovered, can be found under `/tmp/recovered/<table-name>` as `tsv` files
- `-d /var/lib/mysql`: MySQL data directory. Unless running with `sudo`, make sure to have access permissions to this directory or make a copy of it and refer to the path of the copy
