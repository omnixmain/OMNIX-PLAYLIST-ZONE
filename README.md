# Omnix Adult Zone Project

This repository automates the fetching and validation of the Omnix Adult Zone M3U playlist.

## Structure

- `.github/workflows/`: Contains the GitHub Actions for automation.
    - `omnix_adult_zone.yml`: Runs every 12 hours to fetch the fresh M3U.
    - `omnix_adult_zone_validator.yml`: Runs 30 minutes after the fetch to validate streams and remove dead links.
- `scripts/`: Contains the logic.
    - `omnix_adult_zone.py`: Downloads the source playlist.
    - `omnix_adult_zone_validator.py`: Checks stream availability.
- `playlist/`: Stores the generated M3U files.
    - `omnix_adult_zone.m3u`: The raw downloaded list.
    - `omnix_adult_zone_active.m3u`: The active, validated list.

## Setup

1. Push this entire folder to a new GitHub repository or merging into an existing one.
2. Go to the "Actions" tab in your repository to see the workflows running.
3. You can manually trigger them using the "Run workflow" button if you don't want to wait for the schedule.

## Outputs

The workflows will generate/update the following files in the `scripts/` folder:
- `omnix_adult_zone.m3u`: The raw downloaded list.
- `omnix_adult_zone_active.m3u`: The active, validated list.
