import {
  date,
  integer,
  numeric,
  pgTable,
  serial,
  text,
  timestamp,
} from "drizzle-orm/pg-core";

export const nadadores = pgTable("nadadores", {
  codnadador: serial("codnadador").primaryKey(),
  nrosocio: text("nrosocio").notNull().unique(),
  nombre: text("nombre").notNull(),
  apellido: text("apellido").notNull(),
  codgenero: text("codgenero").notNull().default("M"),
  fechaNacimiento: date("fecha_nacimiento"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const usuarios = pgTable("usuarios", {
  id: serial("id").primaryKey(),
  nrosocio: text("nrosocio").notNull().unique(),
  perfil: text("perfil").notNull().default("N"), // N | M | P
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const estilos = pgTable("estilos", {
  codestilo: serial("codestilo").primaryKey(),
  descripcion: text("descripcion").notNull(),
});

export const distancias = pgTable("distancias", {
  coddistancia: serial("coddistancia").primaryKey(),
  descripcion: text("descripcion").notNull(),
  metros: integer("metros"),
});

export const piletas = pgTable("piletas", {
  codpileta: serial("codpileta").primaryKey(),
  nombre: text("nombre").notNull(),
  ubicacion: text("ubicacion"),
});

export const categorias = pgTable("categorias", {
  codcategoria: serial("codcategoria").primaryKey(),
  descripcion: text("descripcion").notNull(),
  edadMin: integer("edad_min"),
  edadMax: integer("edad_max"),
  codgenero: text("codgenero"),
});

export const categoriasRelevos = pgTable("categorias_relevos", {
  codcategoria: serial("codcategoria").primaryKey(),
  descripcion: text("descripcion").notNull(),
  edadMin: integer("edad_min"),
  edadMax: integer("edad_max"),
});

export const competencias = pgTable("competencias", {
  idCompetencia: text("id_competencia").primaryKey(),
  nombre: text("nombre").notNull(),
  fecha: date("fecha").notNull(),
  horaInicio: text("hora_inicio"),
  codpileta: text("codpileta"),
  costo: numeric("costo"),
  descripcion: text("descripcion"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const inscripciones = pgTable("inscripciones", {
  idInscripcion: text("id_inscripcion").primaryKey(),
  idCompetencia: text("id_competencia").notNull(),
  codnadador: integer("codnadador").notNull(),
  pruebas: text("pruebas"),
  fechaInscripcion: date("fecha_inscripcion").defaultNow(),
});

export const tiempos = pgTable("tiempos", {
  id: serial("id").primaryKey(),
  codnadador: integer("codnadador").notNull(),
  codestilo: integer("codestilo"),
  coddistancia: integer("coddistancia"),
  codpileta: text("codpileta"),
  tiempoRegistrado: text("tiempo_registrado").notNull(),
  posicion: integer("posicion"),
  fecha: date("fecha").defaultNow(),
  idCompetencia: text("id_competencia"),
  competencia: text("competencia"),
});

export const relevos = pgTable("relevos", {
  id: serial("id").primaryKey(),
  nadador1: integer("nadador_1"),
  nadador2: integer("nadador_2"),
  nadador3: integer("nadador_3"),
  nadador4: integer("nadador_4"),
  codestilo: integer("codestilo"),
  coddistancia: integer("coddistancia"),
  codcategoria: integer("codcategoria"),
  posicion: integer("posicion"),
  tiempoRegistrado: text("tiempo_registrado").notNull(),
  fecha: date("fecha").defaultNow(),
  idCompetencia: text("id_competencia"),
  competencia: text("competencia"),
});

export const entrenamientos = pgTable("entrenamientos", {
  id: serial("id").primaryKey(),
  codnadador: integer("codnadador").notNull(),
  fecha: date("fecha").defaultNow(),
  codestilo: integer("codestilo"),
  coddistancia: integer("coddistancia"),
  series: integer("series"),
  tiempoPromedio: text("tiempo_promedio"),
  observaciones: text("observaciones"),
});

export const rutinas = pgTable("rutinas", {
  idRutina: serial("id_rutina").primaryKey(),
  nroSesion: integer("nro_sesion").notNull(),
  mes: integer("mes").notNull(),
  anio: integer("anio").notNull(),
  descripcion: text("descripcion"),
  contenido: text("contenido"),
});

export const rutinasSeguimiento = pgTable("rutinas_seguimiento", {
  id: serial("id").primaryKey(),
  codnadador: integer("codnadador").notNull(),
  idRutina: integer("id_rutina").notNull(),
  fechaRealizada: date("fecha_realizada").defaultNow(),
});
