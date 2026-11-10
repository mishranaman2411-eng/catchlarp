package com.catchlarp.app.auth

import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

data class SupabaseSessionResult(
    val ok: Boolean,
    val accessToken: String? = null,
    val userId: String? = null,
    val email: String? = null,
    val errorMessage: String? = null,
)

/**
 * Lightweight Supabase GoTrue password sign-in client initialized strictly with
 * public [SupabaseConfig.supabaseUrl] and [SupabaseConfig.supabaseAnonKey].
 */
class SupabaseAuthClient(private val config: SupabaseConfig) {

    fun signInWithPassword(email: String, password: String): SupabaseSessionResult {
        val cleanEmail = email.trim()
        if (cleanEmail.isEmpty() || password.isEmpty()) {
            return SupabaseSessionResult(ok = false, errorMessage = "Email and password are required.")
        }

        val endpoint = URL("${config.supabaseUrl.trimEnd('/')}/auth/v1/token?grant_type=password")
        var connection: HttpURLConnection? = null
        return try {
            connection = (endpoint.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 10_000
                readTimeout = 15_000
                doOutput = true
                instanceFollowRedirects = false
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("apikey", config.supabaseAnonKey)
            }

            val payload = JSONObject()
                .put("email", cleanEmail)
                .put("password", password)
                .toString()
            connection.outputStream.use { out ->
                out.write(payload.toByteArray(Charsets.UTF_8))
            }

            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            parseSessionResponse(code, body)
        } catch (_: IOException) {
            SupabaseSessionResult(ok = false, errorMessage = "Network error contacting Supabase Auth.")
        } finally {
            connection?.disconnect()
        }
    }

    companion object {
        fun parseSessionResponse(statusCode: Int, responseBody: String): SupabaseSessionResult {
            val json = try {
                JSONObject(responseBody)
            } catch (_: JSONException) {
                return SupabaseSessionResult(
                    ok = false,
                    errorMessage = "Invalid response from Supabase Auth (HTTP $statusCode).",
                )
            }

            if (statusCode !in 200..299) {
                val msg = json.optString("error_description")
                    .ifBlank { json.optString("msg") }
                    .ifBlank { "Supabase sign-in failed (HTTP $statusCode)." }
                return SupabaseSessionResult(ok = false, errorMessage = msg)
            }

            val accessToken = json.optString("access_token", "").trim()
            if (accessToken.isEmpty()) {
                return SupabaseSessionResult(ok = false, errorMessage = "Supabase response did not include an access_token.")
            }

            val userObj = json.optJSONObject("user")
            return SupabaseSessionResult(
                ok = true,
                accessToken = accessToken,
                userId = userObj?.optString("id", "")?.takeIf { it.isNotBlank() },
                email = userObj?.optString("email", "")?.takeIf { it.isNotBlank() },
            )
        }
    }
}
