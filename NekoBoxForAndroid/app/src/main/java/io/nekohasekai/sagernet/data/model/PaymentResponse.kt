package io.nekohasekai.sagernet.data.model

import com.google.gson.annotations.SerializedName

data class PaymentResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String,
    @SerializedName("key") val key: String,
    @SerializedName("protocol") val protocol: String,
    @SerializedName("transaction_id") val transactionId: String
)
