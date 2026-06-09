import os
from datetime import datetime
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage
from flask import request
import requests as http_requests
from app import db
from app.models.viagem import Viagem
from app.models.pedagio import Pedagio
from app.models.motorista import Motorista
from app.models.veiculo import Veiculo

def obter_localizacao_por_ip(ip):
    """Consulta a IP-API e retorna cidade e regiao do IP."""
    try:
        if ip in ("127.0.0.1", "::1", "localhost"):
            resposta = http_requests.get("http://ip-api.com", timeout=3)
        else:
            resposta = http_requests.get(f"http://ip-api.com{ip}", timeout=3)

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

status_model = ns.model("StatusViagem", {
    "status": fields.String(required=True, description="Novo status: concluida ou cancelada")
})

# Estruturação do Parser Multipart para suportar upload de arquivos de imagem e formulário
pedagio_parser = ns.parser()
pedagio_parser.add_argument("valor", type=float, required=True, location="form", help="Valor cobrado na praca de pedagio")
pedagio_parser.add_argument("localizacao", type=str, required=False, location="form", help="Nome/identificacao manual da praca")
pedagio_parser.add_argument("comprovante_tag", type=int, required=False, location="form", help="Opcional: TAG lida pelo sistema físico externo")
pedagio_parser.add_argument("comprovante_localizacao", type=str, required=False, location="form", help="Opcional: Cidade extraída do comprovante físico")
pedagio_parser.add_argument("imagem", location="files", type=FileStorage, required=False, help="Foto/Upload do comprovante físico para indexação")

def avaliar_trajeto(localizacao_teste, viagem):
    """Auxiliar para checar se uma determinada string de localização pertence à rota da viagem"""
    if not localizacao_teste:
        return False
    loc = localizacao_teste.lower().strip()
    cidades = viagem.cidades_lista()
    
    for cidade in cidades:
        if cidade in loc or loc in cidade:
            return True
    if viagem.origem.lower() in loc or viagem.destino.lower() in loc:
        return True
    return False

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
    @ns.expect(pedagio_parser)
    def post(self, id):
        """
        Registra e audita um pedagio vinculado a uma viagem ativa.
        Realiza cruzamento inteligente antifraude de TAGs, rota planejada e indexação de imagem.
        """
        viagem = Viagem.query.get_or_404(id)
        args = pedagio_parser.parse_args()

        valor = args["valor"]
        localizacao_manual = args.get("localizacao")
        comp_tag = args.get("comprovante_tag")
        comp_localizacao = args.get("comprovante_localizacao")
        imagem_arquivo = args.get("imagem")

        if valor <= 0:
            return {"erro": "Valor deve ser maior que zero"}, 400

        if viagem.status != "em_andamento":
            return {"erro": f"Viagem possui status '{viagem.status}'. Registros bloqueados."}, 400

        # 1. Rastreamento e detecção automática de localização por IP
        ip_cliente = request.headers.get("X-Forwarded-For", request.remote_addr)
        localizacao_ip = obter_localizacao_por_ip(ip_cliente)
        
        localizacao_final = localizacao_manual or localizacao_ip or "Localizacao nao identificada"

        # 2. Motor Antifraude Integrado
        status_conciliacao = "conciliado"
        alertas = []

        # Validação de Rota A: Localização Declarada/IP
        if not avaliar_trajeto(localizacao_final, viagem):
            status_conciliacao = "alerta"
            alertas.append(f"Localizacao declarada/IP '{localizacao_final}' fora do trajeto contratado.")

        # Validação de Rota B: Cidade impressa no Comprovante Físico Externo
        if comp_localizacao and not avaliar_trajeto(comp_localizacao, viagem):
            status_conciliacao = "alerta"
            alertas.append(f"Cidade do comprovante '{comp_localizacao}' nao faz parte da rota planejada.")

        # Validação de Hardware: Cruzamento de TAG de segurança do Veículo
        if comp_tag and viagem.veiculo_tag and (viagem.veiculo_tag != comp_tag):
            status_conciliacao = "alerta"
            alertas.append(f"TAG divergente! Sistema: {viagem.veiculo_tag} | Comprovante: {comp_tag}")

        # Montagem do log de auditoria
        if alertas:
            observacao = " | ".join(alertas)
        else:
            observacao = f"Confirmado na rota. (IP Tracker: {localizacao_ip})" if localizacao_ip else "Dados em conformidade."

        # 3. Upload e indexação segura do arquivo de imagem
        caminho_imagem_salva = None
        if imagem_arquivo:
            try:
                pasta_upload = os.path.join("app", "static", "uploads", "comprovantes")
                os.makedirs(pasta_upload, exist_ok=True)
                
                timestamp = int(datetime.utcnow().timestamp())
                nome_seguro = f"viagem_{id}_{timestamp}_{imagem_arquivo.filename}"
                caminho_completo = os.path.join(pasta_upload, nome_seguro)
                
                imagem_arquivo.save(caminho_completo)
                caminho_imagem_salva = f"/static/uploads/comprovantes/{nome_seguro}"
            except Exception as img_err:
                observacao += f" | (Erro upload imagem: {str(img_err)})"

        try:
            pedagio = Pedagio(
                valor=valor,
                localizacao=localizacao_final,
                status_conciliacao=status_conciliacao,
                observacao=observacao[:200],
                viagem_id=id,
                veiculo_tag=viagem.veiculo_tag,
                comprovante_tag=comp_tag,
                comprovante_localizacao=comp_localizacao,
                imagem_comprovante=caminho_imagem_salva
            )
            db.session.add(pedagio)
            db.session.commit()
            
            resposta = pedagio.to_dict()
            resposta["alertas_auditoria"] = alertas if alertas else "Nenhuma inconformidade detectada"
            return resposta, 201
            
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500
