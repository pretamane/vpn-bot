package io.nekohasekai.sagernet.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Bundle
import android.telephony.SubscriptionManager
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import coil.load
import coil.transform.CircleCropTransformation
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.android.gms.tasks.Task
import io.nekohasekai.sagernet.R
import io.nekohasekai.sagernet.SagerNet
import io.nekohasekai.sagernet.data.api.ApiClient
import io.nekohasekai.sagernet.data.model.GoogleLoginRequest
import io.nekohasekai.sagernet.data.model.LoginResponse
import io.nekohasekai.sagernet.data.model.PhoneLoginRequest
import io.nekohasekai.sagernet.database.DataStore
import io.nekohasekai.sagernet.database.ProfileManager
import io.nekohasekai.sagernet.database.SagerDatabase
import io.nekohasekai.sagernet.databinding.ActivityLoginBinding
import io.nekohasekai.sagernet.fmt.shadowsocks.ShadowsocksBean
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var googleSignInClient: GoogleSignInClient
    private lateinit var prefs: SharedPreferences
    private val RC_SIGN_IN = 9001
    private val RC_PHONE_PERM = 9002

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        android.util.Log.e("TapTracker", "LoginActivity CREATED - Logging Check")

        prefs = getSharedPreferences("mmvpn_user_prefs", Context.MODE_PRIVATE)

        // Configure Google Sign-In
        val gso =
                GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                        .requestIdToken(getString(R.string.default_web_client_id))
                        .requestEmail()
                        .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        // Ensure VPN is stopped when on login screen
        if (DataStore.serviceState.canStop) {
            SagerNet.stopService()
        }

        checkSavedUser()
        testConnection()

        binding.signInButton.setOnClickListener { signIn() }

        binding.signInPhoneButton.setOnClickListener { checkPhonePermissionAndLogin() }

        binding.continueButton.setOnClickListener {
            val savedEmail = prefs.getString("user_email", null)
            if (savedEmail != null) {
                // Attempt silent sign-in or just proceed if token is valid (simplified here)
                // For now, we'll trigger a silent sign-in to get a fresh token
                googleSignInClient.silentSignIn().addOnCompleteListener(this) { task ->
                    handleSignInResult(task)
                }
            }
        }

        binding.switchAccountButton.setOnClickListener { signOutAndSwitch() }
    }

    private fun checkSavedUser() {
        val savedName = prefs.getString("user_name", null)
        val savedPhoto = prefs.getString("user_photo", null)
        val loginType = prefs.getString("login_type", "google")

        if (savedName != null) {
            if (loginType == "phone") {
                val savedEmail = prefs.getString("user_email", "") ?: ""
                saveUserAndRedirect(savedName, savedEmail, savedPhoto, "phone")
            } else {
                // User is remembered, attempt auto-login (Google)
                showLoadingState()
                attemptAutoLogin()
            }
        } else {
            // No user remembered
            showLoginState()
        }
    }

    private fun showLoadingState() {
        binding.welcomeText.text = "Signing in..."
        binding.signInButton.visibility = View.GONE
        binding.continueButton.visibility = View.GONE
        binding.switchAccountButton.visibility = View.GONE
        binding.loginAvatar.visibility = View.VISIBLE
        // Ideally show a progress bar here if one exists in layout,
        // or just rely on the text change for now.
    }

    private fun showLoginState() {
        binding.welcomeText.text = "Welcome to MMVPN"
        binding.signInButton.visibility = View.VISIBLE
        binding.continueButton.visibility = View.GONE
        binding.switchAccountButton.visibility = View.GONE
        binding.loginAvatar.visibility = View.GONE
    }

    private fun showContinueState(savedName: String, savedPhoto: String?) {
        binding.welcomeText.text = "Welcome back, $savedName"
        binding.signInButton.visibility = View.GONE
        binding.continueButton.visibility = View.VISIBLE
        binding.switchAccountButton.visibility = View.VISIBLE
        binding.loginAvatar.visibility = View.VISIBLE

        binding.continueButton.text = "Continue as $savedName"

        if (savedPhoto != null) {
            binding.loginAvatar.load(savedPhoto) {
                crossfade(true)
                transformations(CircleCropTransformation())
                placeholder(R.mipmap.ic_launcher)
                error(R.mipmap.ic_launcher)
            }
        }
    }

    private fun attemptAutoLogin() {
        googleSignInClient.silentSignIn().addOnCompleteListener(this) { task ->
            if (task.isSuccessful) {
                handleSignInResult(task)
            } else {
                // Silent sign-in failed, fall back to manual continue
                val savedName = prefs.getString("user_name", "") ?: ""
                val savedPhoto = prefs.getString("user_photo", null)
                showContinueState(savedName, savedPhoto)
            }
        }
    }

    private fun signOutAndSwitch() {
        // Stop VPN before switching accounts
        if (DataStore.serviceState.canStop) {
            Toast.makeText(this, "Disconnecting VPN...", Toast.LENGTH_SHORT).show()
            SagerNet.stopService()
        }

        googleSignInClient.signOut().addOnCompleteListener(this) {
            prefs.edit().clear().apply()
            checkSavedUser()
            signIn()
        }
    }

    private fun signIn() {
        android.util.Log.d("LoginActivity", "signIn() called")
        val signInIntent = googleSignInClient.signInIntent
        startActivityForResult(signInIntent, RC_SIGN_IN)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        android.util.Log.d("LoginActivity", "onActivityResult: req=$requestCode, res=$resultCode")

        if (requestCode == RC_SIGN_IN) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)
            handleSignInResult(task)
        }
    }

    private fun handleSignInResult(completedTask: Task<GoogleSignInAccount>) {
        try {
            val account = completedTask.getResult(ApiException::class.java)
            val idToken = account.idToken

            if (idToken != null) {
                authenticateWithServer(account)
            } else {
                Toast.makeText(this, "Sign-in failed: No ID Token", Toast.LENGTH_SHORT).show()
            }
        } catch (e: ApiException) {
            Toast.makeText(this, "Sign-in failed: ${e.statusCode}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun authenticateWithServer(account: GoogleSignInAccount) {
        val idToken = account.idToken ?: return
        binding.signInButton.isEnabled = false
        Toast.makeText(this, "Authenticating...", Toast.LENGTH_SHORT).show()

        ApiClient.service
                .googleLogin(GoogleLoginRequest(idToken))
                .enqueue(
                        object : Callback<LoginResponse> {
                            override fun onResponse(
                                    call: Call<LoginResponse>,
                                    response: Response<LoginResponse>
                            ) {
                                if (response.isSuccessful) {
                                    val loginResponse = response.body()
                                    if (loginResponse != null) {
                                        lifecycleScope.launch {
                                            try {
                                                val key = loginResponse.key
                                                android.util.Log.e(
                                                        "LoginDebug",
                                                        "Key received from server: ${if (key.isNullOrEmpty()) "NULL/EMPTY" else "PRESENT"}"
                                                )
                                                if (!key.isNullOrEmpty()) {
                                                    // Import the real key
                                                    val proxies =
                                                            withContext(Dispatchers.Default) {
                                                                io.nekohasekai.sagernet.group
                                                                        .RawUpdater.parseRaw(key)
                                                            }

                                                    if (!proxies.isNullOrEmpty()) {
                                                        val targetId =
                                                                DataStore.selectedGroupForImport()
                                                        var lastProfileId = 0L

                                                        // Get current UUID to associate with new
                                                        // profiles
                                                        val currentProfileId =
                                                                DataStore.currentProfile
                                                        val currentProfile =
                                                                ProfileManager.getProfile(
                                                                        currentProfileId
                                                                )
                                                        val uuid = currentProfile?.uuid

                                                        for (proxy in proxies) {
                                                            // Check if profile with this key_uuid
                                                            // already exists
                                                            var existingProfileId = 0L

                                                            // Determine the UUID for this proxy
                                                            var proxyUuid =
                                                                    loginResponse
                                                                            .uuid // Default to User
                                                            // UUID
                                                            if (proxy is
                                                                            io.nekohasekai.sagernet.fmt.v2ray.VMessBean &&
                                                                            !proxy.uuid
                                                                                    .isNullOrEmpty()
                                                            ) {
                                                                proxyUuid = proxy.uuid
                                                            }

                                                            // Check for existing profile by UUID
                                                            // (if we have a specific one)
                                                            if (!proxyUuid.isNullOrEmpty()) {
                                                                val allProfiles =
                                                                        withContext(
                                                                                Dispatchers.IO
                                                                        ) {
                                                                            SagerDatabase.proxyDao
                                                                                    .getByGroup(
                                                                                            targetId
                                                                                    )
                                                                        }
                                                                for (p in allProfiles) {
                                                                    if (p.uuid == proxyUuid) {
                                                                        existingProfileId = p.id
                                                                        break
                                                                    }
                                                                }
                                                            }

                                                            if (existingProfileId != 0L) {
                                                                // Profile exists, select it
                                                                lastProfileId = existingProfileId
                                                                android.util.Log.e(
                                                                        "LoginDebug",
                                                                        "Found existing profile: $lastProfileId"
                                                                )

                                                                // Update name ONLY if it's the
                                                                // primary auto-provisioned key
                                                                if (proxyUuid ==
                                                                                loginResponse
                                                                                        .key_uuid
                                                                ) {
                                                                    val existingProfile =
                                                                            ProfileManager
                                                                                    .getProfile(
                                                                                            existingProfileId
                                                                                    )
                                                                    if (existingProfile != null) {
                                                                        val bean =
                                                                                existingProfile
                                                                                        .requireBean()
                                                                        if (bean.name !=
                                                                                        "MMVPN (Auto)"
                                                                        ) {
                                                                            bean.name =
                                                                                    "MMVPN (Auto)"
                                                                            ProfileManager
                                                                                    .updateProfile(
                                                                                            existingProfile
                                                                                    )
                                                                        }
                                                                    }
                                                                }
                                                            } else {
                                                                // Create new profile
                                                                val profile =
                                                                        ProfileManager
                                                                                .createProfile(
                                                                                        targetId,
                                                                                        proxy
                                                                                )

                                                                // Set UUID
                                                                if (!proxyUuid.isNullOrEmpty()) {
                                                                    profile.uuid = proxyUuid
                                                                }

                                                                // Set Name: Only rename to "MMVPN
                                                                // (Auto)" if it matches primary key
                                                                if (proxyUuid ==
                                                                                loginResponse
                                                                                        .key_uuid
                                                                ) {
                                                                    profile.requireBean().name =
                                                                            "MMVPN (Auto)"
                                                                }
                                                                // Else keep the name from the link
                                                                // (proxy.name)

                                                                ProfileManager.updateProfile(
                                                                        profile
                                                                )
                                                                lastProfileId = profile.id
                                                                android.util.Log.e(
                                                                        "LoginDebug",
                                                                        "Created new profile: $lastProfileId"
                                                                )
                                                            }
                                                        }
                                                        DataStore.editingGroup = targetId

                                                        // Auto-select the last imported (or found)
                                                        // profile
                                                        if (lastProfileId != 0L) {
                                                            DataStore.selectedProxy = lastProfileId
                                                            DataStore.currentProfile = lastProfileId

                                                            saveUserAndRedirect(
                                                                    account.displayName ?: "",
                                                                    account.email ?: "",
                                                                    account.photoUrl?.toString(),
                                                                    "google"
                                                            )
                                                        } else {
                                                            android.util.Log.e(
                                                                    "LoginDebug",
                                                                    "No profiles were imported or found."
                                                            )
                                                            // Fallback if no profiles were imported
                                                            val bean = ShadowsocksBean()
                                                            bean.name = "MMVPN User"
                                                            bean.serverAddress = "127.0.0.1"
                                                            bean.serverPort = 8388
                                                            bean.password = "placeholder"
                                                            bean.method = "chacha20-ietf-poly1305"

                                                            val profile =
                                                                    ProfileManager.createProfile(
                                                                            0L,
                                                                            bean
                                                                    )
                                                            if (!loginResponse.uuid.isNullOrEmpty()
                                                            ) {
                                                                profile.uuid = loginResponse.uuid
                                                            }
                                                            ProfileManager.updateProfile(profile)
                                                            DataStore.selectedProxy = profile.id
                                                            DataStore.currentProfile = profile.id

                                                            // Save user info
                                                            prefs.edit().apply {
                                                                putString(
                                                                        "user_name",
                                                                        account.displayName
                                                                )
                                                                putString(
                                                                        "user_email",
                                                                        account.email
                                                                )
                                                                putString(
                                                                        "user_photo",
                                                                        account.photoUrl?.toString()
                                                                )
                                                                apply()
                                                            }

                                                            val intent =
                                                                    Intent(
                                                                            this@LoginActivity,
                                                                            MainActivity::class.java
                                                                    )
                                                            intent.putExtra(
                                                                    "EXTRA_NAV_ID",
                                                                    R.id.nav_mmvpn_status
                                                            )
                                                            intent.putExtra(
                                                                    "USER_NAME",
                                                                    account.displayName
                                                            )
                                                            intent.putExtra(
                                                                    "USER_EMAIL",
                                                                    account.email
                                                            )
                                                            intent.putExtra(
                                                                    "USER_PHOTO",
                                                                    account.photoUrl?.toString()
                                                            )
                                                            startActivity(intent)
                                                            finish()
                                                        }
                                                    } else {
                                                        throw Exception(
                                                                "Failed to parse provided key"
                                                        )
                                                    }
                                                } else {
                                                    // Fallback to dummy profile if no key returned
                                                    val bean = ShadowsocksBean()
                                                    bean.name = "MMVPN User"
                                                    bean.serverAddress = "127.0.0.1"
                                                    bean.serverPort = 8388
                                                    bean.password = "placeholder"
                                                    bean.method = "chacha20-ietf-poly1305"

                                                    val profile =
                                                            ProfileManager.createProfile(0L, bean)
                                                    profile.uuid = loginResponse.uuid
                                                    ProfileManager.updateProfile(profile)
                                                    DataStore.currentProfile = profile.id

                                                    // Save user info
                                                    prefs.edit().apply {
                                                        putString("user_name", account.displayName)
                                                        putString("user_email", account.email)
                                                        putString(
                                                                "user_photo",
                                                                account.photoUrl?.toString()
                                                        )
                                                        apply()
                                                    }

                                                    val intent =
                                                            Intent(
                                                                    this@LoginActivity,
                                                                    MainActivity::class.java
                                                            )
                                                    intent.putExtra(
                                                            "EXTRA_NAV_ID",
                                                            R.id.nav_mmvpn_status
                                                    )
                                                    intent.putExtra(
                                                            "USER_NAME",
                                                            account.displayName
                                                    )
                                                    intent.putExtra("USER_EMAIL", account.email)
                                                    intent.putExtra(
                                                            "USER_PHOTO",
                                                            account.photoUrl?.toString()
                                                    )
                                                    startActivity(intent)
                                                    finish()
                                                }
                                            } catch (e: Exception) {
                                                android.util.Log.e(
                                                        "LoginDebug",
                                                        "Profile Setup Failed",
                                                        e
                                                )
                                                Toast.makeText(
                                                                this@LoginActivity,
                                                                "Profile Setup Failed: ${e.message}",
                                                                Toast.LENGTH_SHORT
                                                        )
                                                        .show()
                                            }
                                        }
                                    } else {
                                        android.util.Log.e("LoginDebug", "LoginResponse is null")
                                    }
                                } else {
                                    android.util.Log.e(
                                            "LoginDebug",
                                            "Server Auth Failed: ${response.code()}"
                                    )
                                    binding.signInButton.isEnabled = true
                                    // Restore UI state so user can try again
                                    val savedName = prefs.getString("user_name", null)
                                    if (savedName != null) {
                                        val savedPhoto = prefs.getString("user_photo", null)
                                        showContinueState(savedName, savedPhoto)
                                    } else {
                                        showLoginState()
                                    }

                                    Toast.makeText(
                                                    this@LoginActivity,
                                                    "Server Auth Failed: ${response.code()}",
                                                    Toast.LENGTH_SHORT
                                            )
                                            .show()
                                }
                            }

                            override fun onFailure(call: Call<LoginResponse>, t: Throwable) {
                                binding.signInButton.isEnabled = true
                                // Restore UI state so user can try again
                                val savedName = prefs.getString("user_name", null)
                                if (savedName != null) {
                                    val savedPhoto = prefs.getString("user_photo", null)
                                    showContinueState(savedName, savedPhoto)
                                } else {
                                    showLoginState()
                                }

                                android.util.Log.e("LoginActivity", "Sign-in error", t)
                                Toast.makeText(
                                                this@LoginActivity,
                                                "Network Error: ${t.message}",
                                                Toast.LENGTH_SHORT
                                        )
                                        .show()
                            }
                        }
                )
    }

    private fun testConnection() {
        ApiClient.service
                .ping()
                .enqueue(
                        object : Callback<okhttp3.ResponseBody> {
                            override fun onResponse(
                                    call: Call<okhttp3.ResponseBody>,
                                    response: Response<okhttp3.ResponseBody>
                            ) {
                                if (response.isSuccessful) {
                                    Toast.makeText(
                                                    this@LoginActivity,
                                                    "Server Online ✅",
                                                    Toast.LENGTH_SHORT
                                            )
                                            .show()
                                } else {
                                    Toast.makeText(
                                                    this@LoginActivity,
                                                    "Server Error: ${response.code()}",
                                                    Toast.LENGTH_LONG
                                            )
                                            .show()
                                }
                            }

                            override fun onFailure(call: Call<okhttp3.ResponseBody>, t: Throwable) {
                                android.util.Log.e("LoginActivity", "Connection Test Failed", t)
                                Toast.makeText(
                                                this@LoginActivity,
                                                "Cannot Reach Server: ${t.message}",
                                                Toast.LENGTH_LONG
                                        )
                                        .show()
                            }
                        }
                )
    }

    private fun checkPhonePermissionAndLogin() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_NUMBERS) !=
                        PackageManager.PERMISSION_GRANTED &&
                        ContextCompat.checkSelfPermission(
                                this,
                                Manifest.permission.READ_PHONE_STATE
                        ) != PackageManager.PERMISSION_GRANTED
        ) {

            ActivityCompat.requestPermissions(
                    this,
                    arrayOf(
                            Manifest.permission.READ_PHONE_NUMBERS,
                            Manifest.permission.READ_PHONE_STATE
                    ),
                    RC_PHONE_PERM
            )
        } else {
            performPhoneLogin()
        }
    }

    override fun onRequestPermissionsResult(
            requestCode: Int,
            permissions: Array<out String>,
            grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == RC_PHONE_PERM) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                performPhoneLogin()
            } else {
                Toast.makeText(
                                this,
                                "Permission Denied: Cannot read phone number",
                                Toast.LENGTH_SHORT
                        )
                        .show()
            }
        }
    }

    private fun performPhoneLogin() {
        binding.signInPhoneButton.isEnabled = false

        val phoneNumbers = getAllPhoneNumbers()

        when {
            phoneNumbers.isEmpty() -> {
                runOnUiThread {
                    Toast.makeText(this, "Could not read phone number from SIM", Toast.LENGTH_LONG)
                            .show()
                    resetButtons()
                }
            }
            phoneNumbers.size == 1 -> {
                // Single SIM - proceed directly
                loginWithPhoneNumber(phoneNumbers[0])
            }
            else -> {
                // Multiple SIMs - show selection dialog
                runOnUiThread { showPhoneNumberSelectionDialog(phoneNumbers) }
            }
        }
    }

    private fun showPhoneNumberSelectionDialog(phoneNumbers: List<String>) {
        val items = phoneNumbers.toTypedArray()

        androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("Select SIM Card")
                .setItems(items) { dialog, which ->
                    val selectedNumber = phoneNumbers[which]
                    binding.signInPhoneButton.isEnabled = false
                    loginWithPhoneNumber(selectedNumber)
                }
                .setOnCancelListener { resetButtons() }
                .show()
    }

    private fun loginWithPhoneNumber(phoneNumber: String) {
        val phoneLoginRequest = PhoneLoginRequest(phone = phoneNumber)

        ApiClient.service
                .phoneLogin(phoneLoginRequest)
                .enqueue(
                        object : Callback<LoginResponse> {
                            override fun onResponse(
                                    call: Call<LoginResponse>,
                                    response: Response<LoginResponse>
                            ) {
                                runOnUiThread {
                                    if (response.isSuccessful) {
                                        val loginResponse = response.body()
                                        if (loginResponse != null) {
                                            handleLoginSuccess(
                                                    loginResponse,
                                                    phoneNumber,
                                                    phoneNumber
                                            )
                                        } else {
                                            Toast.makeText(
                                                            this@LoginActivity,
                                                            "Login Failed: Empty Response",
                                                            Toast.LENGTH_SHORT
                                                    )
                                                    .show()
                                            resetButtons()
                                        }
                                    } else {
                                        Toast.makeText(
                                                        this@LoginActivity,
                                                        "Login failed: ${response.code()}",
                                                        Toast.LENGTH_LONG
                                                )
                                                .show()
                                        resetButtons()
                                    }
                                }
                            }

                            override fun onFailure(call: Call<LoginResponse>, t: Throwable) {
                                runOnUiThread {
                                    Toast.makeText(
                                                    this@LoginActivity,
                                                    "Network error: ${t.message}",
                                                    Toast.LENGTH_LONG
                                            )
                                            .show()
                                    resetButtons()
                                }
                            }
                        }
                )
    }

    private fun resetButtons() {
        binding.signInButton.isEnabled = true
        binding.signInPhoneButton.isEnabled = true
    }

    private fun getAllPhoneNumbers(): List<String> {
        val phoneNumbers = mutableListOf<String>()
        try {
            val subscriptionManager = getSystemService(SubscriptionManager::class.java)
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_NUMBERS) !=
                            PackageManager.PERMISSION_GRANTED &&
                            ActivityCompat.checkSelfPermission(
                                    this,
                                    Manifest.permission.READ_PHONE_STATE
                            ) != PackageManager.PERMISSION_GRANTED
            ) {
                // Permissions not granted, return empty list.
                // The checkPhonePermissionAndLogin() method should handle requesting permissions.
                return emptyList()
            }

            val activeSubscriptionInfoList = subscriptionManager.activeSubscriptionInfoList
            if (activeSubscriptionInfoList != null && activeSubscriptionInfoList.isNotEmpty()) {
                for (i in 0 until activeSubscriptionInfoList.size) {
                    val subscriptionInfo = activeSubscriptionInfoList[i]
                    val number = subscriptionInfo.number
                    if (!number.isNullOrEmpty()) {
                        phoneNumbers.add(number)
                    }
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("LoginActivity", "Error reading phone numbers", e)
        }
        return phoneNumbers
    }

    private fun handleLoginSuccess(loginResponse: LoginResponse, name: String, email: String) {
        lifecycleScope.launch {
            try {
                val key = loginResponse.key
                if (!key.isNullOrEmpty()) {
                    val proxies =
                            withContext(Dispatchers.Default) {
                                io.nekohasekai.sagernet.group.RawUpdater.parseRaw(key)
                            }

                    if (!proxies.isNullOrEmpty()) {
                        val targetId = DataStore.selectedGroupForImport()
                        var lastProfileId = 0L

                        for (proxy in proxies) {
                            val profile = ProfileManager.createProfile(targetId, proxy)
                            profile.uuid = loginResponse.uuid
                            if (!loginResponse.key_uuid.isNullOrEmpty()) {
                                profile.requireBean().name = "MMVPN (Auto)"
                            }
                            ProfileManager.updateProfile(profile)
                            lastProfileId = profile.id
                        }

                        DataStore.editingGroup = targetId
                        DataStore.selectedProxy = lastProfileId
                        DataStore.currentProfile = lastProfileId

                        saveUserAndRedirect(name, email, null, "phone")
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("LoginActivity", "Profile Setup Failed", e)
            }
        }
    }

    private fun saveUserAndRedirect(
            name: String,
            email: String,
            photo: String?,
            loginType: String
    ) {
        prefs.edit().apply {
            putString("user_name", name)
            putString("user_email", email)
            putString("user_photo", photo)
            putString("login_type", loginType)
            apply()
        }
        val intent = Intent(this@LoginActivity, MainActivity::class.java)
        intent.putExtra("EXTRA_NAV_ID", R.id.nav_mmvpn_status)
        intent.putExtra("USER_NAME", name)
        intent.putExtra("USER_EMAIL", email)
        intent.putExtra("USER_PHOTO", photo)
        startActivity(intent)
        finish()
    }
}
