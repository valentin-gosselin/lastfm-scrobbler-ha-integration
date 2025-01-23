# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2025-01-23

### Added
- **ConfigFlow and OptionsFlow**: Configuration is now fully managed through the Home Assistant UI, removing the need for `configuration.yaml`.
- **Support for multiple Last.fm accounts**: Create separate configurations for different scrobblers with unique media sources and destination accounts.
- **Entity-based conditions (`check_entities`)**: Scrobbling can now be restricted to specific conditions (e.g., only when you're home or a switch is on).
- **Improved Metadata Handling**: Fixes for `Music Assistant` media players, including handling of multi-artist tracks (split by `/`) and radio playback metadata.
  
### Changed
- Removed YAML-based configuration. All configurations must now be set up via the Home Assistant UI.
- Updated documentation to reflect the transition to ConfigFlow and the new features.

### Fixed
- Improved handling of incomplete metadata from media players (e.g., missing artist or track).
- Fixed issues with media players sending incorrect album data when playing radio stations.

## [1.2.0] - 2024-04-19

### Fixed

- Fixed a bug that would cause the configured `scrobble_percentage` to be ignored.

### Added

- Support for updating the currently playing track on Last.fm.
- Updated `__init__.py` to add configuration for the new now playing functionality.

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
