package com.catchlarp.app.bridge

import android.content.ClipboardManager
import android.content.Context
import android.webkit.JavascriptInterface
import com.catchlarp.app.BuildConfig
import com.catchlarp.app.auth.SessionTokenStore
import com.catchlarp.app.auth.SupabaseAuthClient
import com.catchlarp.app.auth.SupabaseConfig
import com.catchlarp.app.data.ServerPreferences
import com.catchlarp.app.net.CatchLarpApiClient
import com.catchlarp.app.net.ServerProbe
import com.catchlarp.app.net.UrlPolicy
import org.json.JSONObject
import java.util.concurrent.ExecutorService

/**
 * Origin-scoped JavaScript bridge between WebView UI and Android native functionality.
 */
class CatchLarpBridge(
    private val context: Context,
    private val serverPrefs: ServerPreferences,
    private val sessionStore: SessionTokenStore,
    private val ioExecutor: ExecutorService,
    private val onConnectCompleted: (String) -> Unit,
    private val onSupabaseAuthCompleted: (String) -> Unit,
    private val onNavigateToBackend: (String) -> Unit,
    private val onOpenServerSettings: () -> Unit,
    private val onThemeUpdated: (Boolean) -> Unit,
    private val consumeSharedUrlCallback: () -> String,
    private val peekSharedUrlCallback: () -> String,
    private val getErrorStateCallback: () -> String,
) {
    @Volatile
    var activePageUrl: String = ""

    private fun isOnConnectPage(): Boolean = activePageUrl.startsWith(CONNECT_ASSET_URL)

    private fun isOnTrustedBackend(): Boolean {
        val savedBackend = serverPrefs.getBackendUrl()
        return savedBackend.isNotEmpty() && UrlPolicy.isSameOrigin(activePageUrl, savedBackend)
    }

    @JavascriptInterface
    fun isDebugBuild(): Boolean = BuildConfig.DEBUG

    @JavascriptInterface
    fun getBackendUrl(): String {
        if (!isOnConnectPage() && !isOnTrustedBackend()) return ""
        return serverPrefs.getBackendUrl()
    }

    @JavascriptInterface
    fun getSupabaseConfigJson(): String {
        if (!isOnTrustedBackend()) return "{}"
        val cfg = serverPrefs.getSupabaseConfig() ?: return "{}"
        return JSONObject()
            .put("supabase_url", cfg.supabaseUrl)
            .put("supabase_anon_key", cfg.supabaseAnonKey)
            .toString()
    }

    @JavascriptInterface
    fun getAccessToken(): String {
        if (!isOnTrustedBackend()) return ""
        return sessionStore.getAccessToken()
    }

    @JavascriptInterface
    fun setAccessToken(token: String?) {
        if (!isOnTrustedBackend()) return
        sessionStore.setAccessToken(token)
    }

    @JavascriptInterface
    fun signInWithSupabase(email: String, password: String) {
        if (!isOnTrustedBackend()) return
        val cfg = serverPrefs.getSupabaseConfig()
        val backendUrl = serverPrefs.getBackendUrl()
        if (cfg == null) {
            val payload = JSONObject()
                .put("ok", false)
                .put("error", "Public Supabase URL / Anon key is not configured.")
                .toString()
            onSupabaseAuthCompleted(payload)
            return
        }

        ioExecutor.execute {
            val sbResult = SupabaseAuthClient(cfg).signInWithPassword(email, password)
            if (!sbResult.ok || sbResult.accessToken.isNullOrBlank()) {
                val payload = JSONObject()
                    .put("ok", false)
                    .put("error", sbResult.errorMessage ?: "Supabase sign-in failed.")
                    .toString()
                onSupabaseAuthCompleted(payload)
                return@execute
            }

            val accessToken = sbResult.accessToken
            // Verify token cleanly against backend /api/auth/me with Authorization: Bearer <token>
            if (backendUrl.isNotEmpty()) {
                val meResp = CatchLarpApiClient.request(
                    backendOrigin = backendUrl,
                    path = "/api/auth/me",
                    method = "GET",
                    accessToken = accessToken,
                )
                if (!meResp.ok) {
                    val detail = try {
                        JSONObject(meResp.body).optString("detail", "")
                    } catch (_: Exception) {
                        ""
                    }.ifBlank { "Backend rejected session token (HTTP ${meResp.statusCode})." }
                    val payload = JSONObject()
                        .put("ok", false)
                        .put("error", detail)
                        .toString()
                    onSupabaseAuthCompleted(payload)
                    return@execute
                }
            }

            sessionStore.setAccessToken(accessToken)
            val payload = JSONObject()
                .put("ok", true)
                .put("access_token", accessToken)
                .put("email", sbResult.email ?: email.trim())
                .toString()
            onSupabaseAuthCompleted(payload)
        }
    }

    @JavascriptInterface
    fun peekPendingSharedUrl(): String {
        if (!isOnConnectPage() && !isOnTrustedBackend()) return ""
        return peekSharedUrlCallback()
    }

    @JavascriptInterface
    fun consumePendingSharedUrl(): String {
        if (!isOnTrustedBackend()) return ""
        return consumeSharedUrlCallback()
    }

    @JavascriptInterface
    fun getPendingErrorStateJson(): String {
        if (!isOnConnectPage()) return "{}"
        return getErrorStateCallback()
    }

    @JavascriptInterface
    fun openServerSettings() {
        if (!isOnTrustedBackend()) return
        onOpenServerSettings()
    }

    @JavascriptInterface
    fun onThemeChanged(isDark: Boolean) {
        if (!isOnConnectPage() && !isOnTrustedBackend()) return
        serverPrefs.setDarkTheme(isDark)
        onThemeUpdated(isDark)
    }

    @JavascriptInterface
    fun readClipboard(): String {
        if (!isOnTrustedBackend()) return ""
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return ""
        val clip = clipboard.primaryClip ?: return ""
        if (clip.itemCount == 0) return ""
        return clip.getItemAt(0)?.coerceToText(context)?.toString()?.trim().orEmpty()
    }

    @JavascriptInterface
    fun useSavedServer() {
        if (!isOnConnectPage()) return
        val saved = serverPrefs.getBackendUrl()
        if (saved.isNotEmpty()) {
            onNavigateToBackend(saved)
        }
    }

    @JavascriptInterface
    fun testAndConnect(rawUrl: String) {
        if (!isOnConnectPage()) return
        val normalizedResult = UrlPolicy.normalizeBackendUrl(rawUrl, allowInsecureLanHttp = BuildConfig.DEBUG)
        normalizedResult.onFailure { err ->
            val payload = JSONObject()
                .put("ok", false)
                .put("error", err.message ?: "Invalid server URL.")
                .toString()
            onConnectCompleted(payload)
            return
        }

        val cleanUrl = normalizedResult.getOrThrow()
        ioExecutor.execute {
            val probe = ServerProbe.probeBackend(cleanUrl)
            if (probe.ok) {
                serverPrefs.setBackendUrl(probe.baseUrl)
                if (probe.supabaseConfig != null) {
                    serverPrefs.setSupabaseConfig(probe.supabaseConfig)
                }
                val payload = JSONObject()
                    .put("ok", true)
                    .put("url", probe.baseUrl)
                    .put("daily_limit", probe.dailyLimit ?: 20)
                    .toString()
                onConnectCompleted(payload)
                onNavigateToBackend(probe.baseUrl)
            } else {
                val payload = JSONObject()
                    .put("ok", false)
                    .put("url", cleanUrl)
                    .put("error", probe.errorMessage ?: "Unable to connect to CatchLARP server.")
                    .toString()
                onConnectCompleted(payload)
            }
        }
    }

    companion object {
        const val BRIDGE_NAME = "CatchLarpAndroid"
        const val CONNECT_ASSET_URL = "file:///android_asset/connect.html"
    }
}
