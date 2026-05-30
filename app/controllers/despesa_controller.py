from flask_restx import Namespace, Resource, fields
from app import db
from app.models.despesa import Despesa
from app.models.usuario import Usuario

ns = Namespace("despesas", description="Operações de despesas")

despesa_model = ns.model("Despesa", {
    "descricao": fields.String(required=True, description="Descrição da despesa"),
    "valor": fields.Float(required=True, description="Valor em reais"),
    "usuario_id": fields.Integer(required=True, description="ID do funcionário")
})

pagamento_model = ns.model("Pagamento", {
    "gestor_id": fields.Integer(required=True, description="ID do gestor que aprova")
})

@ns.route("/")
class DespesaList(Resource):
    def get(self):
        """Lista todas as despesas"""
        despesas = Despesa.query.all()
        return [d.to_dict() for d in despesas], 200

    @ns.expect(despesa_model)
    def post(self):
        """Registra uma nova despesa"""
        dados = ns.payload

        if not dados.get("descricao") or not dados.get("valor") or not dados.get("usuario_id"):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        usuario = Usuario.query.get(dados["usuario_id"])
        if not usuario:
            return {"erro": "Usuário não encontrado"}, 404

        try:
            despesa = Despesa(
                descricao=dados["descricao"],
                valor=dados["valor"],
                usuario_id=dados["usuario_id"]
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
        """Deleta uma despesa"""
        despesa = Despesa.query.get_or_404(id)
        try:
            db.session.delete(despesa)
            db.session.commit()
            return {"mensagem": "Despesa deletada com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:id>/pagar")
class DespesaPagamento(Resource):
    @ns.expect(pagamento_model)
    def patch(self, id):
        """Marca uma despesa como paga (apenas gestor)"""
        despesa = Despesa.query.get_or_404(id)
        dados = ns.payload

        gestor = Usuario.query.get(dados["gestor_id"])
        if not gestor:
            return {"erro": "Gestor não encontrado"}, 404

        if gestor.perfil != "gestor":
            return {"erro": "Apenas gestores podem aprovar pagamentos"}, 403

        if despesa.status == "pago":
            return {"erro": "Despesa já foi paga"}, 400

        try:
            despesa.status = "pago"
            db.session.commit()
            return despesa.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500