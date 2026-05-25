# Image Enhancer — Android APK
## UAS Pengolahan Citra Digital
### Metode: Laplacian Filter + CLAHE

---

## PANDUAN SETUP LENGKAP (Step by Step)

### LANGKAH 1 — Install Tools yang Dibutuhkan

1. Download & install **Android Studio** dari https://developer.android.com/studio
2. Saat instalasi Android Studio, pastikan centang:
   - Android SDK
   - Android SDK Platform
   - Android Virtual Device (AVD)

---

### LANGKAH 2 — Download OpenCV Android SDK

1. Buka https://opencv.org/releases/
2. Pilih versi **OpenCV 4.9.0** (atau terbaru)
3. Klik **Android** → download file zip (±250MB)
4. Ekstrak zip ke folder mudah dijangkau, contoh: `C:/opencv-android/`

---

### LANGKAH 3 — Buat Project Baru di Android Studio

1. Buka Android Studio → **New Project**
2. Pilih template: **Empty Views Activity**
3. Isi:
   - Name: `ImageEnhancer`
   - Package name: `com.example.imageenhancer`
   - Save location: (pilih folder)
   - Language: **Kotlin**
   - Minimum SDK: **API 24 (Android 7.0)**
4. Klik **Finish**

---

### LANGKAH 4 — Import OpenCV sebagai Module

1. Di Android Studio: **File → New → Import Module**
2. Source directory: arahkan ke folder hasil ekstrak OpenCV,
   masuk ke subfolder: `opencv-android-sdk/sdk/`
3. Module name: biarkan default (`:opencv`) → **Finish**
4. Tunggu Gradle sync selesai

---

### LANGKAH 5 — Tambah Dependency OpenCV di app/build.gradle.kts

Buka file `app/build.gradle.kts`, di bagian `dependencies` tambahkan:

```kotlin
implementation(project(":opencv"))
```

Juga buka `settings.gradle.kts` dan pastikan ada:

```kotlin
include(":app")
include(":opencv")
```

Lalu klik **Sync Now** di banner atas.

---

### LANGKAH 6 — Salin File Kode dari Proyek Ini

Salin file-file berikut ke project Android Studio Anda:

| File sumber | Tujuan di project |
|---|---|
| `MainActivity.kt` | `app/src/main/java/com/example/imageenhancer/` |
| `activity_main.xml` | `app/src/main/res/layout/` |
| `AndroidManifest.xml` | `app/src/main/` (timpa yang lama) |
| `colors.xml` | `app/src/main/res/values/` |
| `file_paths.xml` | `app/src/main/res/xml/` (buat folder xml jika belum ada) |

---

### LANGKAH 7 — Buat Drawable Placeholder (Opsional)

Buat file `app/src/main/res/drawable/image_placeholder_bg.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="#E3E8EF"/>
    <corners android:radius="8dp"/>
    <stroke android:width="1dp" android:color="#C5CDD8"/>
</shape>
```

---

### LANGKAH 8 — Build & Jalankan APK

#### Jalankan di Emulator:
1. **Tools → AVD Manager → Create Virtual Device**
2. Pilih Pixel 6 → Next → pilih API 34 → Finish
3. Klik tombol ▶ (Run) di toolbar

#### Generate APK untuk perangkat nyata:
1. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
2. APK ada di: `app/build/outputs/apk/debug/app-debug.apk`
3. Transfer APK ke HP → install (aktifkan "Install dari sumber tidak dikenal")

---

## CARA KERJA APLIKASI

### Alur Penggunaan:
1. Buka aplikasi
2. Pilih gambar dari **Galeri** atau ambil dengan **Kamera**
3. Pilih metode:
   - **Laplacian Filter** → untuk gambar yang blur/buram
   - **CLAHE** → untuk gambar yang gelap/low-light
4. Geser **slider intensitas** untuk mengatur kekuatan efek
5. Klik **Simpan** untuk menyimpan hasil ke galeri

---

## PENJELASAN TEKNIS METODE

### Laplacian Filter (Perbaikan Blur)
```
output = original − k × Laplacian(original)
```
- Menghitung turunan kedua citra (operator Laplacian)
- Mendeteksi tepi/perubahan intensitas piksel
- Hasilnya dikurangkan dari citra asli → efek sharpening
- Didahului Gaussian Blur untuk meredam noise
- PSNR: ~23.78 dB | SSIM: ~0.938

### CLAHE (Perbaikan Low-Light)
```
Konversi BGR → Lab → CLAHE pada L → Gabungkan → BGR
```
- Konversi ke ruang warna Lab (L=luminance, a+b=warna)
- CLAHE diterapkan hanya pada channel L
- Histogram equalization per blok kecil (8×8 tile)
- clipLimit mencegah amplifikasi noise berlebihan
- Warna asli tetap terjaga karena a dan b tidak diubah

---

## TROUBLESHOOTING

| Masalah | Solusi |
|---|---|
| "OpenCV gagal dimuat" | Pastikan OpenCV module sudah di-import dengan benar |
| Gradle sync error | File → Invalidate Caches → Restart |
| APK tidak bisa diinstall | Aktifkan "Install unknown apps" di Setting HP |
| Crash saat buka kamera | Pastikan izin kamera sudah diberikan di Setting HP |
| Gambar tidak muncul setelah proses | Gambar terlalu besar, coba resize dulu |

---

## STRUKTUR PROJECT

```
ImageEnhancer/
├── app/
│   ├── src/main/
│   │   ├── java/com/example/imageenhancer/
│   │   │   └── MainActivity.kt          ← Logika utama + implementasi metode
│   │   ├── res/
│   │   │   ├── layout/activity_main.xml ← Tampilan UI
│   │   │   ├── values/colors.xml        ← Warna tema
│   │   │   └── xml/file_paths.xml       ← Konfigurasi FileProvider
│   │   └── AndroidManifest.xml          ← Izin & konfigurasi app
│   └── build.gradle.kts                 ← Dependency
├── opencv/                              ← Module OpenCV (setelah import)
└── settings.gradle.kts
```
