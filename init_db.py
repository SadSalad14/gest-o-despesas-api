"""
init_db.py — Inicializa o banco de dados PostgreSQL no Neon
Execute na raiz do projeto: python init_db.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Garante que a DATABASE_URL está definida
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL não encontrada no .env")

print(f"Conectando ao banco: {db_url.split('@')[1]}")  # esconde senha no log

from app import create_app, db

app = create_app()

with app.app_context():
    # Importa todos os models para garantir que as tabelas sejam registradas
    from app.models.gestor import Gestor
    from app.models.motorista import Motorista
    from app.models.veiculo import Veiculo
    from app.models.despesa import Despesa

    db.create_all()
    print("✅ Tabelas criadas com sucesso:")
    print("   - gestores")
    print("   - motoristas")
    print("   - veiculos")
    print("   - despesas")
    print("\nBanco pronto para uso. Inicie a API com: python run.py")
