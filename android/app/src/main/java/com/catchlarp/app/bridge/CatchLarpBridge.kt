package com.catchlarp.app.bridge

import android.content.ClipboardManager
import android.content.Context
import android.webkit.JavascriptInterface
import com.catchlarp.app.BuildConfig
import com.catchlarp.app.data.ServerPreferences
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
    private val ioExecutor: ExecutorService,
    private val onConnectCompleted: (String) -> Unit,
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
