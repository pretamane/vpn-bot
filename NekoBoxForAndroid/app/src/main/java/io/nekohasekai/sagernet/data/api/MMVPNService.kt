package io.nekohasekai.sagernet.data.api

import io.nekohasekai.sagernet.data.model.UserStatus
import io.nekohasekai.sagernet.data.model.GoogleLoginRequest
import io.nekohasekai.sagernet.data.model.LoginResponse
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Multipart
import retrofit2.http.Part
import okhttp3.MultipartBody
import okhttp3.RequestBody
import io.nekohasekai.sagernet.data.model.PaymentResponse

interface MMVPNService {
    @GET("/api/status/{uuid}")
    fun getUserStatus(@Path("uuid") uuid: String): Call<UserStatus>

    @GET("/api/keys/{uuid}")
    fun getUserKeys(@Path("uuid") uuid: String): Call<io.nekohasekai.sagernet.data.model.UserKeysResponse>

    @POST("/api/auth/google")
    fun googleLogin(@Body request: GoogleLoginRequest): Call<LoginResponse>

    @POST("/api/auth/phone")
    fun phoneLogin(@Body request: io.nekohasekai.sagernet.data.model.PhoneLoginRequest): Call<LoginResponse>

    @GET("/api/bot/config")
    fun getBotConfig(): Call<io.nekohasekai.sagernet.data.model.BotConfig>

    @Multipart
    @POST("/api/payment/verify")
    fun verifyPayment(
        @Part file: MultipartBody.Part,
        @Part("uuid") uuid: RequestBody,
        @Part("protocol") protocol: RequestBody
    ): Call<PaymentResponse>
    @GET("/")
    fun ping(): Call<okhttp3.ResponseBody>
}
