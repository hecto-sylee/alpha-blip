package co.hecto.blip

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

/**
 * Lets the demo operator paste the ngrok URL. Stored in SharedPreferences and
 * read by MainActivity to load the SPA. (05_android_and_demo.md "server 주소")
 */
class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE)
        val input = findViewById<EditText>(R.id.server_url_input)
        val save = findViewById<Button>(R.id.save_button)

        input.setText(prefs.getString(MainActivity.KEY_SERVER_URL, "https://"))

        save.setOnClickListener {
            var url = input.text.toString().trim()
            if (url.endsWith("/")) url = url.dropLast(1)
            if (url.isBlank() || !url.startsWith("http")) {
                Toast.makeText(this, R.string.invalid_url, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            prefs.edit().putString(MainActivity.KEY_SERVER_URL, url).apply()
            startActivity(Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
            })
            finish()
        }
    }
}
