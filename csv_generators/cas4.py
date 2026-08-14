import csv
import random


def calculate_news2(fc, spo2, temp, sysbp, glasgow_total, fr):
    score = 0
    # FR score (NEWS2)
    if fr <= 8 or fr >= 25: score += 3
    elif 9 <= fr <= 11: score += 1
    elif 21 <= fr <= 24: score += 2
    
    # FC score
    if fc <= 40 or 111 <= fc <= 130: score += 2
    elif 41 <= fc <= 50 or 91 <= fc <= 110: score += 1
    elif fc >= 131: score += 3
    
    # SpO2 score
    if 94 <= spo2 <= 95: score += 1
    elif 92 <= spo2 <= 93: score += 2
    elif spo2 <= 91: score += 3
    
    # Temp score
    if 35.1 <= temp <= 36.0 or 38.1 <= temp <= 39.0: score += 1
    elif temp >= 39.1: score += 2
    elif temp <= 35.0: score += 3
    
    # SysBP score
    if 101 <= sysbp <= 110: score += 1
    elif 91 <= sysbp <= 100: score += 2
    elif sysbp <= 90 or sysbp >= 220: score += 3
    
    # Glasgow score
    if glasgow_total < 15: score += 3
    return score


def generate_glasgow_details(target_total):
    if target_total == 15: return 4, 5, 6
    e, v, m = 4, 5, 6
    current = 15
    while current > target_total:
        choices = []
        if e > 1: choices.append('e')
        if v > 1: choices.append('v')
        if m > 1: choices.append('m')
        if not choices: break
        c = random.choice(choices)
        if c == 'e': e -= 1
        elif c == 'v': v -= 1
        elif c == 'm': m -= 1
        current = e + v + m
    return e, v, m


def ensure_news2_ge_7(fc, spo2, temp, sysbp, gcs, fr):
    """Ajuste les constantes pour garantir NEWS2 >= 7 (patients critiques)."""
    while calculate_news2(fc, spo2, temp, sysbp, gcs, fr) < 7:
        choice = random.choice(['fc', 'fc', 'spo2', 'temps', 'sysbp', 'gcs', 'fr'])
        if choice == 'fc':
            fc = random.choice([random.randint(30, 40), random.randint(131, 200)])
        elif choice == 'spo2':
            spo2 = random.randint(70, 88)
        elif choice == 'temps':
            temp = round(random.uniform(34.0, 35.0), 1) if random.random() < 0.3 else round(random.uniform(39.1, 41.0), 1)
        elif choice == 'sysbp':
            sysbp = random.randint(60, 89)
        elif choice == 'gcs':
            gcs = random.randint(6, 11)
        elif choice == 'fr':
            fr = random.choice([random.randint(5, 8), random.randint(25, 35)])
    return fc, spo2, temp, sysbp, gcs, fr


def ensure_news2_le_6(fc, spo2, temp, sysbp, gcs, fr):
    """Ajuste les constantes pour garantir NEWS2 <= 5 (patients stables)."""
    attempts = 0
    while calculate_news2(fc, spo2, temp, sysbp, gcs, fr) >= 6 and attempts < 20:
        choice = random.choice(['fc', 'spo2', 'temps', 'sysbp', 'fr'])
        if choice == 'fc':
            fc = random.randint(60, 100)
        elif choice == 'spo2':
            spo2 = random.randint(96, 100)
        elif choice == 'temps':
            temp = round(random.uniform(36.5, 37.5), 1)
        elif choice == 'sysbp':
            sysbp = random.randint(110, 135)
        elif choice == 'fr':
            fr = random.randint(12, 18)
        attempts += 1
    return fc, spo2, temp, sysbp, gcs, fr


def determine_rythme(fc, is_severe):
    if fc >= 130:
        if is_severe and random.random() < 0.15: return "tachycardie_ventriculaire"
        return random.choice(["tachycardie_sinusale", "fibrillation_atriale"])
    elif fc > 100:
        return random.choice(["tachycardie_sinusale", "tachycardie_sinusale", "fibrillation_atriale"])
    elif fc < 60:
        return "bradycardie_sinusale"
    else:
        return random.choice(["sinusal", "sinusal", "sinusal", "fibrillation_atriale"])


def generate_patient_trajectory(patient_id):
    rows = []
    is_deteriorating = random.random() < 0.20
    num_steps = random.randint(4, 10)

    fc_base = random.randint(65, 90)
    spo2_base = random.randint(96, 100)
    temp_base = round(random.uniform(36.5, 37.8), 1)
    sysbp_base = random.randint(115, 140)
    gcs_base = 15
    douleur_base = random.randint(0, 5)
    fr_base = random.randint(12, 18)

    if is_deteriorating:
        failure_mode = random.choice(["respiratoire", "hemodynamique", "neurologique"])
        if failure_mode == "respiratoire":
            fc_target = random.randint(110, 140)
            spo2_target = random.randint(80, 88)
            sysbp_target = random.randint(100, 120)
            gcs_target = random.randint(13, 14)
            fr_target = random.randint(25, 35)
        elif failure_mode == "hemodynamique":
            fc_target = random.randint(130, 165)
            spo2_target = random.randint(92, 95)
            sysbp_target = random.randint(65, 85)
            gcs_target = random.randint(11, 14)
            fr_target = random.randint(20, 24)
        else:
            fc_target = random.randint(50, 100)
            spo2_target = random.randint(90, 96)
            sysbp_target = random.randint(145, 185)
            gcs_target = random.randint(6, 11)
            fr_target = random.randint(10, 14)
        temp_target = random.choice([round(random.uniform(35.0, 36.0), 1), round(random.uniform(38.5, 40.0), 1)])
        fc_target, spo2_target, temp_target, sysbp_target, gcs_target, fr_target = ensure_news2_ge_7(
            fc_target, spo2_target, temp_target, sysbp_target, gcs_target, fr_target
        )
        douleur_target = random.randint(6, 10)
    else:
        fc_target, spo2_target, sysbp_target, gcs_target, fr_target = fc_base, spo2_base, sysbp_base, gcs_base, fr_base
        temp_target, douleur_target = temp_base, douleur_base

    current_fc, current_spo2, current_sysbp = fc_base, spo2_base, sysbp_base
    current_temp, current_gcs, current_douleur, current_fr = temp_base, gcs_base, douleur_base, fr_base

    for step in range(1, num_steps + 1):
        if step == 1:
            delta_minutes = 0
        else:
            delta_minutes = random.randint(15, 90)

        t = (step - 1) / (num_steps - 1) if num_steps > 1 else 1.0

        if is_deteriorating:
            current_fc = int(fc_base + (fc_target - fc_base) * t + random.gauss(0, 3))
            current_spo2 = int(spo2_base + (spo2_target - spo2_base) * t + random.gauss(0, 1))
            current_sysbp = int(sysbp_base + (sysbp_target - sysbp_base) * t + random.gauss(0, 4))
            current_temp = round(temp_base + (temp_target - temp_base) * t + random.gauss(0, 0.2), 1)
            if t > 0.7:
                current_gcs = int(gcs_base + (gcs_target - gcs_base) * t)
            current_douleur = int(douleur_base + (douleur_target - douleur_base) * t + random.gauss(0, 1))
            current_fr = int(fr_base + (fr_target - fr_base) * t + random.gauss(0, 1.5))
        else:
            for _ in range(5):
                current_fc = int(fc_base + random.gauss(0, 5))
                current_spo2 = max(96, int(spo2_base + random.gauss(0, 1)))
                current_sysbp = int(sysbp_base + random.gauss(0, 8))
                current_temp = round(temp_base + random.gauss(0, 0.2), 1)
                current_gcs = 15
                current_douleur = max(0, int(douleur_base + random.gauss(0, 1)))
                current_fr = int(fr_base + random.gauss(0, 1.5))
                if calculate_news2(current_fc, current_spo2, current_temp, current_sysbp, current_gcs, current_fr) < 6:
                    break

        current_fc = max(30, min(220, current_fc))
        current_spo2 = max(50, min(100, current_spo2))
        current_sysbp = max(60, min(260, current_sysbp))
        current_temp = round(max(34.0, min(42.0, current_temp)), 1)
        current_gcs = max(3, min(15, current_gcs))
        current_douleur = max(0, min(10, current_douleur))
        current_fr = max(5, min(50, current_fr))

        current_diabp = int(current_sysbp * 0.5) + random.randint(10, 25)
        current_diabp = min(current_diabp, current_sysbp - 10)

        e, v, m = generate_glasgow_details(current_gcs)

        news2 = calculate_news2(current_fc, current_spo2, current_temp, current_sysbp, current_gcs, current_fr)
        alerte = 1 if news2 >= 7 else 0

        rythme = determine_rythme(current_fc, alerte == 1)

        rows.append([
            patient_id,
            patient_id,
            step,
            delta_minutes,
            current_fc,
            current_sysbp,
            current_diabp,
            current_spo2,
            current_temp,
            current_fr,
            e, v, m,
            current_gcs,
            current_douleur,
            rythme,
            news2,
            alerte,
        ])

    return rows


def main():
    random.seed(42)
    num_patients = 6000
    filename = "dataset_news2_timeseries_30k.csv"

    headers = [
        "patient_id", "sejour_id", "sequence_step", "delta_minutes",
        "fc", "ta_systolique", "ta_diastolique", "spo2", "temperature",
        "frequence_respiratoire",
        "glasgow_e", "glasgow_v", "glasgow_m", "glasgow_total",
        "douleur_eva", "rythme_cardiaque", "new_score_2", "alerte_deterioration",
    ]

    print(f"Generation de {num_patients} patients (time-series)...")
    total = 0
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for pid in range(1, num_patients + 1):
            traj = generate_patient_trajectory(pid)
            w.writerows(traj)
            total += len(traj)
    print(f"Termine : {filename} ({total} lignes)")


if __name__ == "__main__":
    main()
