# QA Agent Bot - Dokumentasi 🤖📝

## 1. Pendahuluan

QA Agent Bot adalah asisten berbasis AI yang dirancang untuk membantu *Quality Assurance Engineers* dalam tugas sehari-hari, seperti membuat *test case* dari dokumen persyaratan (PRD) dan tugas terkait QA lainnya. Bot ini berjalan di Telegram dan didukung oleh model bahasa Google Gemini melalui LangChain.

---

## 2. Fitur Utama ✨

* **Pembuatan Test Case:** Mampu menghasilkan *test case* secara otomatis berdasarkan konteks (deskripsi atau teks dari PDF) yang diberikan.
* **Format Test Case Fleksibel:** Pengguna dapat memilih format output *test case*, yaitu:
    * **Steps:** Format langkah-langkah tradisional (Nama, Deskripsi, Prekondisi, Langkah, Hasil yang Diharapkan). Ini adalah format *default*.
    * **BDD:** Format *Behavior-Driven Development* menggunakan Gherkin (Feature, Scenario, Given, When, Then).
* **Manajemen Konteks:** Bot dapat menyimpan teks dari PRD atau dokumen lain sebagai "konteks aktif" untuk digunakan dalam pembuatan *test case* atau analisis lainnya.
* **Input Konteks:** Konteks dapat diatur melalui dua cara:
    * Menyalin dan menempelkan teks langsung ke bot menggunakan perintah `/set_context`.
    * Mengunggah file PDF langsung ke obrolan bot. Bot akan otomatis mengekstrak teksnya dan menjadikannya konteks aktif.
* **Interaksi Telegram:** Semua fitur dapat diakses melalui perintah sederhana di Telegram.

---

## 3. Referensi Perintah ⌨️

Berikut adalah daftar perintah yang tersedia:

| Perintah (Command)   | Deskripsi                                                                                                | Contoh Penggunaan / Argumen                                                                 |
| :------------------- | :------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| `/start`             | Memulai bot dan menampilkan pesan selamat datang.                                                        | `/start`                                                                                    |
| `/help`              | Menampilkan daftar perintah yang tersedia dan cara menggunanya.                                             | `/help`                                                                                     |
| `/set_context`       | Mengatur teks yang diberikan sebagai konteks PRD aktif. Ganti konteks sebelumnya jika ada.               | `/set_context [Tempel teks PRD atau deskripsi fitur di sini]`                               |
| `/show_context`      | Menampilkan sebagian awal dari teks konteks PRD yang sedang aktif saat ini.                               | `/show_context`                                                                             |
| `/clear_context`     | Menghapus konteks PRD yang sedang aktif dari memori bot.                                                  | `/clear_context`                                                                            |
| `/create_tc`         | Membuat *test case* berdasarkan konteks PRD yang aktif. Membutuhkan konteks yang sudah diatur sebelumnya. | `/create_tc` (Akan menggunakan format *steps* secara default)<br>`/create_tc steps`<br>`/create_tc bdd` |
| *(Upload PDF)* | Mengirim file PDF ke bot akan secara otomatis mengekstrak teksnya dan menjadikannya konteks aktif.        | Langsung kirim file PDF ke obrolan bot.                                                                     |

---

## 4. Cara Menggunakan

1.  **Mulai Bot:** Kirim `/start` ke bot di Telegram.
2.  **Atur Konteks:**
    * **Via Teks:** Kirim `/set_context` diikuti dengan teks PRD atau deskripsi fitur Anda.
    * **Via PDF:** Langsung kirim (upload) file PDF ke obrolan. Tunggu konfirmasi bahwa PDF berhasil diproses.
3.  **(Opsional) Cek Konteks:** Kirim `/show_context` untuk memastikan teks yang benar sudah tersimpan.
4.  **Buat Test Case:** Kirim `/create_tc` untuk format *steps* atau `/create_tc bdd` untuk format Gherkin.
5.  **(Opsional) Hapus Konteks:** Kirim `/clear_context` jika Anda ingin memulai dengan konteks baru.
6.  **Bantuan:** Kirim `/help` kapan saja untuk melihat daftar perintah.

---