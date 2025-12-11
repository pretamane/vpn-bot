package io.nekohasekai.sagernet.data.model

import com.google.gson.annotations.SerializedName

data class UserStatus(
        @SerializedName("uuid") val uuid: String,
        @SerializedName("isActive") val isActive: Boolean,
        @SerializedName("expiryDate") val expiryDate: String,
        @SerializedName("dataLimitGb") val dataLimitGb: Float,
        @SerializedName("dailyUsageBytes") val dailyUsageBytes: Long,
        @SerializedName("protocol") val protocol: String,
        @SerializedName("usagePercentage") val usagePercentage: Double = 0.0,
        @SerializedName("inGracePeriod") val inGracePeriod: Boolean = false,
        @SerializedName("graceRemainingHours") val graceRemainingHours: Double = 0.0,
        @SerializedName("warningsSent") val warningsSent: List<String> = emptyList()
)
