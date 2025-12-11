package io.nekohasekai.sagernet.data.model

import com.google.gson.annotations.SerializedName

data class GoogleLoginRequest(
    @SerializedName("token") val token: String
)

data class LoginResponse(
    @SerializedName("uuid") val uuid: String,
    @SerializedName("email") val email: String,
    @SerializedName("key") val key: String? = null,
    val key_uuid: String? = null
)

data class UserStatusResponse(
    @SerializedName("uuid") val uuid: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("expiry_date") val expiryDate: String,
    @SerializedName("data_limit_gb") val dataLimitGb: Double,
    @SerializedName("daily_usage_bytes") val dailyUsageBytes: Long,
    @SerializedName("protocol") val protocol: String,
    @SerializedName("usage_percentage") val usagePercentage: Double = 0.0,
    @SerializedName("in_grace_period") val inGracePeriod: Boolean = false,
    @SerializedName("grace_remaining_hours") val graceRemainingHours: Double = 0.0,
    @SerializedName("warnings_sent") val warningsSent: List<String> = emptyList()
)
