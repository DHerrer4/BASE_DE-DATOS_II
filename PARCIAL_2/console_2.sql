CREATE DATABASE IF NOT EXISTS gestion_legal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE gestion_legal;

-- ------------------------------------------------------------
-- TABLA: aseguradora
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
-- TABLA: licenciado (NUEVA)
-- Abogados/licenciados que llevan los casos
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licenciado (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    cedula          VARCHAR(20)  NOT NULL UNIQUE,
    telefono        VARCHAR(20),
    email           VARCHAR(100) UNIQUE,
    especialidad    VARCHAR(100),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: tipo_caso (NUEVA)
-- Clasificación de los tipos de casos legales
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tipo_caso (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    activo      BOOLEAN DEFAULT TRUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: expediente
-- Ahora incluye FK a licenciado y tipo_caso
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expediente (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    numero          VARCHAR(50)  NOT NULL UNIQUE COMMENT 'Número de expediente judicial',
    cliente_nombre  VARCHAR(150) NOT NULL,
    cliente_cedula  VARCHAR(30),
    descripcion     TEXT,
    estado          ENUM('pendiente','en_curso','cerrado') DEFAULT 'pendiente',
    aseguradora_id  INT,
    juzgado_id      INT,
    abogado_id      INT,
    licenciado_id   INT,
    tipo_caso_id    INT,
    fecha_inicio    DATE,
    fecha_cierre    DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (aseguradora_id) REFERENCES aseguradora(id) ON DELETE SET NULL,
    FOREIGN KEY (juzgado_id)     REFERENCES juzgado(id)     ON DELETE SET NULL,
    FOREIGN KEY (abogado_id)     REFERENCES usuario(id)     ON DELETE SET NULL,
    FOREIGN KEY (licenciado_id)  REFERENCES licenciado(id)  ON DELETE SET NULL,
    FOREIGN KEY (tipo_caso_id)   REFERENCES tipo_caso(id)   ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- TABLA: audiencia
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
-- VISTAS SQL
-- ------------------------------------------------------------

-- Vista 1: Agenda del día con toda la información relevante
CREATE OR REPLACE VIEW v_agenda_dia AS
    SELECT
        au.id,
        au.fecha,
        au.hora,
        au.lugar,
        au.tipo,
        au.estado,
        e.numero          AS expediente,
        e.cliente_nombre,
        a.nombre          AS aseguradora,
        j.nombre          AS juzgado,
        l.nombre_completo AS licenciado,
        tc.nombre         AS tipo_caso
    FROM audiencia au
    JOIN expediente    e  ON au.expediente_id = e.id
    LEFT JOIN aseguradora  a  ON e.aseguradora_id = a.id
    LEFT JOIN juzgado      j  ON e.juzgado_id     = j.id
    LEFT JOIN licenciado   l  ON e.licenciado_id  = l.id
    LEFT JOIN tipo_caso    tc ON e.tipo_caso_id   = tc.id;

-- Vista 2: Resumen de expedientes por estado y aseguradora
CREATE OR REPLACE VIEW v_resumen_expedientes AS
    SELECT
        a.nombre          AS aseguradora,
        e.estado,
        COUNT(e.id)       AS total,
        MIN(e.fecha_inicio) AS primer_caso,
        MAX(e.fecha_inicio) AS ultimo_caso
    FROM expediente e
    LEFT JOIN aseguradora a ON e.aseguradora_id = a.id
    GROUP BY a.nombre, e.estado
    ORDER BY a.nombre, e.estado;

-- Vista 3: Carga de trabajo por licenciado
CREATE OR REPLACE VIEW v_carga_licenciado AS
    SELECT
        l.nombre_completo          AS licenciado,
        l.especialidad,
        COUNT(e.id)                AS total_expedientes,
        SUM(e.estado = 'pendiente')  AS pendientes,
        SUM(e.estado = 'en_curso')   AS en_curso,
        SUM(e.estado = 'cerrado')    AS cerrados
    FROM licenciado l
    LEFT JOIN expediente e ON e.licenciado_id = l.id
    GROUP BY l.id, l.nombre_completo, l.especialidad
    ORDER BY total_expedientes DESC;

-- ------------------------------------------------------------
-- DATOS DE EJEMPLO
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

INSERT INTO licenciado (nombre_completo, cedula, telefono, email, especialidad) VALUES
('Juan Pérez',      '8-123-456', '507-6000-1111', 'jperez@legal.pa',    'Derecho Civil'),
('María González',  '8-234-567', '507-6000-2222', 'mgonzalez@legal.pa', 'Derecho Laboral'),
('Carlos Mendoza',  '8-345-678', '507-6000-3333', 'cmendoza@legal.pa',  'Derecho Penal'),
('Ana Rodríguez',   '8-456-789', '507-6000-4444', 'arodriguez@legal.pa','Derecho Familiar'),
('Luis Castillo',   '8-567-890', '507-6000-5555', 'lcastillo@legal.pa', 'Derecho Mercantil');

INSERT INTO tipo_caso (nombre, descripcion) VALUES
('Accidente de Tránsito',   'Casos relacionados con accidentes vehiculares'),
('Daños y Perjuicios',      'Reclamaciones por daños materiales o personales'),
('Responsabilidad Civil',   'Casos de responsabilidad civil contractual o extracontractual'),
('Seguro de Vida',          'Reclamaciones relacionadas con pólizas de vida'),
('Incapacidad Laboral',     'Casos de incapacidad derivada de accidentes laborales');

INSERT INTO expediente (numero, cliente_nombre, estado, aseguradora_id, juzgado_id, abogado_id, licenciado_id, tipo_caso_id, fecha_inicio) VALUES
('EXP-001', 'ANTHONY TREJOS',      'en_curso',  1, 1, 1, 1, 1, '2019-01-07'),
('EXP-002', 'LUIS MOLINA',         'pendiente', 2, 2, 1, 2, 2, '2019-01-07'),
('EXP-003', 'KATHERINE KENT',      'en_curso',  1, 1, 1, 1, 1, '2019-01-07'),
('EXP-004', 'MARTIN ALVARADO',     'pendiente', 3, 3, 1, 3, 3, '2019-01-07'),
('EXP-005', 'JOEL ARAUZ RODRIGUEZ','cerrado',   4, 4, 1, 4, 4, '2018-06-01'),
('EXP-006', 'MICHELLE VEGA',       'en_curso',  5, 5, 1, 5, 5, '2019-01-07'),
('EXP-007', 'CANDICE HENRY',       'pendiente', 2, 6, 1, 2, 2, '2019-01-07');

INSERT INTO audiencia (expediente_id, fecha, hora, lugar, tipo, estado) VALUES
(1, '2019-01-07', '08:00:00', 'JUZGADO 5TO (PEDREGAL)', 'Audiencia Inicial',  'programada'),
(2, '2019-01-07', '09:00:00', 'JUZGADO 4TO (PEDREGAL)', 'Audiencia de Vista', 'programada'),
(3, '2019-01-07', '10:00:00', 'JUZGADO 5TO (PEDREGAL)', 'Audiencia Final',    'programada'),
(4, '2019-01-07', '11:00:00', 'JUZGADO 1RO (PEDREGAL)', 'Audiencia Inicial',  'programada'),
(5, '2019-01-07', '14:00:00', 'JUZGADO 3RO (PEDREGAL)', 'Sentencia',          'realizada'),
(6, '2019-01-07', '15:00:00', 'ALCALDIA DE PANAMA',     'Mediación',          'programada'),
(7, '2019-01-07', '16:00:00', 'CHITRE',                 'Audiencia Inicial',  'programada');