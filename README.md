# Scheduler
Help teachers submit class schedules


## Backend
- Create an environment (Some of these command are just for windows and are just an example)
    1. `python -m venv .venv` (creates venv)
    2. `path/to/venv/bin/activate` EX `.venv/Scripts/activate` (activates venv)
        - `Set-ExecutionPolicy Unrestricted -Scope Process` if UnauthorizedAccess
    3. `pip install -r requirements.txt` (installs the required libraries)

- Set up the database (pwd scheduler)
    1. `python manage.py makemigrations` (create a migration file if there are changes)
    2. `python manage.py migrate` (migrates the latest migration file and creates a database file)
    3. `python manage.py loadgeneral` Loads generally static csv data
    4. `python manage.py loadclasses` Loads csv data from previous terms
- run the server on local port
    1. `python manage.py runserver`

