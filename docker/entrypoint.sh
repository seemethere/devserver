#!/bin/bash
set -e

# Function to handle SIGHUP
reload_handler() {
  echo "SIGHUP received, reloading..."
  kill -s SIGHUP $PID
  sleep 1
  start_app &
}

# Function to start the application
start_app() {
  echo "Starting application..."
  "$@" &
  PID=$!
  echo "Application started with PID $PID"
}

# Trap SIGHUP
trap 'reload_handler' SIGHUP

# Start the application in the background
start_app "$@"

# Wait for the application to exit
wait $PID
