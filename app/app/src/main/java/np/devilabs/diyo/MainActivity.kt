package np.devilabs.diyo

import android.os.Build
import android.os.Bundle
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp

/**
 * Diyo stage 0 — the standard chat layout every open-source chat client uses:
 * a scrolling message list and a composer pinned to the bottom.
 *
 * Reference pattern: OSS on-device chat clients (PocketPal AI, Ollama App, both Apache/MIT).
 * No custom components beyond the bubble alignment.
 *
 * The one brand decision is the colour: a warm amber seed instead of the framework default.
 */

private data class Msg(val text: String, val fromUser: Boolean)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = DiyoGold,
                    onPrimary = androidx.compose.ui.graphics.Color(0xFF1B1206)
                )
            ) { DiyoApp() }
        }
    }
}

private val DiyoGold = androidx.compose.ui.graphics.Color(0xFFC8871B)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DiyoApp() {
    val context = LocalContext.current
    val speak = remember { Speak(context) }
    val voiceMissing = stringResource(R.string.voice_missing)
    DisposableEffect(Unit) { onDispose { speak.shutdown() } }

    val tagline = stringResource(R.string.tagline)
    val missing = stringResource(R.string.model_missing)
    val messages = remember { mutableStateListOf(Msg(tagline, false)) }
    var draft by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex)
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text(stringResource(R.string.app_name)) }) },
        bottomBar = {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .imePadding()
                    .padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = draft,
                    onValueChange = { draft = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text(stringResource(R.string.composer_hint)) },
                    maxLines = 4
                )
                Button(
                    onClick = {
                        val prompt = draft.trim()
                        if (prompt.isEmpty()) return@Button
                        messages += Msg(prompt, true)
                        draft = ""
                        // The guard answers before the model, exactly as it does on the server.
                        val forced = Guard.check(prompt)
                        val reply = Say.forSpeech(forced ?: missing)
                        messages += Msg(reply, false)
                        speak.speak(reply)
                    },
                    enabled = draft.isNotBlank()
                ) { Text(stringResource(R.string.send)) }
            }
        }
    ) { inner ->
        Box(Modifier.fillMaxSize().padding(inner)) {
            if (!speak.hasNepaliVoice) {
                Text(
                    text = voiceMissing,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp)
            ) {
                items(messages) { m -> Bubble(m) }
            }
        }
    }
}

@Composable
private fun Bubble(m: Msg) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (m.fromUser) Alignment.End else Alignment.Start
    ) {
        Surface(
            shape = MaterialTheme.shapes.large,
            color = if (m.fromUser) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.surfaceVariant
            },
            modifier = Modifier.widthIn(max = 320.dp)
        ) {
            Text(
                text = m.text,
                style = MaterialTheme.typography.bodyLarge,
                color = if (m.fromUser) {
                    MaterialTheme.colorScheme.onPrimary
                } else {
                    MaterialTheme.colorScheme.onSurfaceVariant
                },
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)
            )
        }
    }
}
