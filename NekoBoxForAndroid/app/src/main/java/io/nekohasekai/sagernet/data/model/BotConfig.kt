package io.nekohasekai.sagernet.data.model

data class BotConfig(
    val payment: PaymentConfig,
    val support: SupportConfig,
    val protocols: List<ProtocolConfig>
)

data class PaymentConfig(
    val kbz: String,
    val wave: String,
    val price: String
)

data class SupportConfig(
    val contact: String
)

data class ProtocolConfig(
    val code: String,
    val name: String
)
