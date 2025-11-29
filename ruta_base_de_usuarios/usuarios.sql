-- 3️⃣ Crear tabla de usuarios con referencia a roles
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    rol_id INT,
    contraseña VARCHAR(255) NOT NULL,
    FOREIGN KEY (rol_id) REFERENCES roles(id)
);

-- 4️⃣ Insertar roles preestablecidos
INSERT INTO roles (nombre) VALUES
('admin'),
('supervisor'),
('operador');

-- 5️⃣ Insertar usuarios de ejemplo
INSERT INTO usuarios (nombre, rol_id, contraseña)
VALUES ('Henry', 2, '1234');  -- 2 = supervisor

-- ✅ Verificar datos
SELECT * FROM roles;
SELECT * FROM usuarios;





