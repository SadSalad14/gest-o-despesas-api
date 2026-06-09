from app import db
from datetime import datetime

class Pedagio(db.Model):
    __tablename__ = "pedagogios"

    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Float, nullable=False)
    localizacao = db.Column(db.String(100), nullable=False) # Localização declarada
    data = db.Column(db.DateTime, default=datetime.utcnow)
    status_conciliacao = db.Column(db.String(20), nullable=False, default="pendente")  # conciliado, alerta, pendente
    observacao = db.Column(db.String(200), nullable=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id"), nullable=False)
    veiculo_tag = db.Column(db.Integer, db.ForeignKey("veiculos.tag"), nullable=True) # Tag do veículo no sistema
    comprovante_tag = db.Column(db.Integer, nullable=True)          # Tag capturada pelo comprovante
    comprovante_localizacao = db.Column(db.String(100), nullable=True) # Localização real do comprovante
    imagem_comprovante = db.Column(db.String(255), nullable=True)   # Caminho/URL da foto indexada

    def to_dict(self):
        return {
            "id": self.id,
            "valor": self.valor,
            "localizacao": self.localizacao,
            "data": self.data.isoformat(),
            "status_conciliacao": self.status_conciliacao,
            "observacao": self.observacao,
            "viagem_id": self.viagem_id,
            "veiculo_tag": self.veiculo_tag,
            "comprovante_tag": self.comprovante_tag,
            "comprovante_localizacao": self.comprovante_localizacao,
            "imagem_comprovante": self.imagem_comprovante
        }
