import os
from datetime import datetime
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage
from app import db
from app.models.despesa import Despesa
from app.models.motorista import Motorista
from app.models.gestor import Gestor
from app.models.pedagio import Pedagio
from app.models.viagem import Viagem

ns = Namespace("despesas", description="Registro e aprovacao de despesas corporativas da frota")

despesa_model = ns.model("Despesa", {
    "descricao": fields.String(required=True, description="Descricao da despesa (ex: Abastecimento SP-RJ)"),
    "valor": fields.Float(required=True, description="Valor em reais, maior que zero (ex: 150.50)"),
    "categoria": fields.String(required=False, description="Categoria: abastecimento, pedagio, manutencao, geral. Padrao: geral"),
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

CATEGORIAS_VALIDAS = ["abastecimento", "pedagio", "manutencao", "geral"]

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
            return {"erro": "Para registrar pedagogios de viagem use a rota POST /viagens/{id}/pedagio"}, 403

        if categoria == "multa":
            return {"erro": "Para registrar multas use a rota POST /despesas/multa"}, 403

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

# Parser necessário para indexar imagens através do upload multipart/form-data
upload_parser = ns.parser()
upload_parser.add_argument("viagem_id", type=int, required=True, location="form", help="ID da viagem")
upload_parser.add_argument("valor", type=float, required=True, location="form", help="Valor do pedágio")
upload_parser.add_argument("localizacao", type=str, required=True, location="form", help="Localização informada")
upload_parser.add_argument("comprovante_tag", type=int, required=True, location="form", help="TAG lida pelo sistema externo")
upload_parser.add_argument("comprovante_localizacao", type=str, required=True, location="form", help="Cidade do comprovante")
upload_parser.add_argument("imagem", location="files", type=FileStorage, required=False, help="Foto do comprovante físico para indexação")

@ns.route("/pedagio-externo")
class PedagioExternoConciliacao(Resource):
    @ns.expect(upload_parser)
    def post(self):
        """Recebe dados de comprovante externo, faz cruzamento inteligente de fraude e anexa imagem"""
        args = upload_parser.parse_args()
        
        viagem_id = args["viagem_id"]
        valor = args["valor"]
        localizacao = args["localizacao"]
        comprovante_tag = args["comprovante_tag"]
        comp_localizacao = args["comprovante_localizacao"]
        imagem_arquivo = args.get("imagem")

        # 1. Validar se a viagem informada existe
        viagem = Viagem.query.get(viagem_id)
        if not viagem:
            return {"erro": "Viagem informada não existe no sistema"}, 404

        # 2. Inicializar variáveis de auditoria contra fraudes
        status_conciliacao = "conciliado"
        alertas = []

        # Validação 1: Comparar se a TAG do comprovante bate com a TAG cadastrada no Veículo da viagem
        if viagem.veiculo_tag != comprovante_tag:
            status_conciliacao = "alerta"
            alertas.append(f"TAG divergente! Comprovante indica TAG {comprovante_tag}, mas o veículo possui TAG {viagem.veiculo_tag}")

        # Validação 2: Verificar se a localização do comprovante está dentro da lista de cidades da rota
        cidades_permitidas = viagem.cidades_lista()
        localizacao_limpa = comp_localizacao.strip().lower()

        if localizacao_limpa not in cidades_permitidas:
            status_conciliacao = "alerta"
            alertas.append(f"Localização suspeita! A cidade '{comp_localizacao}' não faz parte da rota planejada desta viagem")

        # 3. Processar e salvar o arquivo de imagem (Indexação para evitar fraudes)
        caminho_imagem_salva = None
        if imagem_arquivo:
            try:
                # Cria uma pasta para uploads caso ela não exista
                pasta_upload = os.path.join("app", "static", "uploads", "comprovantes")
                os.makedirs(pasta_upload, exist_ok=True)
                
                # Gera um nome seguro baseado no timestamp para evitar sobrescrever arquivos
                timestamp = int(datetime.utcnow().timestamp())
                nome_arquivo = f"viagem_{viagem_id}_{timestamp}_{imagem_arquivo.filename}"
                caminho_completo = os.path.join(pasta_upload, nome_arquivo)
                
                imagem_arquivo.save(caminho_completo)
                caminho_imagem_salva = f"/static/uploads/comprovantes/{nome_arquivo}"
            except Exception as img_err:
                alertas.append(f"Erro ao salvar imagem: {str(img_err)}")

        # 4. Criar registro de despesa para o pedagio
        try:
            despesa = Despesa(
                descricao=f"Pedágio - {comp_localizacao}",
                valor=valor,
                categoria="pedagio",
                motorista_id=viagem.motorista_id,
                veiculo_placa=viagem.veiculo_placa,
                localizacao=localizacao
            )
            db.session.add(despesa)
            db.session.flush()

            # 5. Criar registro de pedagio associado
            pedagio = Pedagio(
                viagem_id=viagem_id,
                despesa_id=despesa.id,
                valor=valor,
                localizacao=comp_localizacao,
                tag_veiculo=comprovante_tag,
                status_conciliacao=status_conciliacao,
                comprovante_url=caminho_imagem_salva
            )
            db.session.add(pedagio)
            db.session.commit()

            resposta = {
                "mensagem": "Pedagio registrado com sucesso",
                "despesa_id": despesa.id,
                "pedagio_id": pedagio.id,
                "status_conciliacao": status_conciliacao,
                "alertas": alertas
            }
            return resposta, 201

        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500
