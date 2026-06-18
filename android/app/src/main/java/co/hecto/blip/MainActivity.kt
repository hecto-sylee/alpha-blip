package co.hecto.blip

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

/**
 * WebView host for the blip SPA.
 *
 * 05_android_and_demo.md requirements:
 *  - javaScriptEnabled, domStorageEnabled(localStorage),
 *    mediaPlaybackRequiresUserGesture=false
 *  - server URL from SharedPreferences (set in SettingsActivity)
 *  - camera/mic via WebChromeClient.onPermissionRequest -> grant()
 *  - geolocation via onGeolocationPermissionsShowPrompt -> allow + runtime perm
 *  - file chooser via onShowFileChooser
 *  - deep link app://join/{room_code} -> forwarded to the SPA (?join=code)
 *  - menu: reload / server settings
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var fileChooserCallback: ValueCallback<Array<Uri>>? = null

    companion object {
        const val PREFS = "blip_prefs"
        const val KEY_SERVER_URL = "server_url"
        private const val REQ_PERMS = 1001
        private const val REQ_FILE = 1002
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Request the runtime permissions up front so getUserMedia / Geolocation
        // can be granted instantly inside the WebView.
        requestRuntimePermissions()

        webView = findViewById(R.id.webview)
        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true                       // localStorage for guest token
            mediaPlaybackRequiresUserGesture = false       // MediaRecorder / autoplay
            allowFileAccess = true
            allowContentAccess = true
            setGeolocationEnabled(true)
        }

        webView.webViewClient = WebViewClient()
        webView.webChromeClient = object : WebChromeClient() {
            // Camera + microphone (getUserMedia)
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread { request.grant(request.resources) }
            }

            // HTML5 Geolocation
            override fun onGeolocationPermissionsShowPrompt(
                origin: String,
                callback: GeolocationPermissions.Callback
            ) {
                callback.invoke(origin, true, false)
            }

            // <input type="file"> (clip / photo selection)
            override fun onShowFileChooser(
                wv: WebView?,
                callback: ValueCallback<Array<Uri>>?,
                params: FileChooserParams?
            ): Boolean {
                fileChooserCallback?.onReceiveValue(null)
                fileChooserCallback = callback
                val intent = params?.createIntent() ?: return false
                return try {
                    startActivityForResult(intent, REQ_FILE)
                    true
                } catch (e: Exception) {
                    fileChooserCallback = null
                    false
                }
            }
        }

        loadStartUrl(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        loadStartUrl(intent)
    }

    /** Resolve server URL + optional deep-link join code, then load. */
    private fun loadStartUrl(intent: Intent?) {
        val base = serverUrl()
        if (base.isBlank()) {
            startActivity(Intent(this, SettingsActivity::class.java))
            return
        }
        val joinCode = extractJoinCode(intent)
        val url = if (joinCode != null) "$base/?join=$joinCode" else base
        webView.loadUrl(url)
    }

    /** app://join/{room_code} -> room_code */
    private fun extractJoinCode(intent: Intent?): String? {
        val data: Uri = intent?.data ?: return null
        if (data.scheme == "app" && data.host == "join") {
            return data.lastPathSegment ?: data.pathSegments.firstOrNull()
        }
        return null
    }

    private fun serverUrl(): String {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        return prefs.getString(KEY_SERVER_URL, "") ?: ""
    }

    private fun requestRuntimePermissions() {
        val needed = mutableListOf<String>()
        for (p in listOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO
        )) {
            if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                needed.add(p)
            }
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), REQ_PERMS)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_FILE) {
            val result = WebChromeClient.FileChooserParams.parseResult(resultCode, data)
            fileChooserCallback?.onReceiveValue(result)
            fileChooserCallback = null
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, 1, 0, getString(R.string.menu_reload))
        menu.add(0, 2, 1, getString(R.string.menu_settings))
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            1 -> { webView.reload(); true }
            2 -> { startActivity(Intent(this, SettingsActivity::class.java)); true }
            else -> super.onOptionsItemSelected(item)
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
}
