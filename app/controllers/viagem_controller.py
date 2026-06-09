from flask_restx import Namespace, Resource, fields
from app import db
from app.models.viagem import Viagem
from app.models.pedagio import Pedagio
from app.models.motorista import Motorista
from app.models.veiculo import Veiculo
import requests as http_requests
from flask import request

def obter_localizacao_por_ip(ip):
    """Consulta a IP-API e retorna cidade e regiao do IP."""
    try:
        # Em ambiente local o IP é 127.0.0.1, então usamos o IP público da máquina
        if ip in ("127.0.0.1", "::1", "localhost"):
            resposta = http_requests.get("http://ip-api.com/json/", timeout=3)
        else:
            resposta = http_requests.get(f"http://ip-api.com/json/{ip}", timeout=3)

        dados = resposta.json()
        if dados.get("status") == "success":
            return f"{dados.get('city', '')}, {dados.get('regionName', '')}"
    except Exception:
        pass
    return None

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
    "localizacao": fields.String(required=False, description="Opcional: cidade do pedagio. Se nao informado, detectado automaticamente via IP."),
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
        A API detecta automaticamente a localizacao via IP e cruza com a rota prevista.
        Status gerado automaticamente: conciliado ou alerta (Lei 10.209/2001).
        """
        viagem = Viagem.query.get_or_404(id)
        dados = ns.payload

        if not dados.get("valor"):
            return {"erro": "Valor e obrigatorio"}, 400

        if dados["valor"] <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        if viagem.status != "em_andamento":
            return {"erro": f"Viagem esta com status '{viagem.status}'. Apenas viagens em andamento aceitam pedagogios."}, 400

        # Tenta detectar localização pelo IP automaticamente
        ip_cliente = request.headers.get("X-Forwarded-For", request.remote_addr)
        localizacao_ip = obter_localizacao_por_ip(ip_cliente)

        # Se o motorista informou localização manualmente, usa ela; senão usa a do IP
        localizacao_final = dados.get("localizacao") or localizacao_ip or "Localizacao nao identificada"

        status_conc, observacao = conciliar_pedagio(localizacao_final, viagem)

        # Adiciona info de origem da localização na observação
        if localizacao_ip and not dados.get("localizacao"):
            observacao += f" (Localizacao detectada automaticamente via IP: {localizacao_final})"

        try:
            pedagio = Pedagio(
                valor=dados["valor"],
                localizacao=localizacao_final,
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