from app import db
from datetime import datetime

class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(30), nullable=False, default="geral")
    status = db.Column(db.String(20), nullable=False, default="pendente")
    data = db.Column(db.DateTime, default=datetime.utcnow)
    localizacao = db.Column(db.String(100), nullable=True)
    motorista_id = db.Column(db.Integer, db.ForeignKey("motoristas.matricula"), nullable=False)
    veiculo_placa = db.Column(db.String(7), db.ForeignKey("veiculos.placa"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "descricao": self.descricao,
            "valor": self.valor,
            "categoria": self.categoria,
            "status": self.status,
            "data": self.data.isoformat(),
            "localizacao": self.localizacao,
            "motorista_id": self.motorista_id,
            "veiculo_placa": self.veiculo_placa
        }