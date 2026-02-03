#!/bin/bash

# Check if a password was provided as an argument
if [ $# -eq 0 ]; then
  echo "No password provided. Usage: $0 <PASSWORD>"
  exit 1
fi

PASSWORD=$1
DATABASE_XML="drugbank_all_full_database.xml.zip"
DATABASE_XML_UNZIPPED=${DATABASE_XML%.*} # Remove the zip extension

# Navigate to the data directory and remove both files if they already exist
rm -f data/"$DATABASE_XML"
rm -f data/"$DATABASE_XML_UNZIPPED"

# Download the file, unzip it, rename the unzipped file, and clean up
cd data || exit
curl -Lfv -o "$DATABASE_XML" -u dmk333@psu.edu:"$PASSWORD" "https://go.drugbank.com/releases/5-1-12/downloads/all-full-database"
unzip "$DATABASE_XML"
cd ..