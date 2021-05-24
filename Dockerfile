FROM maven:3.8.1-openjdk-11
COPY ../pom.xml /tmp/
COPY ../src /tmp/src/
WORKDIR /tmp/
RUN mvn jmeter:configure
