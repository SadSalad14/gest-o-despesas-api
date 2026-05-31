from flask_restx import Namespace, Resource, fields
from app import db
from app.models.despesa import Despesa
from app.models.motorista import Motorista
from app.models.gestor import Gestor

ns = Namespace("despesas", description="Registro e aprovação de despesas corporativas da frota")

despesa_model = ns.model("Despesa", {
    "descricao": fields.String(required=True, description="Descrição detalhada da despesa (ex: Abastecimento SP-RJ)"),
    "valor": fields.Float(required=True, description="Valor em reais, maior que zero (ex: 150.50)"),
    "motorista_matricula": fields.Integer(required=True, description="Matrícula do motorista que gerou a despesa")
})

pagamento_model = ns.model("Pagamento", {
    "gestor_matricula": fields.Integer(required=True, description="Matrícula do gestor que autoriza o pagamento")
})

@ns.route("/")
class DespesaList(Resource):
    def get(self):
        """Retorna a lista completa de despesas registradas"""
        despesas = Despesa.query.all()
        return [d.to_dict() for d in despesas], 200

    @ns.expect(despesa_model)
    def post(self):
        """Registra uma nova despesa vinculada a um motorista. Status inicial: pendente."""
        dados = ns.payload

        if not dados.get("descricao") or not dados.get("valor") or not dados.get("motorista_matricula"):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        motorista = Motorista.query.get(dados["motorista_matricula"])
        if not motorista:
            return {"erro": "Motorista não encontrado"}, 404

        try:
            despesa = Despesa(
                descricao=dados["descricao"],
                valor=dados["valor"],
                motorista_id=dados["motorista_matricula"]
            )
            db.session.add(despesa)
            db.session.commit()
            return despesa.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:id>")
class DespesaItem(Resource):
    def get(self, id):
        """Busca uma despesa pelo ID"""
        despesa = Despesa.query.get_or_404(id)
        return despesa.to_dict(), 200

    def delete(self, id):
        """Remove uma despesa do sistema pelo ID"""
        despesa = Despesa.query.get_or_404(id)
        try:
            db.session.delete(despesa)
            db.session.commit()
            return {"mensagem": "Despesa removida com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:id>/pagar")
class DespesaPagamento(Resource):
    @ns.expect(pagamento_model)
    def patch(self, id):
        """Aprova o pagamento de uma despesa. Exclusivo para gestores. Despesas já pagas não podem ser alteradas."""
        despesa = Despesa.query.get_or_404(id)
        dados = ns.payload

        gestor = Gestor.query.get(dados["gestor_matricula"])
        if not gestor:
            return {"erro": "Gestor não encontrado"}, 404

        if despesa.status == "pago":
            return {"erro": "Esta despesa já foi aprovada e paga"}, 400

        try:
            despesa.status = "pago"
            db.session.commit()
            return despesa.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500