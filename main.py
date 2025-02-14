from fastapi import FastAPI, Depends, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session
import uvicorn

from database import SessionLocal, engine, Base
from models import Docente, Horario, Asignatura
from schemas import DocenteCreate, DocenteUpdate, DocenteOut, HorarioCreate, HorarioUpdate, HorarioOut, AsignaturaCreate, AsignaturaUpdate, AsignaturaOut
from fastapi.middleware.cors import CORSMiddleware

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
        cant_estudiantes=asignatura.cant_estudiantes,
        semestre=asignatura.semestre,
        plan=asignatura.plan,
    )
    db.add(db_asignatura)
    db.commit()
    db.refresh(db_asignatura)
    return db

# listar asignaturas
@app.get("/asignaturas/", response_model=list[AsignaturaOut], tags=["asignaturas"])
def read_asignaturas(db: Session = Depends(get_db)):
    asignaturas = db.query(Asignatura).all()
    return asignaturas

# obtener asignatura por ID
@app.get("/asignaturas/{asignatura_id}", response_model=AsignaturaOut, tags=["asignaturas"])
def read_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    return asignatura

# actualizar asignatura
@app.put("/asignaturas/{asignatura_id}", response_model=AsignaturaOut, tags=["asignaturas"])
def update_asignatura(asignatura_id: int, asignatura: AsignaturaUpdate, db: Session = Depends(get_db)):
    db_asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not db_asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")

    if asignatura.codigo is not None:
        db_asignatura.codigo = asignatura.codigo
    if asignatura.nombre is not None:
        db_asignatura.nombre = asignatura.nombre
    if asignatura.intensidad is not None:
        db_asignatura.intensidad = asignatura.intensidad
    if asignatura.grupo is not None:
        db_asignatura.grupo = asignatura.grupo
    if asignatura.cohorte is not None:
        db_asignatura.cohorte = asignatura.cohorte
    if asignatura.aula is not None:
        db_asignatura.aula = asignatura.aula
    if asignatura.cant_estudiantes is not None:
        db_asignatura.cant_estudiantes = asignatura.cant_estudiantes
    if asignatura.semestre is not None:
        db_asignatura.semestre = asignatura.semestre
    if asignatura.plan is not None:
        db_asignatura.plan = asignatura.plan

    db.commit()
    db.refresh(db_asignatura)
    return db_asignatura



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
