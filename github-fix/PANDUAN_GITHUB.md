# Panduan GitHub Actions — Image Enhancer APK

## Kenapa Build Gagal Sebelumnya?

Masalah paling umum ada **dua penyebab utama**:

| Penyebab | Gejala di log Actions |
|---|---|
| OpenCV SDK tidak ada di repo (terlalu besar untuk di-commit) | `Could not resolve project :opencv` atau `Module not found` |
| `gradlew` tidak punya izin eksekusi di Linux | `Permission denied: ./gradlew` |

Solusi di panduan ini mengatasi keduanya.

---

## Perubahan yang Perlu Dilakukan di Repo Kamu

### File yang harus DIGANTI (timpa file lama):

```
settings.gradle.kts       ← hapus include(":opencv")
app/build.gradle.kts      ← ganti ke OpenCV Maven dependency
app/src/main/java/.../MainActivity.kt  ← initLocal() bukan initAsync()
.gitignore                ← pastikan folder opencv/ tidak ter-commit
```

### File yang harus DIBUAT:

```
.github/workflows/build.yml   ← workflow GitHub Actions
```

---

## LANGKAH 1 — Ganti ke OpenCV Maven Dependency

**Buka `settings.gradle.kts`**, pastikan isinya seperti ini:

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "ImageEnhancer"
include(":app")
// TIDAK ADA include(":opencv") di sini
```

**Buka `app/build.gradle.kts`**, ganti bagian dependencies:

```kotlin
dependencies {
    // OpenCV via Maven — GitHub Actions bisa download otomatis
    implementation("org.opencv:opencv:4.9.0")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.activity:activity-ktx:1.9.3")
}
```

---

## LANGKAH 2 — Buat Workflow File

Buat folder dan file berikut di root repo:

```
.github/
└── workflows/
    └── build.yml
```

Isi `build.yml` (gunakan file yang disertakan di zip):

```yaml
name: Build Android APK

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: gradle

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Cache Gradle packages
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
          restore-keys: |
            ${{ runner.os }}-gradle-

      - name: Build Debug APK
        run: ./gradlew assembleDebug --stacktrace

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: app-debug
          path: app/build/outputs/apk/debug/app-debug.apk
          retention-days: 7
```

---

## LANGKAH 3 — Pastikan gradlew Ada di Repo

Di terminal lokal (di folder project), cek:

```bash
ls -la gradlew
```

Jika file ada tapi belum di-commit, jalankan:

```bash
git add gradlew
git add gradle/wrapper/gradle-wrapper.properties
git add gradle/wrapper/gradle-wrapper.jar
git commit -m "add gradle wrapper"
git push
```

---

## LANGKAH 4 — Hapus Folder opencv dari Repo (jika ada)

Jika folder `opencv/` sudah terlanjur di-commit ke repo:

```bash
# Hapus dari tracking Git (file fisik di lokal tidak ikut terhapus)
git rm -r --cached opencv/
git commit -m "remove opencv local module, switch to Maven"
git push
```

---

## LANGKAH 5 — Push Semua Perubahan

```bash
git add .
git commit -m "fix: switch OpenCV to Maven, add GitHub Actions workflow"
git push
```

Setelah push, buka tab **Actions** di GitHub — build akan berjalan otomatis.

---

## LANGKAH 6 — Download APK dari GitHub Actions

1. Buka repo di GitHub → tab **Actions**
2. Klik workflow run yang sudah selesai (centang hijau ✓)
3. Scroll ke bawah ke bagian **Artifacts**
4. Klik **app-debug** → file ZIP berisi APK akan terdownload

---

## Cek Cepat Jika Masih Gagal

Buka log Actions, cari baris merah pertama, lalu cocokkan:

| Pesan Error | Solusi |
|---|---|
| `Could not resolve org.opencv:opencv:4.9.0` | Tambahkan `mavenCentral()` di `settings.gradle.kts` |
| `Permission denied: ./gradlew` | Step `chmod +x gradlew` sudah ada di workflow |
| `Unsupported class file major version` | Ganti `java-version: '17'` di workflow |
| `Could not find com.android.application` | Versi AGP tidak cocok, update `libs.versions.toml` |
| `gradle-wrapper.jar not found` | Commit file `gradle/wrapper/gradle-wrapper.jar` ke repo |

---

## Struktur Repo yang Benar

```
repo-kamu/
├── .github/
│   └── workflows/
│       └── build.yml          ✓ wajib ada
├── app/
│   ├── build.gradle.kts       ✓ pakai OpenCV Maven
│   └── src/...
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar       ✓ wajib di-commit
│       └── gradle-wrapper.properties
├── gradlew                    ✓ wajib di-commit
├── gradlew.bat
├── settings.gradle.kts        ✓ tanpa include(":opencv")
└── .gitignore                 ✓ exclude folder opencv/
```
