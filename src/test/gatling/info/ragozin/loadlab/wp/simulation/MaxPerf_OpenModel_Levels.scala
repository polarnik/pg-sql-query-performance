package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef.{incrementUsersPerSec, _}
import org.aeonbits.owner.ConfigFactory

class MaxPerf_OpenModel_Levels extends Simulation {
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

  // Количество уровней, длительность уровня, ...
  val numberOfSteps = 4
  val incrementUsersPerSec_int = (maxTPS / numberOfSteps).toInt
  val levelDuration = (duration_sec / numberOfSteps).toInt
  val rampDuration = 0
  val initialUsersPerSec = 1

  setUp(
    userOpenMainPage
      .inject(
        incrementUsersPerSec(incrementUsersPerSec_int)
          .times(numberOfSteps)
          .eachLevelLasting(levelDuration)
          .separatedByRampsLasting(rampDuration)
          .startingFrom(initialUsersPerSec)
      )
      .protocols(Protocol.httpConf)
  )
}
