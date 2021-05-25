FROM maven:3.8.1-openjdk-11
COPY pom.xml /tmp/
COPY src /tmp/src/
WORKDIR /tmp/
RUN mvn clean verify clean -P jmeter,Stable -Dtps=0.0
RUN sh -c "rm -rf /tmp/src; rm -f /tmp/pom.xml"
