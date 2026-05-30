from app import db
from datetime import datetime

class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendente")  # 'pendente' ou 'pago'
    data = db.Column(db.DateTime, default=datetime.utcnow)
    motorista_id = db.Column(db.Integer, db.ForeignKey("motoristas.matricula"), nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "descricao": self.descricao,
            "valor": self.valor,
            "status": self.status,
            "data": self.data.isoformat(),
            "usuario_id": self.motorista_id
        }