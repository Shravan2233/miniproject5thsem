USE cabcompare;

INSERT INTO providers (provider_key, display_name, integration_status)
VALUES
  ('uber', 'Uber', 'unavailable'),
  ('rapido', 'Rapido', 'unavailable'),
  ('ola', 'Ola', 'unavailable'),
  ('namma-yatri', 'Namma Yatri', 'unavailable')
ON DUPLICATE KEY UPDATE display_name = VALUES(display_name);