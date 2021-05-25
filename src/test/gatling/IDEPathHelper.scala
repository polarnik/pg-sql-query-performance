object IDEPathHelper {

  val projectRootDir = java.nio.file.Paths.get(System.getProperty("user.dir"))
  val sourcesDirectory = projectRootDir.resolve("src/test/scala")
  val simulationsDirectory = sourcesDirectory.resolve("io/qaload/gatling/reportExample/simulation")
  val resourcesDirectory = projectRootDir.resolve("src/test/resources")
  val targetDirectory = projectRootDir.resolve("target")
  val binariesDirectory = targetDirectory.resolve("test-classes")

  val resultsDirectory = targetDirectory.resolve("gatling")
}