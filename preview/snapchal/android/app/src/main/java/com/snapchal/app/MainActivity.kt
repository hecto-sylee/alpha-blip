package com.snapchal.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.webkit.*
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var uploadMessage: ValueCallback<Array<Uri>>? = null
    private val FILE_CHOOSER_REQUEST = 1
    private val PERMISSION_REQUEST = 2

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        setupWebView()

        // 서버 URL 로드 (저장된 URL 또는 기본값)
        val prefs = getSharedPreferences("snapchal_prefs", MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", "http://localhost:8000") ?: "http://localhost:8000"

        // 딥링크 처리
        val deepLinkData = intent?.data
        if (deepLinkData != null && deepLinkData.scheme == "snapchal") {
            val code = deepLinkData.lastPathSegment
            webView.loadUrl("$serverUrl?join_code=$code")
        } else {
            webView.loadUrl(serverUrl)
        }

        // 권한 요청
        requestPermissions()
    }

    private fun setupWebView() {
        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.allowFileAccess = true
        settings.mediaPlaybackRequiresUserGesture = false
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.setSupportZoom(false)
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // 혼합 콘텐츠 허용 (http 서버 접속)
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW

        webView.webChromeClient = object : WebChromeClient() {
            // 카메라/마이크 권한 요청
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    request.grant(request.resources)
                }
            }

            // 파일 업로드 처리
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>,
                fileChooserParams: FileChooserParams
            ): Boolean {
                uploadMessage?.onReceiveValue(null)
                uploadMessage = filePathCallback
                val intent = fileChooserParams.createIntent()
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST)
                } catch (e: Exception) {
                    uploadMessage = null
                    return false
                }
                return true
            }
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    showServerError()
                }
            }
        }

        // JavaScript 인터페이스
        webView.addJavascriptInterface(AndroidBridge(this), "AndroidBridge")
    }

    private fun showServerError() {
        runOnUiThread {
            val html = """
                <html><body style="background:#fdf8f3;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column;text-align:center;padding:32px;">
                <div style="font-size:48px;margin-bottom:16px;">📡</div>
                <div style="font-size:20px;font-weight:bold;color:#2d2d2d;margin-bottom:8px;">서버에 연결할 수 없어요</div>
                <div style="color:#9e9e9e;margin-bottom:32px;font-size:14px;">서버가 실행 중인지 확인하고<br>설정에서 서버 주소를 확인해주세요</div>
                <button onclick="location.reload()" style="background:#ff7043;color:#fff;border:none;padding:14px 32px;border-radius:16px;font-size:16px;font-weight:bold;cursor:pointer;">다시 시도</button>
                <button onclick="AndroidBridge.openSettings()" style="background:transparent;color:#ff7043;border:2px solid #ff7043;padding:12px 24px;border-radius:16px;font-size:14px;cursor:pointer;margin-top:12px;">서버 주소 설정</button>
                </body></html>
            """.trimIndent()
            webView.loadData(html, "text/html", "UTF-8")
        }
    }

    private fun requestPermissions() {
        val permissions = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO
        )
        val needed = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), PERMISSION_REQUEST)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == FILE_CHOOSER_REQUEST) {
            uploadMessage?.onReceiveValue(
                WebChromeClient.FileChooserParams.parseResult(resultCode, data)
            )
            uploadMessage = null
        }
        super.onActivityResult(requestCode, resultCode, data)
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                startActivity(Intent(this, ServerSettingsActivity::class.java))
                true
            }
            R.id.action_reload -> {
                webView.reload()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    // 설정 화면에서 돌아올 때 URL 재로드
    override fun onResume() {
        super.onResume()
        val prefs = getSharedPreferences("snapchal_prefs", MODE_PRIVATE)
        val savedUrl = prefs.getString("server_url", null)
        if (savedUrl != null && webView.url?.startsWith(savedUrl) == false &&
            !webView.url.orEmpty().contains("localhost") && !webView.url.orEmpty().contains("ngrok")
        ) {
            webView.loadUrl(savedUrl)
        }
    }
}

class AndroidBridge(private val activity: MainActivity) {
    @JavascriptInterface
    fun openSettings() {
        activity.runOnUiThread {
            activity.startActivity(Intent(activity, ServerSettingsActivity::class.java))
        }
    }

    @JavascriptInterface
    fun showToast(message: String) {
        activity.runOnUiThread {
            Toast.makeText(activity, message, Toast.LENGTH_SHORT).show()
        }
    }
}
