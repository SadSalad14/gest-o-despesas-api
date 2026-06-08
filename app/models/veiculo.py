from app import db

class Veiculo(db.Model):
    __tablename__ = "veiculos"

    tag = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(7), unique=True, nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'proprio' ou 'locado'
    status = db.Column(db.String(2), nullable=False, default="OP")
    quilometragem = db.Column(db.Float, nullable=False, default=0.0)

    def to_dict(self):
        return {
            "tag": self.tag,
            "placa": self.placa,
            "modelo": self.modelo,
            "tipo": self.tipo,
            "status": self.status,
            "quilometragem": self.quilometragem
        }