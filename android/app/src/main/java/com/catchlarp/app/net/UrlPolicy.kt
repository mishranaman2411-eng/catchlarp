package com.catchlarp.app.net

import java.net.URI
import java.net.URISyntaxException

/** Pure URL validation, backend origin normalization, and Instagram Share-text extraction helpers. */
object UrlPolicy {
    private val REEL_EXTRACT_REGEX = Regex(
        """(?:https?://)?(?:www\.|m\.)?instagram\.com/(?:(?!(?:share|explore|accounts|stories|direct|about|developer|legal)/)[A-Za-z0-9._]+/)?(reel|reels|p)/([A-Za-z0-9_-]+)""",
        RegexOption.IGNORE_CASE,
    )

    private val SHARE_REDIRECT_REGEX = Regex(
        """(?:https?://)?(?:www\.|m\.)?instagram\.com/share/[^\s<>'"]+""",
        RegexOption.IGNORE_CASE,
    )

    private val IPV4_REGEX = Regex("""^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$""")

    fun isLoopbackOrEmulatorHost(host: String): Boolean {
        val h = host.trim().lowercase()
        return h == "10.0.2.2" || h == "localhost" || h == "127.0.0.1" || h == "::1" || h == "[::1]"
    }

    fun isPrivateLanHost(host: String): Boolean {
        val h = host.trim().lowercase()
        if (isLoopbackOrEmulatorHost(h) || h.endsWith(".local")) return true
        val match = IPV4_REGEX.matchEntire(h) ?: return false
        val octets = match.groupValues.drop(1).map { it.toIntOrNull() ?: return false }
        if (octets.any { it !in 0..255 }) return false
        return when {
            octets[0] == 10 -> true
            octets[0] == 192 && octets[1] == 168 -> true
            octets[0] == 172 && octets[1] in 16..31 -> true
            else -> false
        }
    }

    /**
     * Validate and normalize a CatchLARP backend base URL into canonical scheme://host[:port] form.
     * Release builds enforce HTTPS except for emulator/loopback addresses (10.0.2.2, localhost, 127.0.0.1).
     */
    fun normalizeBackendUrl(rawInput: String, allowInsecureLanHttp: Boolean): Result<String> {
        val trimmed = rawInput.trim()
        if (trimmed.isEmpty()) {
            return Result.failure(IllegalArgumentException("Enter your CatchLARP server URL."))
        }

        val withScheme = if ("://" in trimmed) {
            trimmed
        } else {
            val hostGuess = trimmed.substringBefore("/").substringBefore(":")
            val useHttp = isLoopbackOrEmulatorHost(hostGuess) ||
                (allowInsecureLanHttp && isPrivateLanHost(hostGuess))
            val defaultScheme = if (useHttp) "http://" else "https://"
            defaultScheme + trimmed
        }

        val parsed = try {
            URI(withScheme)
        } catch (_: URISyntaxException) {
            return Result.failure(IllegalArgumentException("Invalid URL syntax."))
        }

        val scheme = parsed.scheme?.lowercase()
        if (scheme != "https" && scheme != "http") {
            return Result.failure(IllegalArgumentException("Only https:// or local http:// server URLs are supported."))
        }
        if (parsed.rawUserInfo != null) {
            return Result.failure(IllegalArgumentException("Credentials embedded in server URLs are not allowed."))
        }

        val host = parsed.host?.lowercase()?.trim().orEmpty()
        if (host.isEmpty()) {
            return Result.failure(IllegalArgumentException("Server URL is missing a valid hostname."))
        }

        if (scheme == "http" && !isLoopbackOrEmulatorHost(host) && !(allowInsecureLanHttp && isPrivateLanHost(host))) {
            val hint = if (allowInsecureLanHttp) {
                "Use https:// for remote servers (http:// is allowed only for local LAN or 10.0.2.2)."
            } else {
                "Release builds require https:// for remote servers."
            }
            return Result.failure(IllegalArgumentException(hint))
        }

        val port = parsed.port
        if (port > 65535) {
            return Result.failure(IllegalArgumentException("Invalid server port."))
        }

        val portSuffix = when {
            port == -1 -> ""
            scheme == "https" && port == 443 -> ""
            scheme == "http" && port == 80 -> ""
            else -> ":$port"
        }

        return Result.success("$scheme://$host$portSuffix")
    }

    /** Extract and normalize an Instagram Reel or Post URL from shared text/deep link, or null. */
    fun extractInstagramReelUrl(rawText: String?): String? {
        if (rawText.isNullOrBlank()) return null
        val match = REEL_EXTRACT_REGEX.find(rawText) ?: return null
        val rawKind = match.groupValues[1].lowercase()
        val normalizedKind = if (rawKind == "p") "p" else "reel"
        val shortcode = match.groupValues[2]
        if (shortcode.isBlank()) return null
        return "https://www.instagram.com/$normalizedKind/$shortcode/"
    }

    fun containsUnsupportedShareRedirect(rawText: String?): Boolean {
        if (rawText.isNullOrBlank()) return false
        return SHARE_REDIRECT_REGEX.containsMatchIn(rawText) && extractInstagramReelUrl(rawText) == null
    }

    /** Strict origin comparison (scheme, host, effective port) for keeping WebView navigation scoped. */
    fun isSameOrigin(targetUrl: String, originUrl: String): Boolean {
        if (targetUrl.isBlank() || originUrl.isBlank()) return false
        return try {
            val target = URI(targetUrl)
            val origin = URI(originUrl)
            val tScheme = target.scheme?.lowercase() ?: return false
            val oScheme = origin.scheme?.lowercase() ?: return false
            val tHost = target.host?.lowercase() ?: return false
            val oHost = origin.host?.lowercase() ?: return false
            tScheme == oScheme && tHost == oHost && effectivePort(target, tScheme) == effectivePort(origin, oScheme)
        } catch (_: URISyntaxException) {
            false
        }
    }

    private fun effectivePort(uri: URI, scheme: String): Int {
        if (uri.port != -1) return uri.port
        return if (scheme == "https") 443 else 80
    }
}
