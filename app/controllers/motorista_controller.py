from flask_restx import Namespace, Resource, fields
from app import db
from app.models.motorista import Motorista
from datetime import date

ns = Namespace("motoristas", description="Gerenciamento de motoristas da frota LogTrans")

motorista_model = ns.model("Motorista", {
    "nome": fields.String(required=True, description="Nome completo do motorista"),
    "cpf": fields.String(required=True, description="CPF do motorista (11 dígitos, sem pontos ou traços)"),
    "tp_cnh": fields.String(required=True, description="Categoria da CNH (ex: B, C, D, E, AE)"),
    "validade_cnh": fields.String(required=True, description="Data de validade da CNH no formato AAAA-MM-DD"),
    "status": fields.String(required=False, description="Status do motorista: AT (ativo) ou NT (não ativo). Padrão: AT")
})

@ns.route("/")
class MotoristaList(Resource):
    def get(self):
        """Retorna a lista completa de motoristas cadastrados"""
        motoristas = Motorista.query.all()
        return [m.to_dict() for m in motoristas], 200

    @ns.expect(motorista_model)
    def post(self):
        """Cadastra um novo motorista. CPF deve ser único e CNH válida."""
        dados = ns.payload

        if not dados.get("nome") or not dados.get("cpf") or not dados.get("tp_cnh") or not dados.get("validade_cnh"):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if len(dados["cpf"]) != 11:
            return {"erro": "CPF deve ter exatamente 11 dígitos, sem pontos ou traços"}, 400

        if Motorista.query.filter_by(cpf=dados["cpf"]).first():
            return {"erro": "CPF já cadastrado no sistema"}, 409

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