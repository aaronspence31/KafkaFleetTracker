import pandas as pd
import matplotlib.pyplot as plt
import snowflake.connector
import os
from datetime import datetime, timedelta
import time

# Snowflake connection parameters - load from environment or .env file
snowflake_params = {
    "user": os.environ.get("SNOWFLAKE_USER", "vehicle_app_user"),
    "password": os.environ.get("SNOWFLAKE_PASSWORD", "placeholder"),
    "account": os.environ.get("SNOWFLAKE_ACCOUNT", "placeholder"),
    "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "VEHICLE_TRACKING_WH"),
    "database": os.environ.get("SNOWFLAKE_DATABASE", "VEHICLE_TRACKING_DB"),
    "schema": os.environ.get("SNOWFLAKE_SCHEMA", "VEHICLE_DATA"),
}


def get_vehicle_positions():
    """Retrieve the latest vehicle positions from Snowflake"""
    try:
        conn = snowflake.connector.connect(**snowflake_params)
        cursor = conn.cursor()

        # Get the latest position for each vehicle
        cursor.execute(
            """
        SELECT 
            vehicle_id, 
            latitude, 
            longitude, 
            speed, 
            vehicle_type,
            status,
            timestamp
        FROM vehicle_positions
        WHERE timestamp > DATEADD(minute, -60, CURRENT_TIMESTAMP())
        ORDER BY timestamp DESC
        """
        )

        # Convert to DataFrame
        positions = pd.DataFrame(
            cursor.fetchall(),
            columns=[
                "vehicle_id",
                "latitude",
                "longitude",
                "speed",
                "vehicle_type",
                "status",
                "timestamp",
            ],
        )

        cursor.close()
        conn.close()
        return positions

    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        return pd.DataFrame()


def get_vehicle_update_counts():
    """Retrieve update counts per vehicle from Snowflake"""
    try:
        conn = snowflake.connector.connect(**snowflake_params)
        cursor = conn.cursor()

        # Get update counts per vehicle ID (summed across all vehicle types)
        cursor.execute(
            """
        SELECT 
            vehicle_id,
            COUNT(*) as update_count,
            MIN(timestamp) as first_update,
            MAX(timestamp) as last_update
        FROM vehicle_positions
        WHERE timestamp > DATEADD(minute, -60, CURRENT_TIMESTAMP())
        GROUP BY vehicle_id
        ORDER BY update_count DESC
        """
        )

        # Convert to DataFrame
        update_counts = pd.DataFrame(
            cursor.fetchall(),
            columns=[
                "vehicle_id",
                "update_count",
                "first_update",
                "last_update",
            ],
        )

        cursor.close()
        conn.close()
        return update_counts

    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        return pd.DataFrame()


def plot_vehicles(output_dir="demo_output"):
    """Create a plot of current vehicle positions"""
    positions = get_vehicle_positions()

    if positions.empty:
        print("No vehicle positions found")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a plot
    plt.figure(figsize=(10, 8))

    # Plot each vehicle type with a different color and increase marker size
    for vehicle_type in positions["vehicle_type"].unique():
        vehicle_data = positions[positions["vehicle_type"] == vehicle_type]
        plt.scatter(
            vehicle_data["longitude"],
            vehicle_data["latitude"],
            label=vehicle_type,
            alpha=0.8,
            s=100,  # Increased marker size for better visibility
        )

    # Add a small legend in the corner with vehicle information instead of text labels
    plt.title(f"Vehicle Positions - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend(title="Vehicle Type", loc="upper right")
    plt.grid(True, linestyle="--", alpha=0.7)

    # Add a text box with vehicle information
    info_text = "Vehicle Fleet:\n"
    for vehicle_type in positions["vehicle_type"].unique():
        vehicle_count = len(positions[positions["vehicle_type"] == vehicle_type])
        info_text += f"{vehicle_type}: {vehicle_count} position updates\n"

    # Add text box with vehicle count information
    plt.figtext(0.15, 0.15, info_text, bbox=dict(facecolor="white", alpha=0.8))

    # San Francisco bay area map boundaries (approximate)
    plt.xlim(-122.5, -122.3)
    plt.ylim(37.7, 37.9)

    # Save the plot
    filename = f"{output_dir}/vehicle_positions_{int(time.time())}.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved plot to {filename}")

    # Show the plot
    plt.show()


def plot_vehicle_updates(output_dir="demo_output"):
    """Create a bar chart showing updates per vehicle ID"""
    update_counts = get_vehicle_update_counts()

    if update_counts.empty:
        print("No update data found")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a bar chart of updates per vehicle ID
    plt.figure(figsize=(12, 6))

    # Create the bar chart with improved styling - using a single color
    bars = plt.bar(
        update_counts["vehicle_id"],
        update_counts["update_count"],
        color="#1f77b4",  # Use a standard blue color for all bars
        width=0.6,  # Adjusted width for better appearance
        edgecolor="black",  # Add edge for better definition
        linewidth=0.5,
    )

    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.5,
            f"{int(height)}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",  # Make numbers stand out
        )

    plt.title("Position Updates Processed Per Vehicle", fontsize=14, pad=20)
    plt.xlabel("Vehicle ID", fontsize=12, labelpad=10)
    plt.ylabel("Number of Updates", fontsize=12, labelpad=10)
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # Add a border around the plot
    plt.box(True)

    # Adjust layout to prevent cutting off elements
    plt.tight_layout(pad=2.0)

    # Save the plot
    filename = f"{output_dir}/vehicle_updates_{int(time.time())}.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved vehicle update counts to {filename}")

    # Show the plot
    plt.show()


def plot_update_timeline(output_dir="demo_output"):
    """Create a timeline visualization of updates for each vehicle"""
    update_counts = get_vehicle_update_counts()

    if update_counts.empty:
        print("No update data found")
        return

    # Create a Snowflake connection to get detailed update timestamps
    try:
        conn = snowflake.connector.connect(**snowflake_params)
        cursor = conn.cursor()

        # Get all update timestamps for the last hour
        cursor.execute(
            """
        SELECT 
            vehicle_id,
            timestamp
        FROM vehicle_positions
        WHERE timestamp > DATEADD(hour, -1, CURRENT_TIMESTAMP())
        ORDER BY vehicle_id, timestamp
        """
        )

        # Convert to DataFrame
        updates = pd.DataFrame(cursor.fetchall(), columns=["vehicle_id", "timestamp"])

        print(
            f"DEBUG: Sample timestamp value: {updates['timestamp'].iloc[0] if not updates.empty else 'No data'}"
        )
        print(f"DEBUG: Timestamp dtype: {updates['timestamp'].dtype}")

        # Try to determine if these are epoch timestamps
        try:
            # First check if these are already datetime objects
            if pd.api.types.is_datetime64_any_dtype(updates["timestamp"]):
                print("DEBUG: Timestamps are already datetime objects")
            else:
                # If values are large integers, they're likely epoch timestamps
                # Try converting using different unit options
                updates["timestamp"] = pd.to_datetime(
                    updates["timestamp"], unit="s", errors="coerce"
                )

                # If we got NaT values, try milliseconds
                if updates["timestamp"].isna().any():
                    print("DEBUG: Trying millisecond conversion")
                    updates["timestamp"] = pd.to_datetime(
                        updates["timestamp"], unit="ms", errors="coerce"
                    )

                # If still NaT values, try microseconds
                if updates["timestamp"].isna().any():
                    print("DEBUG: Trying microsecond conversion")
                    updates["timestamp"] = pd.to_datetime(
                        updates["timestamp"], unit="us", errors="coerce"
                    )
        except Exception as e:
            print(f"DEBUG: Error converting timestamps: {e}")
            # As a last resort, try the format Snowflake typically uses
            updates["timestamp"] = pd.to_datetime(
                updates["timestamp"], format="%Y-%m-%d %H:%M:%S.%f", errors="coerce"
            )

        cursor.close()
        conn.close()

        if updates.empty or updates["timestamp"].isna().all():
            print("No valid timestamp data found for timeline")
            return

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create a timeline plot with improved styling
        plt.figure(figsize=(14, 8))  # Increased size for better readability

        # Get unique vehicle IDs
        vehicle_ids = updates["vehicle_id"].unique()

        # Use a colormap to assign different colors to each vehicle
        colors = plt.cm.tab10(range(len(vehicle_ids)))

        # Get min and max timestamps for plotting
        min_timestamp = updates["timestamp"].min()
        max_timestamp = updates["timestamp"].max()

        print(f"DEBUG: Min timestamp: {min_timestamp}")
        print(f"DEBUG: Max timestamp: {max_timestamp}")

        # Calculate a reasonable buffer (5% of the time range)
        if not pd.isna(min_timestamp) and not pd.isna(max_timestamp):
            time_range = max_timestamp - min_timestamp
            buffer = pd.Timedelta(seconds=time_range.total_seconds() * 0.05)
            plot_min_time = min_timestamp - buffer
            plot_max_time = max_timestamp + buffer
        else:
            # Fallback if timestamps are invalid
            plot_min_time = datetime.now() - timedelta(hours=1)
            plot_max_time = datetime.now()

        # Plot a horizontal line for each vehicle with markers for updates
        for i, (vehicle_id, color) in enumerate(zip(vehicle_ids, colors)):
            vehicle_updates = updates[updates["vehicle_id"] == vehicle_id]

            # Skip if no valid timestamps
            if vehicle_updates["timestamp"].isna().all():
                continue

            # Plot the timeline with improved markers
            plt.plot(
                vehicle_updates["timestamp"],
                [i] * len(vehicle_updates),
                "o-",
                label=vehicle_id,
                markersize=8,
                color=color,
                markeredgecolor="black",
                markeredgewidth=0.5,
                alpha=0.8,
                linewidth=1.5,
            )

            # Add vehicle ID as y-tick label with improved formatting
            plt.text(
                plot_min_time,
                i,
                f"{vehicle_id}",
                va="center",
                ha="right",
                fontsize=11,
                fontweight="bold",
                bbox=dict(facecolor="white", alpha=0.7, boxstyle="round,pad=0.3"),
            )

        # Format the plot
        plt.title("Vehicle Position Update Timeline (Last Hour)", fontsize=16, pad=20)
        plt.xlabel("Time", fontsize=12, labelpad=10)
        plt.yticks([])  # Hide y-axis ticks since we added custom labels

        # Use a light grid for better readability
        plt.grid(True, axis="x", linestyle="-", alpha=0.3)

        # Ensure x-axis limits are set properly to show all data
        plt.xlim(plot_min_time, plot_max_time)

        # Add padding at the top and bottom
        plt.ylim(-1, len(vehicle_ids))

        # Format x-axis to show time nicely
        plt.gcf().autofmt_xdate()

        # Add annotation for update frequency with improved styling
        plt.figtext(
            0.5,
            0.01,
            "Each marker represents a position update received and processed through Kafka",
            ha="center",
            fontsize=10,
            bbox=dict(facecolor="whitesmoke", alpha=0.8, boxstyle="round,pad=0.5"),
        )

        # Add a border around the plot
        plt.box(True)

        plt.tight_layout(pad=3.0)

        # Save the plot
        filename = f"{output_dir}/update_timeline_{int(time.time())}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"Saved update timeline to {filename}")

        # Show the plot
        plt.show()

    except Exception as e:
        print(f"Error creating timeline: {e}")
        # Print more detailed error information for debugging
        import traceback

        traceback.print_exc()


def generate_vehicle_stats():
    """Generate statistics about updates per vehicle"""
    update_counts = get_vehicle_update_counts()

    if update_counts.empty:
        print("No update data found")
        return

    # Print statistics about updates per vehicle
    print("\n===== VEHICLE UPDATE STATISTICS =====")
    print(f"Total Vehicles Tracked: {len(update_counts)}")
    print(f"Total Position Updates: {update_counts['update_count'].sum()}")
    print(f"Average Updates Per Vehicle: {update_counts['update_count'].mean():.1f}")

    # Print details for each vehicle
    print("\nUpdates By Vehicle:")
    print("-----------------")
    for _, row in update_counts.iterrows():
        print(f"{row['vehicle_id']}: {row['update_count']} updates")

    # Print the most active vehicle
    most_active = update_counts.loc[update_counts["update_count"].idxmax()]
    print(
        f"\nMost Active Vehicle: {most_active['vehicle_id']} with {most_active['update_count']} updates"
    )

    print("=====================================\n")


if __name__ == "__main__":
    print("Generating vehicle stats...")
    # Generate vehicle statistics
    generate_vehicle_stats()

    # Plot current vehicle positions on map
    print("Plotting vehicle positions...")
    plot_vehicles()

    # Plot update counts per vehicle
    print("Plotting update counts per vehicle...")
    plot_vehicle_updates()

    # Plot timeline of updates
    print("Plotting update timeline...")
    plot_update_timeline()
