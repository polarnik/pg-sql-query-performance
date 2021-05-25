package info.ragozin.loadlab.wp.process

import io.gatling.core.Predef._
import io.gatling.core.structure.{ChainBuilder, ScenarioBuilder}
import io.gatling.http.Predef._
import java.io.{BufferedOutputStream, File, FileOutputStream}

import scala.concurrent.duration._

object SimpleScenario {

  def getRequestCount(): Int = { 2 }

  def simpleScenario(): ChainBuilder =
      exec(
        http("/ (GET)").get("/")
      )
      .exec(
        http("/40x.html (GET)").get("/40x.html")
      )

}