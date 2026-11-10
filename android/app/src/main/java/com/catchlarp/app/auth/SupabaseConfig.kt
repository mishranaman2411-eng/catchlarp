package com.catchlarp.app.auth

import com.catchlarp.app.net.UrlPolicy
import java.nio.charset.StandardCharsets
import java.util.Base64

/**
 * Validated public Supabase configuration for mobile authentication.
 * Strictly requires public SUPABASE_URL and public SUPABASE_ANON_KEY, and
 * refuses privileged service_role keys, admin keys, or signing secrets.
 */
data class SupabaseConfig(
    val supabaseUrl: String,
    val supabaseAnonKey: String,
) {
    companion object {
        private val BLOCKED_KEY_PREFIXES = listOf("sb_secret_", "gsk_", "AIza")
        private val PRIVILEGED_ROLES = setOf("service_role", "supabase_admin", "postgres", "authenticator")
        private val JWT_ROLE_REGEX = Regex(""""role"\s*:\s*"([^"]+)"""")

        fun isSafePublicAnonKey(candidate: String?): Boolean {
            val clean = candidate?.trim().orEmpty()
            if (clean.isEmpty()) return false
            if (BLOCKED_KEY_PREFIXES.any { clean.startsWith(it, ignoreCase = false) }) {
                return false
            }

            val segments = clean.split('.')
            if (segments.size == 3) {
                val role = extractJwtRoleClaim(segments[1]) ?: return false
                if (role in PRIVILEGED_ROLES) return false
                return role == "anon"
            }

            // Modern Supabase publishable keys use sb_publishable_...
            if (clean.startsWith("sb_publishable_")) {
                return true
            }

            return false
        }

        fun validate(
            rawUrl: String?,
            rawAnonKey: String?,
            allowInsecureLocalHttp: Boolean = false,
        ): Result<SupabaseConfig> {
            val urlCheck = UrlPolicy.normalizeBackendUrl(rawUrl.orEmpty(), allowInsecureLanHttp = allowInsecureLocalHttp)
            if (urlCheck.isFailure) {
                return Result.failure(IllegalArgumentException("Invalid public SUPABASE_URL."))
            }

            val cleanKey = rawAnonKey?.trim().orEmpty()
            if (!isSafePublicAnonKey(cleanKey)) {
                return Result.failure(
                    SecurityException(
                        "Invalid SUPABASE_ANON_KEY: only public anon or publishable keys are permitted on mobile.",
                    ),
                )
            }

            return Result.success(
                SupabaseConfig(
                    supabaseUrl = urlCheck.getOrThrow(),
                    supabaseAnonKey = cleanKey,
                ),
            )
        }

        private fun extractJwtRoleClaim(payloadSegment: String): String? {
            return try {
                val padded = when (payloadSegment.length % 4) {
                    2 -> "$payloadSegment=="
                    3 -> "$payloadSegment="
                    else -> payloadSegment
                }
                val decoded = Base64.getUrlDecoder().decode(padded)
                val rawJson = String(decoded, StandardCharsets.UTF_8)
                JWT_ROLE_REGEX.find(rawJson)?.groupValues?.getOrNull(1)?.trim()?.lowercase()
            } catch (_: Exception) {
                null
            }
        }
    }
}
