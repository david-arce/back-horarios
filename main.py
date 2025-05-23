import json
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import UUID4
from sqlalchemy.orm import Session, joinedload
import uvicorn

from database import SessionLocal, engine, Base
from models import Docente, Horario, Asignatura, Programa, Sede, Disponibilidad, Periodo
from schemas import DocenteCreate, DocenteUpdate, DocenteOut, HorarioCreate, HorarioUpdate, HorarioOut, AsignaturaCreate, AsignaturaUpdate, AsignaturaOut, SedeCreate, SedeUpdate, SedeOut, ProgramaCreate, ProgramaUpdate, ProgramaOut, DisponibilidadCreate, DisponibilidadUpdate, DisponibilidadOut, PeriodoCreate, PeriodoOut, PeriodoUpdate
from fastapi.middleware.cors import CORSMiddleware
from modelo_horarios import ScheduleGenerator
# Crear las tablas en la base de datos (solo para desarrollo)
# En producción es mejor usar migraciones con Alembic
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ejemplo CRUD con FastAPI y PostgreSQL")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Dirección del frontend
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos HTTP
    allow_headers=["*"],  # Permitir todos los headers
)

# Dependencia para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from collections import defaultdict
@app.post("/generar-horarios", tags=["generador"])
def generar_horarios(db: Session = Depends(get_db)):
    
    disponibilidades = db.query(Disponibilidad).all()
    docentes = db.query(Docente).all()
    asignaturas = db.query(Asignatura).options(joinedload(Asignatura.docentes)).all()

    # Crear un diccionario para mapear UUID a nombres
    docente_map = {str(docente.id): f"{docente.apellidos.upper()} {docente.nombres.upper()}" for docente in docentes}

    # Crear la estructura de horarios
    horarios_por_docente = defaultdict(lambda: defaultdict(list))

    for d in disponibilidades:
        docentes_str = str(d.docente)
        dia = d.dia.capitalize()  # Asegurar que los días estén con mayúscula inicial
        hora_inicio = d.hora_inicio
        hora_fin = d.hora_fin

        bloque = f"{hora_inicio}-{hora_fin}"
        nombre_docente = docente_map.get(docentes_str, f"Desconocido ({docentes_str})")

        horarios_por_docente[nombre_docente][dia].append(bloque)
    disponibilidad_estructurada = {
        nombre: dict(dias)
        for nombre, dias in horarios_por_docente.items()
    }
    # === Asignaturas estructuradas ===
    asignaturas_estructuradas = {}
    for a in asignaturas:
        nombre = a.nombre.strip().capitalize()

        if a.docentes:
            nombres_docentes = [
                f"{docente.apellidos.upper()} {docente.nombres.upper()}"
                for docente in a.docentes
            ]
            nombre_docente = ", ".join(nombres_docentes)
        else:
            nombre_docente = "SIN DOCENTE"

        try:
            intensidad_valor = int(a.intensidad)
        except:
            intensidad_valor = a.intensidad

        asignaturas_estructuradas[nombre] = {
            "teacher": nombre_docente,
            "intensity": intensidad_valor
        }
    print("Asignaturas estructuradas:", asignaturas_estructuradas)
    print("Disponibilidad estructurada:", disponibilidad_estructurada)
    for a in asignaturas:
        print(f"Asignatura: {a.nombre}")
        print(f"Docente ID directo: {a.docentes}")
        print(f"Docentes relacionados: {[f'{d.nombres} {d.apellidos}' for d in a.docentes]}")

    # Generar horarios
    schedule_generator = ScheduleGenerator(disponibilidad_estructurada, asignaturas_estructuradas)
    schedule_generator.generate_schedule()
    # Obtener el horario generado como JSON
    schedule_json = schedule_generator.get_schedule_json()
  
    return {"horario": schedule_json}


# Crear un docente
@app.post("/docentes/", response_model=DocenteOut, tags=["docentes"])
def create_docente(docente: DocenteCreate, db: Session = Depends(get_db)):
    db_docente = Docente(
        **docente.model_dump()
    )
    db.add(db_docente)
    db.commit()
    db.refresh(db_docente)
    return db_docente

# Listar todos los docentes
@app.get("/docentes/", response_model=list[DocenteOut], tags=["docentes"])
def read_docentes(db: Session = Depends(get_db)):
    docentes = db.query(Docente).all()
    return docentes

# Obtener un docente por ID
@app.get("/docentes/{docente_id}", response_model=DocenteOut, tags=["docentes"])
def read_docente(docente_id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id == docente_id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return docente

# Actualizar un docente
@app.put("/docentes/{docente_id}", response_model=DocenteOut, tags=["docentes"])
def update_docente(docente_id: UUID4, docente: DocenteUpdate, db: Session = Depends(get_db)):
    db_docente = db.query(Docente).filter(Docente.id == docente_id).first()
    if not db_docente:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    if docente.cc is not None:
        db_docente.cc = docente.cc
    if docente.nombres is not None:
        db_docente.nombres = docente.nombres
    if docente.apellidos is not None:
        db_docente.apellidos = docente.apellidos
    if docente.email is not None:
        db_docente.email = docente.email
    if docente.telefono is not None:
        db_docente.telefono = docente.telefono

    db.commit()
    db.refresh(db_docente)
    return db_docente

# Eliminar un docente
@app.delete("/docentes/{docente_id}", tags=["docentes"])
def delete_docente(docente_id: UUID4, db: Session = Depends(get_db)):
    db_docente = db.query(Docente).filter(Docente.id == docente_id).first()
    if not db_docente:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    db.delete(db_docente)
    db.commit()
    return {"ok": True}


# crear horario
@app.post("/horarios/", response_model=HorarioOut, tags=["horarios"])
def create_horario(horario: HorarioCreate, db: Session = Depends(get_db)):
    db_horario = Horario(
        docente_id=horario.docente_id,
        dia=horario.dia,
        hora_inicio=horario.hora_inicio,
        hora_fin=horario.hora_fin
    )
    db.add(db_horario)
    db.commit()
    db.refresh(db_horario)
    return db_horario

# listar horarios
@app.get("/horarios/", response_model=list[HorarioOut], tags=["horarios"])
def read_horarios(db: Session = Depends(get_db)):
    horarios = db.query(Horario).all()
    return horarios

# obtener horario por ID
@app.get("/horarios/{horario_id}", response_model=HorarioOut, tags=["horarios"])
def read_horario(horario_id: int, db: Session = Depends(get_db)):
    horario = db.query(Horario).filter(Horario.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    return horario

# actualizar horario
@app.put("/horarios/{horario_id}", response_model=HorarioOut, tags=["horarios"])
def update_horario(horario_id: int, horario: HorarioUpdate, db: Session = Depends(get_db)):
    db_horario = db.query(Horario).filter(Horario.id == horario_id).first()
    if not db_horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    if horario.dia is not None:
        db_horario.dia = horario.dia
    if horario.hora_inicio is not None:
        db_horario.hora_inicio = horario.hora_inicio
    if horario.hora_fin is not None:
        db_horario.hora_fin = horario.hora_fin

    db.commit()
    db.refresh(db_horario)
    return db_horario

# eliminar horario
@app.delete("/horarios/{horario_id}", tags=["horarios"])
def delete_horario(horario_id: int, db: Session = Depends(get_db)):
    db_horario = db.query(Horario).filter(Horario.id == horario_id).first()
    if not db_horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    db.delete(db_horario)
    db.commit()
    return {"ok": True}

# crear asignatura
@app.post("/asignaturas/", response_model=AsignaturaOut, tags=["asignaturas"])
def create_asignatura(asignatura: AsignaturaCreate, db: Session = Depends(get_db)):
    
    db_asignatura = Asignatura(
        codigo=asignatura.codigo,
        nombre=asignatura.nombre,
        intensidad=asignatura.intensidad,
        grupo=asignatura.grupo,
        cohorte=asignatura.cohorte,
        aula=asignatura.aula,
        jornada=asignatura.jornada,
        cant_estudiantes=asignatura.cant_estudiantes,
        semestre=asignatura.semestre,
        plan=asignatura.plan,
        programa_id=asignatura.programa_id
    )

    # Agregar docentes a la tabla intermedia
    if asignatura.docentes:
        docentes_encontrados = db.query(Docente).filter(Docente.id.in_(asignatura.docentes)).all()
        db_asignatura.docentes = docentes_encontrados

    db.add(db_asignatura)
    db.commit()
    db.refresh(db_asignatura)
    
    return db_asignatura

# listar asignaturas
@app.get("/asignaturas/", response_model=list[AsignaturaOut], tags=["asignaturas"])
def read_asignaturas(db: Session = Depends(get_db)):
    asignaturas = db.query(Asignatura).all()
    return asignaturas

# obtener asignatura por ID
@app.get("/asignaturas/{asignatura_id}", response_model=AsignaturaOut, tags=["asignaturas"])
def read_asignatura(asignatura_id: UUID4, db: Session = Depends(get_db)):
    asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    return asignatura

# actualizar asignatura
@app.put("/asignaturas/{asignatura_id}", response_model=AsignaturaOut, tags=["asignaturas"])
def update_asignatura(
    asignatura_id: UUID4,
    asignatura: AsignaturaUpdate,
    db: Session = Depends(get_db)
):
    db_asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not db_asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")

    # Actualiza campos simples si están presentes
    for field, value in asignatura.model_dump(exclude_unset=True).items():
        if field != "docentes":
            setattr(db_asignatura, field, value)

    # 👇 Si se especifica la lista de docentes, actualiza la relación muchos-a-muchos
    if asignatura.docentes is not None:
        docentes = db.query(Docente).filter(Docente.id.in_(asignatura.docentes)).all()
        db_asignatura.docentes = docentes

    db.commit()
    db.refresh(db_asignatura)

    return db_asignatura


# eliminar asignatura
@app.delete("/asignaturas/{asignatura_id}", tags=["asignaturas"])
def delete_asignatura(asignatura_id: UUID4, db: Session = Depends(get_db)):
    db_asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not db_asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    db.delete(db_asignatura)
    db.commit()
    return {"ok": True}


# crear sede
@app.post("/sedes/", response_model=SedeOut, tags=["sedes"])
def create_sede(sede: SedeCreate, db: Session = Depends(get_db)):
    db_sede = Sede(
        **sede.model_dump()
    )
    db.add(db_sede)
    db.commit()
    db.refresh(db_sede)
    return db_sede

# listar todas las sedes
@app.get("/sedes/", response_model=list[SedeOut], tags=["sedes"])
def read_sedes(db: Session = Depends(get_db)):
    sedes = db.query(Sede).all()
    return sedes

# obtener sede por ID
@app.get("/sedes/{sede_id}", response_model=SedeOut, tags=["sedes"])
def read_sede(sede_id: int, db: Session = Depends(get_db)):
    sede = db.query(Sede).filter(Sede.id == sede_id).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    return sede

# actualizar sede
@app.put("/sedes/{sede_id}", response_model=SedeOut, tags=["sedes"])
def update_sede(sede_id: UUID4, sede: SedeUpdate, db: Session = Depends(get_db)):
    db_sede = db.query(Sede).filter(Sede.id == sede_id).first()
    if not db_sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    if sede.nombre is not None:
        db_sede.nombre = sede.nombre

    db.commit()
    db.refresh(db_sede)
    return db_sede

# eliminar sede
@app.delete("/sedes/{sede_id}", tags=["sedes"])
def delete_sede(sede_id: UUID4, db: Session = Depends(get_db)):
    db_sede = db.query(Sede).filter(Sede.id == sede_id).first()
    if not db_sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    db.delete(db_sede)
    db.commit()
    return {"ok": True}

# crear programa
@app.post("/programas/", response_model=ProgramaOut, tags=["programas"])
def create_programa(programa: ProgramaCreate, db: Session = Depends(get_db)):
    db_programa = Programa(
        **programa.model_dump()
    )
    db.add(db_programa)
    db.commit()
    db.refresh(db_programa)
    return db_programa

# listar programas
@app.get("/programas/", response_model=list[ProgramaOut], tags=["programas"])
def read_programas(db: Session = Depends(get_db)):
    programas = db.query(Programa).all()
    return programas

# obtener programa por ID
@app.get("/programas/{programa_id}", response_model=ProgramaOut, tags=["programas"])
def read_programa(programa_id: UUID4, db: Session = Depends(get_db)):
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    return programa

# actualizar programa
@app.put("/programas/{programa_id}", response_model=ProgramaOut, tags=["programas"])
def update_programa(programa_id: UUID4, programa: ProgramaUpdate, db: Session = Depends(get_db)):
    db_programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not db_programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")

    if programa.codigo is not None:
        db_programa.codigo = programa.codigo
    if programa.nombre is not None:
        db_programa.nombre = programa.nombre

    db.commit()
    db.refresh(db_programa)
    return db_programa

# eliminar programa
@app.delete("/programas/{programa_id}", tags=["programas"])
def delete_programa(programa_id: UUID4, db: Session = Depends(get_db)):
    db_programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not db_programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")

    db.delete(db_programa)
    db.commit()
    return {"ok": True}

# crear disponibilidad
@app.post("/disponibilidades/", response_model=DisponibilidadOut, tags=["disponibilidades"])
def create_disponibilidad(disponibilidad: DisponibilidadCreate, db: Session = Depends(get_db)):
    db_disponibilidad = Disponibilidad(
        **disponibilidad.model_dump()
    )
    db.add(db_disponibilidad)
    db.commit()
    db.refresh(db_disponibilidad)
    return db_disponibilidad

# listar disponibilidades
@app.get("/disponibilidades/", response_model=list[DisponibilidadOut], tags=["disponibilidades"])
def read_disponibilidades(db: Session = Depends(get_db)):
    disponibilidades = db.query(Disponibilidad).all()
    return disponibilidades

# obtener disponibilidad por ID
@app.get("/disponibilidades/{disponibilidad_id}", response_model=DisponibilidadOut, tags=["disponibilidades"])
def read_disponibilidad(disponibilidad_id: UUID4, db: Session = Depends(get_db)):
    disponibilidad = db.query(Disponibilidad).filter(Disponibilidad.id == disponibilidad_id).first()
    if not disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
    return disponibilidad

# actualizar disponibilidad
@app.put("/disponibilidades/{disponibilidad_id}", response_model=DisponibilidadOut, tags=["disponibilidades"])
def update_disponibilidad(disponibilidad_id: UUID4, disponibilidad: DisponibilidadUpdate, db: Session = Depends(get_db)):
    db_disponibilidad = db.query(Disponibilidad).filter(Disponibilidad.id == disponibilidad_id).first()
    if not db_disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    if disponibilidad.docente_id is not None:
        db_disponibilidad.docente_id = disponibilidad.docente_id
    if disponibilidad.periodo_id is not None:
        db_disponibilidad.periodo_id = disponibilidad.periodo_id
    if disponibilidad.dia is not None:
        db_disponibilidad.dia = disponibilidad.dia
    if disponibilidad.hora_inicio is not None:
        db_disponibilidad.hora_inicio = disponibilidad.hora_inicio
    if disponibilidad.hora_fin is not None:
        db_disponibilidad.hora_fin = disponibilidad.hora_fin

    db.commit()
    db.refresh(db_disponibilidad)
    return db_disponibilidad

# eliminar disponibilidad
@app.delete("/disponibilidades/{disponibilidad_id}", tags=["disponibilidades"])
def delete_disponibilidad(disponibilidad_id: UUID4, db: Session = Depends(get_db)):
    db_disponibilidad = db.query(Disponibilidad).filter(Disponibilidad.id == disponibilidad_id).first()
    if not db_disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    db.delete(db_disponibilidad)
    db.commit()
    return {"ok": True}

# crear periodo 
@app.post("/periodos/", response_model=PeriodoOut, tags=["periodos"])
def create_periodo(periodo: PeriodoCreate, db: Session = Depends(get_db)):
    db_periodo = Periodo(
        **periodo.model_dump()
    )
    db.add(db_periodo)
    db.commit()
    db.refresh(db_periodo)
    return db_periodo

# listar periodos
@app.get("/periodos/", response_model=list[PeriodoOut], tags=["periodos"])
def read_periodos(db: Session = Depends(get_db)):
    periodos = db.query(Periodo).all()
    return periodos

# obtener periodo por ID
@app.get("/periodos/{periodo_id}", response_model=PeriodoOut, tags=["periodos"])
def read_periodo(periodo_id: UUID4, db: Session = Depends(get_db)):
    periodo = db.query(Periodo).filter(Periodo.id == periodo_id).first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")
    return periodo

# actualizar periodo
@app.put("/periodos/{periodo_id}", response_model=PeriodoOut, tags=["periodos"])
def update_periodo(periodo_id: UUID4, periodo: PeriodoUpdate, db: Session = Depends(get_db)):
    db_periodo = db.query(Periodo).filter(Periodo.id == periodo_id).first()
    if not db_periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    if periodo.nombre is not None:
        db_periodo.nombre = periodo.nombre

    db.commit()
    db.refresh(db_periodo)
    return db_periodo

# eliminar periodo
@app.delete("/periodos/{periodo_id}", tags=["periodos"])
def delete_periodo(periodo_id: UUID4, db: Session = Depends(get_db)):
    db_periodo = db.query(Periodo).filter(Periodo.id == periodo_id).first()
    if not db_periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    db.delete(db_periodo)
    db.commit()
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
