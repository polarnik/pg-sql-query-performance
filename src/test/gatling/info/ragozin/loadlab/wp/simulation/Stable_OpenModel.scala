package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef._
import org.aeonbits.owner.ConfigFactory

class Stable_OpenModel extends Simulation {
  // Сценарий работы виртульного пользователя -
  // одна итерация
  val userOpenMainPage : ScenarioBuilder =
  scenario(Protocol.cfg.title())
    .exec(
      SimpleScenario.simpleScenario()
    )

  val maxTPS = Protocol.cfg.tps()

  // Длительность теста
  val duration_sec = Protocol.cfg.duration()

  setUp(
    userOpenMainPage
      .inject(
        constantUsersPerSec(maxTPS) during (duration_sec seconds)
      )
      .protocols(Protocol.httpConf)
  )
}
