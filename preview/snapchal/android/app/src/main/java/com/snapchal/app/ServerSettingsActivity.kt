package com.snapchal.app

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class ServerSettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_server_settings)

        supportActionBar?.title = "서버 주소 설정"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val prefs = getSharedPreferences("snapchal_prefs", MODE_PRIVATE)
        val etUrl = findViewById<EditText>(R.id.etServerUrl)
        val btnSave = findViewById<Button>(R.id.btnSave)

        val currentUrl = prefs.getString("server_url", "https://xxxx.ngrok-free.app")
        etUrl.setText(currentUrl)

        btnSave.setOnClickListener {
            val url = etUrl.text.toString().trim().trimEnd('/')
            if (url.isEmpty()) {
                Toast.makeText(this, "URL을 입력해주세요", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            prefs.edit().putString("server_url", url).apply()
            Toast.makeText(this, "저장됨! 앱이 재로드돼요.", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }
}
