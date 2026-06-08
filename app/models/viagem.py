from app import db
from datetime import datetime

class Viagem(db.Model):
    __tablename__ = "viagens"

    id = db.Column(db.Integer, primary_key=True)
    origem = db.Column(db.String(100), nullable=False)
    destino = db.Column(db.String(100), nullable=False)
    cidades_rota = db.Column(db.Text, nullable=False)  # cidades separadas por vírgula
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="em_andamento")  # em_andamento, concluida, cancelada
    motorista_id = db.Column(db.Integer, db.ForeignKey("motoristas.matricula"), nullable=False)
    veiculo_tag = db.Column(db.Integer, db.ForeignKey("veiculos.tag"), nullable=True)

    pedagogios = db.relationship("Pedagio", backref="viagem", lazy=True)

    def cidades_lista(self):
        return [c.strip().lower() for c in self.cidades_rota.split(",")]

    def to_dict(self):
        return {
            "id": self.id,
            "origem": self.origem,
            "destino": self.destino,
            "cidades_rota": self.cidades_rota,
            "data_inicio": self.data_inicio.isoformat(),
            "status": self.status,
            "motorista_id": self.motorista_id,
            "veiculo_tag": self.veiculo_tag
        }