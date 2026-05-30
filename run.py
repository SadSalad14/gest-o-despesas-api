from app import create_app, db
from app.models.usuario import Usuario
from app.models.despesa import Despesa

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)