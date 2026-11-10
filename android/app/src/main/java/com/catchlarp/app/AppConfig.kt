package com.catchlarp.app

import com.catchlarp.app.auth.SupabaseConfig
import com.catchlarp.app.net.UrlPolicy

/**
 * Central Android client constants for the permanent Render backend and public Supabase config.
 * Contains strictly public client configuration — never backend JWT secrets or service-role/AI keys.
 */
object AppConfig {
    const val PRODUCTION_BACKEND_URL = "https://catchlarp.onrender.com"

    val DEFAULT_BACKEND_URL: String by lazy {
        UrlPolicy.normalizeBackendUrl(
            BuildConfig.DEFAULT_BACKEND_URL.ifBlank { PRODUCTION_BACKEND_URL },
            allowInsecureLanHttp = BuildConfig.DEBUG,
        ).getOrDefault(PRODUCTION_BACKEND_URL)
    }

    val PUBLIC_SUPABASE_URL: String
        get() = BuildConfig.SUPABASE_URL.trim()

    val PUBLIC_SUPABASE_ANON_KEY: String
        get() = BuildConfig.SUPABASE_ANON_KEY.trim()

    fun createStaticSupabaseConfig(): SupabaseConfig? {
        return SupabaseConfig.validate(
            PUBLIC_SUPABASE_URL,
            PUBLIC_SUPABASE_ANON_KEY,
            allowInsecureLocalHttp = BuildConfig.DEBUG,
        ).getOrNull()
    }
}
