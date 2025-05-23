from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

# Esquema para Disponibilidad
class DisponibilidadBase(BaseModel):
    docente_id: UUID4 | None = None
    periodo_id: UUID4 | None = None
    dia: str
    hora_inicio: str
    hora_fin: str

class DisponibilidadCreate(DisponibilidadBase):
    pass

class DisponibilidadUpdate(BaseModel):
    docente_id: UUID4 | None = None
    periodo_id: UUID4 | None = None
    dia: str | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None

class DisponibilidadOut(DisponibilidadBase):
    id: UUID4
    docente_id: UUID4
    periodo_id: UUID4

    class Config:
        from_attributes = True

# esquema para docentes
class DocenteBase(BaseModel):
    cc: str
    nombres: str
    apellidos: str
    email: str
    telefono: Optional[str] = None


class DocenteCreate(DocenteBase):
    pass

class DocenteUpdate(BaseModel):
    cc: str | None = None
    nombres: str | None = None
    apellidos: str | None = None
    email: str | None = None
    telefono: str | None = None

class DocenteOut(DocenteBase):
    id: UUID4
    disponibilidad: List[DisponibilidadOut] = []

    class Config:
        from_attributes = True

# Esquema para Periodos
class PeriodoBase(BaseModel):
    nombre: str

class PeriodoCreate(PeriodoBase):
    pass

class PeriodoUpdate(BaseModel):
    nombre: str | None = None

class PeriodoOut(PeriodoBase):
    id: UUID4
    class Config:
        from_attributes = True

# esquema para horarios
class HorarioBase(BaseModel):
    docente_id: UUID4
    asignatura_id: UUID4
    periodo_id: UUID4
    dia: str
    hora_inicio: str
    hora_fin: str

class HorarioCreate(HorarioBase):
    pass

class HorarioUpdate(BaseModel):
    docente_id: UUID4 | None = None
    asignatura_id: UUID4 | None = None
    periodo_id: UUID4 | None = None
    dia: str | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    
class HorarioOut(HorarioBase):
    id: UUID4
    class Config:
        from_attributes = True
        
# esquema para asignaturas
class AsignaturaBase(BaseModel):
    codigo: str
    nombre: str
    intensidad: Optional[str] = None
    grupo: Optional[str] = None
    cohorte: Optional[str] = None
    aula: Optional[str] = None
    jornada: Optional[str] = None
    cant_estudiantes: Optional[int] = None
    semestre: Optional[str] = None
    plan: Optional[str] = None
    programa_id: UUID4 | None = None

class AsignaturaCreate(AsignaturaBase):
    docentes: List[UUID4] = []

class AsignaturaUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    intensidad: str | None = None
    grupo: str | None = None
    cohorte: str | None = None
    aula: str | None = None
    jornada: str | None = None
    cant_estudiantes: int | None = None
    semestre: str | None = None
    plan: str | None = None
    programa_id: UUID4 | None = None
    

class AsignaturaOut(AsignaturaBase):
    id: UUID4
    docentes: List[DocenteOut] = []  # 👈 Se agrega esta línea
    class Config:
        from_attributes = True
        
# Esquema base para Sede
class SedeBase(BaseModel):
    nombre: str

class SedeCreate(SedeBase):
    pass

class SedeUpdate(BaseModel):
    nombre: str | None = None

class SedeOut(SedeBase):
    id: UUID4
    programas: List["ProgramaOut"] = []

    class Config:
        from_attributes = True

# Esquema base para Programa
class ProgramaBase(BaseModel):
    codigo: str
    nombre: str

class ProgramaCreate(ProgramaBase):
    pass

class ProgramaUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None

class ProgramaOut(ProgramaBase):
    id: UUID4
    sedes: List[SedeOut] = []

    class Config:
        from_attributes = True

SedeOut.model_rebuild() # resolver referencia circular
ProgramaOut.model_rebuild()
