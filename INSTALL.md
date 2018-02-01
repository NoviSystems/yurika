
# Install

## Development Setup

These instructions were written for CentOS 7, but steps should be similar for
most Linux distributions.

### ElasticSearch

Install Java > 1.8:

    [user@yurika]$ sudo yum install -y java

Currently ElasticSearch 5.x is required. Download the latest 5.x version on
their [past releases page](https://www.elastic.co/downloads/past-releases) and
install it, or use the commands:

    [user@yurika]$ sudo yum install -y wget
    [user@yurika]$ wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.6.6.rpm
    [user@yurika]$ sudo rpm -Uvh elasticsearch-5.6.6.rpm

Edit the elasticsearch configuration at `/etc/elasticsearch/elasticsearch.yml`
and uncomment or add the following lines:

    cluster.name: yurika
    node.name: node-1
    network.host: <ip address of host>

Start the elasticsearch service:

    [user@yurika]$ sudo service elasticsearch start

Wait a minute for the service to start, then make a test request to ensure
the cluster is running. Note that "status" will show as yellow unless we add at
least one other node in the cluster.

    [user@yurika]$ curl -XGET http://<ip_addr>:9200/_cluster/health?pretty=true
    {
        "cluster_name" : "yurika",
        "status" : "yellow",
        "timed_out" : false,
        "number_of_nodes" : 1,
        "number_of_data_nodes" : 1,
        "active_primary_shards" : 25,
        "active_shards" : 25,
        "relocating_shards" : 0,
        "initializing_shards" : 0,
        "unassigned_shards" : 25,
        "delayed_unassigned_shards" : 0,
        "number_of_pending_tasks" : 0,
        "number_of_in_flight_fetch" : 0,
        "task_max_waiting_in_queue_millis" : 0,
        "active_shards_percent_as_number" : 50.0
    }

### Yurika Web App

Install Python 3:

    [user@yurika]$ sudo -i
    [root@yurika]# yum -y groupinstall development
    [root@yurika]# yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    [root@yurika]# yum -y install python36u python36u-devel

Set up Redis server for Celery tasks:

    [root@yurika]# yum install -y epel-release redis
    [root@yurika]# systemctl start redis.service

Clone and pull the latest version of the Yurika code:

    [root@yurika]# cd /opt
    [root@yurika]# git clone https://github.com/ITNG/yurika.git
    [root@yurika]# cd yurika

Switch to another branch (optional):

    [root@yurika]# git checkout dev

Create Mortar user and set permissions:

    [root@yurika]# useradd mortar
    [root@yurika]# chown -R mortar:mortar /opt/yurika

Create a virtual environment:

    [root@yurika]# sudo -iu mortar
    [mortar@yurika]$ cd /opt/yurika
    [mortar@yurika]$ python3.6 -m venv .venv

For convenience in later commands, activate your virtualenv for this terminal.
This makes commands like `pip` and `python` run the virtualenv executables in
`.env/bin/`:

    [mortar@yurika]$ source .venv/bin/activate

Install Python requirements:

    [mortar@yurika]$ pip install -r requirements.txt

Clone dictionaries repository from github:

    [mortar@yurika] git clone https://github.com/ITNG/yurika-dictionaries.git dictionaries

Copy settings files:

    [mortar@yurika]$ cp project/settings.ex.py project/settings.py
    [mortar@yurika]$ cp project/develop/env .env

Edit settings in `project/settings.py`:

  * Set `ES_URL` to your IP address

Make migrations, run collect static and create Django superuser:

    [mortar@yurika]$ python manage.py makemigrations
    [mortar@yurika]$ python manage.py migrate
    [mortar@yurika]$ python manage.py migrate --database explorer
    [mortar@yurika]$ python manage.py collectstatic
    [mortar@yurika]$ python manage.py createsuperuser

Install NLTK packages:

    [mortar@yurika]$ python -m nltk.downloader punkt averaged_perceptron_tagger


## Running in Development

For the development setup, you will need to run both celery and the Django
testserver. Celery handles long running tasks such as web crawling, while
Django serves the webpages.

Start Celery in one terminal:

    [user@yurika]$ sudo -iu mortar
    [mortar@yurika]$ cd /opt/yurika
    [mortar@yurika]$ source .venv/bin/activate
    [mortar@yurika]$ celery -A project.celery worker -l info

Start Django in another terminal:

    [user@yurika]$ sudo -iu mortar
    [mortar@yurika]$ cd /opt/yurika
    [mortar@yurika]$ source .venv/bin/activate
    [mortar@yurika]$ python manage.py runserver

You can now access Yurika at `http://127.0.0.1:8000`


## Production Setup

The following is used for the development setup:

  * NGINX: webserver. Handles static files and passes other requests to
           Gunicorn.
  * Gunicorn: serves Django requests.
  * Supervisor: runs Gunicorn and Celery workers.
  * PostgreSQL: database.

Install yum requirements:

    [user@yurika]$ sudo -i
    [root@yurika]# yum install -y nginx postgresql-server supervisor

### NGINX

Copy over server config file:

    [root@yurika]# cp /opt/yurika/scripts/configs/nginx.conf /etc/nginx/conf.d/yurika.conf

Edit NGINX config file in `/etc/nginx/conf.d/yurika.conf`:

  * Change `server_name` to your hostname. Include any hostnames you want the
    server to serve Yurika on (including 127.0.0.1 if desired) separated by
    spaces.

Restart Nginx:

    [root@yurika]# service nginx restart

### PostgreSQL

Initialize database and start Postgres:

    [root@yurika]# postgresql-setup initdb
    [root@yurika]# service postgresql start

Create postgres database and user:

    [root@yurika] sudo -iu postgres
    [postgres@yurika]$ createdb mortar
    [postgres@yurika]$ createuser mortar
    [postgres@yurika]$ psql mortar
    mortar=# GRANT ALL ON DATABASE mortar TO mortar;
    mortar=# ALTER USER mortar PASSWORD 'ratrom';
    mortar=# \q
    [postgres@yurika]$ exit

Update `/var/lib/pgsql/data/pg_hba.conf` to allow md5 passwords over http
connections. Line order is significant; put this as the first non-commented
line:

    # TYPE  DATABASE        USER            ADDRESS                 METHOD
    host    mortar          mortar          127.0.0.1/32            md5

Restart PostgreSQL:

    [root@yurika]# service postgresql restart

### Django Confguration

Change Django settings in `/opt/yurika/.env` to use postgres and disable debug
mode:

    DATABASE_URL=psql://mortar:ratrom@127.0.0.1:5432/mortar
    DEBUG=false

Install Python requirements:

    [user@yurika]$ sudo -iu mortar
    [mortar@yurika]$ cd /opt/yurika/
    [mortar@yurika]$ source .venv/bin/activate
    [mortar@yurika]$ pip install -r requirements_production.txt

Create database schema and create Django superuser:

    [mortar@yurika]$ python manage.py migrate
    [mortar@yurika]$ python manage.py migrate --database explorer
    [mortar@yurika]$ python manage.py createsuperuser
    [mortar@yurika]$ exit

### Supervisor

Install supervisor and copy Gunicorn configuration to
`/etc/supervisord.d/mortar.conf`:

    [user@yurika]$ sudo -i
    [root@yurika]# cp /opt/yurika/scripts/configs/supervisor.ini /etc/supervisord.d/yurika.ini

Start supervisord:

    [root@yurika]# service supervisord restart
