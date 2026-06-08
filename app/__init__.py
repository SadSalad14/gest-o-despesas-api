from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    api = Api(
        app,
        title="LogTrans — Controle de Despesas Corporativas",
        version="2.0",
        description="API RESTful para gestão de despesas da frota LogTrans. "
                    "Cadastre motoristas, gestores e veículos. Registre despesas com rastreamento GPS. "
                    "Apenas gestores podem aprovar pagamentos e registrar multas.",
        doc="/swagger"
    )

    from app.controllers.motorista_controller import ns as motorista_ns
    from app.controllers.gestor_controller import ns as gestor_ns
    from app.controllers.veiculo_controller import ns as veiculo_ns
    from app.controllers.despesa_controller import ns as despesa_ns
    from app.controllers.viagem_controller import ns as viagem_ns

    api.add_namespace(viagem_ns)
    api.add_namespace(motorista_ns)
    api.add_namespace(gestor_ns)
    api.add_namespace(veiculo_ns)
    api.add_namespace(despesa_ns)

    views_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "views")

    @app.route("/home")
    def index():
        return send_from_directory(views_dir, "index.html")

    return app