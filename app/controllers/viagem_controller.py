from flask_restx import Namespace, Resource, fields
from app import db
from app.models.viagem import Viagem
from app.models.pedagio import Pedagio
from app.models.motorista import Motorista
from app.models.veiculo import Veiculo

ns = Namespace("viagens", description="Gerenciamento de viagens e conciliacao de pedagios")

viagem_model = ns.model("Viagem", {
    "origem": fields.String(required=True, description="Cidade de origem (ex: Recife, PE)"),
    "destino": fields.String(required=True, description="Cidade de destino (ex: Sao Paulo, SP)"),
    "cidades_rota": fields.String(required=True, description="Cidades do trajeto separadas por virgula (ex: Recife, Caruaru, Arcoverde, Garanhuns)"),
    "motorista_id": fields.Integer(required=True, description="Matricula do motorista"),
    "veiculo_tag": fields.Integer(required=False, description="Tag do veiculo")
})

pedagio_model = ns.model("Pedagio", {
    "valor": fields.Float(required=True, description="Valor cobrado na praca de pedagio"),
    "localizacao": fields.String(required=True, description="Cidade ou trecho onde o pedagio foi cobrado (ex: Caruaru, PE)"),
    "veiculo_tag": fields.Integer(required=False, description="Tag do veiculo que passou pelo pedagio")
})

status_model = ns.model("StatusViagem", {
    "status": fields.String(required=True, description="Novo status: concluida ou cancelada")
})

def conciliar_pedagio(localizacao, viagem):
    """
    Verifica se a localização do pedágio está dentro da rota prevista.
    Retorna (status, observacao).
    """
    loc = localizacao.lower().strip()
    cidades = viagem.cidades_lista()

    # Verifica se alguma cidade da rota está contida na localização informada
    for cidade in cidades:
        if cidade in loc or loc in cidade:
            return "conciliado", f"Localizacao '{localizacao}' confirmada na rota prevista."

    # Verifica origem e destino também
    if viagem.origem.lower() in loc or viagem.destino.lower() in loc:
        return "conciliado", f"Localizacao '{localizacao}' confirmada na rota prevista."

    return "alerta", (
        f"ALERTA Lei 10.209/2001: Localizacao '{localizacao}' nao identificada na rota prevista "
        f"({viagem.origem} → {viagem.destino}). Verifique se o motorista desviou da rota contratada."
    )

@ns.route("/")
class ViagemList(Resource):
    def get(self):
        """Retorna todas as viagens cadastradas"""
        viagens = Viagem.query.all()
        return [v.to_dict() for v in viagens], 200

    @ns.expect(viagem_model)
    def post(self):
        """Cadastra uma nova viagem com rota prevista"""
        dados = ns.payload

        if not all(dados.get(c) for c in ["origem", "destino", "cidades_rota", "motorista_id"]):
            return {"erro": "Todos os campos obrigatorios devem ser preenchidos"}, 400

        motorista = Motorista.query.get(dados["motorista_id"])
        if not motorista:
            return {"erro": "Motorista nao encontrado"}, 404

        if dados.get("veiculo_tag"):
            veiculo = Veiculo.query.get(dados["veiculo_tag"])
            if not veiculo:
                return {"erro": "Veiculo nao encontrado"}, 404

        try:
            viagem = Viagem(
                origem=dados["origem"],
                destino=dados["destino"],
                cidades_rota=dados["cidades_rota"],
                motorista_id=dados["motorista_id"],
                veiculo_tag=dados.get("veiculo_tag")
            )
            db.session.add(viagem)
            db.session.commit()
            return viagem.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:id>")
class ViagemItem(Resource):
    def get(self, id):
        """Busca uma viagem pelo ID"""
        viagem = Viagem.query.get_or_404(id)
        return viagem.to_dict(), 200

    @ns.expect(status_model)
    def patch(self, id):
        """Atualiza o status da viagem (concluida ou cancelada)"""
        viagem = Viagem.query.get_or_404(id)
        dados = ns.payload

        if dados["status"] not in ["concluida", "cancelada"]:
            return {"erro": "Status deve ser concluida ou cancelada"}, 400

        try:
            viagem.status = dados["status"]
            db.session.commit()
            return viagem.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:id>/pedagio")
class ViagemPedagio(Resource):
    @ns.expect(pedagio_model)
    def post(self, id):
        """
        Registra um pedagio em uma viagem.
        A API cruza automaticamente a localizacao com a rota prevista
        e gera status: conciliado ou alerta (Lei 10.209/2001).
        """
        viagem = Viagem.query.get_or_404(id)
        dados = ns.payload

        if not dados.get("valor") or not dados.get("localizacao"):
            return {"erro": "Valor e localizacao sao obrigatorios"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        if viagem.status != "em_andamento":
            return {"erro": f"Viagem esta com status '{viagem.status}'. Apenas viagens em andamento aceitam pedagios."}, 400

        status_conc, observacao = conciliar_pedagio(dados["localizacao"], viagem)

        try:
            pedagio = Pedagio(
                valor=dados["valor"],
                localizacao=dados["localizacao"],
                status_conciliacao=status_conc,
                observacao=observacao,
                viagem_id=id,
                veiculo_tag=dados.get("veiculo_tag")
            )
            db.session.add(pedagio)
            db.session.commit()
            return pedagio.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

    def get(self, id):
        """Lista todos os pedagios de uma viagem com status de conciliacao"""
        viagem = Viagem.query.get_or_404(id)
        pedagios = Pedagio.query.filter_by(viagem_id=id).all()
        total = sum(p.valor for p in pedagios)
        alertas = [p.to_dict() for p in pedagios if p.status_conciliacao == "alerta"]
        conciliados = [p.to_dict() for p in pedagios if p.status_conciliacao == "conciliado"]

        return {
            "viagem_id": id,
            "rota": f"{viagem.origem} → {viagem.destino}",
            "total_gasto_pedagios": total,
            "total_conciliados": len(conciliados),
            "total_alertas": len(alertas),
            "pedagios": [p.to_dict() for p in pedagios]
        }, 200