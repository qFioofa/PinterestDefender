import sqlite3

class pDataBase:

    @staticmethod
    def get_db_connection(DataBaseName = "database.db") -> sqlite3.Connection:
        conn: sqlite3.Connection = sqlite3.connect(DataBaseName)
        conn.row_factory = sqlite3.Row
        return conn

    def __init__(self, app, schema : str = "schema.sql") -> None:
        with app.app_context():
            self.db: sqlite3.Connection = pDataBase.get_db_connection()
            with app.open_resource(schema, mode='r') as f:
                self.db.executescript(f.read())
            self.db.commit()

