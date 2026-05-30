from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    api = Api(app, title="LogTrans — Controle de Despesas", version="1.0", doc="/swagger")

    from app.controllers.motorista_controller import ns as motorista_ns
    from app.controllers.gestor_controller import ns as gestor_ns
    from app.controllers.despesa_controller import ns as despesa_ns

    api.add_namespace(motorista_ns)
    api.add_namespace(gestor_ns)
    api.add_namespace(despesa_ns)

    return app