from ortools.sat.python import cp_model
import json
import pandas as pd

class ScheduleGenerator:
    def __init__(self, teacher_availabilities, courses):
        self.teacher_availabilities = teacher_availabilities
        self.courses = courses
        self.days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        self.hours = [h for h in range(7, 19)]  # Horas desde las 7 hasta las 18
        self.schedule = {}

    def parse_availability(self):
        """Convierte las franjas horarias amplias en horas individuales."""
        parsed_availabilities = {}
        for teacher, days in self.teacher_availabilities.items():
            parsed_availabilities[teacher] = {}
            for day, slots in days.items():
                hours_set = set()
                for slot in slots:
                    start_str, end_str = slot.split('-')
                    start_hour = int(start_str.split(':')[0])
                    end_hour = int(end_str.split(':')[0])
                    hours_set.update(range(start_hour, end_hour))
                parsed_availabilities[teacher][day] = sorted(hours_set)
            # Ordenar las horas para facilitar la generación de bloques continuos
            for day in parsed_availabilities[teacher]:
                parsed_availabilities[teacher][day] = sorted(parsed_availabilities[teacher][day])
        self.teacher_availabilities = parsed_availabilities

    def generate_possible_time_blocks(self, available_hours, max_block_length):
        """Genera todos los bloques de tiempo continuos posibles dado un conjunto de horas disponibles y la duración máxima del bloque."""
        time_blocks = []
        for length in range(1, max_block_length + 1):
            for i in range(len(available_hours)):
                block = [available_hours[i]]
                for j in range(i+1, len(available_hours)):
                    if available_hours[j] == block[-1] + 1:
                        block.append(available_hours[j])
                    else:
                        break
                    if len(block) == length:
                        break
                if len(block) == length:
                    time_blocks.append(block)
        return time_blocks

    def generate_schedule(self):
        self.parse_availability()
        model = cp_model.CpModel()

        # Variables de decisión: (curso, día, índice de bloque)
        schedule_vars = {}
        all_blocks = {}
        for course_id, course_info in self.courses.items():
            intensity = course_info["intensity"]
            teacher_id = course_info["teacher"]
            max_block_length = min(4, intensity)  # Máximo 4 horas por día
            for day in self.days:
                available_hours = self.teacher_availabilities.get(teacher_id, {}).get(day, [])
                possible_blocks = self.generate_possible_time_blocks(available_hours, max_block_length)
                # Filtrar bloques que coincidan exactamente con la intensidad si intensidad <= 4
                if intensity <= 4:
                    possible_blocks = [block for block in possible_blocks if len(block) == intensity]
                all_blocks[(course_id, day)] = possible_blocks
                for idx, block in enumerate(possible_blocks):
                    var_name = f"{course_id}_{day}_block_{idx}"
                    schedule_vars[(course_id, day, idx)] = model.NewBoolVar(var_name)

        # Restricción 1: La suma total de horas asignadas a cada curso debe ser igual a su intensidad
        for course_id, course_info in self.courses.items():
            total_hours_assigned = []
            for day in self.days:
                blocks = all_blocks.get((course_id, day), [])
                for idx, block in enumerate(blocks):
                    block_length = len(block)
                    total_hours_assigned.append(schedule_vars[(course_id, day, idx)] * block_length)
            model.Add(sum(total_hours_assigned) == course_info["intensity"])

        # Restricción 2: No asignar más de un bloque por día a la misma asignatura
        for course_id, course_info in self.courses.items():
            for day in self.days:
                blocks = all_blocks.get((course_id, day), [])
                if blocks:
                    vars_in_day = [schedule_vars[(course_id, day, idx)] for idx in range(len(blocks))]
                    model.Add(sum(vars_in_day) <= 1)

        # Restricción adicional: Asignaturas con intensidad <= 4 deben asignarse en un solo día
        for course_id, course_info in self.courses.items():
            intensity = course_info["intensity"]
            if intensity <= 4:
                days_assigned = []
                for day in self.days:
                    blocks = all_blocks.get((course_id, day), [])
                    vars_in_day = [schedule_vars[(course_id, day, idx)] for idx in range(len(blocks))]
                    if vars_in_day:
                        day_assigned = model.NewBoolVar(f"{course_id}_{day}_assigned")
                        model.Add(sum(vars_in_day) >= 1).OnlyEnforceIf(day_assigned)
                        model.Add(sum(vars_in_day) == 0).OnlyEnforceIf(day_assigned.Not())
                        days_assigned.append(day_assigned)
                # La asignatura debe asignarse en exactamente un día
                model.Add(sum(days_assigned) == 1)

        # Restricción 4: Evitar conflictos de horario para los docentes
        for teacher_id in self.teacher_availabilities:
            for day in self.days:
                hour_conflicts = {}
                for course_id, course_info in self.courses.items():
                    if course_info["teacher"] != teacher_id:
                        continue
                    blocks = all_blocks.get((course_id, day), [])
                    for idx, block in enumerate(blocks):
                        var = schedule_vars[(course_id, day, idx)]
                        for hour in block:
                            if hour not in hour_conflicts:
                                hour_conflicts[hour] = []
                            hour_conflicts[hour].append(var)
                for hour, vars_at_hour in hour_conflicts.items():
                    model.Add(sum(vars_at_hour) <= 1)

        # Resolver el problema
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        # Verificar si se encontró una solución
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for course_id, course_info in self.courses.items():
                for day in self.days:
                    blocks = all_blocks.get((course_id, day), [])
                    for idx, block in enumerate(blocks):
                        if solver.Value(schedule_vars[(course_id, day, idx)]) == 1:
                            start_hour = block[0]
                            end_hour = block[-1] + 1
                            if course_id not in self.schedule:
                                self.schedule[course_id] = []
                            self.schedule[course_id].append({
                                "day": day,
                                "hour": f"{start_hour}:00-{end_hour}:00",
                                "teacher": course_info["teacher"]
                            })
        else:
            print("No se pudo encontrar una solución factible.")

    def get_schedule_json(self):
        """Devuelve el horario en formato JSON (diccionario)."""
        schedule_json = {}
        for course_id, slots in self.schedule.items():
            schedule_json[course_id] = []
            for slot in sorted(slots, key=lambda x: (self.days.index(x['day']), x['hour'])):
                schedule_json[course_id].append({
                    "day": slot["day"],
                    "hour": slot["hour"],
                    "teacher": slot["teacher"]
                })
        return schedule_json
    
    def print_schedule(self):
        """Imprime el horario generado."""
        for course_id, slots in self.schedule.items():
            print(f"Curso: {course_id}")
            for slot in sorted(slots, key=lambda x: (self.days.index(x['day']), x['hour'])):
                print(
                    f"  Día: {slot['day']}, Hora: {slot['hour']}, Docente: {slot['teacher']}"
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
