import csv
import random


def generate_glasgow_details(target_total: int) -> tuple[int, int, int]:
    """
    Décompose un Glasgow total (3-15) en E (1-4), V (1-5), M (1-6).
    Garantit E+V+M = target_total.
    """
    e, v, m = 4, 5, 6
    current = 15
    while current > target_total:
        choices = []
        if e > 1: choices.append('e')
        if v > 1: choices.append('v')
        if m > 1: choices.append('m')
        if not choices:
            break
        c = random.choice(choices)
        if c == 'e': e -= 1
        elif c == 'v': v -= 1
        elif c == 'm': m -= 1
        current = e + v + m
    return e, v, m


def pick_age() -> int:
    """Âge avec distribution réaliste pour les urgences."""
    r = random.random()
    if r < 0.08:      return random.randint(0, 2)
    if r < 0.15:      return random.randint(3, 15)
    if r < 0.65:      return random.randint(16, 64)
    if r < 0.90:      return random.randint(65, 84)
    return random.randint(85, 110)


def pick_weight(age: int) -> float:
    """Poids physiologiquement cohérent avec l'âge."""
    if age < 2:        return round(random.uniform(2.0, 14.0), 1)
    if age < 10:       return round(random.uniform(14.0, 40.0), 1)
    if age < 18:       return round(random.uniform(40.0, 70.0), 1)
    if age < 65:       return round(random.gauss(75.0, 14.0), 1)
    return round(random.gauss(68.0, 12.0), 1)


def pick_minor_anomaly() -> tuple[int, int, int, int, int]:
    """
    Génère 1 ou 2 anomalies légères pour CCMU 2.
    Retourne (glasgow, spo2, fc, ta_sys, douleur_eva) avec les valeurs modifiées.
    """
    glasgow_total, spo2, fc, ta_sys, douleur_eva = 15, random.randint(96, 100), random.randint(60, 90), random.randint(110, 135), random.randint(0, 3)
    pool = ['spo2', 'fc', 'ta', 'eva']
    n = 1 if random.random() < 0.55 else 2
    for a in random.sample(pool, n):
        if a == 'spo2':    spo2 = random.randint(91, 94)
        elif a == 'fc':    fc = random.randint(91, 110)
        elif a == 'ta':    ta_sys = random.choice([random.randint(100, 109), random.randint(140, 159)])
        elif a == 'eva':   douleur_eva = random.randint(4, 6)
    return glasgow_total, spo2, fc, ta_sys, douleur_eva


def pick_moderate_anomaly() -> tuple[int, int, int, int, int]:
    """2-3 anomalies modérées pour CCMU 3."""
    glasgow_total, spo2, fc, ta_sys, douleur_eva = 15, random.randint(96, 100), random.randint(65, 95), random.randint(110, 135), random.randint(5, 9)
    pool = ['glasgow', 'spo2', 'fc', 'ta']
    n = random.randint(2, 3)
    for a in random.sample(pool, n):
        if a == 'glasgow': glasgow_total = random.randint(10, 14)
        elif a == 'spo2':  spo2 = random.randint(90, 94)
        elif a == 'fc':    fc = random.randint(101, 130)
        elif a == 'ta':    ta_sys = random.randint(90, 99)
    return glasgow_total, spo2, fc, ta_sys, douleur_eva


def pick_severe_anomaly() -> tuple[int, int, int, int, int]:
    """2-3 anomalies sévères pour CCMU 4."""
    glasgow_total, spo2, fc, ta_sys, douleur_eva = 15, random.randint(96, 100), random.randint(65, 95), random.randint(110, 135), random.randint(5, 10)
    pool = ['glasgow', 'spo2', 'fc', 'ta']
    n = random.randint(2, 3)
    for a in random.sample(pool, n):
        if a == 'glasgow': glasgow_total = random.randint(7, 12)
        elif a == 'spo2':  spo2 = random.randint(75, 89)
        elif a == 'fc':    fc = random.randint(121, 180)
        elif a == 'ta':    ta_sys = random.randint(70, 89)
    return glasgow_total, spo2, fc, ta_sys, douleur_eva


def pick_critical_anomaly() -> tuple[int, int, int, int, int]:
    """3 anomalies critiques pour CCMU 5."""
    glasgow_total, spo2, fc, ta_sys, douleur_eva = 15, random.randint(96, 100), random.randint(65, 95), random.randint(110, 135), random.randint(0, 5)
    for a in random.sample(['glasgow', 'spo2', 'fc', 'ta'], 3):
        if a == 'glasgow': glasgow_total = random.randint(3, 7)
        elif a == 'spo2':  spo2 = random.randint(50, 74)
        elif a == 'fc':    fc = random.choice([random.randint(30, 39), random.randint(151, 220)])
        elif a == 'ta':    ta_sys = random.randint(60, 79)
    return glasgow_total, spo2, fc, ta_sys, douleur_eva


def generate_row(patient_id: int) -> list:
    r = random.random()
    if r < 0.20:      ccmu = 1
    elif r < 0.50:    ccmu = 2
    elif r < 0.80:    ccmu = 3
    elif r < 0.95:    ccmu = 4
    else:             ccmu = 5

    if ccmu == 1:
        glasgow_total = 15
        spo2 = random.randint(96, 100)
        fc = random.randint(60, 90)
        ta_sys = random.randint(110, 135)
        douleur_eva = random.randint(0, 3)

    elif ccmu == 2:
        glasgow_total, spo2, fc, ta_sys, douleur_eva = pick_minor_anomaly()

    elif ccmu == 3:
        glasgow_total, spo2, fc, ta_sys, douleur_eva = pick_moderate_anomaly()

    elif ccmu == 4:
        glasgow_total, spo2, fc, ta_sys, douleur_eva = pick_severe_anomaly()

    else:
        glasgow_total, spo2, fc, ta_sys, douleur_eva = pick_critical_anomaly()

    glasgow_e, glasgow_v, glasgow_m = generate_glasgow_details(glasgow_total)

    ta_dia = int(ta_sys * 0.55) + random.randint(5, 15)
    ta_dia = min(ta_dia, ta_sys - 10)

    age = pick_age()
    sexe = random.choice(["M", "F"])
    poids = pick_weight(age)
    poids = max(1.5, min(280.0, poids))

    if ccmu == 1:
        temperature = round(random.uniform(36.0, 37.5), 1)
    elif ccmu == 2:
        if random.random() < 0.20:
            temperature = round(random.uniform(37.6, 38.0), 1)
        else:
            temperature = round(random.uniform(36.0, 37.5), 1)
    elif ccmu == 3:
        if random.random() < 0.30:
            temperature = round(random.uniform(37.6, 39.0), 1)
        else:
            temperature = round(random.uniform(36.0, 37.5), 1)
    else:
        if random.random() < 0.50:
            temperature = round(random.uniform(37.6, 41.0), 1)
        else:
            temperature = round(random.uniform(36.0, 37.5), 1)

    if ccmu == 5:
        mode_arrivee = random.choice(["SMUR", "SMUR", "SMUR", "ambulance"])
    elif ccmu == 4:
        mode_arrivee = random.choice(["SMUR", "ambulance", "ambulance", "pompiers"])
    elif ccmu == 3:
        mode_arrivee = random.choice(["ambulance", "ambulance", "pompiers", "autonome"])
    elif ccmu == 2:
        mode_arrivee = random.choice(["ambulance", "pompiers", "autonome", "autonome"])
    else:
        mode_arrivee = random.choices(
            ["autonome", "ambulance", "pompiers", "SMUR"],
            weights=[70, 18, 8, 4], k=1
        )[0]

    if ccmu == 1:       score_french = random.choice([4, 5])
    elif ccmu == 2:     score_french = random.choice([3, 4])
    elif ccmu == 3:     score_french = random.choice([2, 3])
    else:               score_french = random.choice([1, 2])

    h = random.randint(0, 23)
    m = random.randint(0, 59)
    heure_arrivee = f"{h:02d}:{m:02d}"

    if   h < 6:   tranche_horaire = "Nuit"
    elif h < 12:  tranche_horaire = "Matin"
    elif h < 18:  tranche_horaire = "Après-midi"
    else:         tranche_horaire = "Soirée"

    jour_semaine = random.randint(0, 6)
    weekend = 1 if jour_semaine in (5, 6) else 0

    return [
        patient_id, age, sexe, mode_arrivee, score_french, poids, temperature,
        fc, ta_sys, ta_dia, spo2,
        glasgow_e, glasgow_v, glasgow_m, glasgow_total,
        douleur_eva, heure_arrivee, tranche_horaire, jour_semaine, weekend, ccmu,
    ]


def main():
    random.seed(42)
    num_rows = 20000
    filename = "dataset_urgences_20k.csv"

    headers = [
        "patient_id", "age", "sexe", "mode_arrivee", "score_french",
        "poids", "temperature",
        "fc", "ta_systolique", "ta_diastolique", "spo2",
        "glasgow_e", "glasgow_v", "glasgow_m", "glasgow_total",
        "douleur_eva", "heure_arrivee", "tranche_horaire",
        "jour_semaine", "weekend", "score_ccmu",
    ]

    print(f"Génération de {num_rows} lignes...")
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for i in range(1, num_rows + 1):
            w.writerow(generate_row(i))

    print(f"Terminé : {filename}")


if __name__ == "__main__":
    main()
