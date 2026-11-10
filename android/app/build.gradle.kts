import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

base {
    archivesName.set("CatchLARP-1.2.0")
}

android {
    namespace = "com.catchlarp.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.catchlarp.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.2.0"

        val configuredServerUrl = (project.findProperty("CATCHLARP_SERVER_URL") as String?)
            ?: System.getenv("CATCHLARP_SERVER_URL")
            ?: ""
        val escapedServerUrl = configuredServerUrl
            .trim()
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
        buildConfigField("String", "DEFAULT_BACKEND_URL", "\"$escapedServerUrl\"")
    }

    signingConfigs {
        val ksPath = System.getenv("CATCHLARP_KEYSTORE_PATH")?.trim().orEmpty()
        val ksPass = System.getenv("CATCHLARP_KEYSTORE_PASS").orEmpty()
        val ksAlias = System.getenv("CATCHLARP_KEY_ALIAS")?.trim().orEmpty()
        val ksKeyPass = System.getenv("CATCHLARP_KEY_PASS").orEmpty()
        if (ksPath.isNotEmpty() && ksPass.isNotEmpty() && ksAlias.isNotEmpty() && ksKeyPass.isNotEmpty() && file(ksPath).isFile) {
            create("release") {
                storeFile = file(ksPath)
                storePassword = ksPass
                keyAlias = ksAlias
                keyPassword = ksKeyPass
            }
        }
    }

    buildTypes {
        debug {
            isDebuggable = true
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfigs.findByName("release")?.let { releaseSigning ->
                signingConfig = releaseSigning
            }
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.17.0")
    implementation("androidx.core:core-splashscreen:1.2.0")
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("androidx.activity:activity-ktx:1.11.0")
    implementation("com.google.android.material:material:1.13.0")

    testImplementation("junit:junit:4.13.2")
}
