package com.catchlarp.app.data

import android.content.Context
import com.catchlarp.app.AppConfig
import com.catchlarp.app.BuildConfig
import com.catchlarp.app.auth.SupabaseConfig
import com.catchlarp.app.net.UrlPolicy

/** Persists active CatchLARP Render backend origin, validated public Supabase config, and theme state. */
class ServerPreferences(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getBackendUrl(): String {
        val buildDefault = AppConfig.DEFAULT_BACKEND_URL
        if (BuildConfig.DEBUG) {
            val stored = prefs.getString(KEY_BACKEND_URL, null)?.trim().orEmpty()
            if (stored.isNotEmpty()) {
                val check = UrlPolicy.normalizeBackendUrl(stored, allowInsecureLanHttp = true)
                if (check.isSuccess) return check.getOrThrow()
            }
        }
        return buildDefault
    }

    fun setBackendUrl(normalizedOrigin: String) {
        prefs.edit().putString(KEY_BACKEND_URL, normalizedOrigin).apply()
    }

    fun clearBackendUrl() {
        prefs.edit().remove(KEY_BACKEND_URL).apply()
    }

    fun getSupabaseConfig(): SupabaseConfig? {
        val staticConfig = AppConfig.createStaticSupabaseConfig()
        if (staticConfig != null) return staticConfig

        val storedUrl = prefs.getString(KEY_SUPABASE_URL, null)
        val storedAnonKey = prefs.getString(KEY_SUPABASE_ANON_KEY, null)
        return SupabaseConfig.validate(
            storedUrl,
            storedAnonKey,
            allowInsecureLocalHttp = BuildConfig.DEBUG,
        ).getOrNull()
    }

    fun setSupabaseConfig(config: SupabaseConfig?) {
        if (config == null) {
            prefs.edit().remove(KEY_SUPABASE_URL).remove(KEY_SUPABASE_ANON_KEY).apply()
        } else {
            prefs.edit()
                .putString(KEY_SUPABASE_URL, config.supabaseUrl)
                .putString(KEY_SUPABASE_ANON_KEY, config.supabaseAnonKey)
                .apply()
        }
    }

    fun isDarkTheme(): Boolean = prefs.getBoolean(KEY_DARK_THEME, true)

    fun setDarkTheme(isDark: Boolean) {
        prefs.edit().putBoolean(KEY_DARK_THEME, isDark).apply()
    }

    private companion object {
        const val PREFS_NAME = "catchlarp_prefs"
        const val KEY_BACKEND_URL = "backend_url"
        const val KEY_SUPABASE_URL = "supabase_url"
        const val KEY_SUPABASE_ANON_KEY = "supabase_anon_key"
        const val KEY_DARK_THEME = "dark_theme"
    }
}
