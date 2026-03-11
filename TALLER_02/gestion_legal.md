classDiagram
direction BT
class aseguradora {
   varchar(100) nombre
   varchar(20) telefono
   varchar(100) email
   varchar(200) direccion
   tinyint(1) activa
   datetime created_at
   datetime updated_at
   int(11) id
}
class audiencia {
   int(11) expediente_id
   date fecha
   time hora
   varchar(200) lugar
   tipo  /* Tipo de audiencia (inicial, final, etc.) */ varchar(100)
   text observaciones
   enum('programada', 'realizada', 'cancelada', 'reprogramada') estado
   datetime created_at
   datetime updated_at
   int(11) id
}
class expediente {
   varchar(50) numero  /* Número de expediente judicial */
   varchar(150) cliente_nombre
   varchar(30) cliente_cedula
   text descripcion
   enum('pendiente', 'en_curso', 'cerrado') estado
   int(11) aseguradora_id
   int(11) juzgado_id
   int(11) abogado_id
   date fecha_inicio
   date fecha_cierre
   datetime created_at
   datetime updated_at
   int(11) id
}
class juzgado {
   varchar(150) nombre
   varchar(200) ubicacion
   varchar(20) telefono
   tinyint(1) activo
   datetime created_at
   datetime updated_at
   int(11) id
}
class usuario {
   varchar(150) nombre_completo
   varchar(50) username
   varchar(255) password_hash
   varchar(100) email
   enum('admin', 'abogado', 'asistente') rol
   tinyint(1) activo
   datetime created_at
   datetime updated_at
   int(11) id
}

audiencia  -->  expediente : expediente_id:id
expediente  -->  aseguradora : aseguradora_id:id
expediente  -->  juzgado : juzgado_id:id
expediente  -->  usuario : abogado_id:id
