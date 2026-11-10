package com.catchlarp.app.net

import com.catchlarp.app.BuildConfig
import com.catchlarp.app.auth.SupabaseConfig
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import javax.net.ssl.SSLException

/** Health check result returned by [ServerProbe.probeBackend]. */
data class ProbeResult(
    val ok: Boolean,
    val baseUrl: String,
    val dailyLimit: Int? = null,
    val supabaseConfig: SupabaseConfig? = null,
    val errorMessage: String? = null,
)

/** Verifies that a user-supplied URL points to a live CatchLARP FastAPI server. */
object ServerProbe {
    private const val CONNECT_TIMEOUT_MS = 8_000
    private const val READ_TIMEOUT_MS = 15_000
    private const val MAX_RESPONSE_BYTES = 64 * 1024

    fun probeBackend(baseUrl: String): ProbeResult {
        val cleanBase = baseUrl.trimEnd('/')
        var connection: HttpURLConnection? = null
        return try {
            val endpoint = URL("$cleanBase/api/auth/config")
            connection = (endpoint.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                instanceFollowRedirects = false
                setRequestProperty("Accept", "application/json")
            }

            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.use { input ->
                val buffer = ByteArray(MAX_RESPONSE_BYTES)
                val read = input.read(buffer)
                if (read > 0) String(buffer, 0, read, Charsets.UTF_8) else ""
            }.orEmpty()

            if (code == 502 || code == 503 || code == 504) {
                return ProbeResult(
                    ok = false,
                    baseUrl = cleanBase,
                    errorMessage = "Server is waking up or unavailable (HTTP $code). If using Render free tier, wait 20–30s and retry.",
                )
            }
            if (code != 200) {
                return ProbeResult(
                    ok = false,
                    baseUrl = cleanBase,
                    errorMessage = "Server responded with HTTP $code at /api/auth/config.",
                )
            }

            val json = JSONObject(body)
            if (!json.has("daily_limit")) {
                return ProbeResult(
                    ok = false,
                    baseUrl = cleanBase,
                    errorMessage = "Reachable host did not identify as a CatchLARP FastAPI backend.",
                )
            }

            val sbConfig = SupabaseConfig.validate(
                json.optString("supabase_url", ""),
                json.optString("supabase_anon_key", ""),
                allowInsecureLocalHttp = BuildConfig.DEBUG,
            ).getOrNull()

            ProbeResult(
                ok = true,
                baseUrl = cleanBase,
                dailyLimit = json.optInt("daily_limit", 20),
                supabaseConfig = sbConfig,
            )
        } catch (_: UnknownHostException) {
            ProbeResult(false, cleanBase, errorMessage = "Host not found. Check the URL spelling and your network connection.")
        } catch (_: SocketTimeoutException) {
            ProbeResult(false, cleanBase, errorMessage = "Connection timed out. Render free-tier instances can take ~30s on cold start — tap Retry.")
        } catch (_: ConnectException) {
            ProbeResult(false, cleanBase, errorMessage = "Connection refused. Ensure the FastAPI server is running and bound to 0.0.0.0.")
        } catch (_: SSLException) {
            ProbeResult(false, cleanBase, errorMessage = "TLS/SSL handshake failed for $cleanBase.")
        } catch (_: JSONException) {
            ProbeResult(false, cleanBase, errorMessage = "Invalid JSON response from /api/auth/config.")
        } catch (_: IOException) {
            ProbeResult(false, cleanBase, errorMessage = "Network error while verifying CatchLARP backend.")
        } finally {
            connection?.disconnect()
        }
    }
}
