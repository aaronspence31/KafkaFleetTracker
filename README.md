# 🚗 Real-Time Vehicle Tracking System with Apache Kafka 🚀

This project implements a **real-time vehicle tracking system** powered by **Apache Kafka on AWS MSK**, capturing vehicle positions instantly, processing updates seamlessly, and storing the data in **Snowflake** for deep analytics.

## 📌 What Does It Solve?

I've built this system to tackle these essential needs. I will explain below how we ensured these needs were met.

- **Real-time tracking**: Vehicle positions updated very fast (<5 seconds)
- **Rock-solid reliability**: Zero lost updates—even if things go wrong
- **Accurate data**: Always know the latest location of each vehicle
- **Historical analysis**: Easily analyze the last 24 hours of vehicle data
- **Instant access**: Get current vehicle locations immediately

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
  - Ensures any new consumer instantly sees the latest vehicle states

- **3 partitions**:

  - Give each broker a partition to process
  - Might want to increase the number of partitions as the fleet grows

- **Replication factor of 2**:

  - Keeps data safe without blowing the budget

- **24-hour retention**:
  - Ideal for daily analytics and quick recovery scenarios

### 🛠 Producer Strategy

Ran as a single producer task on ECS Fargate, however it is meant to simulate a fleet of vehicles providing position updates to the system every 5 seconds. In the real system, each vehicle will have its own producer sending updates to the system rather than a single producer simulating all vehicles.

- **Vehicle ID as key**:

  - Keeps each vehicle's data organized in Kafka
  - Guarantees ordering of updates per vehicle
  - Ensures compaction always works properly

- **Acks=all**:

  - Makes sure every message is safely delivered
  - Prioritizes reliability above absolute lowest latency

- **Built-in retry logic**:
  - Smooths out connectivity issues common with vehicles

### 🎯 Consumer Strategy

The consumer is running as a single task on ECS Fargate, processing all position updates and writing them to Snowflake.

#### Pull-Based Consumption Model

Our consumer implements Kafka's pull-based approach where the consumer controls when and how many messages to retrieve:

- **Active Polling**: Consumer explicitly requests messages from the broker rather than having messages pushed to it

  - Gives consumer control over processing pace to prevent overwhelming
  - Enables backpressure handling for surge situations (e.g., morning rush hour with many vehicles reporting)
  - Allows for graceful recovery after processing delays

- **Configurable Poll Behavior**:
  - `max.poll.records`: Limits the number of records processed in a single poll cycle
  - `max.poll.interval.ms`: Allows sufficient time for Snowflake processing
  - Balanced for both normal operations and peak traffic periods

#### Processing Optimizations

- **Batched Processing**: Groups position records before writing to Snowflake

  - Reduces database connection overhead

- **Graceful Flush Window**: Ensures timely updates during periods of low traffic too

  - Processes partial batches after 5 seconds
  - Balances real-time updates with database efficiency

- **Earliest Offset Reset**: Provides fault tolerance

  - Recovers missed positions after consumer restarts
  - Guarantees complete data processing after failures

- **Minimal Fetch Threshold**: Prioritizes real-time processing
  - `fetch.min.bytes=1`: Retrieves data as soon as it's available
  - `fetch.wait.max.ms=500`: Short wait time ensures position updates are processed immediately
  - Optimized for low-latency vehicle tracking

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

- Consumer lags (catch delays quickly!)
- Broker disk usage (avoid surprises!)
- Network throughput (spot bottlenecks early!)

### 🔄 Disaster Recovery

- Replication and retention strategy means quick, worry-free recovery
- Snowflake backs up all historical data safely

## 🚧 What's Next?

Future improvements planned:

1. **Enhanced security**: Adding SASL/SSL authentication to Kafka
2. **Dynamic consumer scaling**: Auto-scaling based on real-time lag
3. **Schema registry integration**: Avro serialization for cleaner data

## 🎥 Demo

_Coming Soon!_

## 📖 Setup Instructions

_Coming Soon!_
