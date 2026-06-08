from app import create_app, db
from app.models.motorista import Motorista
from app.models.gestor import Gestor
from app.models.veiculo import Veiculo
from app.models.despesa import Despesa
from app.models.viagem import Viagem
from app.models.pedagio import Pedagio

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)