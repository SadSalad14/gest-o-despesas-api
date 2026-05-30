from app import db

class Motorista(db.Model):
    __tablename__ = "motoristas"

    matricula = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    tp_cnh = db.Column(db.String(3), nullable=False)
    validade_cnh = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(2), nullable=False, default="AT")

    despesas = db.relationship("Despesa", backref="motorista", lazy=True)

    def to_dict(self):
        return {
            "matricula": self.matricula,
            "nome": self.nome,
            "cpf": self.cpf,
            "tp_cnh": self.tp_cnh,
            "validade_cnh": self.validade_cnh.isoformat(),
            "status": self.status
        }