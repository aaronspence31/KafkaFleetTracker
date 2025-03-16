from confluent_kafka import Producer
import json
import time
import uuid
import random
import logging
import signal
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vehicle-producer")

# Configure the Kafka producer with all brokers for redundancy
producer_config = {
    "bootstrap.servers": "b-2.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092,b-3.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092,b-1.vehicletrackingcluste.xxxxxx.c25.kafka.us-east-1.amazonaws.com:9092",
    "client.id": "vehicle-position-producer",
    "acks": "all",  # Wait for all replicas to acknowledge
    "retries": 5,  # Retry on transient failures
}

# Initialize Kafka producer
producer = Producer(producer_config)

# Define a small set of vehicles for testing
VEHICLE_FLEET = [
    {
        "id": f"VEH-{i:04d}",
        "type": random.choice(["sedan", "suv", "truck", "van"]),
        "status": "active",
        "position": (
            37.7749 + (random.random() - 0.5) * 0.1,
            -122.4194 + (random.random() - 0.5) * 0.1,
        ),
        "speed": random.uniform(0, 65),
    }
    for i in range(1, 6)  # Start with just 5 vehicles for testing
]


def delivery_report(err, msg):
    """Callback for message delivery reports"""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(
            f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
        )


def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    logger.info("Shutdown signal received, flushing messages...")
    producer.flush(10000)  # 10 second timeout
    logger.info("Producer shutdown complete")
    sys.exit(0)


def generate_vehicle_position(vehicle):
    """Generate a position update for a vehicle"""
    # Get current position
    lat, lng = vehicle["position"]

    # Generate small movement
    new_lat = lat + random.uniform(-0.001, 0.001)
    new_lng = lng + random.uniform(-0.001, 0.001)

    # Update vehicle position
    vehicle["position"] = (new_lat, new_lng)

    # Update speed occasionally
    if random.random() < 0.3:
        vehicle["speed"] = random.uniform(0, 65)

    # Create position data
    return {
        "vehicle_id": vehicle["id"],
        "vehicle_type": vehicle["type"],
        "timestamp": int(time.time()),
        "latitude": new_lat,
        "longitude": new_lng,
        "speed": vehicle["speed"],
        "status": vehicle["status"],
        "event_id": str(uuid.uuid4()),
    }


def produce_vehicle_positions():
    """Generate and send vehicle position messages to Kafka"""
    logger.info(
        f"Starting vehicle position producer with {len(VEHICLE_FLEET)} vehicles"
    )

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        message_count = 0
        while True:
            # Update each vehicle in the fleet
            for vehicle in VEHICLE_FLEET:
                # Generate position data
                position_data = generate_vehicle_position(vehicle)

                # Convert to JSON string
                position_json = json.dumps(position_data)

                # Send to Kafka
                producer.produce(
                    "vehicle_positions",
                    key=position_data["vehicle_id"],
                    value=position_json,
                    callback=delivery_report,
                )

                message_count += 1
                if message_count % 10 == 0:
                    logger.info(f"Produced {message_count} messages")

            # Trigger any callbacks for previously sent messages
            producer.poll(0)

            # Sleep between fleet updates
            time.sleep(5.0)  # Update each vehicle every 5 seconds for testing

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Ensure all messages are delivered before exiting
        producer.flush(30000)  # 30 second timeout
        logger.info("Producer shutdown complete")


if __name__ == "__main__":
    logger.info("Vehicle position producer initializing...")
    produce_vehicle_positions()
