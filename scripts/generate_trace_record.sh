#! /bin/bash

# Get current time in nanoseconds  
CURRENT_TIME_NANOS=$(date +%s)000000000  
END_TIME_NANOS=$((CURRENT_TIME_NANOS + 1000000000))  
ID=$(date +%Y%m%d%H%M%S%N)

#         1         2         3
#12345678901234567890123456789012
#aaaabbbbccccdddd1111222233334444
#20251207212933230959718000000000

curl -v -X POST http://localhost:4318/v1/traces -H "Content-Type: application/json"   -d "{  \"resourceSpans\": [{  \"resource\": {  \"attributes\": [{  \"key\": \"service.name\",  \"value\": {\"stringValue\": \"my-test-service\"}  }]  },  \"scopeSpans\": [{  \"scope\": {  \"name\": \"manual-test\"  },  \"spans\": [{  \"traceId\": \"${ID}000000000\",  \"spanId\": \"1111222233334444\",  \"name\": \"current-time-test\",  \"kind\": 1,  \"startTimeUnixNano\": \"${CURRENT_TIME_NANOS}\",  \"endTimeUnixNano\": \"${END_TIME_NANOS}\",  \"status\": {  \"code\": 0  }  }]  }]  }]  }"  
