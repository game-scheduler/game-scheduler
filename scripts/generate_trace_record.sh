#! /bin/bash
# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



# Get current time in nanoseconds
CURRENT_TIME_NANOS=$(date +%s)000000000
END_TIME_NANOS=$((CURRENT_TIME_NANOS + 1000000000))
ID=$(date +%Y%m%d%H%M%S%N)

#         1         2         3
#12345678901234567890123456789012
#aaaabbbbccccdddd1111222233334444
#20251207212933230959718000000000

curl -v -X POST http://localhost:4318/v1/traces -H "Content-Type: application/json"   -d "{  \"resourceSpans\": [{  \"resource\": {  \"attributes\": [{  \"key\": \"service.name\",  \"value\": {\"stringValue\": \"my-test-service\"}  }]  },  \"scopeSpans\": [{  \"scope\": {  \"name\": \"manual-test\"  },  \"spans\": [{  \"traceId\": \"${ID}000000000\",  \"spanId\": \"1111222233334444\",  \"name\": \"current-time-test\",  \"kind\": 1,  \"startTimeUnixNano\": \"${CURRENT_TIME_NANOS}\",  \"endTimeUnixNano\": \"${END_TIME_NANOS}\",  \"status\": {  \"code\": 0  }  }]  }]  }]  }"
