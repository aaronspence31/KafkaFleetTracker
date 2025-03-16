from confluent_kafka import Consumer, KafkaError
import json
import logging
import time
import signal
import sys
import os
from datetime import datetime
import snowflake.connector

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vehicle-consumer")

# Configure the Kafka consumer
consumer_config = {
    "bootstrap.servers": "b-2.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092,b-3.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092,b-1.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092",
    "group.id": "vehicle-tracking-consumer-group",
    "auto.offset.reset": "earliest",  # Read everything, even stuff from before we started
    "enable.auto.commit": True,
    "auto.commit.interval.ms": 5000,  # Commit offsets every 5 seconds
    "session.timeout.ms": 30000,  # Session timeout
    "max.poll.interval.ms": 300000,  # Max time between polls
    "fetch.min.bytes": 1,  # Get data as soon as it's available for real-time processing
    "fetch.wait.max.ms": 500,  # Wait up to 500ms for min.bytes
}

# Initialize Kafka consumer
consumer = Consumer(consumer_config)


# Subscribe to the topic with assignment callback
def on_assign(consumer, partitions):
    for p in partitions:
        logger.info(f"Assigned partition {p.partition}")

    # Get watermarks to check if messages exist
    for p in partitions:
        low, high = consumer.get_watermark_offsets(p)
        logger.info(f"Partition {p.partition} has messages from {low} to {high}")


# Subscribe with the assignment callback
consumer.subscribe(["vehicle_positions"], on_assign=on_assign)

# Snowflake connection parameters
snowflake_params = {
    "user": os.environ.get("SNOWFLAKE_USER", "vehicle_app_user"),
    "password": os.environ.get("SNOWFLAKE_PASSWORD", "placeholder"),
    "account": os.environ.get("SNOWFLAKE_ACCOUNT", "placeholder"),
    "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "VEHICLE_TRACKING_WH"),
    "database": os.environ.get("SNOWFLAKE_DATABASE", "VEHICLE_TRACKING_DB"),
    "schema": os.environ.get("SNOWFLAKE_SCHEMA", "VEHICLE_DATA"),
}

# Batch processing configuration
BATCH_SIZE = 10
MAX_BATCH_TIME_MS = 5000

# In-memory vehicle state tracking
vehicle_states = {}
batch_records = []
last_batch_time = time.time() * 1000

# Flag for graceful shutdown
running = True


def process_message(msg):
    """Process a single Kafka message"""
    try:
        # Parse the message value as JSON
        position_data = json.loads(msg.value().decode("utf-8"))

        # Extract vehicle ID and timestamp
        vehicle_id = position_data.get("vehicle_id")
        timestamp = position_data.get("timestamp")

        # Log the received message
        logger.info(f"Received position update for vehicle {vehicle_id} at {timestamp}")

        # Update in-memory state for this vehicle
        vehicle_states[vehicle_id] = position_data

        # Add to batch for processing
        batch_records.append(position_data)

        return True
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.error(f"Message content: {msg.value() if msg.value() else 'Empty'}")
        return False


def process_batch(records):
    """Process a batch of vehicle position records and write to Snowflake"""
    if not records:
        return True

    try:
        start_time = time.time()
        logger.info(f"Processing batch of {len(records)} records")

        # Connect to Snowflake
        conn = snowflake.connector.connect(
            user=snowflake_params["user"],
            password=snowflake_params["password"],
            account=snowflake_params["account"],
            warehouse=snowflake_params["warehouse"],
            database=snowflake_params["database"],
            schema=snowflake_params["schema"],
        )

        # Create a cursor
        cursor = conn.cursor()

        # Prepare the SQL insert statement
        insert_sql = """
        INSERT INTO VEHICLE_POSITIONS (
            VEHICLE_ID, TIMESTAMP, LATITUDE, LONGITUDE, 
            SPEED, VEHICLE_TYPE, STATUS
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s
        )
        """

        # Prepare batch of records for insertion
        values = []
        for record in records:
            values.append(
                (
                    record.get("vehicle_id"),
                    record.get("timestamp"),
                    record.get("latitude"),
                    record.get("longitude"),
                    record.get("speed"),
                    record.get("vehicle_type"),
                    record.get("status"),
                )
            )

        # Execute batch insert
        cursor.executemany(insert_sql, values)

        # Commit the transaction
        conn.commit()

        # Close the connection
        cursor.close()
        conn.close()

        elapsed = time.time() - start_time
        logger.info(
            f"Successfully wrote {len(records)} records to Snowflake in {elapsed:.2f} seconds"
        )
        return True

    except Exception as e:
        logger.error(f"Error writing to Snowflake: {e}")
        logger.error(f"Exception details: {str(e)}")
        return False


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global running
    logger.info("Shutdown signal received, closing consumer...")
    running = False


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Main consumer loop
def main():
    global batch_records, last_batch_time, running

    logger.info("Starting Kafka consumer for vehicle position data")

    try:
        while running:
            # Poll for messages
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                # No message received
                pass
            elif msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event - not an error
                    logger.debug(f"Reached end of partition {msg.partition()}")
                else:
                    # Error
                    logger.error(f"Error: {msg.error()}")
            else:
                # Process the message
                process_message(msg)

            # Check if it's time to process the batch
            current_time = time.time() * 1000  # Convert to milliseconds
            time_elapsed = current_time - last_batch_time

            if len(batch_records) >= BATCH_SIZE or (
                len(batch_records) > 0 and time_elapsed >= MAX_BATCH_TIME_MS
            ):
                # Process the batch
                if process_batch(batch_records):
                    # Clear the batch after successful processing
                    batch_records = []
                    last_batch_time = current_time

    except Exception as e:
        logger.error(f"Unexpected error in consumer main loop: {e}")

    finally:
        # Process any remaining records in the batch
        if batch_records:
            logger.info("Processing remaining records before shutdown")
            process_batch(batch_records)

        # Close the consumer
        logger.info("Closing consumer")
        consumer.close()
        logger.info("Consumer closed")


if __name__ == "__main__":
    main()
