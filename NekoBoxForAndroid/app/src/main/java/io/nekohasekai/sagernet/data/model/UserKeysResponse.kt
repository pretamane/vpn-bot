package io.nekohasekai.sagernet.data.model

data class VpnKeyItem(
    val id: Int,
    val user_uuid: String,
    val key_name: String,
    val protocol: String,
    val server_address: String,
    val server_port: Int,
    val key_uuid: String,
    val key_password: String?,
    val config_link: String?,
    val is_active: Int,
    val created_at: String,
    val expires_at: String?
)

data class UserKeysResponse(
    val keys: List<VpnKeyItem>
)
