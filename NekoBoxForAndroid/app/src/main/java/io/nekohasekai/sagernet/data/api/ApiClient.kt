package io.nekohasekai.sagernet.data.api

import io.nekohasekai.sagernet.SagerNet
import java.net.Socket
import java.util.concurrent.TimeUnit
import javax.net.SocketFactory
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val BASE_URL = "http://43.205.90.213:8082/"

    val service: MMVPNService by lazy {
        val client =
                OkHttpClient.Builder()
                        .connectTimeout(30, TimeUnit.SECONDS)
                        .readTimeout(30, TimeUnit.SECONDS)
                        .writeTimeout(30, TimeUnit.SECONDS)
                        .socketFactory(
                                object : javax.net.SocketFactory() {
                                    override fun createSocket(): java.net.Socket {
                                        val network =
                                                io.nekohasekai.sagernet.SagerNet.underlyingNetwork
                                        return if (network != null) {
                                            network.socketFactory.createSocket()
                                        } else {
                                            javax.net.SocketFactory.getDefault().createSocket()
                                        }
                                    }

                                    override fun createSocket(
                                            host: String?,
                                            port: Int
                                    ): java.net.Socket {
                                        val network =
                                                io.nekohasekai.sagernet.SagerNet.underlyingNetwork
                                        return if (network != null) {
                                            network.socketFactory.createSocket(host, port)
                                        } else {
                                            javax.net.SocketFactory.getDefault()
                                                    .createSocket(host, port)
                                        }
                                    }

                                    override fun createSocket(
                                            host: String?,
                                            port: Int,
                                            localHost: java.net.InetAddress?,
                                            localPort: Int
                                    ): java.net.Socket {
                                        val network =
                                                io.nekohasekai.sagernet.SagerNet.underlyingNetwork
                                        return if (network != null) {
                                            network.socketFactory.createSocket(
                                                    host,
                                                    port,
                                                    localHost,
                                                    localPort
                                            )
                                        } else {
                                            javax.net.SocketFactory.getDefault()
                                                    .createSocket(host, port, localHost, localPort)
                                        }
                                    }

                                    override fun createSocket(
                                            host: java.net.InetAddress?,
                                            port: Int
                                    ): java.net.Socket {
                                        val network =
                                                io.nekohasekai.sagernet.SagerNet.underlyingNetwork
                                        return if (network != null) {
                                            network.socketFactory.createSocket(host, port)
                                        } else {
                                            javax.net.SocketFactory.getDefault()
                                                    .createSocket(host, port)
                                        }
                                    }

                                    override fun createSocket(
                                            address: java.net.InetAddress?,
                                            port: Int,
                                            localAddress: java.net.InetAddress?,
                                            localPort: Int
                                    ): java.net.Socket {
                                        val network =
                                                io.nekohasekai.sagernet.SagerNet.underlyingNetwork
                                        return if (network != null) {
                                            network.socketFactory.createSocket(
                                                    address,
                                                    port,
                                                    localAddress,
                                                    localPort
                                            )
                                        } else {
                                            javax.net.SocketFactory.getDefault()
                                                    .createSocket(
                                                            address,
                                                            port,
                                                            localAddress,
                                                            localPort
                                                    )
                                        }
                                    }
                                }
                        )
                        .build()

        Retrofit.Builder()
                .baseUrl(BASE_URL)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(MMVPNService::class.java)
    }
}
