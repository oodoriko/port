#!/bin/bash

# Load environment variables from !.env file
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=SQwSa5uHR8SIqgFQIr_8GUAHmNc6xPlu6nC7hxht3pD0g9yGAfdoXv0yjbgENkVFJN_7Hi7gyRsBkbj8mLvqBQ==
export INFLUXDB_ORG=bikini-bottom
export INFLUXDB_BUCKET=patrick

echo "🔧 Starting API server with InfluxDB configuration..."
echo "   URL: $INFLUXDB_URL"
echo "   ORG: $INFLUXDB_ORG"
echo "   BUCKET: $INFLUXDB_BUCKET"
echo ""

cargo run --bin api-server 