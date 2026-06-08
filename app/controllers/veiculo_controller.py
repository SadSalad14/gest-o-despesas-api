from flask_restx import Namespace, Resource, fields
from app import db
from app.models.veiculo import Veiculo

ns = Namespace("veiculos", description="Gerenciamento da frota de veiculos LogTrans")

veiculo_model = ns.model("Veiculo", {
    "placa": fields.String(required=True, description="Placa do veiculo (7 caracteres, ex: ABC1234)"),
    "modelo": fields.String(required=True, description="Modelo do veiculo (ex: Volvo FH 460)"),
    "tipo": fields.String(required=True, description="Tipo: proprio ou locado"),
    "status": fields.String(required=False, description="OP (operacional) ou NP (nao operacional). Padrao: OP"),
    "quilometragem": fields.Float(required=False, description="Quilometragem atual. Padrao: 0.0")
})

km_model = ns.model("Quilometragem", {
    "quilometragem": fields.Float(required=True, description="Nova quilometragem do veiculo")
})

@ns.route("/")
class VeiculoList(Resource):
    def get(self):
        """Retorna a lista completa de veiculos da frota"""
        veiculos = Veiculo.query.all()
        return [v.to_dict() for v in veiculos], 200

    @ns.expect(veiculo_model)
    def post(self):
        """Cadastra um novo veiculo na frota. Placa deve ser unica."""
        dados = ns.payload

        if not dados.get("placa") or not dados.get("modelo") or not dados.get("tipo"):
            return {"erro": "Todos os campos sao obrigatorios"}, 400

        if len(dados["placa"]) != 7:
            return {"erro": "Placa deve ter exatamente 7 caracteres"}, 400

        if dados["tipo"] not in ["proprio", "locado"]:
            return {"erro": "Tipo deve ser proprio ou locado"}, 400

        if Veiculo.query.filter_by(placa=dados["placa"].upper()).first():
            return {"erro": "Placa ja cadastrada no sistema"}, 409

        try:
            veiculo = Veiculo(
                placa=dados["placa"].upper(),
                modelo=dados["modelo"],
                tipo=dados["tipo"],
                status=dados.get("status", "OP"),
                quilometragem=dados.get("quilometragem", 0.0)
            )
            db.session.add(veiculo)
            db.session.commit()
            return veiculo.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:tag>")
class VeiculoItem(Resource):
    def get(self, tag):
        """Busca um veiculo pela tag"""
        veiculo = Veiculo.query.get_or_404(tag)
        return veiculo.to_dict(), 200

    def delete(self, tag):
        """Remove um veiculo da frota pela tag"""
        veiculo = Veiculo.query.get_or_404(tag)
        try:
            db.session.delete(veiculo)
            db.session.commit()
            return {"mensagem": "Veiculo removido com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:tag>/quilometragem")
class VeiculoKm(Resource):
    @ns.expect(km_model)
    def patch(self, tag):
        """Atualiza a quilometragem do veiculo"""
        veiculo = Veiculo.query.get_or_404(tag)
        dados = ns.payload

        if dados["quilometragem"] < veiculo.quilometragem:
            return {"erro": "Nova quilometragem nao pode ser menor que a atual"}, 400

        try:
            veiculo.quilometragem = dados["quilometragem"]
            db.session.commit()
            return veiculo.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500