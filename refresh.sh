source .venv/bin/activate

rm -rf mortar/migrations/00*
rm -rf db.sqlite3
rm -rf explorer.sqlite3
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py migrate --database=explorer
