package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef._
import org.aeonbits.owner.ConfigFactory

class Stable_CloseModel extends Simulation {

  // Шаг нагрузки (примерный) - лимит времени на выполнение сценария
  val pase_sec = 5.0

  // Количество виртуальных пользователей (с округлением)
  val virtual_users_count : Int = (Protocol.cfg.tps() * pase_sec).toInt

  // Шаг нагрузки (с учетом округления количества потоков)
  val pase_ms = 1000.0 * virtual_users_count / Protocol.cfg.tps();

  // Длительность теста
  val duration_sec = Protocol.cfg.duration()

  // Сценарий работы виртульного пользователя -
  // бесконечный запуск сценария каждые pase_ms миллисекунд
  val userOpenMainPage : ScenarioBuilder =
  scenario(Protocol.cfg.title())
    .forever(
      pace(pase_ms millisecond)
        .exec(
          SimpleScenario.simpleScenario()
        )
    )

  setUp(
    userOpenMainPage
      .inject(
        constantConcurrentUsers(virtual_users_count) during (duration_sec seconds)
      )
      .protocols(Protocol.httpConf)
  )

}
