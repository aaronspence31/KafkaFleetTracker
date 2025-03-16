#!/bin/bash
BROKER="b-3.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092"
TOPIC="vehicle_positions"
KAFKA_HOME="./kafka_2.13-3.6.0"

# Ensure we're using the correct config directory
export KAFKA_LOG4J_OPTS="-Dlog4j.configuration=file:$KAFKA_HOME/config/tools-log4j.properties"

$KAFKA_HOME/bin/kafka-topics.sh --create \
    --bootstrap-server ${BROKER} \
    --topic ${TOPIC} \
    --partitions 3 \
    --replication-factor 2 \
    --config cleanup.policy=compact \
    --config min.insync.replicas=1 \
    --config retention.ms=86400000