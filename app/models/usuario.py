from app import db

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    perfil = db.Column(db.String(20), nullable=False)  # 'funcionario' ou 'gestor'

    despesas = db.relationship("Despesa", backref="usuario", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "perfil": self.perfil
        }