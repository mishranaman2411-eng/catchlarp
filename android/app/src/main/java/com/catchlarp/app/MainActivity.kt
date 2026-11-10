package com.catchlarp.app

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.graphics.Insets
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.catchlarp.app.auth.SessionTokenStore
import com.catchlarp.app.bridge.CatchLarpBridge
import com.catchlarp.app.data.ServerPreferences
import com.catchlarp.app.net.ServerProbe
import com.catchlarp.app.net.UrlPolicy
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * Main host activity for CatchLARP Android.
 * Combines edge-to-edge WebView presentation, Instagram Share Sheet handling,
 * external source Custom Tab opening, and an offline backend setup/recovery flow.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var rootContainer: View
    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var serverPrefs: ServerPreferences
    private lateinit var sessionStore: SessionTokenStore
    private lateinit var bridge: CatchLarpBridge

    private val ioExecutor = Executors.newSingleThreadExecutor()

    @Volatile
    private var pendingSharedReelUrl: String = ""

    @Volatile
    private var pendingConnectionError: String = ""

    @Volatile
    private var pendingErrorTargetUrl: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        rootContainer = findViewById(R.id.root_container)
        webView = findViewById(R.id.catchlarp_webview)
        progressBar = findViewById(R.id.page_progress_bar)
        serverPrefs = ServerPreferences(this)
        sessionStore = SessionTokenStore(this)

        applySystemBarAppearance(serverPrefs.isDarkTheme())
        setupWindowInsets()
        extractIncomingShareIntent(intent)
        setupBridge()
        setupWebView()
        setupBackNavigation()

        val targetBackend = serverPrefs.getBackendUrl()
        syncPublicSupabaseConfigInBackground(targetBackend)
        loadBackendRoot(targetBackend)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val capturedUrl = extractIncomingShareIntent(intent) ?: return
        val activeUrl = bridge.activePageUrl
        val backendUrl = serverPrefs.getBackendUrl()
        if (UrlPolicy.isSameOrigin(activeUrl, backendUrl)) {
            val quoted = JSONObject.quote(capturedUrl)
            webView.post {
                webView.evaluateJavascript("window.__catchLarpReceiveSharedUrl && window.__catchLarpReceiveSharedUrl($quoted);", null)
            }
        } else {
            loadBackendRoot(backendUrl)
        }
    }

    private fun syncPublicSupabaseConfigInBackground(backendUrl: String) {
        ioExecutor.execute {
            val probe = ServerProbe.probeBackend(backendUrl)
            if (probe.ok && probe.supabaseConfig != null) {
                serverPrefs.setSupabaseConfig(probe.supabaseConfig)
            }
        }
    }

    override fun onDestroy() {
        ioExecutor.shutdownNow()
        webView.removeJavascriptInterface(CatchLarpBridge.BRIDGE_NAME)
        webView.stopLoading()
        webView.destroy()
        super.onDestroy()
    }

    private fun setupWindowInsets() {
        ViewCompat.setOnApplyWindowInsetsListener(rootContainer) { view, windowInsets ->
            val insets: Insets = windowInsets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime()
            )
            view.setPadding(insets.left, insets.top, insets.right, insets.bottom)
            WindowInsetsCompat.CONSUMED
        }
    }

    private fun applySystemBarAppearance(isDark: Boolean) {
        val bgColor = Color.parseColor(if (isDark) "#070709" else "#F4F6F9")
        rootContainer.setBackgroundColor(bgColor)
        val controller = WindowInsetsControllerCompat(window, window.decorView)
        controller.isAppearanceLightStatusBars = !isDark
        controller.isAppearanceLightNavigationBars = !isDark
    }

    private fun setupBridge() {
        bridge = CatchLarpBridge(
            context = applicationContext,
            serverPrefs = serverPrefs,
            sessionStore = sessionStore,
            ioExecutor = ioExecutor,
            onConnectCompleted = { jsonPayload ->
                val quoted = JSONObject.quote(jsonPayload)
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        webView.evaluateJavascript("window.__catchLarpConnectResult && window.__catchLarpConnectResult($quoted);", null)
                    }
                }
            },
            onSupabaseAuthCompleted = { jsonPayload ->
                val quoted = JSONObject.quote(jsonPayload)
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        webView.evaluateJavascript("window.__catchLarpSupabaseAuthResult && window.__catchLarpSupabaseAuthResult($quoted);", null)
                    }
                }
            },
            onNavigateToBackend = { backendOrigin ->
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        pendingConnectionError = ""
                        pendingErrorTargetUrl = ""
                        loadBackendRoot(backendOrigin)
                    }
                }
            },
            onOpenServerSettings = {
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        pendingConnectionError = ""
                        pendingErrorTargetUrl = serverPrefs.getBackendUrl()
                        loadConnectPage("settings")
                    }
                }
            },
            onThemeUpdated = { isDark ->
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        applySystemBarAppearance(isDark)
                    }
                }
            },
            consumeSharedUrlCallback = {
                val url = pendingSharedReelUrl
                pendingSharedReelUrl = ""
                url
            },
            peekSharedUrlCallback = { pendingSharedReelUrl },
            getErrorStateCallback = {
                JSONObject()
                    .put("error", pendingConnectionError)
                    .put("targetUrl", pendingErrorTargetUrl)
                    .toString()
            },
        )
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            @Suppress("DEPRECATION")
            databaseEnabled = false
            allowFileAccess = false
            allowContentAccess = false
            @Suppress("DEPRECATION")
            allowFileAccessFromFileURLs = false
            @Suppress("DEPRECATION")
            allowUniversalAccessFromFileURLs = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            setSupportMultipleWindows(false)
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = false
            displayZoomControls = false
        }

        webView.setBackgroundColor(Color.TRANSPARENT)
        webView.addJavascriptInterface(bridge, CatchLarpBridge.BRIDGE_NAME)

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress in 1..99) {
                    progressBar.visibility = View.VISIBLE
                    progressBar.progress = newProgress
                } else {
                    progressBar.visibility = View.GONE
                }
            }
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                bridge.activePageUrl = url.orEmpty()
                super.onPageStarted(view, url, favicon)
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                bridge.activePageUrl = url.orEmpty()
                progressBar.visibility = View.GONE
                super.onPageFinished(view, url)
            }

            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val targetUri = request?.url ?: return false
                val target = targetUri.toString()
                val scheme = targetUri.scheme?.lowercase().orEmpty()

                if (target.startsWith(CatchLarpBridge.CONNECT_ASSET_URL)) {
                    return false
                }

                val savedOrigin = serverPrefs.getBackendUrl()
                if (savedOrigin.isNotEmpty() && UrlPolicy.isSameOrigin(target, savedOrigin)) {
                    return false
                }

                if (scheme == "https" || scheme == "http") {
                    openExternalUrl(targetUri)
                    return true
                }

                return true
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                if (request?.isForMainFrame == true) {
                    val failingUrl = request.url?.toString().orEmpty()
                    if (!failingUrl.startsWith(CatchLarpBridge.CONNECT_ASSET_URL)) {
                        val desc = error?.description?.toString()?.takeIf { it.isNotBlank() }
                            ?: "Unable to reach CatchLARP server."
                        pendingErrorTargetUrl = failingUrl
                        pendingConnectionError = "$desc (Wait ~30s if your free-tier Render service is waking up, then tap Retry.)"
                        loadConnectPage("error")
                    }
                }
            }

            override fun onReceivedHttpError(
                view: WebView?,
                request: WebResourceRequest?,
                errorResponse: WebResourceResponse?,
            ) {
                val statusCode = errorResponse?.statusCode ?: return
                if (request?.isForMainFrame == true && statusCode >= 500) {
                    val failingUrl = request.url?.toString().orEmpty()
                    if (!failingUrl.startsWith(CatchLarpBridge.CONNECT_ASSET_URL)) {
                        pendingErrorTargetUrl = failingUrl
                        pendingConnectionError = "Server returned HTTP $statusCode. Render free tier may be waking up from sleep."
                        loadConnectPage("error")
                    }
                }
            }
        }
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    val activeUrl = bridge.activePageUrl
                    val backendUrl = serverPrefs.getBackendUrl()
                    if (backendUrl.isNotEmpty() && UrlPolicy.isSameOrigin(activeUrl, backendUrl)) {
                        webView.evaluateJavascript("window.__catchLarpHandleBack ? window.__catchLarpHandleBack() : false;") { result ->
                            if (result == "true") {
                                return@evaluateJavascript
                            }
                            if (webView.canGoBack()) {
                                webView.goBack()
                            } else {
                                isEnabled = false
                                onBackPressedDispatcher.onBackPressed()
                            }
                        }
                    } else if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                    }
                }
            },
        )
    }

    private fun loadConnectPage(mode: String = "setup") {
        val url = "${CatchLarpBridge.CONNECT_ASSET_URL}?mode=$mode"
        bridge.activePageUrl = url
        webView.loadUrl(url)
    }

    private fun loadBackendRoot(backendOrigin: String) {
        val clean = backendOrigin.trimEnd('/') + "/"
        bridge.activePageUrl = clean
        webView.loadUrl(clean)
    }

    private fun openExternalUrl(uri: Uri) {
        val customTabExtras = Bundle().apply {
            putBinder("android.support.customtabs.extra.SESSION", null)
        }
        val customTabIntent = Intent(Intent.ACTION_VIEW, uri).apply {
            addCategory(Intent.CATEGORY_BROWSABLE)
            putExtras(customTabExtras)
            putExtra("android.support.customtabs.extra.TITLE_VISIBILITY", 1)
        }
        try {
            startActivity(customTabIntent)
        } catch (_: Exception) {
            Toast.makeText(this, "No browser installed to open citation link.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun extractIncomingShareIntent(incoming: Intent?): String? {
        if (incoming == null) return null
        val rawText = when (incoming.action) {
            Intent.ACTION_SEND -> incoming.getStringExtra(Intent.EXTRA_TEXT)
            Intent.ACTION_VIEW -> {
                val data = incoming.data
                data?.getQueryParameter("url") ?: data?.toString()
            }
            else -> null
        } ?: return null

        val extracted = UrlPolicy.extractInstagramReelUrl(rawText)
        if (extracted != null) {
            pendingSharedReelUrl = extracted
            return extracted
        }

        if (UrlPolicy.containsUnsupportedShareRedirect(rawText)) {
            Toast.makeText(
                this,
                "Instagram /share/ links cannot be parsed directly — paste the /reel/<id>/ URL.",
                Toast.LENGTH_LONG,
            ).show()
        }
        return null
    }
}
