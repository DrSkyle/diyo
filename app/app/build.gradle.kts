plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "np.devilabs.diyo"
    compileSdk = 35

    defaultConfig {
        applicationId = "np.devilabs.diyo"
        minSdk = 28          // Android 9 — the Diyo floor (docs/DECISIONS.md D9)
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-stage0"
    }

    buildFeatures {
        buildConfig = true
        compose = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

// Gate 10 from docs/QUALITY.md: the build fails if a network call exists outside NetSearch.kt.
val networkDiscipline by tasks.registering {
    val src = layout.projectDirectory.dir("src/main/java")
    doLast {
        val offenders = mutableListOf<String>()
        val forbidden = listOf("java.net.", "HttpURLConnection", "okhttp3", "URL(")
        src.asFile.walkTopDown().filter { it.isFile && it.extension in setOf("kt", "java") }
            .forEach { file ->
                if (file.name == "NetSearch.kt") return@forEach
                file.readText().lines().forEachIndexed { i, line ->
                    if (forbidden.any { it in line }) {
                        offenders.add("${file.relativeTo(src.asFile)}:${i + 1}: ${line.trim()}")
                    }
                }
            }
        if (offenders.isNotEmpty()) {
            throw GradleException(
                "Network code outside NetSearch.kt:\n" + offenders.joinToString("\n"))
        }
        println("network discipline: ok")
    }
}

tasks.named("preBuild") { dependsOn(networkDiscipline) }

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
}
