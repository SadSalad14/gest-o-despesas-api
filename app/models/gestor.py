from app import db

class Gestor(db.Model):
    __tablename__ = "gestores"

    matricula = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(11), nullable=False)
    departamento = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            "matricula": self.matricula,
            "nome": self.nome,
            "email": self.email,
            "telefone": self.telefone,
            "departamento": self.departamento
        }