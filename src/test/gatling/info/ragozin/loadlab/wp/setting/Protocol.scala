package info.ragozin.loadlab.wp.setting

import com.softwaremill.quicklens
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import io.gatling.http.protocol.{HttpProxy, Proxy}
import com.softwaremill.quicklens._
import io.gatling.http.client.proxy.ProxyServer

import scala.concurrent.duration._

object Protocol {

  import org.aeonbits.owner.ConfigFactory

  val cfg: TestConfig = ConfigFactory.create(classOf[TestConfig])

  def httpProxy: Option[ProxyServer] = {
    if(cfg.httpProxyHost() != "") {
      val proxy = Proxy(
        host = cfg.httpProxyHost(),
        port = cfg.httpProxyPort(),
        securePort = cfg.httpProxyPort(),
        proxyType = HttpProxy
      )
      return Some(proxy.proxyServer)
    }
    else
      return None
  }

  /*
  Настройки для HTTP
  */
  val httpConf = http
    .baseUrl(s"${cfg.scheme()}://${cfg.hostname()}:${cfg.port()}") // Here is the root for all relative URLs
    .acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8") // Here are the common headers
    .doNotTrackHeader("1")
    .acceptEncodingHeader("gzip, deflate, br")
    .acceptLanguageHeader("en-US,en;q=0.5")
    .inferHtmlResources()
    .nameInferredHtmlResources(_ => "static")
    .shareConnections
    .maxConnectionsPerHostLikeFirefox
    .header("Upgrade-Insecure-Requests", "1")
    //.header("X-Scenario", "${scenario}")
    //.header("X-userId", "${userId}")
    .userAgentHeader("Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:16.0) Gecko/20100101 Firefox/16.0")
    .disableWarmUp
    .noProxyFor(cfg.noProxyFor())
    .build
    .modify(_.proxyPart.proxy).setTo(httpProxy)
}
