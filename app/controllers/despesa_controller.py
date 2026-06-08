from flask_restx import Namespace, Resource, fields
from app import db
from app.models.despesa import Despesa
from app.models.motorista import Motorista
from app.models.gestor import Gestor
import math

ns = Namespace("despesas", description="Registro e aprovação de despesas corporativas da frota")

despesa_model = ns.model("Despesa", {
    "descricao": fields.String(required=True, description="Descrição da despesa (ex: Abastecimento SP-RJ)"),
    "valor": fields.Float(required=True, description="Valor em reais, maior que zero (ex: 150.50)"),
    "categoria": fields.String(required=False, description="Categoria: abastecimento, pedagio, manutencao, geral. Padrão: geral"),
    "motorista_matricula": fields.Integer(required=True, description="Matrícula do motorista que gerou a despesa"),
    "veiculo_placa": fields.String(required=False, description="Placa do veículo associado à despesa"),
    "latitude": fields.Float(required=False, description="Latitude GPS do local da despesa"),
    "longitude": fields.Float(required=False, description="Longitude GPS do local da despesa")
})

pagamento_model = ns.model("Pagamento", {
    "gestor_matricula": fields.Integer(required=True, description="Matrícula do gestor que autoriza o pagamento")
})

multa_model = ns.model("Multa", {
    "descricao": fields.String(required=True, description="Descrição da multa"),
    "valor": fields.Float(required=True, description="Valor da multa em reais"),
    "gestor_matricula": fields.Integer(required=True, description="Matrícula do gestor que registra a multa"),
    "motorista_matricula": fields.Integer(required=True, description="Matrícula do motorista que recebeu a multa"),
    "veiculo_placa": fields.String(required=False, description="Placa do veículo envolvido"),
    "latitude": fields.Float(required=False, description="Latitude do local da multa"),
    "longitude": fields.Float(required=False, description="Longitude do local da multa")
})

CATEGORIAS_VALIDAS = ["abastecimento", "pedagio", "manutencao", "geral"]

def distancia_km(lat1, lon1, lat2, lon2):
    """Calcula distância entre dois pontos GPS em km (fórmula de Haversine)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

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
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        categoria = dados.get("categoria", "geral")
        if categoria not in CATEGORIAS_VALIDAS:
            return {"erro": f"Categoria inválida. Use: {', '.join(CATEGORIAS_VALIDAS)}"}, 400

        if categoria == "multa":
            return {"erro": "Para registrar multas use a rota POST /despesas/multa"}, 403

        motorista = Motorista.query.get(dados["motorista_matricula"])
        if not motorista:
            return {"erro": "Motorista não encontrado"}, 404

        # Verificação GPS — alerta se despesa tiver GPS mas estiver a mais de 500km de outras do mesmo motorista
        alerta_gps = None
        lat = dados.get("latitude")
        lon = dados.get("longitude")
        if lat and lon:
            despesas_anteriores = Despesa.query.filter_by(
                motorista_id=dados["motorista_matricula"]
            ).filter(Despesa.latitude.isnot(None)).order_by(Despesa.data.desc()).limit(3).all()

            for d in despesas_anteriores:
                dist = distancia_km(lat, lon, d.latitude, d.longitude)
                if dist > 500:
                    alerta_gps = f"Alerta: localização incomum — {dist:.0f}km de distância de registros anteriores deste motorista"
                    break

        try:
            despesa = Despesa(
                descricao=dados["descricao"],
                valor=dados["valor"],
                categoria=categoria,
                motorista_id=dados["motorista_matricula"],
                veiculo_placa=dados.get("veiculo_placa"),
                latitude=lat,
                longitude=lon
            )
            db.session.add(despesa)
            db.session.commit()
            resultado = despesa.to_dict()
            if alerta_gps:
                resultado["alerta"] = alerta_gps
            return resultado, 201
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
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        gestor = Gestor.query.get(dados["gestor_matricula"])
        if not gestor:
            return {"erro": "Gestor não encontrado. Apenas gestores podem registrar multas."}, 403

        motorista = Motorista.query.get(dados["motorista_matricula"])
        if not motorista:
            return {"erro": "Motorista não encontrado"}, 404

        try:
            despesa = Despesa(
                descricao=dados["descricao"],
                valor=dados["valor"],
                categoria="multa",
                motorista_id=dados["motorista_matricula"],
                veiculo_placa=dados.get("veiculo_placa"),
                latitude=dados.get("latitude"),
                longitude=dados.get("longitude")
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