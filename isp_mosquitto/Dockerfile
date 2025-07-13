FROM eclipse-mosquitto:latest

# Copy custom configuration files into the container
COPY mosquitto.conf /mosquitto/config/mosquitto.conf

# Expose MQTT default port and optional WebSocket port
EXPOSE 1883
EXPOSE 9001

# Optionally add persistence directory for message storage
VOLUME ["/mosquitto/data", "/mosquitto/log"]

# Run the Mosquitto broker
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]