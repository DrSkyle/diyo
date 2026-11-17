package np.devilabs.diyo

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

/**
 * Speech out. Uses the phone's own TTS engine — no cloud, no bundled voice, works offline.
 *
 * Nepali coverage varies by device: Android's built-in engine usually has no नेपाली voice, and
 * some OEM engines do. We ask for ne-NP, fall back to the device default, and say so through
 * [onVoiceUnavailable] rather than pretending. The model pack will ship a Piper voice later.
 */
class Speak(context: Context) {

    private var tts: TextToSpeech? = null
    private var ready = false
    private var nepali = false
    private var pending: String? = null

    var onVoiceUnavailable: (() -> Unit)? = null
    var onDone: (() -> Unit)? = null

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            val engine = tts ?: return@TextToSpeech
            if (status != TextToSpeech.SUCCESS) return@TextToSpeech

            val ne = Locale("ne", "NP")
            val result = engine.setLanguage(ne)
            nepali = result != TextToSpeech.LANG_MISSING_DATA &&
                result != TextToSpeech.LANG_NOT_SUPPORTED
            if (!nepali) {
                engine.setLanguage(Locale.getDefault())
                onVoiceUnavailable?.invoke()
            }
            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) = onDone?.invoke() ?: Unit
                @Deprecated("kept for older engines")
                override fun onError(utteranceId: String?) {}
                override fun onError(utteranceId: String?, errorCode: Int) {}
            })
            ready = true
            pending?.let { speak(it) }
            pending = null
        }
    }

    /** Speak an already-formatted answer (see [Say.forSpeech]). */
    fun speak(text: String) {
        val engine = tts ?: return
        if (!ready) {
            pending = text
            return
        }
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "diyo-${System.nanoTime()}")
    }

    fun stop() {
        tts?.stop()
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ready = false
    }

    val hasNepaliVoice: Boolean get() = nepali
}
