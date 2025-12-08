#! /bin/bash

curl -s http://localhost:12345/metrics | grep -E "otelcol_receiver.*(accepted|refused).*spans" 
