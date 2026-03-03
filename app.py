import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appliances.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Template globals
app.jinja_env.globals.update(date=date, timedelta=timedelta)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from routes import *
