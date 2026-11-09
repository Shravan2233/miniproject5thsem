CREATE DATABASE IF NOT EXISTS cabcompare
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE cabcompare;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email VARCHAR(254) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS providers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  provider_key VARCHAR(64) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  integration_status ENUM('unavailable', 'pending_approval', 'configured', 'active') NOT NULL DEFAULT 'unavailable',
  booking_url_template VARCHAR(1000) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_providers_key (provider_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS routes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  pickup_label VARCHAR(255) NOT NULL,
  destination_label VARCHAR(255) NOT NULL,
  route_key CHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_routes_key (route_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS search_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NULL,
  route_id BIGINT UNSIGNED NOT NULL,
  searched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_search_history_user_time (user_id, searched_at),
  KEY ix_search_history_route_time (route_id, searched_at),
  CONSTRAINT fk_search_history_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
  CONSTRAINT fk_search_history_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fare_observations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  route_id BIGINT UNSIGNED NOT NULL,
  provider_id BIGINT UNSIGNED NOT NULL,
  ride_type ENUM('bike', 'auto', 'sedan', 'premium') NOT NULL,
  fare DECIMAL(10,2) NULL,
  currency CHAR(3) NOT NULL,
  fare_status ENUM('demo', 'estimated', 'live', 'unavailable') NOT NULL,
  source_status VARCHAR(160) NOT NULL,
  availability_status ENUM('available', 'unavailable', 'unknown') NOT NULL DEFAULT 'unknown',
  pickup_eta_minutes SMALLINT UNSIGNED NULL,
  trip_duration_minutes SMALLINT UNSIGNED NULL,
  distance_km DECIMAL(8,2) NULL,
  observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_fare_route_time (route_id, observed_at),
  KEY ix_fare_provider_time (provider_id, observed_at),
  CONSTRAINT ck_fare_nonnegative CHECK (fare IS NULL OR fare >= 0),
  CONSTRAINT fk_fare_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE,
  CONSTRAINT fk_fare_provider FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id BIGINT UNSIGNED NOT NULL,
  preferred_ride_type ENUM('bike', 'auto', 'sedan', 'premium') NULL,
  currency CHAR(3) NOT NULL DEFAULT 'INR',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  CONSTRAINT fk_preferences_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS favorite_routes (
  user_id BIGINT UNSIGNED NOT NULL,
  route_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, route_id),
  CONSTRAINT fk_favorites_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_favorites_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE
) ENGINE=InnoDB;