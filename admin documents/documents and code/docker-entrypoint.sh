#!/bin/sh

DB_FILE="website/database.db"

# Check if DB exists; if not, seed it
if [ ! -f "$DB_FILE" ]; then
    echo "Database not found. Seeding initial data..."
    python -m website.seed_data
    echo "Database seeded successfully."
else
    echo "Database already exists. Skipping seeding."
fi

# Start the Flask website
python run_website.py
