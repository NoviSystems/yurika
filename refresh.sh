source .venv/bin/activate

rm -rf mortar/migrations/00*
rm -rf db.sqlite3
pip install -r requirements.in

python manage.py makemigrations
python manage.py migrate
