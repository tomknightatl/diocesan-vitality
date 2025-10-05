-- Expected parishes for Diocese ID 2002 (Diocese of Orange) accuracy testing
-- This creates a reference table for testing parish extraction accuracy

CREATE TABLE IF NOT EXISTS expected_parishes_2002 (
    id SERIAL PRIMARY KEY,
    diocese_id INTEGER NOT NULL,
    parish_name TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Clear existing data for diocese 2002
DELETE FROM expected_parishes_2002 WHERE diocese_id = 2002;

-- Insert expected parishes for Diocese of Orange (ID: 2002)
INSERT INTO expected_parishes_2002 (diocese_id, parish_name, city) VALUES
(2002, 'Saint Thomas Syro-Malabar Forane Catholic Church', 'Orange'),
(2002, 'Saint John Maron Catholic Church', 'Orange'),
(2002, 'Saint John Henry Newman Catholic Church', 'Irvine'),
(2002, 'Saint George Chaldean Catholic Church', 'Santa Ana'),
(2002, 'Holy Cross Melkite Catholic Church', 'Placentia'),
(2002, 'Annunciation Byzantine Catholic Church', 'Anaheim'),
(2002, 'Vietnamese Catholic Center', 'Santa Ana'),
(2002, 'Saint Vincent de Paul Catholic Church', 'Huntington Beach'),
(2002, 'Saint Timothy Catholic Church', 'Laguna Niguel'),
(2002, 'Saint Thomas Korean Catholic Center', 'Anaheim'),
(2002, 'Saints Simon and Jude Catholic Church', 'Huntington Beach'),
(2002, 'Saint Polycarp Catholic Church', 'Stanton'),
(2002, 'Saint Pius V Catholic Church', 'Buena Park'),
(2002, 'Saint Philip Benizi Catholic Church', 'Fullerton'),
(2002, 'Saint Norbert Catholic Church', 'Orange'),
(2002, 'Saint Nicholas Catholic Churh', 'Laguna Woods'),
(2002, 'Saint Mary''s by The Sea Catholic Church', 'Huntington Beach'),
(2002, 'Saint Mary Catholic Church', 'Fullerton'),
(2002, 'Saint Martin de Porres Catholic Church', 'Yorba Linda'),
(2002, 'Saint Kilian Catholic Church', 'Mission Viejo'),
(2002, 'Saint Justin Martyr Catholic Church', 'Anaheim'),
(2002, 'Saint Juliana Falconieri Catholic Church', 'Fullerton'),
(2002, 'Saint Joseph Catholic Church, Santa Ana', 'Santa Ana'),
(2002, 'Saint Joseph Catholic Church, Placentia', 'Placentia'),
(2002, 'Saint John Vianney Chapel', 'Newport Beach'),
(2002, 'Saint John The Baptist Catholic Chuch', 'Costa Mesa'),
(2002, 'Saint John Neumann Catholic Church', 'Irvine'),
(2002, 'Saint Joachim Catholic Church', 'Costa Mesa'),
(2002, 'Saint Irenaeus Catholic Church', 'Cypress'),
(2002, 'Saint Hedwig Catholic Church', 'Los Alamitos'),
(2002, 'Saint Elizabeth Ann Seton Catholic Church', 'Irvine'),
(2002, 'Saint Edward The Confessor Catholic Church', 'Dana Point'),
(2002, 'Saint Columban Catholic Church', 'Garden Grove'),
(2002, 'Saint Cecilia Catholic Church', 'Tustin'),
(2002, 'Saint Catherine of Siena Catholic Church', 'Laguna Beach'),
(2002, 'Saint Boniface Catholic Church', 'Anaheim'),
(2002, 'Saint Bonaventure Catholic Church', 'Huntington Beach'),
(2002, 'Saint Barbara Catholic Church', 'Santa Ana'),
(2002, 'Saint Anthony Claret Catholic Church', 'Anaheim'),
(2002, 'Saint Anne Catholic Church, Seal Beach', 'Seal Beach'),
(2002, 'Saint Anne Catholic Church, Santa Ana', 'Santa Ana'),
(2002, 'Saint Angela Merici Catholic Church', 'Brea'),
(2002, 'Santiago de Compostela Catholic Church', 'Lake Forest'),
(2002, 'Santa Clara de Asis Catholic Church', 'Yorba Linda'),
(2002, 'San Francisco Solano Catholic Church', 'Rancho Santa Margarita'),
(2002, 'San Antonio de Padua Catholic Church', 'Anaheim Hills'),
(2002, 'Our Lady Queen of Angels Catholic Church', 'Newport Beach'),
(2002, 'Our Lady of The Pillar Catholic Church', 'Santa Ana'),
(2002, 'Our Lady of Mount Carmel Catholic Church', 'Newport Beach'),
(2002, 'Our Lady of La Vang Catholic Church', 'Santa Ana'),
(2002, 'Our Lady of Guadalupe, La Habra', 'La Habra'),
(2002, 'Our Lady of Guadalupe, Delhi', 'Santa Ana'),
(2002, 'Our Lady of Guadalupe, Santa Ana', 'Santa Ana'),
(2002, 'Our Lady of Fatima Catholic Church', 'San Clemente'),
(2002, 'Our Lady of Peace Korean Catholic Center', 'Irvine'),
(2002, 'Mission Basilica', 'San Juan Capistrano'),
(2002, 'La Purisima Catholic Church', 'Orange'),
(2002, 'Korean Martyrs Catholic Center', 'Westminster'),
(2002, 'Saint John Paul II Catholic Polish Center', 'Yorba Linda'),
(2002, 'Immaculate Heart of Mary Catholic Church', 'Santa Ana'),
(2002, 'Holy Spirit Catholic Church', 'Fountain Valley'),
(2002, 'Holy Family Catholic Church, Seal Beach', 'Seal Beach'),
(2002, 'Holy Family Catholic Church, Orange', 'Orange'),
(2002, 'Corpus Christi Catholic Church', 'Aliso Viejo'),
(2002, 'Christ Our Savior Catholic Parish', 'Santa Ana'),
(2002, 'Christ Cathedral Parish', 'Garden Grove'),
(2002, 'Blessed Sacrament Catholic Church', 'Westminster'),
(2002, 'Holy Trinity Catholic Church', 'Ladera Ranch'),
(2002, 'Saint Thomas More Catholic Church', 'Irvine');

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_expected_parishes_2002_diocese_id ON expected_parishes_2002(diocese_id);

-- Show summary
SELECT
    diocese_id,
    COUNT(*) as total_expected_parishes,
    COUNT(DISTINCT city) as unique_cities
FROM expected_parishes_2002
WHERE diocese_id = 2002
GROUP BY diocese_id;

-- Show all expected parishes for verification
SELECT parish_name, city FROM expected_parishes_2002 WHERE diocese_id = 2002 ORDER BY parish_name;
