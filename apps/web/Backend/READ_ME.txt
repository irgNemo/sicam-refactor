### Dependencias ###

- pip install django
- pip install djangorestframework
- pip install django-cors-headers
- pip install psycopg2

### Iniciar Django ###

### Si no tienes creado la carpeta de backend  (desde la carpetra raiz, para crear la carpeta backend con todo) ####
django-admin startproject backend
cd backend
python manage.py startapp api

### Si ya creaste la carpeta de backend (dentro de esa carpeta correr el comando) ####
django-admin startproject config .

### correr Django ###
python manage.py runserver

### Si hay un "error" que tenga que ver con la base de datos ###
CONTROL + C (para detener la ejecucion)
python manage.py migrate
python manage.py runserver

### despues de verificar, ahora crearemos el API ###
python manage.py startapp api


/// BASE DE DATOS /////

### Intalar Dependencias ###
pip install psycopg2-binary

/// Para las Imagenes usamos ImageField /////
## hay que instalar una Dependencia ##
pip install Pillow

// OTRAS Dependencias para el Framework en caso de no tenerlas //
pip install djangorestframework django-cors-headers

