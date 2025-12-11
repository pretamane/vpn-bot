package io.nekohasekai.sagernet.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import io.nekohasekai.sagernet.R
import io.nekohasekai.sagernet.SagerNet
import io.nekohasekai.sagernet.aidl.ISagerNetService
import io.nekohasekai.sagernet.bg.BaseService
import io.nekohasekai.sagernet.bg.SagerConnection
import io.nekohasekai.sagernet.data.api.ApiClient
import io.nekohasekai.sagernet.data.model.BotConfig
import io.nekohasekai.sagernet.data.model.PaymentResponse
import io.nekohasekai.sagernet.data.model.UserStatus
import io.nekohasekai.sagernet.database.DataStore
import io.nekohasekai.sagernet.database.ProfileManager
import io.nekohasekai.sagernet.fmt.AbstractBean
import io.nekohasekai.sagernet.ktx.launchCustomTab
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import io.nekohasekai.sagernet.BuildConfig
import io.nekohasekai.sagernet.ktx.runOnIoDispatcher
import io.nekohasekai.sagernet.ktx.runOnMainDispatcher
import libcore.Libcore
import moe.matsuri.nb4a.utils.Util
import org.json.JSONObject
import androidx.core.net.toUri

class MMVPNStatusFragment : ToolbarFragment(), SagerConnection.Callback {
    private lateinit var statusText: TextView
    private lateinit var usageText: TextView
    private lateinit var expiryText: TextView
    private lateinit var usagePercentageText: TextView
    private lateinit var usageProgressBar:
            com.google.android.material.progressindicator.LinearProgressIndicator
    private lateinit var gracePeriodWarning: TextView
    private lateinit var refreshButton: Button
    private lateinit var buyButton: Button
    private lateinit var helpButton: Button
    private lateinit var btnConnectToggle: com.google.android.material.button.MaterialButton
    private var botConfig: BotConfig? = null
    private var selectedProtocolCode: String? = null

    private val connection = SagerConnection(10, true)

    private val pickImage =
            registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
                uri?.let { uploadSlip(it) }
            }

    private val connect =
            registerForActivityResult(
                    io.nekohasekai.sagernet.ui.VpnRequestActivity.StartService()
            ) {
                if (it)
                        Toast.makeText(context, R.string.vpn_permission_denied, Toast.LENGTH_SHORT)
                                .show()
            }

    override fun onCreateView(
            inflater: LayoutInflater,
            container: ViewGroup?,
            savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_mmvpn_status, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        toolbar.title = "My Status"

        statusText = view.findViewById(R.id.status_text)
        usageText = view.findViewById(R.id.usage_text)
        expiryText = view.findViewById(R.id.expiry_text)
        usagePercentageText = view.findViewById(R.id.usage_percentage_text)
        usageProgressBar = view.findViewById(R.id.usage_progress_bar)
        gracePeriodWarning = view.findViewById(R.id.grace_period_warning)
        refreshButton = view.findViewById(R.id.refresh_button)

        refreshButton.setOnClickListener { fetchStatus() }

        buyButton = view.findViewById(R.id.buy_button)
        helpButton = view.findViewById(R.id.help_button)

        buyButton.setOnClickListener { showBuyDialog() }

        helpButton.setOnClickListener { showHelpDialog() }

        view.findViewById<com.google.android.material.button.MaterialButton>(R.id.btnRetrieveLists)
                .setOnClickListener { fetchUserLists() }

        btnConnectToggle = view.findViewById(R.id.btn_connect_toggle)
        updateConnectButtonState()

        btnConnectToggle.setOnClickListener {
            if (io.nekohasekai.sagernet.database.DataStore.serviceState.canStop) {
                io.nekohasekai.sagernet.SagerNet.stopService()
                updateConnectButtonState()
            } else {
                connect.launch(null)
                updateConnectButtonState()
            }
        }

        view.findViewById<com.google.android.material.button.MaterialButton>(R.id.btn_update_app)
                .setOnClickListener { checkUpdate() }

        fetchStatus()
        fetchBotConfig()
    }

    override fun onStart() {
        super.onStart()
        connection.connect(requireContext(), this)
    }

    override fun onStop() {
        super.onStop()
        connection.disconnect(requireContext())
    }

    override fun stateChanged(state: BaseService.State, profileName: String?, msg: String?) {
        updateConnectButtonState()
    }

    override fun onServiceConnected(service: ISagerNetService) {
        updateConnectButtonState()
    }

    override fun onServiceDisconnected() {
        updateConnectButtonState()
    }

    override fun onBinderDied() {
        connection.disconnect(requireContext())
        connection.connect(requireContext(), this)
    }

    private fun fetchBotConfig() {
        ApiClient.service
                .getBotConfig()
                .enqueue(
                        object : Callback<BotConfig> {
                            override fun onResponse(
                                    call: Call<BotConfig>,
                                    response: Response<BotConfig>
                            ) {
                                if (response.isSuccessful) {
                                    botConfig = response.body()
                                }
                            }
                            override fun onFailure(call: Call<BotConfig>, t: Throwable) {
                                // Silent failure, buttons will just show error if clicked before
                                // load
                            }
                        }
                )
    }

    private fun showBuyDialog() {
        Toast.makeText(context, "Loading options...", Toast.LENGTH_SHORT).show()

        ApiClient.service
                .getBotConfig()
                .enqueue(
                        object : Callback<BotConfig> {
                            override fun onResponse(
                                    call: Call<BotConfig>,
                                    response: Response<BotConfig>
                            ) {
                                if (response.isSuccessful) {
                                    botConfig = response.body()
                                    val config = botConfig

                                    if (config != null) {
                                        val protocols =
                                                config.protocols.map { it.name }.toTypedArray()

                                        MaterialAlertDialogBuilder(requireContext())
                                                .setTitle("Buy VPN Key")
                                                .setItems(protocols) { _, which ->
                                                    val selectedProtocol = config.protocols[which]
                                                    showPaymentDialog(selectedProtocol.name, config)
                                                }
                                                .setNegativeButton("Cancel", null)
                                                .show()
                                    } else {
                                        Toast.makeText(
                                                        context,
                                                        "Failed to load config",
                                                        Toast.LENGTH_SHORT
                                                )
                                                .show()
                                    }
                                } else {
                                    Toast.makeText(
                                                    context,
                                                    "Server Error: ${response.code()}",
                                                    Toast.LENGTH_SHORT
                                            )
                                            .show()
                                }
                            }
                            override fun onFailure(call: Call<BotConfig>, t: Throwable) {
                                Toast.makeText(
                                                context,
                                                "Network Error: ${t.message}",
                                                Toast.LENGTH_SHORT
                                        )
                                        .show()
                            }
                        }
                )
    }

    private fun showPaymentDialog(protocolName: String, config: BotConfig) {
        val message =
                """
            Selected: $protocolName
            Price: ${config.payment.price}
            
            Please send payment to:
            KBZ Pay: ${config.payment.kbz}
            Wave Pay: ${config.payment.wave}
            
            1. Make payment
            2. Take screenshot
            3. Upload screenshot below
        """.trimIndent()

        MaterialAlertDialogBuilder(requireContext())
                .setTitle("Payment Instructions")
                .setMessage(message)
                .setPositiveButton("Upload Slip") { _, _ ->
                    // Find protocol code
                    selectedProtocolCode = config.protocols.find { it.name == protocolName }?.code
                    pickImage.launch("image/*")
                }
                .setNeutralButton("Open Telegram") { _, _ ->
                    requireContext().launchCustomTab("https://t.me/lilPreta2k77ZLibUserNameBot")
                }
                .setNegativeButton("Cancel", null)
                .show()
    }

    private fun uploadSlip(uri: Uri) {
        val context = requireContext()
        val contentResolver = context.contentResolver

        // Create temp file
        val tempFile = File(context.cacheDir, "upload_slip.jpg")
        try {
            contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(tempFile).use { output -> input.copyTo(output) }
            }
        } catch (e: Exception) {
            Toast.makeText(context, "Failed to read file", Toast.LENGTH_SHORT).show()
            return
        }

        val requestFile = tempFile.asRequestBody("image/*".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", tempFile.name, requestFile)

        // Get UUID
        val profileId = DataStore.currentProfile
        val profile = ProfileManager.getProfile(profileId)
        val uuid = profile?.uuid ?: ""

        val uuidPart = uuid.toRequestBody("text/plain".toMediaTypeOrNull())
        val protocolPart =
                (selectedProtocolCode ?: "vless").toRequestBody("text/plain".toMediaTypeOrNull())

        val dialog =
                MaterialAlertDialogBuilder(context)
                        .setTitle("Verifying Payment")
                        .setMessage("Please wait while we verify your slip...")
                        .setCancelable(false)
                        .show()

        ApiClient.service
                .verifyPayment(body, uuidPart, protocolPart)
                .enqueue(
                        object : Callback<PaymentResponse> {
                            override fun onResponse(
                                    call: Call<PaymentResponse>,
                                    response: Response<PaymentResponse>
                            ) {
                                dialog.dismiss()
                                if (response.isSuccessful) {
                                    val result = response.body()
                                    if (result != null && result.success) {
                                        showSuccessDialog(result)
                                    } else {
                                        Toast.makeText(
                                                        context,
                                                        "Verification failed: ${result?.message}",
                                                        Toast.LENGTH_LONG
                                                )
                                                .show()
                                    }
                                } else {
                                    Toast.makeText(
                                                    context,
                                                    "Error: ${response.code()} - ${response.errorBody()?.string()}",
                                                    Toast.LENGTH_LONG
                                            )
                                            .show()
                                }
                            }

                            override fun onFailure(call: Call<PaymentResponse>, t: Throwable) {
                                dialog.dismiss()
                                Toast.makeText(
                                                context,
                                                "Network Error: ${t.message}",
                                                Toast.LENGTH_SHORT
                                        )
                                        .show()
                            }
                        }
                )
    }

    private fun showSuccessDialog(result: PaymentResponse) {
        MaterialAlertDialogBuilder(requireContext())
                .setTitle("Payment Verified! ✅")
                .setMessage("Transaction ID: ${result.transactionId}\n\nKey:\n${result.key}")
                .setPositiveButton("Import Key") { _, _ ->
                    val context = requireContext()
                    CoroutineScope(Dispatchers.Main).launch {
                        try {
                            val proxies =
                                    withContext(Dispatchers.Default) {
                                        io.nekohasekai.sagernet.group.RawUpdater.parseRaw(
                                                result.key
                                        )
                                    }

                            if (proxies.isNullOrEmpty()) {
                                Toast.makeText(context, "Failed to parse key", Toast.LENGTH_SHORT)
                                        .show()
                            } else {
                                // Get current UUID to associate with new profiles
                                val currentProfileId = DataStore.currentProfile
                                val currentProfile = ProfileManager.getProfile(currentProfileId)
                                val uuid = currentProfile?.uuid

                                importProxies(context, proxies, uuid)
                            }
                        } catch (e: Exception) {
                            android.util.Log.e("KeysDebug", "Import failed", e)
                            Toast.makeText(
                                            context,
                                            "Import failed: ${e.message}",
                                            Toast.LENGTH_SHORT
                                    )
                                    .show()
                        }
                    }
                }
                .setNeutralButton("Copy Key") { _, _ ->
                    val clipboard =
                            requireContext().getSystemService(Context.CLIPBOARD_SERVICE) as
                                    ClipboardManager
                    val clip = ClipData.newPlainText("VPN Key", result.key)
                    clipboard.setPrimaryClip(clip)
                    Toast.makeText(context, "Key copied to clipboard", Toast.LENGTH_SHORT).show()
                }
                .setNegativeButton("Close", null)
                .show()
    }

    private fun showHelpDialog() {
        val config = botConfig
        if (config == null) {
            Toast.makeText(context, "Loading config...", Toast.LENGTH_SHORT).show()
            fetchBotConfig()
            return
        }

        MaterialAlertDialogBuilder(requireContext())
                .setTitle("Help & Support")
                .setMessage("Contact Support: ${config.support.contact}")
                .setPositiveButton("Open Chat") { _, _ ->
                    requireContext().launchCustomTab("https://t.me/pretamane")
                }
                .setNegativeButton("Close", null)
                .show()
    }

    private fun fetchStatus() {
        statusText.text = "Loading..."

        CoroutineScope(Dispatchers.IO).launch {
            val profileId = DataStore.currentProfile
            if (profileId == 0L) {
                withContext(Dispatchers.Main) {
                    statusText.text = "No Profile Selected"
                    Toast.makeText(context, "Please select a profile first", Toast.LENGTH_SHORT)
                            .show()
                }
                return@launch
            }

            val profile = ProfileManager.getProfile(profileId)

            // Determine which UUID to use for status check
            // 1. Try to get UUID from the specific proxy config (Bean)
            var uuid: String? = null
            if (profile != null) {
                try {
                    val bean = profile.requireBean()
                    if (bean is io.nekohasekai.sagernet.fmt.v2ray.StandardV2RayBean) {
                        uuid = bean.uuid
                    } else if (bean is io.nekohasekai.sagernet.fmt.tuic.TuicBean) {
                        uuid = bean.uuid
                    }
                } catch (e: Exception) {
                    // Ignore bean errors
                }

                // 2. Fallback to the Profile's "Master UUID" if bean didn't have one
                if (uuid.isNullOrEmpty()) {
                    uuid = profile.uuid
                }
            }

            if (uuid.isNullOrEmpty()) {
                withContext(Dispatchers.Main) {
                    statusText.text = "Invalid Profile"
                    Toast.makeText(context, "Current profile has no UUID", Toast.LENGTH_SHORT)
                            .show()
                }
                return@launch
            }

            android.util.Log.e("StatusDebug", "Calling getUserStatus for UUID: $uuid")

            ApiClient.service
                    .getUserStatus(uuid)
                    .enqueue(
                            object : Callback<UserStatus> {
                                override fun onResponse(
                                        call: Call<UserStatus>,
                                        response: Response<UserStatus>
                                ) {
                                    android.util.Log.i(
                                            "StatusDebug",
                                            "Response received: code=${response.code()}, success=${response.isSuccessful}"
                                    )

                                    if (response.isSuccessful) {
                                        val status = response.body()
                                        android.util.Log.i("StatusDebug", "Response body: $status")

                                        if (status != null) {
                                            android.util.Log.i(
                                                    "StatusDebug",
                                                    "Parsing response: protocol=${status.protocol}, limit=${status.dataLimitGb}GB, usage=${status.dailyUsageBytes}bytes"
                                            )
                                            val protocolName =
                                                    when (status.protocol) {
                                                        "vless_limited" -> "VLESS Limited (12 Mbps)"
                                                        "vless" -> "VLESS Reality"
                                                        "tuic" -> "TUIC"
                                                        "vlessplain" -> "VLESS + TLS"
                                                        "ss" -> "Shadowsocks"
                                                        "ss_legacy" -> "Shadowsocks (Legacy)"
                                                        "admin_tuic" -> "Admin TUIC"
                                                        else -> status.protocol.uppercase()
                                                    }
                                            statusText.text =
                                                    "$protocolName: ${if (status.isActive) "Active ✅" else "Inactive ❌"}"
                                            android.util.Log.i(
                                                    "StatusDebug",
                                                    "Updated statusText: ${statusText.text}"
                                            )

                                            val usageGb =
                                                    status.dailyUsageBytes /
                                                            (1024.0 * 1024.0 * 1024.0)
                                            usageText.text =
                                                    String.format(
                                                            "Usage: %.2f GB / %.0f GB",
                                                            usageGb,
                                                            status.dataLimitGb
                                                    )
                                            android.util.Log.i(
                                                    "StatusDebug",
                                                    "Updated usageText: ${usageText.text}"
                                            )

                                            expiryText.text = "Expires at: ${status.expiryDate}"
                                            android.util.Log.i(
                                                    "StatusDebug",
                                                    "Updated expiryText: ${expiryText.text}"
                                            )

                                            // Update progress bar
                                            val percentage =
                                                    status.usagePercentage.toInt().coerceIn(0, 100)
                                            usageProgressBar.progress = percentage
                                            usagePercentageText.text = "Data Usage: ${percentage}%"

                                            // Change progress bar color based on usage
                                            when {
                                                percentage >= 95 ->
                                                        usageProgressBar.setIndicatorColor(
                                                                android.graphics.Color.parseColor(
                                                                        "#F44336"
                                                                )
                                                        ) // Red
                                                percentage >= 65 ->
                                                        usageProgressBar.setIndicatorColor(
                                                                android.graphics.Color.parseColor(
                                                                        "#FF9800"
                                                                )
                                                        ) // Orange
                                                percentage >= 30 ->
                                                        usageProgressBar.setIndicatorColor(
                                                                android.graphics.Color.parseColor(
                                                                        "#FFC107"
                                                                )
                                                        ) // Yellow
                                                else ->
                                                        usageProgressBar.setIndicatorColor(
                                                                android.graphics.Color.parseColor(
                                                                        "#E91E63"
                                                                )
                                                        ) // Pink
                                            }

                                            // Show grace period warning if applicable
                                            if (status.inGracePeriod) {
                                                gracePeriodWarning.visibility = View.VISIBLE
                                                val hoursRemaining =
                                                        status.graceRemainingHours.toInt()
                                                gracePeriodWarning.text =
                                                        "⚠️ Grace Period: $hoursRemaining hours remaining"
                                            } else {
                                                gracePeriodWarning.visibility = View.GONE
                                            }
                                        } else {
                                            android.util.Log.e(
                                                    "StatusDebug",
                                                    "Response body is NULL"
                                            )
                                        }
                                    } else {
                                        android.util.Log.e(
                                                "StatusDebug",
                                                "Response not successful: ${response.code()} - ${response.errorBody()?.string()}"
                                        )
                                        statusText.text = "Error: ${response.code()}"
                                    }
                                }

                                override fun onFailure(call: Call<UserStatus>, t: Throwable) {
                                    android.util.Log.e(
                                            "StatusDebug",
                                            "Network failure: ${t.message}",
                                            t
                                    )
                                    statusText.text = "Network Error"
                                    Toast.makeText(context, t.message, Toast.LENGTH_SHORT).show()
                                }
                            }
                    )
        }
    }

    private fun fetchUserLists() {
        val context = requireContext()
        val profileId = DataStore.currentProfile
        val profile = ProfileManager.getProfile(profileId)
        val uuid = profile?.uuid

        if (uuid.isNullOrEmpty()) {
            // Check if user is theoretically logged in (prefs exist)
            val prefs = context.getSharedPreferences("mmvpn_user_prefs", Context.MODE_PRIVATE)
            val savedName = prefs.getString("user_name", null)

            if (savedName != null) {
                // User is remembered, but session/profile is lost.
                // Auto-redirect to LoginActivity to heal the session.
                Toast.makeText(context, "Refreshing session...", Toast.LENGTH_SHORT).show()
                val intent = Intent(context, LoginActivity::class.java)
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                startActivity(intent)
            } else {
                // Genuine logout state. Show dialog.
                MaterialAlertDialogBuilder(context)
                        .setTitle("Re-authentication Required")
                        .setMessage(
                                "Your session needs to be refreshed. Please sign in again to access your VPN keys."
                        )
                        .setPositiveButton("Sign In") { _, _ ->
                            // Clear current profile and redirect to login
                            DataStore.currentProfile = 0L
                            val intent = Intent(context, LoginActivity::class.java)
                            intent.flags =
                                    Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                            startActivity(intent)
                        }
                        .setNegativeButton("Cancel", null)
                        .show()
            }
            return
        }

        android.util.Log.e("KeysDebug", "Fetching keys for UUID: $uuid")
        android.util.Log.e("KeysDebug", "Full URL: http://43.205.90.213:8082/api/keys/$uuid")

        val dialog =
                MaterialAlertDialogBuilder(context)
                        .setTitle("Retrieving Keys")
                        .setMessage("Please wait...")
                        .setCancelable(false)
                        .show()

        ApiClient.service
                .getUserKeys(uuid)
                .enqueue(
                        object : Callback<io.nekohasekai.sagernet.data.model.UserKeysResponse> {
                            override fun onResponse(
                                    call: Call<io.nekohasekai.sagernet.data.model.UserKeysResponse>,
                                    response:
                                            Response<
                                                    io.nekohasekai.sagernet.data.model.UserKeysResponse>
                            ) {
                                dialog.dismiss()
                                android.util.Log.i("KeysDebug", "Response Code: ${response.code()}")
                                if (response.isSuccessful) {
                                    val keysResponse = response.body()
                                    val keys = keysResponse?.keys
                                    android.util.Log.i("KeysDebug", "Keys received: ${keys?.size}")
                                    if (!keys.isNullOrEmpty()) {

                                        // Create custom view for the dialog
                                        val scrollView = android.widget.ScrollView(context)
                                        val container = android.widget.LinearLayout(context)
                                        container.orientation = android.widget.LinearLayout.VERTICAL
                                        container.setPadding(16, 16, 16, 16)
                                        scrollView.addView(container)

                                        for (key in keys) {
                                            val itemView =
                                                    LayoutInflater.from(context)
                                                            .inflate(
                                                                    R.layout.item_vpn_key,
                                                                    container,
                                                                    false
                                                            )
                                            val keyNameText =
                                                    itemView.findViewById<TextView>(R.id.key_name)
                                            val copyButton =
                                                    itemView.findViewById<Button>(R.id.btn_copy)
                                            val importButton =
                                                    itemView.findViewById<Button>(R.id.btn_import)

                                            keyNameText.text = key.key_name
                                            val textToCopy = key.config_link ?: key.key_name

                                            copyButton.setOnClickListener {
                                                val clipboard =
                                                        context.getSystemService(
                                                                Context.CLIPBOARD_SERVICE
                                                        ) as
                                                                ClipboardManager
                                                val clip =
                                                        ClipData.newPlainText("VPN Key", textToCopy)
                                                clipboard.setPrimaryClip(clip)
                                                Toast.makeText(
                                                                context,
                                                                "Copied to clipboard",
                                                                Toast.LENGTH_SHORT
                                                        )
                                                        .show()
                                            }

                                            importButton.setOnClickListener {
                                                CoroutineScope(Dispatchers.Main).launch {
                                                    try {
                                                        val proxies =
                                                                withContext(Dispatchers.Default) {
                                                                    io.nekohasekai.sagernet.group
                                                                            .RawUpdater.parseRaw(
                                                                            textToCopy
                                                                    )
                                                                }

                                                        if (proxies.isNullOrEmpty()) {
                                                            Toast.makeText(
                                                                            context,
                                                                            "Failed to parse key",
                                                                            Toast.LENGTH_SHORT
                                                                    )
                                                                    .show()
                                                        } else {
                                                            importProxies(context, proxies, uuid)
                                                        }
                                                    } catch (e: Exception) {
                                                        android.util.Log.e(
                                                                "KeysDebug",
                                                                "Import failed",
                                                                e
                                                        )
                                                        Toast.makeText(
                                                                        context,
                                                                        "Import failed: ${e.message}",
                                                                        Toast.LENGTH_SHORT
                                                                )
                                                                .show()
                                                    }
                                                }
                                            }

                                            container.addView(itemView)
                                        }

                                        MaterialAlertDialogBuilder(context)
                                                .setTitle("Your VPN Keys")
                                                .setView(scrollView)
                                                .setPositiveButton("Close", null)
                                                .show()
                                    } else {
                                        android.util.Log.e("KeysDebug", "No keys in response")
                                        MaterialAlertDialogBuilder(context)
                                                .setTitle("No Keys Found")
                                                .setMessage("You don't have any VPN keys yet.")
                                                .setPositiveButton("OK", null)
                                                .show()
                                    }
                                } else {
                                    android.util.Log.e(
                                            "KeysDebug",
                                            "Error: ${response.errorBody()?.string()}"
                                    )
                                    MaterialAlertDialogBuilder(context)
                                            .setTitle("Error")
                                            .setMessage(
                                                    "Failed to retrieve keys. Server returned code: ${response.code()}"
                                            )
                                            .setPositiveButton("OK", null)
                                            .show()
                                }
                            }

                            override fun onFailure(
                                    call: Call<io.nekohasekai.sagernet.data.model.UserKeysResponse>,
                                    t: Throwable
                            ) {
                                dialog.dismiss()
                                android.util.Log.e("KeysDebug", "Network Error: ${t.message}")
                                MaterialAlertDialogBuilder(context)
                                        .setTitle("Network Error")
                                        .setMessage("Failed to connect to server: ${t.message}")
                                        .setPositiveButton("OK", null)
                                        .show()
                            }
                        }
                )
    }

    private fun updateConnectButtonState() {
        if (io.nekohasekai.sagernet.database.DataStore.serviceState.canStop) {
            btnConnectToggle.text = "Disconnect VPN"
            btnConnectToggle.setIconResource(R.drawable.ic_baseline_link_24)
        } else {
            btnConnectToggle.text = "Connect VPN"
            btnConnectToggle.setIconResource(R.drawable.ic_baseline_link_24)
        }
    }

    override fun onResume() {
        super.onResume()
        updateConnectButtonState()
        fetchStatus()
    }
    private suspend fun importProxies(
            context: Context,
            proxies: List<AbstractBean>,
            userUuid: String?
    ) {
        android.util.Log.d("KeysDebug", "Entering importProxies. Proxies count: ${proxies.size}")

        // 1. Check if VPN is currently running
        val isVpnRunning = io.nekohasekai.sagernet.database.DataStore.serviceState.canStop
        android.util.Log.d("KeysDebug", "isVpnRunning: $isVpnRunning")

        // 2. Get the currently selected profile (the one FAB uses)
        val currentProfileId = io.nekohasekai.sagernet.database.DataStore.currentProfile
        val currentProfile = ProfileManager.getProfile(currentProfileId)
        android.util.Log.d(
                "KeysDebug",
                "currentProfileId: $currentProfileId, found: ${currentProfile != null}"
        )

        var targetProfileId = 0L
        var message = ""

        if (currentProfile != null && proxies.size > 0) {
            // Substitute the active profile with the FIRST imported key
            android.util.Log.d("KeysDebug", "Substituting active profile")
            val proxy = proxies[0]
            currentProfile.putBean(proxy)

            // DO NOT overwrite the Profile UUID with the Proxy UUID.
            // We need to keep the "Master UUID" (User UUID) for "Retrieve Keys" to work.
            // The Proxy UUID will be used by fetchStatus() via profile.requireBean()

            ProfileManager.updateProfile(currentProfile)
            targetProfileId = currentProfile.id
            message = "Active VPN profile updated."

            // If there are more proxies (rare), add them as new profiles
            if (proxies.size > 1) {
                val targetGroupId =
                        io.nekohasekai.sagernet.database.DataStore.selectedGroupForImport()
                for (i in 1 until proxies.size) {
                    val newProfile = ProfileManager.createProfile(targetGroupId, proxies[i])
                    // Apply UUID logic if needed for extras
                }
                message += "\n(+${proxies.size - 1} extra profiles added)"
            }
        } else {
            // No active profile or empty list (fallback), create new profiles
            android.util.Log.d("KeysDebug", "Creating new profile(s)")
            val targetGroupId = io.nekohasekai.sagernet.database.DataStore.selectedGroupForImport()
            for (proxy in proxies) {
                val newProfile = ProfileManager.createProfile(targetGroupId, proxy)

                var finalUuid = userUuid
                if (finalUuid.isNullOrEmpty()) {
                    if (proxy is io.nekohasekai.sagernet.fmt.v2ray.StandardV2RayBean) {
                        finalUuid = proxy.uuid
                    } else if (proxy is io.nekohasekai.sagernet.fmt.tuic.TuicBean) {
                        finalUuid = proxy.uuid
                    }
                }

                if (!finalUuid.isNullOrEmpty()) {
                    newProfile.uuid = finalUuid
                    ProfileManager.updateProfile(newProfile)
                }
                targetProfileId = newProfile.id
            }
            message = "New VPN profile(s) imported."
        }

        // 3. Update Selection
        if (targetProfileId != 0L) {
            io.nekohasekai.sagernet.database.DataStore.selectedProxy = targetProfileId
            io.nekohasekai.sagernet.database.DataStore.currentProfile = targetProfileId
        }

        // 4. Auto-Reconnect if it was running
        withContext(Dispatchers.Main) {
            android.util.Log.d("KeysDebug", "Updating UI. isVpnRunning: $isVpnRunning")
            if (isVpnRunning) {
                Toast.makeText(context, "Updating VPN Connection...", Toast.LENGTH_SHORT).show()
                // Reload service to pick up the new profile configuration
                android.util.Log.d("KeysDebug", "Calling reloadService")
                io.nekohasekai.sagernet.SagerNet.reloadService()
            } else {
                // Auto-start VPN if not running
                Toast.makeText(context, "Starting VPN...", Toast.LENGTH_SHORT).show()
                connect.launch(null)
            }
            // Refresh status to show new profile details
            fetchStatus()
        }
    }

    private fun checkUpdate() {
        runOnIoDispatcher {
            try {
                val client =
                        Libcore.newHttpClient().apply {
                            modernTLS()
                            trySocks5(DataStore.mixedPort)
                        }
                val response = client.newRequest().apply {
                    setURL("https://api.github.com/repos/pretamane/vpn-bot/releases/latest")
                }.execute()

                val jsonStr = Util.getStringBox(response.contentString)
                val json = JSONObject(jsonStr)

                if (json.has("message") && json.getString("message") == "Not Found") {
                    runOnMainDispatcher {
                        Toast.makeText(context, "No releases found on GitHub. Please create a release.", Toast.LENGTH_LONG).show()
                    }
                    return@runOnIoDispatcher
                }

                val releaseName = json.getString("name")
                val releaseUrl = json.getString("html_url")


                
                // Simple check: if release name is different from current version
                val haveUpdate = releaseName.isNotBlank() && !releaseName.contains(BuildConfig.VERSION_NAME)

                runOnMainDispatcher {
                    if (haveUpdate) {
                        val context = requireContext()
                        MaterialAlertDialogBuilder(context)
                                .setTitle(R.string.update_dialog_title)
                                .setMessage(
                                        "Current: ${SagerNet.appVersionNameForDisplay}\nLatest: $releaseName\n\nA new version is available!"
                                )
                                .setPositiveButton(R.string.yes) { _, _ ->
                                    val intent = Intent(Intent.ACTION_VIEW, releaseUrl.toUri())
                                    context.startActivity(intent)
                                }
                                .setNegativeButton(R.string.no, null)
                                .show()
                    } else {
                        Toast.makeText(context, R.string.check_update_no, Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                runOnMainDispatcher {
                    Toast.makeText(context, "Update check failed: ${e.message}", Toast.LENGTH_SHORT)
                            .show()
                }
            }
        }
    }
}
