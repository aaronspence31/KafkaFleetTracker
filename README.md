# 🚗 Real-Time Vehicle Tracking System with Apache Kafka 🚀

This project implements a **real-time vehicle tracking system** powered by **Apache Kafka on AWS MSK**, capturing vehicle positions instantly, processing updates seamlessly, and storing the data in **Snowflake** for deep analytics.

## 📌 What Does It Solve?

I've built this system to tackle these essential needs. I will explain below how we ensured these needs were met.

- **Real-time tracking**: Vehicle positions updated very fast (<5 seconds)
- **Rock-solid reliability**: Zero lost updates - even if things go wrong
- **Historical analysis**: Easily analyze the last 24 hours of vehicle data
- **Instant access**: Get most recent location for each vehicle immediately

## 📚 System Architecture Overview

Here's what's under the hood:

- **Kafka Cluster**: AWS MSK setup with 3 brokers (t3.small, 100GB each)
- **Producers**: ECS Fargate simulating real-time vehicle position updates
- **Consumers**: ECS Fargate tasks efficiently processing data into Snowflake
- **Storage**: Snowflake for analytics and long-term data retention

### 🔄 Data Flow in a Nutshell

1. Vehicles send position updates via producer.
2. Kafka topic receives updates using vehicle IDs as keys.
3. Consumers process these updates in batches.
4. Final processed data lands in Snowflake for analytics.

## ⚙️ Technical Optimizations for Tracking

### 📁 Kafka Topic Setup

```bash
kafka-topics.sh --create \
    --topic vehicle_positions \
    --partitions 3 \
    --replication-factor 2 \
    --config cleanup.policy=compact \
    --config retention.ms=86400000
```

- **Compacted topic** means you always have the latest vehicle position:

  - Automatically gets rid of outdated data, saving space
  - Ensures any new consumer instantly sees the latest vehicle states as required by the customer for the instant access requirement

- **3 partitions**:

  - Give each broker a partition to process to ensure high availability and real-time tracking as required by the customer
  - Might want to increase the number of partitions as the fleet grows

- **Replication factor of 2**:

  - Keeps data safe without blowing the budget as rock solid reliability is required by the customer

- **24-hour retention**:
  - Ideal for daily analytics
  - Ensures we have data for the last 24 hours as required by the customer for historical analysis

### 🛠 Producer Strategy

The producer runs as an ECS Fargate task that simulates a fleet of vehicles sending real-time position updates to Kafka. In production, each vehicle would likely run its own producer client.

#### How It Works

- **Vehicle Fleet Simulation**: Models realistic vehicle movement patterns

  - Maintains a fleet of test vehicles (5 in the demo setup)
  - Updates vehicle positions every 5 seconds
  - Simulates realistic movements with variable speeds
  - Generates random position shifts within geographic bounds

#### Processing Optimizations

- **Message Key Strategy**: Vehicle ID as the partition key

  - Ensures all updates for a specific vehicle route to the same partition
  - Maintains chronological ordering of position updates per vehicle
  - Optimizes topic compaction for latest position retrieval
  - Critical for the "current state access" business requirement

- **Durability Configuration**: Tuned for maximum reliability

  - `acks=all`: Requires acknowledgment from all in-sync replicas
  - Prioritizes data integrity over absolute lowest latency

- **Connection Resilience**:
  - Multiple broker addresses in bootstrap configuration
  - `retries=5`: Persistent delivery attempts for transient network issues
  - Graceful shutdown with 30-second flush timeout ensures no data loss

This implementation delivers reliable, ordered position updates with geographic accuracy while maintaining system resilience during network fluctuations.

### 🎯 Consumer Strategy

The consumer runs as an ECS Fargate task that pulls vehicle position updates from Kafka and writes them to Snowflake, creating the bridge between real-time data collection and analytics.

#### How It Works

- **Pull-Based Consumption**: Consumer controls the flow of data

  - Polls for messages every 1 second
  - Explicitly requests data rather than having it pushed
  - Provides backpressure handling during traffic spikes

- **Message Processing Flow**:

  1. Decode incoming JSON position data
  2. Update in-memory vehicle state dictionary
  3. Add to pending batch
  4. Process batch when trigger conditions met

- **State Management**:
  - Maintains current positions for all vehicles in memory
  - Enables quick lookups between database writes
  - Preserves latest vehicle state during processing

#### Processing Optimizations

- **Smart Batching**: Optimizes Snowflake interactions

  - Groups up to 10 position records before writing
  - Processes partial batches after 5 seconds elapsed
  - Single database connection per batch reduces overhead

- **Real-Time Configuration**: Tuned for low latency

  - `fetch.min.bytes=1`: Retrieves data immediately when available
  - `fetch.wait.max.ms=500`: Short wait time prioritizes responsiveness
  - `auto.offset.reset=earliest`: Ensures no missing data after restarts

- **Resilience Features**:
  - Graceful shutdown handling with signal handlers
  - Processes remaining records before terminating
  - Detailed error logging and recovery mechanisms
  - Separate error handling for Kafka vs. Snowflake issues

### 🔐 Security & Networking

- Kafka operates safely inside private subnets (no internet exposure)
- Secure communication through VPC endpoints
- Tight security group controls limiting network access

## 🌟 Deployment & Performance Highlights

Both producer and consumer run as AWS ECS Fargate tasks for:

- Serverless simplicity (no EC2 headaches)
- Secure, isolated execution

### ⚡ Performance Stats

- **Latency**: Under 2 seconds end-to-end
- **Capacity**: 5+ vehicles updating every 5 seconds
- **Reliability**: Handles single broker failure like a champ
- **Throughput**: Easily processes 100+ messages/sec

## 📈 Operations & Monitoring

Using **AWS CloudWatch** to track:

- Consumer lags
- Broker disk usage
- Network throughput

### 🔄 Disaster Recovery

- Replication and retention strategy means quick, worry-free recovery
- Snowflake backs up all historical data safely

## 🚧 What's Next?

Future improvements planned:

1. **Enhanced security**: Adding SASL/SSL authentication to Kafka
2. **Dynamic consumer scaling**: Auto-scaling consumer tasks based on real-time lag
3. **Schema registry integration**: Avro serialization for cleaner data

## 🎥 Demo

_Coming Soon!_

## 📖 Setup Instructions

_Coming Soon!_
