from flask_restx import Namespace, Resource, fields
from app import db
from app.models.usuario import Usuario

ns = Namespace("usuarios", description="Operações de usuários")

usuario_model = ns.model("Usuario", {
    "nome": fields.String(required=True, description="Nome do usuário"),
    "email": fields.String(required=True, description="Email do usuário"),
    "perfil": fields.String(required=True, description="'funcionario' ou 'gestor'")
})

@ns.route("/")
class UsuarioList(Resource):
    def get(self):
        """Lista todos os usuários"""
        usuarios = Usuario.query.all()
        return [u.to_dict() for u in usuarios], 200

    @ns.expect(usuario_model)
    def post(self):
        """Cadastra um novo usuário"""
        dados = ns.payload

        if not dados.get("nome") or not dados.get("email") or not dados.get("perfil"):
            return {"erro": "Todos os campos são obrigatórios"}, 400

        if dados["perfil"] not in ["funcionario", "gestor"]:
            return {"erro": "Perfil deve ser 'funcionario' ou 'gestor'"}, 400

        if Usuario.query.filter_by(email=dados["email"]).first():
            return {"erro": "Email já cadastrado"}, 409

        try:
            usuario = Usuario(
                nome=dados["nome"],
                email=dados["email"],
                perfil=dados["perfil"]
            )
            db.session.add(usuario)
            db.session.commit()
            return usuario.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route("/<int:id>")
class UsuarioItem(Resource):
    def get(self, id):
        """Busca um usuário pelo ID"""
        usuario = Usuario.query.get_or_404(id)
        return usuario.to_dict(), 200

    def delete(self, id):
        """Deleta um usuário"""
        usuario = Usuario.query.get_or_404(id)
        try:
            db.session.delete(usuario)
            db.session.commit()
            return {"mensagem": "Usuário deletado com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500