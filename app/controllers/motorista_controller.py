from flask_restx import Namespace, Resource, fields
from app import db
from app.models.motorista import Motorista
from datetime import date

ns = Namespace("motoristas", description="Gerenciamento de motoristas da frota LogTrans")

motorista_model = ns.model("Motorista", {
    "nome": fields.String(required=True, description="Nome completo do motorista"),
    "cpf": fields.String(required=True, description="CPF (11 dígitos, sem pontos ou traços)"),
    "email": fields.String(required=True, description="Email do motorista"),
    "telefone": fields.String(required=True, description="Telefone (11 dígitos, ex: 81999990000)"),
    "tp_cnh": fields.String(required=True, description="Categoria da CNH (ex: B, C, D, E, AE)"),
    "validade_cnh": fields.String(required=True, description="Validade da CNH no formato AAAA-MM-DD"),
    "status": fields.String(required=False, description="AT (ativo) ou NT (não ativo). Padrão: AT")
})

@ns.route("/")
class MotoristaList(Resource):
    def get(self):
        """Retorna a lista completa de motoristas cadastrados"""
        motoristas = Motorista.query.all()
        return [m.to_dict() for m in motoristas], 200

    @ns.expect(motorista_model)
    def post(self):
        """Cadastra um novo motorista. CPF e email devem ser únicos."""
        dados = ns.payload

        campos = ["nome", "cpf", "email", "telefone", "tp_cnh", "validade_cnh"]
        if not all(dados.get(c) for c in campos):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if len(dados["cpf"]) != 11:
            return {"erro": "CPF deve ter exatamente 11 dígitos"}, 400

        if len(dados["telefone"]) != 11:
            return {"erro": "Telefone deve ter 11 dígitos (ex: 81999990000)"}, 400

        if Motorista.query.filter_by(cpf=dados["cpf"]).first():
            return {"erro": "CPF já cadastrado no sistema"}, 409

        if Motorista.query.filter_by(email=dados["email"]).first():
            return {"erro": "Email já cadastrado no sistema"}, 409

        try:
            validade = date.fromisoformat(dados["validade_cnh"])
            motorista = Motorista(
                nome=dados["nome"],
                cpf=dados["cpf"],
                email=dados["email"],
                telefone=dados["telefone"],
                tp_cnh=dados["tp_cnh"],
                validade_cnh=validade,
                status=dados.get("status", "AT")
            )
            db.session.add(motorista)
            db.session.commit()
            return motorista.to_dict(), 201
        except ValueError:
            return {"erro": "Data inválida, use o formato AAAA-MM-DD (ex: 2027-12-31)"}, 400
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:matricula>")
class MotoristaItem(Resource):
    def get(self, matricula):
        """Busca um motorista pela matrícula"""
        motorista = Motorista.query.get_or_404(matricula)
        return motorista.to_dict(), 200

    def delete(self, matricula):
        """Remove um motorista do sistema pela matrícula"""
        motorista = Motorista.query.get_or_404(matricula)
        try:
            db.session.delete(motorista)
            db.session.commit()
            return {"mensagem": "Motorista removido com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500