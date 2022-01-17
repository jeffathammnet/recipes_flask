# Install requirements
python3 -m pip install -r requirements.txt

# Generate Flask secret key
python3 -c 'import os; print(os.urandom(16))'

# Initialize Database
python3 -c 'from app import db; db.create_all()'