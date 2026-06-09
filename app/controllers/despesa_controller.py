import os
from datetime import datetime
from flask_restx import Namespace, Resource, fields
from app import db
from app.models.despesa import Despesa
from app.models.motorista import Motorista
from app.models.gestor import Gestor

ns = Namespace("despesas", description="Registro e aprovacao de despesas corporativas da frota")

despesa_model = ns.model("Despesa", {
    "descricao": fields.String(required=True, description="Descricao da despesa (ex: Abastecimento SP-RJ)"),
    "valor": fields.Float(required=True, description="Valor em reais, maior que zero (ex: 150.50)"),
    "categoria": fields.String(required=False, description="Categoria: abastecimento, manutencao, geral. Padrao: geral"),
    "motorista_matricula": fields.Integer(required=True, description="Matricula do motorista que gerou a despesa"),
    "veiculo_placa": fields.String(required=False, description="Placa do veiculo associado"),
    "localizacao": fields.String(required=False, description="Cidade ou local da despesa (ex: Caruaru, PE)")
})

pagamento_model = ns.model("Pagamento", {
    "gestor_matricula": fields.Integer(required=True, description="Matricula do gestor que autoriza o pagamento")
})

multa_model = ns.model("Multa", {
    "descricao": fields.String(required=True, description="Descricao da multa"),
    "valor": fields.Float(required=True, description="Valor da multa em reais"),
    "gestor_matricula": fields.Integer(required=True, description="Matricula do gestor que registra a multa"),
    "motorista_matricula": fields.Integer(required=True, description="Matricula do motorista que recebeu a multa"),
    "veiculo_placa": fields.String(required=False, description="Placa do veiculo envolvido"),
    "localizacao": fields.String(required=False, description="Local onde a multa foi aplicada")
})

CATEGORIAS_VALIDAS = ["abastecimento", "manutencao", "geral"]

@ns.route("/")
class DespesaList(Resource):
    def get(self):
        """Retorna a lista completa de despesas registradas"""
        despesas = Despesa.query.all()
        return [d.to_dict() for d in despesas], 200

    @ns.expect(despesa_model)
    def post(self):
        """Registra uma nova despesa. Status inicial: pendente."""
        dados = ns.payload

        if not dados.get("descricao") or not dados.get("valor") or not dados.get("motorista_matricula"):
            return {"erro": "Todos os campos obrigatorios devem ser preenchidos"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        categoria = dados.get("categoria", "geral")
        if categoria not in CATEGORIAS_VALIDAS:
            return {"erro": f"Categoria invalida. Use: {', '.join(CATEGORIAS_VALIDAS)}"}, 400

        if categoria == "pedagio":
            return {"erro": "Para registrar pedagios de viagem use o endpoint multipart de /viagens/{id}/pedagio"}, 403

        motorista = Motorista.query.get(dados["motorista_matricula"])
        if not motorista:
            return {"erro": "Motorista nao encontrado"}, 404

        try:
            despesa = Despesa(
                descricao=dados["descricao"],
                valor=dados["valor"],
                categoria=categoria,
                motorista_id=dados["motorista_matricula"],
                veiculo_placa=dados.get("veiculo_placa"),
                localizacao=dados.get("localizacao")
            )
            db.session.add(despesa)
            db.session.commit()
            return despesa.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/multa")
class DespesaMulta(Resource):
    @ns.expect(multa_model)
    def post(self):
        """Registra uma multa. Exclusivo para gestores."""
        dados = ns.payload

        if not all(dados.get(c) for c in ["descricao", "valor", "gestor_matricula", "motorista_matricula"]):
            return {"erro": "Todos os campos obrigatorios devem ser preenchidos"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        gestor = Gestor.query.get(dados["gestor_matricula"])
        if not gestor:
            return {"erro": "Gestor nao encontrado. Apenas gestores podem registrar multas."}, 403

        motorista = Motorista.query.get(dados["motorista_matricula"])
        if not motorista:
            return {"erro": "Motorista nao encontrado"}, 404

        try:
            despesa = Despesa(
                descricao=dados["descricao"],
                valor=dados["valor"],
                categoria="multa",
                motorista_id=dados["motorista_matricula"],
                veiculo_placa=dados.get("veiculo_placa"),
                localizacao=dados.get("localizacao")
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
        """Aprova o pagamento de uma despesa. Exclusivo para gestores."""
        despesa = Despesa.query.get_or_404(id)
        dados = ns.payload

        gestor = Gestor.query.get(dados["gestor_matricula"])
        if not gestor:
            return {"erro": "Gestor nao encontrado"}, 404

        if despesa.status == "pago":
            return {"erro": "Esta despesa ja foi aprovada e paga"}, 400

        try:
            despesa.status = "pago"
            db.session.commit()
            return despesa.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500
