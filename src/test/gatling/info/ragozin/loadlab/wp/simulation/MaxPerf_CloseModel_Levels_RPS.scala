package info.ragozin.loadlab.wp.simulation

import io.gatling.core.structure.ScenarioBuilder
import info.ragozin.loadlab.wp.process.SimpleScenario
import info.ragozin.loadlab.wp.setting.{Protocol, TestConfig}

import scala.concurrent.duration._
import io.gatling.core.Predef._
import org.aeonbits.owner.ConfigFactory

class MaxPerf_CloseModel_Levels_RPS extends Simulation {
  val cfg: TestConfig = ConfigFactory.create(classOf[TestConfig])

  /*
                     +-----+ - rps = tps * SimpleScenario.getRequestCount()
               +-----+     |
         +-----+           |
   +-----+                 |
   |<------ duration ----->| - rps = 0
   */

  // Сценарий работы виртульного пользователя -
  // бесконечный запуск сценария без пауз, шаг нагрузки в явном виде можно не задавать,
  // нагрузка будет ограничена на уровне количества запросов в сек через throttle
  val userOpenMainPage : ScenarioBuilder =
  scenario(cfg.title())
    .forever(
      SimpleScenario.simpleScenario()
    )

  // Количество виртуальных пользователей - размер пула потоков
  // можно задавать с запасом, это неточное значение, а значение большее, чем нужно
  // должно быть больше, чем Protocol.cfg.tps() * pase_sec, где pase_sec - размер шага нагрузки
  val virtual_users_count : Int = cfg.thread_count()

  // Количество запросов в одной итерации
  val userOpenMainPage_Requests = SimpleScenario.getRequestCount()

  val maxRPS = cfg.tps() * userOpenMainPage_Requests

  // Длительность теста
  val duration_sec = cfg.duration()

  // Количество уровней, длительность уровня, ...
  val numberOfSteps = 4.0
  val levelDuration = (duration_sec / numberOfSteps).toInt
  val rampDuration = 0
  val initialConcurrentUsers = 1

  // Уровень в RPS
  val levelRPS = (maxRPS / numberOfSteps).toInt

  setUp(
    userOpenMainPage
      .inject(
        rampConcurrentUsers(initialConcurrentUsers) to (virtual_users_count) during (duration_sec seconds)
      )
      .protocols(Protocol.httpConf)
      .throttle(
        reachRps(levelRPS)   in (rampDuration seconds), holdFor(levelDuration seconds),
        reachRps(levelRPS*2) in (rampDuration seconds), holdFor(levelDuration seconds),
        reachRps(levelRPS*3) in (rampDuration seconds), holdFor(levelDuration seconds),
        reachRps(levelRPS*4) in (rampDuration seconds), holdFor(levelDuration seconds)
      )
  )
}
