CREATE DATABASE IF NOT EXISTS gestion_legal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE gestion_legal;

-- ------------------------------------------------------------
-- TABLA: aseguradora
-- Empresas aseguradoras que tienen casos en el sistema
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aseguradora (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL UNIQUE,
    telefono    VARCHAR(20),
    email       VARCHAR(100),
    direccion   VARCHAR(200),
    activa      BOOLEAN DEFAULT TRUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: juzgado
-- Tribunales / juzgados donde se realizan audiencias
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS juzgado (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL UNIQUE,
    ubicacion   VARCHAR(200),
    telefono    VARCHAR(20),
    activo      BOOLEAN DEFAULT TRUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: usuario
-- Abogados y personal del sistema
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(100) UNIQUE,
    rol             ENUM('admin','abogado','asistente') DEFAULT 'abogado',
    activo          BOOLEAN DEFAULT TRUE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: expediente
-- Casos / expedientes legales gestionados
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expediente (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    numero          VARCHAR(50) NOT NULL UNIQUE COMMENT 'Número de expediente judicial',
    cliente_nombre  VARCHAR(150) NOT NULL,
    cliente_cedula  VARCHAR(30),
    descripcion     TEXT,
    estado          ENUM('pendiente','en_curso','cerrado') DEFAULT 'pendiente',
    aseguradora_id  INT,
    juzgado_id      INT,
    abogado_id      INT,
    fecha_inicio    DATE,
    fecha_cierre    DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (aseguradora_id) REFERENCES aseguradora(id) ON DELETE SET NULL,
    FOREIGN KEY (juzgado_id)     REFERENCES juzgado(id)     ON DELETE SET NULL,
    FOREIGN KEY (abogado_id)     REFERENCES usuario(id)     ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: audiencia
-- Citas / audiencias en la agenda del día
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audiencia (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    expediente_id   INT NOT NULL,
    fecha           DATE NOT NULL,
    hora            TIME NOT NULL,
    lugar           VARCHAR(200),
    tipo            VARCHAR(100) COMMENT 'Tipo de audiencia (inicial, final, etc.)',
    observaciones   TEXT,
    estado          ENUM('programada','realizada','cancelada','reprogramada') DEFAULT 'programada',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (expediente_id) REFERENCES expediente(id) ON DELETE CASCADE,
    INDEX idx_fecha (fecha)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- DATOS DE EJEMPLO (semilla)
-- ------------------------------------------------------------

INSERT INTO aseguradora (nombre, telefono, email) VALUES
('ASSA',          '507-300-1234', 'legal@assa.com.pa'),
('ANCON',         '507-300-2345', 'legal@ancon.com.pa'),
('CONANCE',       '507-300-3456', 'legal@conance.com.pa'),
('PARTICULAR',    NULL,           NULL),
('INTEROCEANICA', '507-300-5678', 'legal@interoceanica.com.pa');

INSERT INTO juzgado (nombre, ubicacion) VALUES
('JUZGADO 5TO (PEDREGAL)',  'Pedregal, Ciudad de Panamá'),
('JUZGADO 4TO (PEDREGAL)',  'Pedregal, Ciudad de Panamá'),
('JUZGADO 1RO (PEDREGAL)',  'Pedregal, Ciudad de Panamá'),
('JUZGADO 3RO (PEDREGAL)',  'Pedregal, Ciudad de Panamá'),
('ALCALDIA DE PANAMA',      'Casco Antiguo, Ciudad de Panamá'),
('CHITRE',                  'Chitré, Herrera');

INSERT INTO usuario (nombre_completo, username, password_hash, rol) VALUES
('Juan Pérez', 'jperez', SHA2('admin123', 256), 'admin');

INSERT INTO expediente (numero, cliente_nombre, estado, aseguradora_id, juzgado_id, abogado_id, fecha_inicio) VALUES
('EXP-001', 'ANTHONY TREJOS',    'en_curso',  1, 1, 1, '2019-01-07'),
('EXP-002', 'LUIS MOLINA',       'pendiente', 2, 2, 1, '2019-01-07'),
('EXP-003', 'KATHERINE KENT',    'en_curso',  1, 1, 1, '2019-01-07'),
('EXP-004', 'MARTIN ALVARADO',   'pendiente', 3, 3, 1, '2019-01-07'),
('EXP-005', 'JOEL ARAUZ RODRIGUEZ','cerrado', 4, 4, 1, '2018-06-01'),
('EXP-006', 'MICHELLE VEGA',     'en_curso',  5, 5, 1, '2019-01-07'),
('EXP-007', 'CANDICE HENRY',     'pendiente', 2, 6, 1, '2019-01-07');

INSERT INTO audiencia (expediente_id, fecha, hora, lugar, tipo, estado) VALUES
(1, '2019-01-07', '08:00:00', 'JUZGADO 5TO (PEDREGAL)', 'Audiencia Inicial',  'programada'),
(2, '2019-01-07', '09:00:00', 'JUZGADO 4TO (PEDREGAL)', 'Audiencia de Vista', 'programada'),
(3, '2019-01-07', '10:00:00', 'JUZGADO 5TO (PEDREGAL)', 'Audiencia Final',    'programada'),
(4, '2019-01-07', '11:00:00', 'JUZGADO 1RO (PEDREGAL)', 'Audiencia Inicial',  'programada'),
(5, '2019-01-07', '14:00:00', 'JUZGADO 3RO (PEDREGAL)', 'Sentencia',          'realizada'),
(6, '2019-01-07', '15:00:00', 'ALCALDIA DE PANAMA',     'Mediación',          'programada'),
(7, '2019-01-07', '16:00:00', 'CHITRE',                  'Audiencia Inicial',  'programada');




