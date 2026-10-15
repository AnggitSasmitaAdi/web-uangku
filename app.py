import os
import sqlite3
import tempfile
from datetime import date, datetime

from flask import Flask, g, jsonify, request, send_file

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "uangku-local-development-key")
default_database_path = (
    os.path.join(tempfile.gettempdir(), "uangku.sqlite3")
    if os.environ.get("VERCEL")
    else os.path.join(app.instance_path, "uangku.sqlite3")
)
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", default_database_path)

CATEGORIES = {
    "income": {"Gaji", "Freelance", "Investasi", "Hadiah", "Lainnya"},
    "expense": {
        "Makanan", "Transportasi", "Belanja", "Tagihan", "Kesehatan",
        "Hiburan", "Pendidikan", "Lainnya",
    },
}


def get_db():
    if "db" not in g:
        database_path = app.config["DATABASE"]
        os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute(
            """CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                amount INTEGER NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL
            )"""
        )
        g.db.commit()
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def transaction_dict(row):
    return {key: row[key] for key in ("id", "type", "amount", "category", "note", "date")}


@app.get("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "web.html"))


@app.get("/api/transactions")
def list_transactions():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        month_start = datetime.strptime(month, "%Y-%m").date()
    except ValueError:
        return jsonify(error="Format bulan tidak valid."), 400
    next_month = date(month_start.year + (month_start.month == 12), month_start.month % 12 + 1, 1)
    database = get_db()
    transactions = database.execute(
        "SELECT * FROM transactions WHERE date >= ? AND date < ? ORDER BY date DESC, id DESC",
        (month_start.isoformat(), next_month.isoformat()),
    ).fetchall()
    month_totals = database.execute(
        """SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense
            FROM transactions WHERE date >= ? AND date < ?""",
        (month_start.isoformat(), next_month.isoformat()),
    ).fetchone()
    balance = database.execute(
        "SELECT COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END), 0) FROM transactions"
    ).fetchone()[0]
    categories = database.execute(
        """SELECT category, SUM(amount) AS total FROM transactions
            WHERE type = 'expense' AND date >= ? AND date < ?
            GROUP BY category ORDER BY total DESC""",
        (month_start.isoformat(), next_month.isoformat()),
    ).fetchall()
    return jsonify(
        month=month,
        transactions=[transaction_dict(row) for row in transactions],
        summary={"balance": balance, "income": month_totals["income"], "expense": month_totals["expense"]},
        categories=[{"category": row["category"], "total": row["total"]} for row in categories],
    )


@app.post("/api/transactions")
def create_transaction():
    payload = request.get_json(silent=True) or {}
    transaction_type = payload.get("type")
    category = str(payload.get("category", "")).strip()
    note = str(payload.get("note", "")).strip()
    transaction_date = str(payload.get("date", ""))

    try:
        amount = int(payload.get("amount"))
    except (TypeError, ValueError):
        return jsonify(error="Masukkan nominal berupa angka bulat."), 400
    if transaction_type not in CATEGORIES:
        return jsonify(error="Pilih jenis transaksi yang valid."), 400
    if amount < 1 or amount > 1_000_000_000_000:
        return jsonify(error="Nominal harus lebih dari Rp0 dan tidak lebih dari Rp1 triliun."), 400
    if category not in CATEGORIES[transaction_type]:
        return jsonify(error="Pilih kategori yang tersedia."), 400
    if len(note) > 120:
        return jsonify(error="Catatan maksimal 120 karakter."), 400
    try:
        parsed_date = date.fromisoformat(transaction_date)
    except ValueError:
        return jsonify(error="Tanggal transaksi tidak valid."), 400
    if parsed_date.isoformat() != transaction_date:
        return jsonify(error="Tanggal transaksi tidak valid."), 400

    database = get_db()
    cursor = database.execute(
        "INSERT INTO transactions (type, amount, category, note, date) VALUES (?, ?, ?, ?, ?)",
        (transaction_type, amount, category, note, transaction_date),
    )
    database.commit()
    row = database.execute("SELECT * FROM transactions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(transaction=transaction_dict(row)), 201


@app.delete("/api/transactions/<int:transaction_id>")
def delete_transaction(transaction_id):
    database = get_db()
    cursor = database.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    database.commit()
    if cursor.rowcount == 0:
        return jsonify(error="Transaksi tidak ditemukan."), 404
    return jsonify(success=True)


if __name__ == "__main__":
    app.run(debug=False)
