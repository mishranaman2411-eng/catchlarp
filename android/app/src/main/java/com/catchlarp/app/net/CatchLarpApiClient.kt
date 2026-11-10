package com.catchlarp.app.net

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

data class ApiResponse(
    val statusCode: Int,
    val body: String,
    val ok: Boolean = statusCode in 200..299,
)

/**
 * Authenticated HTTP client for CatchLARP FastAPI endpoints.
 * Ensures all backend API requests attach `Authorization: Bearer <access_token>`.
 */
object CatchLarpApiClient {
    private const val CONNECT_TIMEOUT_MS = 10_000
    private const val READ_TIMEOUT_MS = 60_000

    fun buildBackendHeaders(
        accessToken: String?,
        extraHeaders: Map<String, String> = emptyMap(),
    ): Map<String, String> {
        val headers = linkedMapOf<String, String>()
        headers["Accept"] = "application/json"
        val cleanToken = accessToken?.trim().orEmpty()
        if (cleanToken.isNotEmpty()) {
            headers["Authorization"] = "Bearer $cleanToken"
        }
        for ((k, v) in extraHeaders) {
            headers[k] = v
        }
        return headers
    }

    fun request(
        backendOrigin: String,
        path: String,
        method: String = "GET",
        accessToken: String? = null,
        jsonBody: JSONObject? = null,
    ): ApiResponse {
        val cleanOrigin = backendOrigin.trimEnd('/')
        val cleanPath = if (path.startsWith("/")) path else "/$path"
        val url = URL("$cleanOrigin$cleanPath")

        var connection: HttpURLConnection? = null
        return try {
            connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = method
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                instanceFollowRedirects = false
                val extra = if (jsonBody != null) mapOf("Content-Type" to "application/json") else emptyMap()
                for ((k, v) in buildBackendHeaders(accessToken, extra)) {
                    setRequestProperty(k, v)
                }
                if (jsonBody != null) {
                    doOutput = true
                    outputStream.use { out ->
                        out.write(jsonBody.toString().toByteArray(Charsets.UTF_8))
                    }
                }
            }

            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            ApiResponse(statusCode = code, body = body)
        } catch (_: IOException) {
            ApiResponse(statusCode = 0, body = "{\"detail\":\"Network error contacting CatchLARP backend.\"}", ok = false)
        } finally {
            connection?.disconnect()
        }
    }
}
