package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef._
import org.aeonbits.owner.ConfigFactory

class Stable_OpenModel_RPS extends Simulation {
  // Сценарий работы виртульного пользователя -
  // одна итерация
  val userOpenMainPage : ScenarioBuilder =
  scenario(Protocol.cfg.title())
    .exec(
      SimpleScenario.simpleScenario()
    )

  // Количество запросов в одной итерации
  val userOpenMainPage_Requests = SimpleScenario.getRequestCount()

  val maxTPS = Protocol.cfg.tps()
  val maxRPS = (maxTPS * userOpenMainPage_Requests ).toInt

  // Длительность теста
  val duration_sec = Protocol.cfg.duration()

  setUp(
    userOpenMainPage
      .inject(
        //rampUsersPerSec(maxTPS) to (maxTPS) during (duration_sec seconds)
        constantUsersPerSec(maxTPS) during (duration_sec seconds)
      )
      .protocols(Protocol.httpConf)
      .throttle(
        jumpToRps(maxRPS),
        holdFor(duration_sec seconds)
      )
  )
}
