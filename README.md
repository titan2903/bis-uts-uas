# bis-cakrawala-starter — Business Intelligence Systems (SDA2161)

Repo template untuk 9 tim. Satu repo per tim (`Use this template`), semua artefak dikerjakan **di
dalam sesi** dan dibuktikan lewat commit bertanggal sebelum 20:00.

## Setup 5 menit

```bash
pip install -r requirements.txt
python -m pipeline.profile --topic t3 --slice k1      # D1: profil data sebelum transformasi
python -m pipeline.load    --topic t3 --slice k1 --twice   # D3: load 2x, cek row count
python tests/run_tests.py  --topic t2 --slice k8      # D4 selesai: 6 quality test, PASS/FAIL + severity
python checkpoint.py verify --sesi 5 --topic t2 --slice k8 # DoD Tugas Sesi 5 — D4 test kualitas (t2/k8)
python checkpoint.py verify --sesi 8                  # DoD UTS (design checkpoint)
```

Semua perintah **offline** — data seed sudah ada di `data/raw/`, tidak ada unduhan saat lab.

## D4 individu selesai — T2/k8

Nama: **Titanio Yudista** · NIM: **24120500031**.

Slice k8 mencakup outlet A+B+C selama tahun 2025. Enam test mewakili completeness,
uniqueness, validity, consistency, timeliness, dan accuracy; masing-masing memiliki
severity dan satu baris alasan klasifikasi.

Berkas hasil dan bukti:

- [Laporan PDF D4](docs/D4_t2_k8_kualitas_data.pdf) — dua halaman, di bawah batas 10 MB, termasuk gambar bukti.
- [Laporan Markdown](docs/D4_t2_k8.md) — log, tafsir FAIL, grain, serta paragraf keputusan blocking/warning sepanjang 72 kata.
- [Definisi enam test](tests/test_definitions.yml).
- [Screenshot runner](images/run_test.png) dan [screenshot checkpoint](images/checkpoint.png).

Jalankan ulang setelah memasang dependensi:

```bash
python tests/run_tests.py --topic t2 --slice k8
python checkpoint.py verify --sesi 5 --topic t2 --slice k8
```

Runner tanpa argumen juga memakai T2/k8. YAML saat ini berisi enam test khusus slice
tersebut; topik atau slice lain memerlukan definisi test yang sesuai.

Hasil pada seed: **lima FAIL nyata dan satu PASS**, dengan empat FAIL berstatus
blocking dan satu FAIL berstatus warning. Tidak ada error SQL atau hasil yang berbeda
dari `expected`; checkpoint D4 memenuhi **6/6 syarat**. Runner menghasilkan **exit code
1** karena ada FAIL blocking, termasuk ketika FAIL tersebut memang diharapkan pada
seed. `expected: fail` mencatat cacat seed dan tidak membatalkan klasifikasi blocking.
Exit code 1 juga digunakan untuk error eksekusi atau hasil yang berbeda dari `expected`.

Test membaca data tanpa mengubah grain sumber. Timeliness menggunakan freshness per outlet terhadap tanggal tutup laporan
31 Desember 2025, dengan tanggal transaksi tercatat sebagai proksi. Batas ini merupakan
asumsi laporan tahunan; keterlambatan ingest tidak dapat diukur tanpa timestamp ingest.
Screenshot runner merekam versi awal test timeliness; log terbaru di laporan memakai
freshness per outlet dengan hitungan yang tetap sama.
Status selesai di bagian ini berlaku untuk tugas D4 individu; artefak D3, desain UTS,
dan tugas UAS memiliki checkpoint tersendiri.

## Tiga topik (dataset dari dosen, bukan pilihan sendiri)

| Topik | Folder | Slice |
|---|---|---|
| **T1** Kampus: Presensi & Kelulusan | `data/raw/t1_kampus/` | `--slice k4` (angkatan 2024) · `k5` (2023) · `k7` (2022) |
| **T2** POS UMKM Multi-Outlet | `data/raw/t2_umkm/` | `--slice k8` (outlet A+B+C, 12 bulan) · `k9` (outlet A, 6 bulan, scope −20%) |
| **T3** Cuaca Ekstrem per Desa (BMKG) | `data/raw/t3_publik/<slice>/` | `--slice k1` Kota Bogor · `k2` Kota Semarang · `k3` Kota Makassar · `k6` Kota Denpasar |

## Struktur

```
├── data/raw/            seed (jangan diubah; baca saja)
├── sql/
│   ├── 00_profiling.sql        DIBERIKAN — 6 query profil
│   ├── 10_dim_date.sql         DIBERIKAN — generator dimensi tanggal
│   ├── 20_dim_*.sql            TUGAS tim (D2) — DDL dimensi
│   ├── 30_fact_*.sql           TUGAS tim (D2) — DDL fact
│   ├── 40_analytics/q0N.sql    TUGAS tim (D5 + UTS item 4)
│   ├── 50_metrics/*.sql        TUGAS tim (D6) — satu berkas per metrik
│   └── load.sql                URUTAN EKSEKUSI tim (D3) — loader menolak jalan selama masih TODO
├── pipeline/
│   ├── profile.py       D1 + UTS item 3 (angka untuk test)
│   └── load.py          D3 — idempoten, `--twice`
├── tests/
│   ├── test_definitions.yml    TUGAS tim (D4 + UTS item 3)
│   └── run_tests.py            eksekutor, cetak PASS/FAIL + exit code
├── checkpoint.py        daftar cek DoD per sesi (design & build)
├── docs/                D0, D6, D7, D12 — template terisi contoh
└── warehouse/           hasil kerja: <topik>_<slice>.duckdb + fallback/
```

## Aturan yang dinilai

- **Idempotensi adalah syarat, bukan bonus.** `--twice` harus mencetak row count yang sama. Kalau tim mau membuktikan bahwa `INSERT` polos menggandakan baris, jalankan `--strategy insert_only` — itu contoh yang sengaja salah.
- **Test wajib punya severity.** `blocking` berarti data tidak boleh masuk warehouse; `warning` memberi peringatan. Runner D4 menghasilkan exit code 1 saat ada FAIL blocking. Definisi tanpa severity valid (`blocking`/`warning`) ditolak. Runner ini memverifikasi data sumber; penerapan gate pada loader merupakan pekerjaan pipeline tersendiri.
- **`WHERE 1=1` bukan test.** Test harus gagal ketika datanya salah, bukan ketika tabel kosong.
- **Desain dulu (UTS), bangun kemudian (UAS).** `checkpoint.py verify --sesi 8` untuk desain; `--sesi 4|5` untuk artefak build.

## Jalur penyelamat

`warehouse/fallback/<topik>_<slice>.duckdb` adalah warehouse yang **sudah jadi** untuk topikmu —
dipakai **hanya** kalau pipeline tim jebol di tengah sesi dan kamu butuh lanjut ke Sesi 9–10.
Catatan penting:

- **Tidak ada berkas `.sql` acuan di repo ini.** SQL lengkapnya tidak dibagikan; yang ada hanya
  hasil jadinya. Kalau kamu memakai fallback, itu menggantikan artefak D3-mu — katakan terus terang
  ke dosen, jangan mengaku sebagai hasil tim.
- Dosen menanyakan bagian mana pun dari artefak yang kamu kumpulkan. Yang tidak bisa dijelaskan
  bernilai 0 (RPS butir 5), dan fallback ini tidak bisa dijelaskan sebagai kerja tim.
