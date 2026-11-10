package com.catchlarp.app.data

import android.content.Context
import com.catchlarp.app.BuildConfig
import com.catchlarp.app.net.UrlPolicy

/** Persists the configured CatchLARP FastAPI backend origin and theme state. */
class ServerPreferences(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getBackendUrl(): String {
        val stored = prefs.getString(KEY_BACKEND_URL, null)?.trim().orEmpty()
        if (stored.isNotEmpty()) {
            val check = UrlPolicy.normalizeBackendUrl(stored, allowInsecureLanHttp = BuildConfig.DEBUG)
            if (check.isSuccess) return check.getOrThrow()
        }

        val buildDefault = BuildConfig.DEFAULT_BACKEND_URL.trim()
        if (buildDefault.isNotEmpty()) {
            val check = UrlPolicy.normalizeBackendUrl(buildDefault, allowInsecureLanHttp = BuildConfig.DEBUG)
            if (check.isSuccess) return check.getOrThrow()
        }
        return ""
    }

    fun setBackendUrl(normalizedOrigin: String) {
        prefs.edit().putString(KEY_BACKEND_URL, normalizedOrigin).apply()
    }

    fun clearBackendUrl() {
        prefs.edit().remove(KEY_BACKEND_URL).apply()
    }

    fun isDarkTheme(): Boolean = prefs.getBoolean(KEY_DARK_THEME, true)

    fun setDarkTheme(isDark: Boolean) {
        prefs.edit().putBoolean(KEY_DARK_THEME, isDark).apply()
    }

    private companion object {
        const val PREFS_NAME = "catchlarp_prefs"
        const val KEY_BACKEND_URL = "backend_url"
        const val KEY_DARK_THEME = "dark_theme"
    }
}
