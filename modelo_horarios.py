from ortools.sat.python import cp_model
import json
import pandas as pd

class ScheduleGenerator:
    """
    Genera un horario factible asignando:
      • día-bloque   (30 min)  para cada curso
      • aula         compatible (tipo y capacidad)
      • sin solapes  ni de docente ni de aula
    """

    def __init__(self, teacher_availabilities: dict, courses: dict, classrooms: dict):
        self.teacher_availabilities = teacher_availabilities
        self.courses = courses
        self.classrooms = classrooms
        self.days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        self.schedule = {}

    def parse_availability(self):
        """Convierte 'HH:MM-HH:MM' en índices de slots de 30 min (enteros)."""
        parsed = {}
        for teacher, days in self.teacher_availabilities.items():
            parsed[teacher] = {}
            for day, slots in days.items():
                slot_idxs = set()
                for slot in slots:
                    start_str, end_str = slot.split("-")
                    sh, sm = map(int, start_str.split(":"))
                    eh, em = map(int, end_str.split(":"))
                    start = sh * 60 + sm
                    end = eh * 60 + em
                    # cada 30min
                    for t in range(start, end, 30):
                        slot_idxs.add(t // 30)
                parsed[teacher][day] = sorted(slot_idxs)
        self.teacher_availabilities = parsed

    # 2. Bloques consecutivos de longitud fija
    @staticmethod
    def generate_possible_time_blocks(available_slots, block_len):
        """Bloques consecutivos de longitud block_len en unidades de 30min."""
        blocks = []
        for i in range(len(available_slots)):
            block = []
            for j in range(i, len(available_slots)):
                if not block or available_slots[j] == block[-1] + 1:
                    block.append(available_slots[j])
                    if len(block) == block_len:
                        blocks.append(block.copy())
                        break
                else:
                    break
        return blocks

    def validate_teacher_availability(self):
        """Valida que la intensidad total de los cursos asignados a cada docente no supere su disponibilidad."""
        for teacher, availability in self.teacher_availabilities.items():
            # Calcular la disponibilidad total del docente sumando las horas de todos los días de la semana
            total_available_hours = 0
            for day in self.days:
                # Si el docente tiene disponibilidad ese día, sumamos las horas
                if day in availability:
                    for slot in availability[day]:
                        start_str, end_str = slot.split("-")
                        start_hour = int(start_str.split(":")[0])
                        end_hour = int(end_str.split(":")[0])
                        total_available_hours += (
                            end_hour - start_hour
                        )  # Sumar la duración de la franja horaria

            # Calcular la intensidad total de los cursos asignados al docente
            total_assigned_hours = sum(
                course_info["intensity"]
                for course_id, course_info in self.courses.items()
                if course_info["teacher"] == teacher
            )

            # Si la intensidad total supera la disponibilidad, lanzar un error
            if total_assigned_hours > total_available_hours:
                print(
                    f"Error: El docente {teacher} tiene más horas asignadas ({total_assigned_hours}) que su disponibilidad ({total_available_hours})."
                )
                return False
        return True

    # 4. Construir y resolver el modelo CP-SAT
    def generate_schedule(self):
        if not self.validate_teacher_availability():
            return  # Si la validación falla, no generamos el horario.

        self.parse_availability()
        model = cp_model.CpModel()

        schedule_vars = {}  # (curso, día, bloque_idx) → variable booleana
        all_blocks = {}  # (curso, día) → lista de bloques posibles
        classroom_vars = (
            {}
        )  # (curso, día, bloque_idx, aula) → variable booleana para aula

        # Construcción de variables y bloques
        for course_id, info in self.courses.items():
            intensity_slots = info["intensity"] * 2
            teacher = info["teacher"]
            # Definimos tamaños de bloque en medias horas
            block_sizes = [intensity_slots] if info["intensity"] <= 4 else [6, 4]

            # aulas compatibles: tipo y capacidad
            aulas_compatibles = [
                aula_id
                for aula_id, datos in self.classrooms.items()
                if datos["type"] == info["room_type"]
                and datos["capacity"] >= info["students"]
            ]
            if not aulas_compatibles:
                raise ValueError(
                    f"No hay aulas compatibles para el curso '{course_id}'"
                )

            for day in self.days:
                avail = self.teacher_availabilities.get(teacher, {}).get(day, [])
                if not avail:
                    continue

                # Generamos todos los bloques posibles para cada tamaño
                possible = []
                for bs in block_sizes:
                    possible += self.generate_possible_time_blocks(avail, bs)
                if not possible:
                    continue

                all_blocks[(course_id, day)] = possible
                for idx, block in enumerate(possible):
                    schedule_vars[(course_id, day, idx)] = model.NewBoolVar(
                        f"{course_id}_{day}_{idx}"
                    )
                    # variable por aula
                    for aula in aulas_compatibles:
                        classroom_vars[(course_id, day, idx, aula)] = model.NewBoolVar(
                            f"{course_id}_{day}_{idx}_{aula}"
                        )

        # 2) Cada curso debe cubrir exactamente `intensity_slots` medias horas
        for course_id, info in self.courses.items():
            terms = [] # variables de horario
            for day in self.days:
                for idx, block in enumerate(all_blocks.get((course_id, day), [])):
                    terms.append(schedule_vars[(course_id, day, idx)] * len(block))
            model.Add(sum(terms) == info["intensity"] * 2)

        # 3) A lo sumo un bloque por día por curso
        for course_id in self.courses:
            for day in self.days:
                vars_day = [
                    schedule_vars[(course_id, day, idx)]
                    for idx in range(len(all_blocks.get((course_id, day), [])))
                ]
                if vars_day:
                    model.Add(sum(vars_day) <= 1)

        # 4) Cursos con intensidad ≤4 solo en un día
        for course_id, info in self.courses.items():
            if info["intensity"] <= 4:
                day_assigned = []
                for day in self.days:
                    vars_day = [
                        schedule_vars[(course_id, day, idx)]
                        for idx in range(len(all_blocks.get((course_id, day), [])))
                    ]
                    if vars_day:
                        b = model.NewBoolVar(f"{course_id}_{day}_used")
                        model.Add(sum(vars_day) >= 1).OnlyEnforceIf(b)
                        model.Add(sum(vars_day) == 0).OnlyEnforceIf(b.Not())
                        day_assigned.append(b)
                if day_assigned:
                    model.Add(sum(day_assigned) == 1)

        # 5) Ningún docente puede solapar bloques, es decir, un mismo docente no puede estar en dos bloques al mismo tiempo
        # Para cada docente, día y slot, la suma de variables que cubren ese slot ≤ 1
        for teacher in self.teacher_availabilities:
            for day in self.days:
                # construir mapa slot → vars
                slot_map = {}
                for course_id, info in self.courses.items():
                    if info["teacher"] != teacher:
                        continue
                    for idx, block in enumerate(all_blocks.get((course_id, day), [])):
                        var = schedule_vars[(course_id, day, idx)]
                        for slot in block:
                            slot_map.setdefault(slot, []).append(var)
                for slot, vars_at in slot_map.items():
                    model.Add(sum(vars_at) <= 1)

        # 6) Ejemplo de exclusión de hora de almuerzo (12:00-13:00 = slots 24 y 25)
        for (course_id, day), blocks in all_blocks.items():
            for idx, block in enumerate(blocks):
                if any(s in (24, 25) for s in block):
                    model.Add(schedule_vars[(course_id, day, idx)] == 0)

        # ---------- 4.3 Restricciones de aulas ----------------------------
        # (f) cada bloque elegido debe asignarse a exactamente un aula, es decir, Asignar una sola aula de clase para cada asignatura.
        for (course_id, day), blocks in all_blocks.items():
            for idx, _ in enumerate(blocks):
                vars_aula = [
                    classroom_vars[(course_id, day, idx, aula)]
                    for aula in self.classrooms
                    if (course_id, day, idx, aula) in classroom_vars
                ]
                if vars_aula:  # puede no existir si no había aula compatible ese día
                    model.Add(sum(vars_aula) == schedule_vars[(course_id, day, idx)])

        # (g) no solapamiento dentro de cada aula. Un mismo salón no puede albergar dos clases al mismo tiempo.
        for aula in self.classrooms:
            for day in self.days:
                slot_map = {}
                for (course_id, day2), blocks in all_blocks.items():
                    if day2 != day:
                        continue
                    for idx, block in enumerate(blocks):
                        key = (course_id, day, idx, aula)
                        if key not in classroom_vars:
                            continue
                        var = classroom_vars[key]
                        for slot in block:
                            slot_map.setdefault(slot, []).append(var)
                for vars_at in slot_map.values():
                    model.Add(sum(vars_at) <= 1)

        # ---------- R8  máximo 20 h por docente  (40 slots) ------------------
        for docente in {info["teacher"] for info in self.courses.values()}:
            expr = []
            for c_id, info in self.courses.items():
                if info["teacher"] != docente:
                    continue
                for d in self.days:
                    for idx, blk in enumerate(all_blocks.get((c_id, d), [])):
                        expr.append(len(blk) * schedule_vars[(c_id, d, idx)])
            model.Add(sum(expr) <= 40)

        # Resolver
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("No se encontró solución viable.")
            return

        # Extraer solución
        for (course_id, day), blocks in all_blocks.items():
            for idx, block in enumerate(blocks):
                if solver.Value(schedule_vars[(course_id, day, idx)]) == 1:
                    # aula asignada
                    aula_asignada = next(
                        aula for aula in self.classrooms
                        if (course_id, day, idx, aula) in classroom_vars
                        and solver.Value(classroom_vars[(course_id, day, idx, aula)]) == 1
                    )
                    start, end = block[0], block[-1] + 1
                    sh, sm = divmod(start * 30, 60)
                    eh, em = divmod(end * 30, 60)
                    timeframe = f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"
                    self.schedule.setdefault(course_id, []).append(
                        {
                            "day": day,
                            "hour": timeframe,
                            "teacher": self.courses[course_id]["teacher"],
                            "classroom": aula_asignada,
                            "semester": self.courses[course_id].get("semester")
                        }
                    )

    def get_schedule_json(self):
        """Devuelve el horario en formato JSON (diccionario)."""
        schedule_json = {}
        for course_id, slots in self.schedule.items():
            schedule_json[course_id] = []
            for slot in sorted(slots, key=lambda x: (self.days.index(x['day']), x['hour'])):
                schedule_json[course_id].append({
                    "day": slot["day"],
                    "hour": slot["hour"],
                    "teacher": slot["teacher"],
                    "classroom": slot["classroom"],
                    "semester": slot.get("semester")
                })
        return schedule_json
    
    def print_schedule(self):
        """Imprime el horario generado."""
        for course_id, slots in self.schedule.items():
            print(f"Curso: {course_id}")
            for slot in sorted(
                slots, key=lambda x: (self.days.index(x["day"]), x["hour"])
            ):
                print(
                    f"  Día: {slot['day']}, Hora: {slot['hour']}, Docente: {slot['teacher']}, Aula: {slot['classroom']}, Semestre: {slot['semester']}"
                )

    def save_schedule_to_excel(self, filename="horario.xlsx"):
        """Guarda el horario en un archivo Excel."""
        data = []
        for course_id, slots in self.schedule.items():
            for slot in slots:
                row = {
                    "Día": slot["day"],
                    "Hora": slot["hour"],
                    "Curso": course_id,
                    "Docente": slot["teacher"]
                }
                data.append(row)

        # Crear un DataFrame con los datos
        df = pd.DataFrame(data)
        # print(df)
        # Guardar en un archivo Excel
        # df.to_excel(filename, index=False)
        # print(f"Horario guardado en el archivo: {filename}")
