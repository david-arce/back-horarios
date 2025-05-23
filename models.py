from sqlalchemy import Column, ForeignKey, Integer, String, Table
from database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Disponibilidad(Base):
    __tablename__ = "disponibilidad"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    docente_id = Column(UUID(as_uuid=True), ForeignKey("docentes.id"), nullable=False)
    periodo_id = Column(UUID(as_uuid=True), ForeignKey("periodos.id"), nullable=False)
    dia = Column(String, nullable=False)
    hora_inicio = Column(String, nullable=False)
    hora_fin = Column(String, nullable=False)

    docente = relationship("Docente", back_populates="disponibilidad")
    periodo = relationship("Periodo", back_populates="disponibilidad")

# 1. Crear la tabla de asociación (intermedia) entre Docente y Asignatura
docentes_asignaturas = Table(
    "docentes_asignaturas",
    Base.metadata,
    Column("docente_id", UUID(as_uuid=True), ForeignKey("docentes.id"), primary_key=True),
    Column("asignatura_id", UUID(as_uuid=True), ForeignKey("asignaturas.id"), primary_key=True),
)

# Modelo Docentes
class Docente(Base):
    __tablename__ = "docentes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    cc = Column(String, unique=True, nullable=False)
    nombres = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    email = Column(String, nullable=False)
    telefono = Column(String, nullable=True)

    disponibilidad = relationship("Disponibilidad", back_populates="docente")
    horarios = relationship("Horario", back_populates="docente")
    asignaturas = relationship("Asignatura", secondary=docentes_asignaturas, back_populates="docentes")

# Modelo Periodos
class Periodo(Base):
    __tablename__ = "periodos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, nullable=False)

    disponibilidad = relationship("Disponibilidad", back_populates="periodo")
    horarios = relationship("Horario", back_populates="periodo")

# Modelo Horarios
class Horario(Base):
    __tablename__ = "horarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    docente_id = Column(UUID(as_uuid=True), ForeignKey("docentes.id"))
    asignatura_id = Column(UUID(as_uuid=True), ForeignKey("asignaturas.id"))
    periodo_id = Column(UUID(as_uuid=True), ForeignKey("periodos.id"))
    dia = Column(String)
    hora_inicio = Column(String)
    hora_fin = Column(String)

    docente = relationship("Docente", back_populates="horarios")
    asignatura = relationship("Asignatura", back_populates="horarios")
    periodo = relationship("Periodo", back_populates="horarios")

# Modelo Asignaturas
class Asignatura(Base):
    __tablename__ = "asignaturas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    intensidad = Column(String)
    grupo = Column(String)
    cohorte = Column(String)
    aula = Column(String)
    jornada = Column(String)
    cant_estudiantes = Column(Integer)
    semestre = Column(String)
    plan = Column(String)
    programa_id = Column(UUID(as_uuid=True), ForeignKey("programas.id"), nullable=False)

    programa = relationship("Programa", back_populates="asignaturas")
    horarios = relationship("Horario", back_populates="asignatura")
    docentes = relationship("Docente", secondary=docentes_asignaturas, back_populates="asignaturas")


# Tabla intermedia para la relación Many-to-Many
sede_programa = Table(
    "sede_programa",
    Base.metadata,
    Column("sede_id", UUID(as_uuid=True), ForeignKey("sedes.id"), primary_key=True),
    Column("programa_id", UUID(as_uuid=True), ForeignKey("programas.id"), primary_key=True),
)

# clase para la sede
class Sede (Base):
    __tablename__ = "sedes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String)
    programas = relationship("Programa", secondary=sede_programa, back_populates="sedes")

# Modelo Programas
class Programa(Base):
    __tablename__ = "programas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    asignaturas = relationship("Asignatura", back_populates="programa")
    sedes = relationship("Sede", secondary=sede_programa, back_populates="programas")