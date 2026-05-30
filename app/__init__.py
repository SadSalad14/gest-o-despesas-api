from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    api = Api(app, title="Controle de Despesas Corporativas", version="1.0", doc="/swagger")

    from app.controllers.usuario_controller import ns as usuario_ns
    from app.controllers.despesa_controller import ns as despesa_ns

    api.add_namespace(usuario_ns)
    api.add_namespace(despesa_ns)

    return app