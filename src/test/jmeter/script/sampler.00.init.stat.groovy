import java.util.concurrent.*

ConcurrentHashMap<String,Integer> stat = new ConcurrentHashMap<String,Integer>()
props.put('stat', stat)
SampleResult.setIgnore();