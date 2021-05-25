package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef._
import org.aeonbits.owner.ConfigFactory

class MaxPerf_CloseModel_Levels extends Simulation {
  val cfg: TestConfig = ConfigFactory.create(classOf[TestConfig])

  // Шаг нагрузки (примерный) - лимит времени на выполнение сценария
  val pase_sec = cfg.pase_sec()

  // Количество виртуальных пользователей (с округлением)
  val virtual_users_count : Int = (cfg.tps() * pase_sec).toInt

  // Шаг нагрузки (с учетом округления количества потоков)
  val pase_ms = 1000.0 * virtual_users_count / cfg.tps();

  // Длительность теста
  val duration_sec = cfg.duration()

  // Количество уровней, длительность уровня, ...
  val numberOfSteps = 4
  val levelDuration = (duration_sec / numberOfSteps).toInt
  val rampDuration = 0
  val initialConcurrentUsers = 1

  // Сценарий работы виртульного пользователя -
  // бесконечный запуск сценария каждые pase_ms миллисекунд
  val userOpenMainPage : ScenarioBuilder =
  scenario(cfg.title())
    .forever(
      pace(pase_ms millisecond)
        .exec(
          SimpleScenario.simpleScenario()
        )
    )

  setUp(
    userOpenMainPage
      .inject(
        incrementConcurrentUsers(virtual_users_count)
          .times(numberOfSteps)
          .eachLevelLasting(levelDuration)
          .separatedByRampsLasting(rampDuration)
          .startingFrom(initialConcurrentUsers)
      )
      .protocols(Protocol.httpConf)
  )
}
