# Changelog

All notable changes to this project will be documented in this file.

## [1.1.1] - 2023-10-15

### Fixed

- Error handling in `calculate_current_position` method to manage different data types and values for `last_updated_at`.
- Enhanced logging to provide more insightful information for debugging.

## [1.1.0] - 2023-10-09

### Added

- Support for adjustable scrobble percentage.
- Error handling for invalid media duration and position data.
- Logging to provide debugging information on the scrobbling process.

### Changed

- Updated README documentation with new configuration options and troubleshooting section.
- Improved code comments.
- Updated `__init__.py` and `media_player.py` to handle new scrobble percentage configuration.

## [1.0.0] - 2023-10-08

### Added

- Initial release of LastFM Scrobbler Integration for Home Assistant.
- Support for scrobbling tracks played on selected media players to a user's Last.fm account.
- Configuration via `configuration.yaml` and `secrets.yaml`.
- Documentation on installation, configuration, and usage in README.
