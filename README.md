# Health-Management-Backend
Web API's for Health-Management Application PoweredBy AAT.

## Quick Start

Clone this repository to your local machine and Copy .env.txt file, create new folder name as .env then paste the .env.txt contents on .env file. 

Creat a database and database user

1. Create a Python virtual environment and activate it.
2. Open up your terminal and run the following command to install the packages used in this project.

```
$ pip install -r requirements.txt
```

3. Set up a Postgres database for the project.
4. Run the following commands to setup the database tables and create a superuser.

```
$ python manage.py makemigrations
$ python manage.py migrate
```

5. Run the development server using:

```
$ python manage.py runserver
```

6. create supadmin user run this command.

```
$ python manage.py create_superadmin
```

7. Open a browser and go to http://localhost:8000/
