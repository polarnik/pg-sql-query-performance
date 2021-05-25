package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef._
import org.aeonbits.owner.ConfigFactory

class Stable_CloseModel_RPS extends Simulation {

  // Сценарий работы виртульного пользователя -
  // бесконечный запуск сценария без пауз, шаг нагрузки в явном виде можно не задавать,
  // нагрузка будет ограничена на уровне количества запросов в сек через throttle
  val userOpenMainPage : ScenarioBuilder =
  scenario(Protocol.cfg.title())
    .forever(
      SimpleScenario.simpleScenario()
    )

  // Количество виртуальных пользователей - размер пула потоков
  // можно задавать с запасом, это неточное значение, а значение большее, чем нужно
  // должно быть больше, чем Protocol.cfg.tps() * pase_sec, где pase_sec - размер шага нагрузки
  val virtual_users_count : Int = Protocol.cfg.thread_count()

  // Количество запросов в одной итерации
  val userOpenMainPage_Requests = SimpleScenario.getRequestCount()

  val maxRPS = (Protocol.cfg.tps() * userOpenMainPage_Requests ).toInt

  // Длительность теста
  val duration_sec = Protocol.cfg.duration()

  setUp(
    userOpenMainPage
      .inject(
        rampConcurrentUsers(virtual_users_count) to (virtual_users_count) during (duration_sec seconds)
      )
      .protocols(Protocol.httpConf)
      .throttle(
        jumpToRps(maxRPS),
        holdFor(duration_sec seconds)
      )
  )
}
