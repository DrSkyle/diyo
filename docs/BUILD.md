# Building Diyo

## Normal machine (x86_64 Linux, macOS, CI)

```sh
cd app
./gradlew assembleDebug
# app/app/build/outputs/apk/debug/app-debug.apk
```

CI does exactly this (`.github/workflows/build.yml`). Nothing else is required.

## ARM64 Linux (the current dev box)

Google ships **AAPT2 only as an x86_64 binary**. On an ARM64 Linux host the build dies with:

```
aapt2: 1: Syntax error: "(" unexpected
```

Fix: run AAPT2 under qemu with an x86_64 sysroot.

```sh
# 1. emulator
sudo apt-get install -y qemu-user-static

# 2. an x86_64 sysroot (the ARM ports archive has no amd64 packages)
python3 - <<'PY'
import gzip, urllib.request, re, subprocess, os
BASE="http://archive.ubuntu.com/ubuntu/"
want={"libc6","libstdc++6","libgcc-s1","zlib1g"}
found={}
for path in ["dists/noble/main/binary-amd64/Packages.gz",
             "dists/noble-updates/main/binary-amd64/Packages.gz",
             "dists/noble-security/main/binary-amd64/Packages.gz"]:
    data=gzip.decompress(urllib.request.urlopen(BASE+path).read()).decode()
    for st in data.split("\n\n"):
        p=re.search(r"^Package: (\S+)", st, re.M); f=re.search(r"^Filename: (\S+)", st, re.M)
        if p and f and p.group(1) in want and p.group(1) not in found:
            found[p.group(1)]=f.group(1)
root=os.path.expanduser("~/x86root"); os.makedirs(root, exist_ok=True)
for pkg, fn in found.items():
    out=f"/tmp/{pkg}.deb"
    urllib.request.urlretrieve(BASE+fn, out)
    subprocess.run(["dpkg-deb","-x",out,root], check=True)
PY
cd ~/x86root && ln -sfn usr/lib64 lib64 && ln -sfn usr/lib lib

# 3. wrapper — the filename must be exactly `aapt2`, AGP resolves the directory + "aapt2"
mkdir -p ~/bin && cat > ~/bin/aapt2 <<'SH'
#!/bin/sh
exec /usr/bin/qemu-x86_64-static -L "$HOME/x86root" "$HOME/Android/Sdk/build-tools/35.0.0/aapt2" "$@"
SH
chmod +x ~/bin/aapt2

# 4. build
cd app
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64 ./gradlew assembleDebug \
  -Pandroid.aapt2FromMavenOverride="$HOME/bin/aapt2"
```

Verified on this box: `aarch64`, JDK 17.0.21, SDK platform 35, build-tools 35.0.0, Gradle 8.9,
AGP 8.7.3, Kotlin 2.0.21. Build time ~15s, APK 2.3MB.

## Two build gates

| Gate | Where | Fails when |
|---|---|---|
| Network discipline | `app/app/build.gradle.kts` → `networkDiscipline` | any network API appears outside `NetSearch.kt` |
| Pipeline guarantees | `pipeline/test_pipeline.py` | consent, scope, QC or redaction breaks |

Run them directly:

```sh
cd app && ./gradlew :app:networkDiscipline
python3 pipeline/test_pipeline.py
```

## What is in the APK (stage 0)

One screen, zero permissions, zero network, no model. It exists to prove the toolchain and hold
the shape of the product. Everything real — assistant role, VAD, ASR, Diyo-1, voice — lands on top
of this shell.
