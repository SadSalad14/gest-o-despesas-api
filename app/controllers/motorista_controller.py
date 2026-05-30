from flask_restx import Namespace, Resource, fields
from app import db
from app.models.motorista import Motorista
from datetime import date

ns = Namespace("motoristas", description="Operações de motoristas")

motorista_model = ns.model("Motorista", {
    "nome": fields.String(required=True, description="Nome do motorista"),
    "cpf": fields.String(required=True, description="CPF (11 dígitos, sem pontos)"),
    "tp_cnh": fields.String(required=True, description="Tipo da CNH (ex: B, C, AE)"),
    "validade_cnh": fields.String(required=True, description="Validade da CNH (AAAA-MM-DD)"),
    "status": fields.String(required=False, description="AT (ativo) ou NT (não ativo)")
})

@ns.route("/")
class MotoristaList(Resource):
    def get(self):
        """Lista todos os motoristas"""
        motoristas = Motorista.query.all()
        return [m.to_dict() for m in motoristas], 200

    @ns.expect(motorista_model)
    def post(self):
        """Cadastra um novo motorista"""
        dados = ns.payload

        if not dados.get("nome") or not dados.get("cpf") or not dados.get("tp_cnh") or not dados.get("validade_cnh"):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if len(dados["cpf"]) != 11:
            return {"erro": "CPF deve ter 11 dígitos"}, 400

        if Motorista.query.filter_by(cpf=dados["cpf"]).first():
            return {"erro": "CPF já cadastrado"}, 409

        try:
            validade = date.fromisoformat(dados["validade_cnh"])
            motorista = Motorista(
                nome=dados["nome"],
                cpf=dados["cpf"],
                tp_cnh=dados["tp_cnh"],
                validade_cnh=validade,
                status=dados.get("status", "AT")
            )
            db.session.add(motorista)
            db.session.commit()
            return motorista.to_dict(), 201
        except ValueError:
            return {"erro": "Data inválida, use o formato AAAA-MM-DD"}, 400
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:matricula>")
class MotoristaItem(Resource):
    def get(self, matricula):
        """Busca um motorista pelo ID"""
        motorista = Motorista.query.get_or_404(id)
        return motorista.to_dict(), 200

    def delete(self, matricula):
        """Deleta um motorista"""
        motorista = Motorista.query.get_or_404(id)
        try:
            db.session.delete(motorista)
            db.session.commit()
            return {"mensagem": "Motorista deletado com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500