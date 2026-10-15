# UANGKU — Catatan Keuangan Pribadi

Aplikasi pencatatan pemasukan dan pengeluaran berbasis Flask. Antarmuka, CSS, dan JavaScript berada di `web.html`; `app.py` menyediakan halaman dan API transaksi.

## Jalankan lokal di Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Buka `http://127.0.0.1:5000`. Secara lokal, data disimpan di `instance/uangku.sqlite3`.

## Deploy ke Vercel

1. Pastikan `app.py`, `web.html`, `requirements.txt`, dan `vercel.json` berada di root repository, lalu push perubahan ke GitHub.
2. Masuk ke [Vercel](https://vercel.com), pilih **Add New → Project**, lalu impor repository GitHub tersebut.
3. Pada konfigurasi project, gunakan root directory repository (folder yang berisi `app.py`). Biarkan **Build Command** dan **Output Directory** kosong/default; Vercel mendeteksi Flask dari `requirements.txt` dan `app.py`.
4. Buka **Environment Variables**, tambahkan `SECRET_KEY`, lalu isi dengan nilai acak. Buat nilai di PowerShell dengan:

   ```powershell
   py -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Jangan masukkan nilai rahasia itu ke GitHub.
5. Klik **Deploy**. Jika sudah berhasil, buka URL deployment lalu uji halaman utama, tambah transaksi, dan hapus transaksi.
6. Setiap kali mengubah kode, push ke branch GitHub yang terhubung; Vercel akan membuat deployment baru.

`vercel.json` sengaja tidak menambahkan rewrite khusus; route halaman dan API ditangani oleh aplikasi Flask.

## Catatan penyimpanan

Filesystem fungsi Vercel tidak persisten. Untuk mencegah error tulis di filesystem yang hanya-baca, aplikasi memakai SQLite di `/tmp` saat berjalan di Vercel. Data di sana hanya sementara dan bisa hilang atau berbeda antar-instance; jangan gunakan deployment ini sebagai penyimpanan transaksi permanen. Untuk penggunaan sungguhan, ganti SQLite dengan database terkelola yang persisten.
