from flask_restx import Namespace, Resource, fields
from app import db
from app.models.gestor import Gestor

ns = Namespace("gestores", description="Gerenciamento de gestores responsáveis pela aprovação de despesas")

gestor_model = ns.model("Gestor", {
    "nome": fields.String(required=True, description="Nome completo do gestor"),
    "email": fields.String(required=True, description="Email corporativo do gestor"),
    "telefone": fields.String(required=True, description="Telefone (11 dígitos, ex: 81999990000)"),
    "departamento": fields.String(required=True, description="Departamento do gestor (ex: Financeiro, Logística)")
})

@ns.route("/")
class GestorList(Resource):
    def get(self):
        """Retorna a lista completa de gestores cadastrados"""
        gestores = Gestor.query.all()
        return [g.to_dict() for g in gestores], 200

    @ns.expect(gestor_model)
    def post(self):
        """Cadastra um novo gestor. Email deve ser único."""
        dados = ns.payload

        if not all(dados.get(c) for c in ["nome", "email", "telefone", "departamento"]):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if len(dados["telefone"]) != 11:
            return {"erro": "Telefone deve ter 11 dígitos"}, 400

        if Gestor.query.filter_by(email=dados["email"]).first():
            return {"erro": "Email já cadastrado no sistema"}, 409

        try:
            gestor = Gestor(
                nome=dados["nome"],
                email=dados["email"],
                telefone=dados["telefone"],
                departamento=dados["departamento"]
            )
            db.session.add(gestor)
            db.session.commit()
            return gestor.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:matricula>")
class GestorItem(Resource):
    def get(self, matricula):
        """Busca um gestor pela matrícula"""
        gestor = Gestor.query.get_or_404(matricula)
        return gestor.to_dict(), 200

    def delete(self, matricula):
        """Remove um gestor do sistema pela matrícula"""
        gestor = Gestor.query.get_or_404(matricula)
        try:
            db.session.delete(gestor)
            db.session.commit()
            return {"mensagem": "Gestor removido com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500