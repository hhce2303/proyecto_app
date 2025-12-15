-- =====================================================
-- ESTRUCTURA COMPLETA DE BASE DE DATOS: daily
-- Generado: 2025-12-14 02:15:51
-- NOTA: Este script NO incluye datos, solo estructura
-- =====================================================

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS `daily` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `daily`;

-- Deshabilitar verificación de foreign keys temporalmente
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- Tabla: actividades
-- =====================================================

DROP TABLE IF EXISTS `actividades`;

CREATE TABLE `actividades` (
  `ID_Actividad` int NOT NULL AUTO_INCREMENT,
  `Nombre_Actividad` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`ID_Actividad`),
  UNIQUE KEY `Nombre_Actividad_UNIQUE` (`Nombre_Actividad`)
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb3;

-- Columnas de actividades:
--   ID_Actividad: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_Actividad: varchar(255) [UNIQUE]

-- =====================================================
-- Tabla: covers
-- =====================================================

DROP TABLE IF EXISTS `covers`;

CREATE TABLE `covers` (
  `ID_Covers` int NOT NULL AUTO_INCREMENT,
  `Nombre_Usuarios` varchar(45) DEFAULT NULL,
  `Cover_in` datetime NOT NULL,
  `Cover_Out` datetime DEFAULT NULL,
  `Covered_by` varchar(45) DEFAULT NULL,
  `Motivo` varchar(45) NOT NULL,
  `Activo` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`ID_Covers`),
  UNIQUE KEY `ID_Covers` (`ID_Covers`),
  KEY `Motivo_idx` (`Motivo`),
  KEY `Usuario_idx` (`Nombre_Usuarios`),
  KEY `covered_idx` (`Covered_by`),
  CONSTRAINT `covered` FOREIGN KEY (`Covered_by`) REFERENCES `user` (`Nombre_Usuario`),
  CONSTRAINT `covers_ibfk_1` FOREIGN KEY (`Nombre_Usuarios`) REFERENCES `user` (`Nombre_Usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `covers_ibfk_2` FOREIGN KEY (`Covered_by`) REFERENCES `user` (`Nombre_Usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `user cover` FOREIGN KEY (`Nombre_Usuarios`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=2487 DEFAULT CHARSET=utf8mb3;

-- Columnas de covers:
--   ID_Covers: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_Usuarios: varchar(45) [INDEX]
--   Cover_in: datetime NOT NULL
--   Cover_Out: datetime
--   Covered_by: varchar(45) [INDEX]
--   Motivo: varchar(45) [INDEX] NOT NULL
--   Activo: varchar(10)

-- Foreign Keys de covers:
--   Covered_by -> user(Nombre_Usuario) [covered]
--   Nombre_Usuarios -> user(Nombre_Usuario) [covers_ibfk_1]
--   Covered_by -> user(Nombre_Usuario) [covers_ibfk_2]
--   Nombre_Usuarios -> user(Nombre_Usuario) [user cover]

-- =====================================================
-- Tabla: covers_deleted
-- =====================================================

DROP TABLE IF EXISTS `covers_deleted`;

CREATE TABLE `covers_deleted` (
  `ID_Covers` int NOT NULL AUTO_INCREMENT,
  `Nombre_Usuarios` varchar(45) DEFAULT NULL,
  `Cover_in` datetime NOT NULL,
  `Cover_Out` datetime DEFAULT NULL,
  `Covered_by` varchar(45) NOT NULL,
  `Motivo` varchar(45) NOT NULL,
  `Activo` varchar(10) DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deletion_reason` text,
  PRIMARY KEY (`ID_Covers`),
  UNIQUE KEY `ID_Covers` (`ID_Covers`),
  KEY `Motivo_idx` (`Motivo`),
  KEY `Usuario_idx` (`Nombre_Usuarios`),
  KEY `covered_idx` (`Covered_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de covers_deleted:
--   ID_Covers: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_Usuarios: varchar(45) [INDEX]
--   Cover_in: datetime NOT NULL
--   Cover_Out: datetime
--   Covered_by: varchar(45) [INDEX] NOT NULL
--   Motivo: varchar(45) [INDEX] NOT NULL
--   Activo: varchar(10)
--   deleted_at: timestamp DEFAULT CURRENT_TIMESTAMP DEFAULT_GENERATED
--   deleted_by: varchar(100)
--   deletion_reason: text

-- =====================================================
-- Tabla: covers_programados
-- =====================================================

DROP TABLE IF EXISTS `covers_programados`;

CREATE TABLE `covers_programados` (
  `ID_Cover` int NOT NULL AUTO_INCREMENT,
  `ID_user` varchar(50) NOT NULL,
  `Time_request` datetime NOT NULL,
  `Station` varchar(45) DEFAULT NULL,
  `Reason` varchar(45) DEFAULT NULL,
  `Approved` tinyint DEFAULT NULL,
  `is_Active` tinyint NOT NULL,
  PRIMARY KEY (`ID_Cover`),
  KEY `covers_ss_idx` (`ID_user`),
  KEY `stations_idx` (`Station`),
  CONSTRAINT `stations_cover` FOREIGN KEY (`Station`) REFERENCES `estaciones_id` (`id_station`),
  CONSTRAINT `user_cover` FOREIGN KEY (`ID_user`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb3;

-- Columnas de covers_programados:
--   ID_Cover: int [PRIMARY KEY] NOT NULL auto_increment
--   ID_user: varchar(50) [INDEX] NOT NULL
--   Time_request: datetime NOT NULL
--   Station: varchar(45) [INDEX]
--   Reason: varchar(45)
--   Approved: tinyint
--   is_Active: tinyint NOT NULL

-- Foreign Keys de covers_programados:
--   Station -> estaciones_id(id_station) [stations_cover]
--   ID_user -> user(Nombre_Usuario) [user_cover]

-- =====================================================
-- Tabla: covers_realizados
-- =====================================================

DROP TABLE IF EXISTS `covers_realizados`;

CREATE TABLE `covers_realizados` (
  `ID_Covers` int NOT NULL AUTO_INCREMENT,
  `Nombre_usuarios` varchar(45) NOT NULL,
  `ID_programacion_covers` int DEFAULT NULL,
  `Cover_in` datetime NOT NULL,
  `Cover_out` datetime DEFAULT NULL,
  `Covered_by` varchar(45) DEFAULT NULL,
  `Motivo` varchar(45) NOT NULL,
  PRIMARY KEY (`ID_Covers`),
  KEY `ID_programacion_idx` (`ID_programacion_covers`),
  KEY `Nombre_usuario_idx` (`Nombre_usuarios`),
  KEY `Covered_by_idx` (`Covered_by`),
  KEY `Motivo_idx` (`Motivo`),
  CONSTRAINT `Covered_by` FOREIGN KEY (`Covered_by`) REFERENCES `user` (`Nombre_Usuario`),
  CONSTRAINT `motivo` FOREIGN KEY (`Motivo`) REFERENCES `motivo_id` (`Motivo`),
  CONSTRAINT `Nombre_usuario` FOREIGN KEY (`Nombre_usuarios`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=194 DEFAULT CHARSET=utf8mb3;

-- Columnas de covers_realizados:
--   ID_Covers: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_usuarios: varchar(45) [INDEX] NOT NULL
--   ID_programacion_covers: int [INDEX]
--   Cover_in: datetime NOT NULL
--   Cover_out: datetime
--   Covered_by: varchar(45) [INDEX]
--   Motivo: varchar(45) [INDEX] NOT NULL

-- Foreign Keys de covers_realizados:
--   Covered_by -> user(Nombre_Usuario) [Covered_by]
--   Motivo -> motivo_id(Motivo) [motivo]
--   Nombre_usuarios -> user(Nombre_Usuario) [Nombre_usuario]

-- =====================================================
-- Tabla: estaciones
-- =====================================================

DROP TABLE IF EXISTS `estaciones`;

CREATE TABLE `estaciones` (
  `ID_Estaciones` int NOT NULL AUTO_INCREMENT,
  `User_Logged` varchar(100) DEFAULT NULL,
  `Station_Number` int DEFAULT NULL,
  PRIMARY KEY (`ID_Estaciones`),
  UNIQUE KEY `ID_Estaciones` (`ID_Estaciones`),
  KEY `estaciones_id` (`Station_Number`),
  KEY `user_idx` (`User_Logged`),
  CONSTRAINT `estaciones_id` FOREIGN KEY (`Station_Number`) REFERENCES `estaciones_id` (`numero_estacion`),
  CONSTRAINT `user` FOREIGN KEY (`User_Logged`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=9286 DEFAULT CHARSET=utf8mb3;

-- Columnas de estaciones:
--   ID_Estaciones: int [PRIMARY KEY] NOT NULL auto_increment
--   User_Logged: varchar(100) [INDEX]
--   Station_Number: int [INDEX]

-- Foreign Keys de estaciones:
--   Station_Number -> estaciones_id(numero_estacion) [estaciones_id]
--   User_Logged -> user(Nombre_Usuario) [user]

-- =====================================================
-- Tabla: estaciones_deleted
-- =====================================================

DROP TABLE IF EXISTS `estaciones_deleted`;

CREATE TABLE `estaciones_deleted` (
  `ID_Estaciones` int NOT NULL AUTO_INCREMENT,
  `User_Logged` varchar(100) DEFAULT NULL,
  `Station_Number` int DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deletion_reason` text,
  PRIMARY KEY (`ID_Estaciones`),
  UNIQUE KEY `ID_Estaciones` (`ID_Estaciones`),
  KEY `estaciones_id` (`Station_Number`),
  KEY `user_idx` (`User_Logged`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de estaciones_deleted:
--   ID_Estaciones: int [PRIMARY KEY] NOT NULL auto_increment
--   User_Logged: varchar(100) [INDEX]
--   Station_Number: int [INDEX]
--   deleted_at: timestamp DEFAULT CURRENT_TIMESTAMP DEFAULT_GENERATED
--   deleted_by: varchar(100)
--   deletion_reason: text

-- =====================================================
-- Tabla: estaciones_id
-- =====================================================

DROP TABLE IF EXISTS `estaciones_id`;

CREATE TABLE `estaciones_id` (
  `numero_estacion` int NOT NULL,
  `id_station` varchar(45) NOT NULL,
  PRIMARY KEY (`id_station`),
  UNIQUE KEY `id_station` (`id_station`),
  UNIQUE KEY `numero_estacion_UNIQUE` (`numero_estacion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de estaciones_id:
--   numero_estacion: int [UNIQUE] NOT NULL
--   id_station: varchar(45) [PRIMARY KEY] NOT NULL

-- =====================================================
-- Tabla: eventos
-- =====================================================

DROP TABLE IF EXISTS `eventos`;

CREATE TABLE `eventos` (
  `ID_Eventos` int NOT NULL AUTO_INCREMENT,
  `FechaHora` datetime DEFAULT NULL,
  `ID_Sitio` int DEFAULT NULL,
  `Nombre_Actividad` varchar(255) DEFAULT NULL,
  `Cantidad` varchar(45) DEFAULT NULL,
  `Camera` varchar(45) DEFAULT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `ID_Usuario` int DEFAULT NULL,
  `Eventoscol` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`ID_Eventos`),
  UNIQUE KEY `ID_Eventos` (`ID_Eventos`),
  KEY `Sitio_idx` (`ID_Sitio`),
  KEY `Actividad_idx` (`Nombre_Actividad`) /*!80000 INVISIBLE */,
  KEY `Usuario_idx` (`ID_Usuario`),
  CONSTRAINT `actividades_eventos` FOREIGN KEY (`Nombre_Actividad`) REFERENCES `actividades` (`Nombre_Actividad`),
  CONSTRAINT `eventos_ibfk_1` FOREIGN KEY (`ID_Sitio`) REFERENCES `sitios` (`ID_Sitio`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `eventos_ibfk_2` FOREIGN KEY (`ID_Usuario`) REFERENCES `user` (`ID_Usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `eventos_ibfk_3` FOREIGN KEY (`Nombre_Actividad`) REFERENCES `actividades` (`Nombre_Actividad`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `Sitio` FOREIGN KEY (`ID_Sitio`) REFERENCES `sitios` (`ID_Sitio`)
) ENGINE=InnoDB AUTO_INCREMENT=17839 DEFAULT CHARSET=utf8mb3;

-- Columnas de eventos:
--   ID_Eventos: int [PRIMARY KEY] NOT NULL auto_increment
--   FechaHora: datetime
--   ID_Sitio: int [INDEX]
--   Nombre_Actividad: varchar(255) [INDEX]
--   Cantidad: varchar(45)
--   Camera: varchar(45)
--   Descripcion: varchar(255)
--   ID_Usuario: int [INDEX]
--   Eventoscol: varchar(45)

-- Foreign Keys de eventos:
--   Nombre_Actividad -> actividades(Nombre_Actividad) [actividades_eventos]
--   ID_Sitio -> sitios(ID_Sitio) [eventos_ibfk_1]
--   ID_Usuario -> user(ID_Usuario) [eventos_ibfk_2]
--   Nombre_Actividad -> actividades(Nombre_Actividad) [eventos_ibfk_3]
--   ID_Sitio -> sitios(ID_Sitio) [Sitio]

-- =====================================================
-- Tabla: eventos_backup
-- =====================================================

DROP TABLE IF EXISTS `eventos_backup`;

CREATE TABLE `eventos_backup` (
  `ideventos_backup` int NOT NULL,
  PRIMARY KEY (`ideventos_backup`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de eventos_backup:
--   ideventos_backup: int [PRIMARY KEY] NOT NULL

-- =====================================================
-- Tabla: eventos_deleted
-- =====================================================

DROP TABLE IF EXISTS `eventos_deleted`;

CREATE TABLE `eventos_deleted` (
  `ID_Eventos` int NOT NULL AUTO_INCREMENT,
  `FechaHora` datetime DEFAULT NULL,
  `ID_Sitio` int DEFAULT NULL,
  `Nombre_Actividad` varchar(255) DEFAULT NULL,
  `Cantidad` varchar(45) DEFAULT NULL,
  `Camera` varchar(45) DEFAULT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `ID_Usuario` int DEFAULT NULL,
  `Eventoscol` varchar(45) DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deletion_reason` text,
  PRIMARY KEY (`ID_Eventos`),
  UNIQUE KEY `ID_Eventos` (`ID_Eventos`),
  KEY `Sitio_idx` (`ID_Sitio`),
  KEY `Actividad_idx` (`Nombre_Actividad`) /*!80000 INVISIBLE */,
  KEY `Usuario_idx` (`ID_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=17809 DEFAULT CHARSET=utf8mb3;

-- Columnas de eventos_deleted:
--   ID_Eventos: int [PRIMARY KEY] NOT NULL auto_increment
--   FechaHora: datetime
--   ID_Sitio: int [INDEX]
--   Nombre_Actividad: varchar(255) [INDEX]
--   Cantidad: varchar(45)
--   Camera: varchar(45)
--   Descripcion: varchar(255)
--   ID_Usuario: int [INDEX]
--   Eventoscol: varchar(45)
--   deleted_at: timestamp DEFAULT CURRENT_TIMESTAMP DEFAULT_GENERATED
--   deleted_by: varchar(100)
--   deletion_reason: text

-- =====================================================
-- Tabla: gestion_breaks_programados
-- =====================================================

DROP TABLE IF EXISTS `gestion_breaks_programados`;

CREATE TABLE `gestion_breaks_programados` (
  `ID_cover` int NOT NULL AUTO_INCREMENT,
  `User_covering` int NOT NULL,
  `User_covered` int DEFAULT NULL,
  `Fecha_hora_cover` datetime NOT NULL,
  `is_Active` tinyint DEFAULT NULL,
  `Supervisor` int NOT NULL,
  `Fecha_creacion` datetime NOT NULL,
  PRIMARY KEY (`ID_cover`),
  KEY `user_covering_idx` (`User_covering`),
  KEY `user_covered_idx` (`User_covered`),
  KEY `supervisor_idx` (`Supervisor`),
  KEY `created_supervisor_idx` (`Supervisor`),
  CONSTRAINT `created_supervisor` FOREIGN KEY (`Supervisor`) REFERENCES `user` (`ID_Usuario`),
  CONSTRAINT `user_covered` FOREIGN KEY (`User_covered`) REFERENCES `user` (`ID_Usuario`),
  CONSTRAINT `user_covering` FOREIGN KEY (`User_covering`) REFERENCES `user` (`ID_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Columnas de gestion_breaks_programados:
--   ID_cover: int [PRIMARY KEY] NOT NULL auto_increment
--   User_covering: int [INDEX] NOT NULL
--   User_covered: int [INDEX]
--   Fecha_hora_cover: datetime NOT NULL
--   is_Active: tinyint
--   Supervisor: int [INDEX] NOT NULL
--   Fecha_creacion: datetime NOT NULL

-- Foreign Keys de gestion_breaks_programados:
--   Supervisor -> user(ID_Usuario) [created_supervisor]
--   User_covered -> user(ID_Usuario) [user_covered]
--   User_covering -> user(ID_Usuario) [user_covering]

-- =====================================================
-- Tabla: information
-- =====================================================

DROP TABLE IF EXISTS `information`;

CREATE TABLE `information` (
  `ID_information` int NOT NULL AUTO_INCREMENT,
  `info_type` varchar(45) NOT NULL,
  `name_info` varchar(45) NOT NULL,
  `urgency` varchar(45) NOT NULL,
  `publish_by` varchar(45) DEFAULT NULL,
  `fechahora_in` datetime NOT NULL,
  `fechahora_out` datetime DEFAULT NULL,
  `is_Active` tinyint NOT NULL,
  PRIMARY KEY (`ID_information`),
  KEY `publish_by_idx` (`publish_by`),
  CONSTRAINT `publish_by` FOREIGN KEY (`publish_by`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb3;

-- Columnas de information:
--   ID_information: int [PRIMARY KEY] NOT NULL auto_increment
--   info_type: varchar(45) NOT NULL
--   name_info: varchar(45) NOT NULL
--   urgency: varchar(45) NOT NULL
--   publish_by: varchar(45) [INDEX]
--   fechahora_in: datetime NOT NULL
--   fechahora_out: datetime
--   is_Active: tinyint NOT NULL

-- Foreign Keys de information:
--   publish_by -> user(Nombre_Usuario) [publish_by]

-- =====================================================
-- Tabla: motivo_id
-- =====================================================

DROP TABLE IF EXISTS `motivo_id`;

CREATE TABLE `motivo_id` (
  `id_motivo` int NOT NULL AUTO_INCREMENT,
  `Motivo` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_motivo`),
  UNIQUE KEY `id_motivo` (`id_motivo`),
  UNIQUE KEY `Motivo_UNIQUE` (`Motivo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;

-- Columnas de motivo_id:
--   id_motivo: int [PRIMARY KEY] NOT NULL auto_increment
--   Motivo: varchar(45) [UNIQUE]

-- =====================================================
-- Tabla: rol_id
-- =====================================================

DROP TABLE IF EXISTS `rol_id`;

CREATE TABLE `rol_id` (
  `id_rol` int NOT NULL AUTO_INCREMENT,
  `nombre_rol` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_rol`),
  UNIQUE KEY `nombre_rol_UNIQUE` (`nombre_rol`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;

-- Columnas de rol_id:
--   id_rol: int [PRIMARY KEY] NOT NULL auto_increment
--   nombre_rol: varchar(45) [UNIQUE]

-- =====================================================
-- Tabla: sesion
-- =====================================================

DROP TABLE IF EXISTS `sesion`;

CREATE TABLE `sesion` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `ID_user` varchar(45) NOT NULL,
  `Log_in` datetime NOT NULL,
  `ID_estacion` varchar(45) NOT NULL,
  `Log_out` datetime DEFAULT NULL,
  `Active` tinyint NOT NULL,
  `Statuses` tinyint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `user_sesion_idx` (`ID_user`),
  KEY `station_idx` (`ID_estacion`),
  CONSTRAINT `station` FOREIGN KEY (`ID_estacion`) REFERENCES `estaciones_id` (`id_station`),
  CONSTRAINT `user_sesion` FOREIGN KEY (`ID_user`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=1633 DEFAULT CHARSET=utf8mb3;

-- Columnas de sesion:
--   ID: int [PRIMARY KEY] NOT NULL auto_increment
--   ID_user: varchar(45) [INDEX] NOT NULL
--   Log_in: datetime NOT NULL
--   ID_estacion: varchar(45) [INDEX] NOT NULL
--   Log_out: datetime
--   Active: tinyint NOT NULL
--   Statuses: tinyint

-- Foreign Keys de sesion:
--   ID_estacion -> estaciones_id(id_station) [station]
--   ID_user -> user(Nombre_Usuario) [user_sesion]

-- =====================================================
-- Tabla: sesiones
-- =====================================================

DROP TABLE IF EXISTS `sesiones`;

CREATE TABLE `sesiones` (
  `ID_Sesion` int NOT NULL AUTO_INCREMENT,
  `Nombre_Usuario` varchar(45) DEFAULT NULL,
  `Stations_ID` int DEFAULT NULL,
  `Login_Time` datetime DEFAULT NULL,
  `Log_Out` datetime DEFAULT NULL,
  `Is_Active` binary(10) NOT NULL,
  PRIMARY KEY (`ID_Sesion`),
  UNIQUE KEY `ID_Sesion` (`ID_Sesion`),
  KEY `user_idx` (`Nombre_Usuario`),
  CONSTRAINT `sesiones_ibfk_1` FOREIGN KEY (`Nombre_Usuario`) REFERENCES `user` (`Nombre_Usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `users_sesion` FOREIGN KEY (`Nombre_Usuario`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=8276 DEFAULT CHARSET=utf8mb3;

-- Columnas de sesiones:
--   ID_Sesion: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_Usuario: varchar(45) [INDEX]
--   Stations_ID: int
--   Login_Time: datetime
--   Log_Out: datetime
--   Is_Active: binary(10) NOT NULL

-- Foreign Keys de sesiones:
--   Nombre_Usuario -> user(Nombre_Usuario) [sesiones_ibfk_1]
--   Nombre_Usuario -> user(Nombre_Usuario) [users_sesion]

-- =====================================================
-- Tabla: sesiones_deleted
-- =====================================================

DROP TABLE IF EXISTS `sesiones_deleted`;

CREATE TABLE `sesiones_deleted` (
  `ID_Sesion` int NOT NULL AUTO_INCREMENT,
  `Nombre_Usuario` varchar(45) NOT NULL,
  `Stations_ID` int DEFAULT NULL,
  `Login_Time` datetime DEFAULT NULL,
  `Log_Out` datetime DEFAULT NULL,
  `Is_Active` binary(10) NOT NULL,
  `deleted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deletion_reason` text,
  PRIMARY KEY (`ID_Sesion`),
  UNIQUE KEY `ID_Sesion` (`ID_Sesion`),
  KEY `user_idx` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=4288 DEFAULT CHARSET=utf8mb3;

-- Columnas de sesiones_deleted:
--   ID_Sesion: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_Usuario: varchar(45) [INDEX] NOT NULL
--   Stations_ID: int
--   Login_Time: datetime
--   Log_Out: datetime
--   Is_Active: binary(10) NOT NULL
--   deleted_at: timestamp DEFAULT CURRENT_TIMESTAMP DEFAULT_GENERATED
--   deleted_by: varchar(100)
--   deletion_reason: text

-- =====================================================
-- Tabla: sitios
-- =====================================================

DROP TABLE IF EXISTS `sitios`;

CREATE TABLE `sitios` (
  `ID_Sitio` int NOT NULL,
  `ID_Grupo` varchar(255) DEFAULT NULL,
  `Nombre_sitio` varchar(255) DEFAULT NULL,
  `Time_Zone` varchar(45) NOT NULL,
  PRIMARY KEY (`ID_Sitio`),
  UNIQUE KEY `idSitios` (`ID_Sitio`),
  KEY `timezones_idx` (`Time_Zone`),
  CONSTRAINT `timezones` FOREIGN KEY (`Time_Zone`) REFERENCES `time_zone_id` (`time_zone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de sitios:
--   ID_Sitio: int [PRIMARY KEY] NOT NULL
--   ID_Grupo: varchar(255)
--   Nombre_sitio: varchar(255)
--   Time_Zone: varchar(45) [INDEX] NOT NULL

-- Foreign Keys de sitios:
--   Time_Zone -> time_zone_id(time_zone) [timezones]

-- =====================================================
-- Tabla: specials
-- =====================================================

DROP TABLE IF EXISTS `specials`;

CREATE TABLE `specials` (
  `ID_Special` int NOT NULL AUTO_INCREMENT,
  `FechaHora` datetime NOT NULL,
  `ID_Sitio` int DEFAULT NULL,
  `Nombre_Actividad` varchar(45) DEFAULT NULL,
  `Cantidad` varchar(45) NOT NULL,
  `Camera` varchar(45) NOT NULL,
  `Descripcion` varchar(255) NOT NULL,
  `Usuario` varchar(45) DEFAULT NULL,
  `Time_Zone` varchar(45) NOT NULL,
  `Supervisor` varchar(45) DEFAULT NULL,
  `marked_status` varchar(20) DEFAULT NULL COMMENT 'Estado de marca: flagged, last o NULL',
  `marked_at` timestamp NULL DEFAULT NULL COMMENT 'Fecha/hora de marcado',
  `marked_by` varchar(100) DEFAULT NULL COMMENT 'Usuario que marcó el registro',
  PRIMARY KEY (`ID_Special`),
  UNIQUE KEY `ID_Special` (`ID_Special`),
  KEY `Sitio_idx` (`ID_Sitio`),
  KEY `Actividad_idx` (`Nombre_Actividad`),
  KEY `Time_zone_idx` (`Time_Zone`),
  KEY `supervisor_idx` (`Supervisor`) /*!80000 INVISIBLE */,
  KEY `usuario_idx` (`Usuario`),
  CONSTRAINT `Actividades` FOREIGN KEY (`Nombre_Actividad`) REFERENCES `actividades` (`Nombre_Actividad`),
  CONSTRAINT `specials_ibfk_1` FOREIGN KEY (`ID_Sitio`) REFERENCES `sitios` (`ID_Sitio`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `specials_ibfk_2` FOREIGN KEY (`Nombre_Actividad`) REFERENCES `actividades` (`Nombre_Actividad`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `specials_ibfk_3` FOREIGN KEY (`Usuario`) REFERENCES `user` (`Nombre_Usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `specials_ibfk_4` FOREIGN KEY (`Supervisor`) REFERENCES `user` (`Nombre_Usuario`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `Specials_Sitio_fk` FOREIGN KEY (`ID_Sitio`) REFERENCES `sitios` (`ID_Sitio`),
  CONSTRAINT `supervisor` FOREIGN KEY (`Supervisor`) REFERENCES `user` (`Nombre_Usuario`),
  CONSTRAINT `usuario` FOREIGN KEY (`Usuario`) REFERENCES `user` (`Nombre_Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=9752 DEFAULT CHARSET=utf8mb3;

-- Columnas de specials:
--   ID_Special: int [PRIMARY KEY] NOT NULL auto_increment
--   FechaHora: datetime NOT NULL
--   ID_Sitio: int [INDEX]
--   Nombre_Actividad: varchar(45) [INDEX]
--   Cantidad: varchar(45) NOT NULL
--   Camera: varchar(45) NOT NULL
--   Descripcion: varchar(255) NOT NULL
--   Usuario: varchar(45) [INDEX]
--   Time_Zone: varchar(45) [INDEX] NOT NULL
--   Supervisor: varchar(45) [INDEX]
--   marked_status: varchar(20) -- Estado de marca: flagged, last o NULL
--   marked_at: timestamp -- Fecha/hora de marcado
--   marked_by: varchar(100) -- Usuario que marcó el registro

-- Foreign Keys de specials:
--   Nombre_Actividad -> actividades(Nombre_Actividad) [Actividades]
--   ID_Sitio -> sitios(ID_Sitio) [specials_ibfk_1]
--   Nombre_Actividad -> actividades(Nombre_Actividad) [specials_ibfk_2]
--   Usuario -> user(Nombre_Usuario) [specials_ibfk_3]
--   Supervisor -> user(Nombre_Usuario) [specials_ibfk_4]
--   ID_Sitio -> sitios(ID_Sitio) [Specials_Sitio_fk]
--   Supervisor -> user(Nombre_Usuario) [supervisor]
--   Usuario -> user(Nombre_Usuario) [usuario]

-- =====================================================
-- Tabla: specials_deleted
-- =====================================================

DROP TABLE IF EXISTS `specials_deleted`;

CREATE TABLE `specials_deleted` (
  `ID_Special` int NOT NULL AUTO_INCREMENT,
  `FechaHora` datetime NOT NULL,
  `ID_Sitio` int DEFAULT NULL,
  `Nombre_Actividad` varchar(45) DEFAULT NULL,
  `Cantidad` varchar(45) NOT NULL,
  `Camera` varchar(45) NOT NULL,
  `Descripcion` varchar(255) NOT NULL,
  `Usuario` varchar(45) DEFAULT NULL,
  `Time_Zone` varchar(45) NOT NULL,
  `Supervisor` varchar(45) NOT NULL,
  `deleted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deletion_reason` text,
  PRIMARY KEY (`ID_Special`),
  UNIQUE KEY `ID_Special` (`ID_Special`),
  KEY `Sitio_idx` (`ID_Sitio`),
  KEY `Actividad_idx` (`Nombre_Actividad`),
  KEY `Time_zone_idx` (`Time_Zone`),
  KEY `supervisor_idx` (`Supervisor`) /*!80000 INVISIBLE */,
  KEY `usuario_idx` (`Usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de specials_deleted:
--   ID_Special: int [PRIMARY KEY] NOT NULL auto_increment
--   FechaHora: datetime NOT NULL
--   ID_Sitio: int [INDEX]
--   Nombre_Actividad: varchar(45) [INDEX]
--   Cantidad: varchar(45) NOT NULL
--   Camera: varchar(45) NOT NULL
--   Descripcion: varchar(255) NOT NULL
--   Usuario: varchar(45) [INDEX]
--   Time_Zone: varchar(45) [INDEX] NOT NULL
--   Supervisor: varchar(45) [INDEX] NOT NULL
--   deleted_at: timestamp DEFAULT CURRENT_TIMESTAMP DEFAULT_GENERATED
--   deleted_by: varchar(100)
--   deletion_reason: text

-- =====================================================
-- Tabla: specials_duplicates_backup
-- =====================================================

DROP TABLE IF EXISTS `specials_duplicates_backup`;

CREATE TABLE `specials_duplicates_backup` (
  `ID_Special` int NOT NULL AUTO_INCREMENT,
  `FechaHora` datetime NOT NULL,
  `ID_Sitio` int DEFAULT NULL,
  `Nombre_Actividad` varchar(45) DEFAULT NULL,
  `Cantidad` varchar(45) NOT NULL,
  `Camera` varchar(45) NOT NULL,
  `Descripcion` varchar(255) NOT NULL,
  `Usuario` varchar(45) DEFAULT NULL,
  `Time_Zone` varchar(45) NOT NULL,
  `Supervisor` varchar(45) DEFAULT NULL,
  `marked_status` varchar(20) DEFAULT NULL COMMENT 'Estado de marca: flagged, last o NULL',
  `marked_at` timestamp NULL DEFAULT NULL COMMENT 'Fecha/hora de marcado',
  `marked_by` varchar(100) DEFAULT NULL COMMENT 'Usuario que marcó el registro',
  `deleted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `deleted_reason` varchar(255) DEFAULT 'Duplicate removal',
  PRIMARY KEY (`ID_Special`),
  UNIQUE KEY `ID_Special` (`ID_Special`),
  KEY `Sitio_idx` (`ID_Sitio`),
  KEY `Actividad_idx` (`Nombre_Actividad`),
  KEY `Time_zone_idx` (`Time_Zone`),
  KEY `supervisor_idx` (`Supervisor`) /*!80000 INVISIBLE */,
  KEY `usuario_idx` (`Usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=9250 DEFAULT CHARSET=utf8mb3;

-- Columnas de specials_duplicates_backup:
--   ID_Special: int [PRIMARY KEY] NOT NULL auto_increment
--   FechaHora: datetime NOT NULL
--   ID_Sitio: int [INDEX]
--   Nombre_Actividad: varchar(45) [INDEX]
--   Cantidad: varchar(45) NOT NULL
--   Camera: varchar(45) NOT NULL
--   Descripcion: varchar(255) NOT NULL
--   Usuario: varchar(45) [INDEX]
--   Time_Zone: varchar(45) [INDEX] NOT NULL
--   Supervisor: varchar(45) [INDEX]
--   marked_status: varchar(20) -- Estado de marca: flagged, last o NULL
--   marked_at: timestamp -- Fecha/hora de marcado
--   marked_by: varchar(100) -- Usuario que marcó el registro
--   deleted_at: datetime DEFAULT CURRENT_TIMESTAMP DEFAULT_GENERATED
--   deleted_reason: varchar(255) DEFAULT Duplicate removal

-- =====================================================
-- Tabla: stations
-- =====================================================

DROP TABLE IF EXISTS `stations`;

CREATE TABLE `stations` (
  `ID_Stations` int NOT NULL,
  PRIMARY KEY (`ID_Stations`),
  UNIQUE KEY `idStations_UNIQUE` (`ID_Stations`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de stations:
--   ID_Stations: int [PRIMARY KEY] NOT NULL

-- =====================================================
-- Tabla: supervisor_status
-- =====================================================

DROP TABLE IF EXISTS `supervisor_status`;

CREATE TABLE `supervisor_status` (
  `ID_supervisor` varchar(45) NOT NULL,
  `Nombre_supervisor` varchar(45) DEFAULT NULL,
  `Status` tinyint NOT NULL,
  PRIMARY KEY (`ID_supervisor`),
  UNIQUE KEY `Nombre_supervisor_UNIQUE` (`Nombre_supervisor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Columnas de supervisor_status:
--   ID_supervisor: varchar(45) [PRIMARY KEY] NOT NULL
--   Nombre_supervisor: varchar(45) [UNIQUE]
--   Status: tinyint NOT NULL

-- =====================================================
-- Tabla: time_zone_id
-- =====================================================

DROP TABLE IF EXISTS `time_zone_id`;

CREATE TABLE `time_zone_id` (
  `id_time_zone` int NOT NULL AUTO_INCREMENT,
  `time_zone` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id_time_zone`),
  UNIQUE KEY `time_zone_UNIQUE` (`time_zone`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;

-- Columnas de time_zone_id:
--   id_time_zone: int [PRIMARY KEY] NOT NULL auto_increment
--   time_zone: varchar(45) [UNIQUE]

-- =====================================================
-- Tabla: user
-- =====================================================

DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `ID_Usuario` int NOT NULL AUTO_INCREMENT,
  `Nombre_Usuario` varchar(45) NOT NULL,
  `Rol` varchar(45) NOT NULL,
  `Contraseña` varchar(255) NOT NULL,
  PRIMARY KEY (`ID_Usuario`),
  UNIQUE KEY `Nombre_Usuario_UNIQUE` (`Nombre_Usuario`),
  KEY `roles_idx` (`Rol`)
) ENGINE=InnoDB AUTO_INCREMENT=111 DEFAULT CHARSET=utf8mb3;

-- Columnas de user:
--   ID_Usuario: int [PRIMARY KEY] NOT NULL auto_increment
--   Nombre_Usuario: varchar(45) [UNIQUE] NOT NULL
--   Rol: varchar(45) [INDEX] NOT NULL
--   Contraseña: varchar(255) NOT NULL

-- Rehabilitar verificación de foreign keys
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- EXPORTACIÓN COMPLETADA: 26 tablas
-- Archivo generado: 2025-12-14 02:15:51
-- =====================================================
