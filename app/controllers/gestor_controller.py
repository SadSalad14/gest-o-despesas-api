from flask_restx import Namespace, Resource, fields
from app import db
from app.models.gestor import Gestor

ns = Namespace("gestores", description="Operações de gestores")

gestor_model = ns.model("Gestor", {
    "nome": fields.String(required=True, description="Nome do gestor"),
    "email": fields.String(required=True, description="Email do gestor")
})

@ns.route("/")
class GestorList(Resource):
    def get(self):
        """Lista todos os gestores"""
        gestores = Gestor.query.all()
        return [g.to_dict() for g in gestores], 200

    @ns.expect(gestor_model)
    def post(self):
        """Cadastra um novo gestor"""
        dados = ns.payload

        if not dados.get("nome") or not dados.get("email"):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if Gestor.query.filter_by(email=dados["email"]).first():
            return {"erro": "Email já cadastrado"}, 409

        try:
            gestor = Gestor(nome=dados["nome"], email=dados["email"])
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
        """Deleta um gestor"""
        gestor = Gestor.query.get_or_404(matricula)
        try:
            db.session.delete(gestor)
            db.session.commit()
            return {"mensagem": "Gestor deletado com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500