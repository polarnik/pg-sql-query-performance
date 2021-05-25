package info.ragozin.loadlab.wp.setting

import java.lang.reflect.Method
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.{Calendar, Date, GregorianCalendar}

import org.aeonbits.owner.Config
import org.aeonbits.owner.Config._
import org.aeonbits.owner.Converter
import org.aeonbits.owner._
import org.aeonbits.owner.Converter._
import scala.math._

@LoadPolicy(LoadType.MERGE)
@Sources (
  Array(
    "classpath:user.properties",
    "file:${user.home}/user.properties",
    //"system:env",
    "system:properties"
  )
)
trait TestConfig extends Config {
  @Key("run")
  @DefaultValue("")
  @ConverterClass(classOf[RunIdConvertor])
  def run(): String

  @Key("host")
  @DefaultValue("")
  @ConverterClass(classOf[HostConvertor])
  def host(): String

  @Key("http.scheme")
  @DefaultValue("http")
  def scheme(): String

  @Key("host.name")
  @DefaultValue("wp.loadlab.ragozin.info")
  def hostname(): String

  @Key("http.port")
  @DefaultValue("80")
  def port(): Int

  @Key("http.proxy.host")
  @DefaultValue("")
  def httpProxyHost(): String

  @Key("http.proxy.port")
  @DefaultValue("")
  def httpProxyPort(): Int

  @Key("http.proxy.noProxyFor")
  @DefaultValue("google.com, yandex.ru")
  def noProxyFor(): String

  @Key("isStable")
  @DefaultValue("0")
  def isStable(): Int

  @Key("isMaxPerf")
  @DefaultValue("0")
  def isMaxPerf(): Int

  @Key("duration")
  @DefaultValue("0")
  def duration(): Int

  @Key("tps")
  @DefaultValue("0.0")
  def tps(): Double

  @Key("thread_count")
  @DefaultValue("0")
  def thread_count(): Int

  @Key("pase_sec")
  @DefaultValue("0.0")
  def pase_sec(): Double

  @Key("title")
  @DefaultValue("")
  def title(): String
}

class RunIdConvertor extends Converter[String] {

  def getRoundStartTime(roundMinute: Int): String = {
    val dateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd_HH")
    val startTime = OffsetDateTime.now().format(dateTimeFormatter)
    val date = new Date()                  // given date
    val calendar = new GregorianCalendar() // creates a new calendar instance
    calendar.setTime(date)                 // assigns calendar to given date
    val minute = calendar.get(Calendar.MINUTE)
    val minuteRound = round(floor( 1.0d * minute / roundMinute) * roundMinute)
    s"${startTime}:${"%02d".format(minuteRound)}"
  }

  def convert(targetMethod: Method, text: String): String = {
    if (text != "") {
      text
    } else {
      getRoundStartTime(5)
    }
  }
}

class HostConvertor extends Converter[String] {

  def getHostName: String = {
    import java.net.InetAddress
    import java.net.UnknownHostException

    try {
      val result = InetAddress.getLocalHost.getHostName
      if (! result.isEmpty) return result
    } catch {
      case e: UnknownHostException =>
    }

    var host = System.getenv("COMPUTERNAME")
    if (host != null) return host
    host = System.getenv("HOSTNAME")
    if (host != null) return host

    return null
  }

  def getClearHostName: String = {
    val hostName = getHostName

    return hostName
      .replace(' ', '_')
      .replace('.', '_')
  }

  def convert(targetMethod: Method, text: String): String = {
    if (text != "") {
      text
    } else {
      getClearHostName
    }
  }
}