import sqlite3
import os

class pDataBase:
    @staticmethod
    def get_db_connection(DataBaseName="database.db") -> sqlite3.Connection:
        db_path: str = os.path.join(os.getcwd(), DataBaseName)

        db_dir: str = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn: sqlite3.Connection = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def __init__(self, app, schema: str = "schema.sql") -> None:
        with app.app_context():
            self.db: sqlite3.Connection = pDataBase.get_db_connection()
            try:
                with app.open_resource(schema, mode='r') as f:
                    self.db.executescript(f.read())
                self.db.commit()
            except Exception as e:
                self.db.close()
                print(f"Database initialization error: {str(e)}")
                raise e