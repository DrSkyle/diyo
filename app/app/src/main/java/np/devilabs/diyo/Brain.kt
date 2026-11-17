package np.devilabs.diyo

import android.content.Context
import java.io.File

/**
 * The answer engine. Swappable so the same app shell runs with:
 *  - no pack  → grounded fallback from the corpus (ships today)
 *  - a pack   → on-device GGUF base + LoRA via llama.cpp JNI (stage 1)
 *  - online   → opt-in cloud call from NetSearch.kt only (never by default)
 *
 * Nothing here opens a network socket; the network-discipline build gate enforces that.
 */
interface Brain {
    /** A complete answer to [prompt], or null if this brain cannot answer. */
    fun answer(prompt: String): String?
}

object Brains {
    /** Picks the best brain available on this device. */
    fun pick(context: Context): Brain {
        GroundedBrain.context = context.applicationContext
        val pack = Pack.find(context)
        return if (pack != null) LlamaBrain(pack) else GroundedBrain
    }
}

/**
 * Grounded fallback: finds the best corpus chunk and returns it as a plain answer.
 * Not a language model — but it is honest, offline, cited by content, and never hallucinates.
 */
object GroundedBrain : Brain {
    var context: Context? = null
    override fun answer(prompt: String): String? {
        val hits = Corpus.search(prompt, limit = 1, context = context)
        return hits.firstOrNull()?.text
    }
}

/** An on-device model pack: a base GGUF and an optional LoRA adapter. */
data class Pack(val base: File, val adapter: File?)

object Pack {
    // The app looks for a model pack under filesDir/models/. A download manager will place it there.
    fun find(context: Context): Pack? {
        val dir = File(context.filesDir, "models")
        val base = dir.listFiles()?.firstOrNull { it.extension == "gguf" } ?: return null
        val adapter = dir.listFiles()?.firstOrNull { it.name.endsWith(".gguf") && it != base }
            ?: dir.listFiles()?.firstOrNull { it.name == "adapter" || it.extension == "bin" }
        return Pack(base, adapter)
    }
}

/**
 * llama.cpp-backed brain. The native binding is loaded only when a pack is present; without the
 * JNI library this degrades to the grounded fallback instead of crashing.
 */
class LlamaBrain(private val pack: Pack) : Brain {
    override fun answer(prompt: String): String? {
        val grounded = Corpus.ground(prompt)
        val full = if (grounded.isEmpty()) prompt else "$grounded\n\nप्रश्न: $prompt"
        return try {
            NativeBridge.complete(pack.base.absolutePath, pack.adapter?.absolutePath, full)
        } catch (_: UnsatisfiedLinkError) {
            // Native library not bundled yet — fall back rather than crash.
            GroundedBrain.answer(prompt)
        } catch (_: Throwable) {
            GroundedBrain.answer(prompt)
        }
    }
}

/** JNI surface for llama.cpp. The .so is added with the model pack in stage 1. */
object NativeBridge {
    @JvmStatic external fun complete(basePath: String, adapterPath: String?, prompt: String): String
}
