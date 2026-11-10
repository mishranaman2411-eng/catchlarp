package com.catchlarp.app.auth

import android.content.Context

/** Persists the active user session access token (never backend secrets) for CatchLARP API calls. */
class SessionTokenStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    @Volatile
    private var cachedToken: String? = null

    fun getAccessToken(): String {
        val current = cachedToken
        if (current != null) return current
        val stored = prefs.getString(KEY_ACCESS_TOKEN, "")?.trim().orEmpty()
        cachedToken = stored
        return stored
    }

    fun setAccessToken(token: String?) {
        val clean = token?.trim().orEmpty()
        cachedToken = clean
        if (clean.isEmpty()) {
            prefs.edit().remove(KEY_ACCESS_TOKEN).apply()
        } else {
            prefs.edit().putString(KEY_ACCESS_TOKEN, clean).apply()
        }
    }

    fun clear() {
        cachedToken = ""
        prefs.edit().remove(KEY_ACCESS_TOKEN).apply()
    }

    private companion object {
        const val PREFS_NAME = "catchlarp_session"
        const val KEY_ACCESS_TOKEN = "supabase_access_token"
    }
}
