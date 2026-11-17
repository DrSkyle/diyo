package np.devilabs.diyo

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Diyo — stage 0.
 *
 * One screen, no permissions, no network, no model. It exists to prove the build, and to hold the
 * shape of the product: a lamp, a mic, and an honest answer.
 */
class MainActivity : Activity() {

    private lateinit var heard: TextView
    private lateinit var answer: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(56, 120, 56, 56)
            setBackgroundColor(Color.parseColor("#0E0C0A"))
        }

        val title = TextView(this).apply {
            text = getString(R.string.app_name)
            textSize = 44f
            setTextColor(Color.parseColor("#F2C14E"))
            gravity = Gravity.CENTER
        }

        val tagline = TextView(this).apply {
            text = getString(R.string.tagline)
            textSize = 16f
            setTextColor(Color.parseColor("#B9AFA3"))
            gravity = Gravity.CENTER
            setPadding(0, 12, 0, 48)
        }

        heard = TextView(this).apply {
            text = getString(R.string.heard_idle)
            textSize = 15f
            setTextColor(Color.parseColor("#8A8078"))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 20)
        }

        answer = TextView(this).apply {
            text = ""
            textSize = 20f
            setTextColor(Color.parseColor("#EFE9E1"))
            gravity = Gravity.CENTER
            setPadding(0, 8, 0, 40)
        }

        val mic = Button(this).apply {
            text = getString(R.string.mic)
            textSize = 18f
            setOnClickListener {
                // Stage 0 is honest about what it cannot do yet.
                heard.text = getString(R.string.heard_placeholder)
                answer.text = getString(R.string.offline_note)
            }
        }

        val build = TextView(this).apply {
            text = getString(R.string.version, BuildConfig.VERSION_NAME)
            textSize = 12f
            setTextColor(Color.parseColor("#5F5851"))
            gravity = Gravity.CENTER
            setPadding(0, 48, 0, 0)
        }

        listOf(title, tagline, heard, answer, mic, build).forEach { root.addView(it) }
        setContentView(root)
    }
}
