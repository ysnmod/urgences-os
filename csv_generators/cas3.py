import csv
import random

CIM_PROFILES = {
    "A09.0": {
        "motifs": ["Diarrhee et vomissements", "Douleurs au ventre et selles liquides", "Incapacite a garder les liquides, vomissements", "Gastro depuis 2 jours"],
        "triage": ["Patient se plaignant de diarrhees profuses. Constantes stables. Un peu deshydrate.", "Vomissements incoercibles. Abdomen souple. Nausees +++.", "Suspicion gastro-enterite. T a 37.8. Pale."],
        "anamnese": ["Episode d'apparition brutale de diarrhee aqueuse (environ 10 episodes/jour) associee a des vomissements alimentaires puis bilieux.", "Notion de contage familial, debut des symptomes il y a 48h avec crampes abdominales diffuses."],
        "examen": ["Abdomen souple, depressible, gargouillement peri-ombilical. Pas de defense. Pli cutane leger.", "Bruits hydro-aeriques augmentes. Sensibilite diffuse sans localisation precise. Muqueuses un peu seches."],
        "paraclinique": ["Bilan standard sans hyperleucocytose. Iono: legere hypokaliemie a 3.4. Reste RAS.", "BU negative. Iono sanguin sans anomalie majeure, fonction renale conservee."],
        "atcd": ["Aucun", "Syndrome de l'intestin irritable", "Ulcere gastrique ancien"],
        "ttt": ["Spasfon", "Paracetamol", "Smecta"]
    },
    "A41.9": {
        "motifs": ["Fievre elevee, confusion", "Frissons, hypotension", "Patient tres faible, ne tient pas debout", "Alteration de l'etat general avec fievre"],
        "triage": ["Urgence absolue. Choc? FC 130, TA 85/50, marbrures. En attente dechocage.", "Patient somnolent, febrile a 39.5. SpO2 91%. Marbrures aux genoux. Voie d'eau posee."],
        "anamnese": ["Alteration profonde de l'etat general depuis 24h avec frissons intenses, sueurs et confusion d'apparition recente.", "Degradation rapide chez un patient rapportant une fievre non mesuree, oligurie depuis hier."],
        "examen": ["Patient obnubile, Glasgow 13. Tachycardie reguliere. Pression arterielle pincee. Marbrures cutanees remontant au-dessus des genoux. TRC > 4 secondes.", "Polypnee a 28/min. Tachycarde. Extremites froides et cyanotiques. Souffle systolique fonctionnel."],
        "paraclinique": ["Hyperleucocytose a 22 G/L. Hyperlactatemie a 4.5 mmol/L. Procalcitonine tres elevee. Hemocultures prelevees.", "Gaz du sang: acidose metabolique severe (pH 7.25). Lactates > 5. Insuffisance renale aigue (Creat 180)."],
        "atcd": ["Diabete type 2", "Immunodepression", "Cancer en remission", "Infections urinaires a repetition"],
        "ttt": ["Metformine", "Corticotherapie", "Amoxicilline (recent)"]
    },
    "I10": {
        "motifs": ["Tension elevee prise a la pharmacie", "Maux de tete et pic hypertensif", "Acouphenes et TA a 19", "Vertiges, TA haute chez le MT"],
        "triage": ["Cephalees en casque. Constantes: TA 195/105, FC 75. Patiente anxieuse.", "Asymptomatique, adresse par medecin traitant pour TA a 200/100. Pas de douleur tho."],
        "anamnese": ["Decouverte fortuite d'une pression arterielle elevee ou cephalees pulsatiles isolees sans deficit neuro.", "Patient connu pour HTA, en rupture de traitement depuis 1 mois, se plaint de phosphenes."],
        "examen": ["Examen neuro strictement normal. Auscultation cardio-pulmonaire normale. Bruits du cUrs reguliers.", "Pas de deficit sensitivo-moteur. Pas d'anomalie aux paires craniennes. Reste de l'examen clinique sans particularite."],
        "paraclinique": ["ECG: rythme sinusal, HVG electrique, pas de trouble de la repolarisation. Tropo negative. Bio standard normale.", "Fond d'Uil aux urgences non realise. Iono: creatinine de base normale. BU: pas de proteinurie."],
        "atcd": ["HTA essentielle", "Dyslipidemie", "Surpoids"],
        "ttt": ["Amlodipine", "Ramipril", "Bisoprolol"]
    },
    "I21.0": {
        "motifs": ["Douleur thoracique forte", "Serrement poitrine, irradiation bras", "Douleur au cUr", "Oppression thoracique avec sueurs"],
        "triage": ["Dlr tho typique 8/10. Pale, sueurs. ECG fait en box 1 a voir en urgence.", "Urgence vitale. Serrement thoracique depuis 1h. ECG: sus-ST. Appel SAMU pour transfert."],
        "anamnese": ["Douleur retrosternale constrictive, en etau, irradiant vers la machoire gauche et le bras gauche, associee a des sueurs profuses.", "Debut brutal au repos d'une oppression thoracique intense, non calmee par la trinitrine per os, evoluant depuis 2h."],
        "examen": ["Patient angoisse, algique, se tenant la poitrine. Bruits du cUr assourdis. Pas de signe d'insuffisance cardiaque droite ou gauche a ce stade.", "Hemodynamique conservee mais patient cyanose. Pas de souffle cardiaque. Auscultation pulmonaire libre."],
        "paraclinique": ["ECG franc: sus-decalage du segment ST en anterieur etendu (V1 a V6). Miroir en inferieur. Troponines ultra-sensibles positives a >2000 ng/L.", "L'ECG retrouve un sus-ST en V2-V4. Biologie: elevation des CPK et troponines. Appel cardiologue pour coro en urgence."],
        "atcd": ["Tabagisme actif", "Diabete", "Infarctus ancien", "Hypercholesterolemie"],
        "ttt": ["Kardegic", "Statines", "Metformine"]
    },
    "I48": {
        "motifs": ["Palpitations", "Le cUr bat vite et de travers", "Sensation de rates du cUr", "Montre connectee indique rythme irregulier"],
        "triage": ["Patient sent son cUr palpiter. FC irreguliere oscillant entre 110 et 140. TA stable.", "Palpitations depuis ce matin. Pas de douleur thoracique. Pouls tres irregulier."],
        "anamnese": ["Sensation de palpitations desagreables de survenue inopinee, sans douleur thoracique associee. Notion d'episodes similaires resolutifs par le passe.", "Symptomatologie fonctionnelle a type de tachycardie ressentie, associee a une legere asthenie."],
        "examen": ["Auscultation: rythme cardiaque totalement arythmique, rapide. Pas de souffle. Pouls peripherique avec deficit par rapport a la FC centrale.", "Arythmie complete. Bruits du cUr clairs. Examen pleuro-pulmonaire normal."],
        "paraclinique": ["ECG confirme une Fibrillation Atriale (FA) rapide a 125 bpm. Pas d'onde P, rythme RR irregulier. Biologie: TSH normale, Iono OK.", "Fibrillation auriculaire sur l'ECG. Troponines negatives. Radio thorax sans cardiomegalie."],
        "atcd": ["HTA", "ACFA paroxystique connue", "Syndrome d'apnee du sommeil"],
        "ttt": ["Eliquis", "Preterax", "Cordarone"]
    },
    "I50.0": {
        "motifs": ["Essoufflement important", "Jambes gonflees et mal a respirer", "Ne peut plus dormir couche", "Detresse respiratoire"],
        "triage": ["Polypnee a 26. Orthopnee. Sat 88% en air ambiant. O2 mis a 3L. Udimes des membres inferieurs.", "Detresse respiratoire. Crepitants audibles a distance. TA a 160/90."],
        "anamnese": ["Dyspnee d'effort d'aggravation progressive depuis 1 semaine, devenue de repos ce jour. Plainte d'orthopnee (dort avec 3 oreillers).", "Prise de poids de 4kg en 5 jours, avec apparition d'OOMI et dyspnee paroxystique nocturne."],
        "examen": ["Auscultation pulmonaire: rales crepitants bilateraux remontant a mi-champs. Bruit de galop (B3) a l'auscultation cardiaque. Turgescence jugulaire presente.", "OMI bilateraux, blancs, mous, prenant le godet. Reflux hepato-jugulaire positif. Tachypnee."],
        "paraclinique": ["Radio thorax: cardiomegalie, redistribution vasculaire aux sommets, lignes de Kerley. Biologie: pro-BNP tres eleve > 5000 pg/mL.", "Echographie clinique: lignes B bilaterales diffuses (syndrome interstitiel). BNP eleve. Fonction renale alteree (syndrome cardio-renal)."],
        "atcd": ["Insuffisance cardiaque FEVG alteree", "Cardiopathie ischemique", "HTA severe"],
        "ttt": ["Furosemide", "Entresto", "Spironolactone"]
    },
    "I63.9": {
        "motifs": ["Faiblesse du bras droit", "Difficulte a parler, bouche de travers", "AVC probable", "Aphasie et hemiplegie"],
        "triage": ["Alerte Thrombolyse! Hemiplegie droite et aphasie depuis 45 min. Transfert direct au scanner.", "Suspicion AVC. Debut brutal a 14h. Deviation commissure labiale. Constantes OK."],
        "anamnese": ["Installation brutale (heure du debut des symptomes claire) d'un deficit moteur hemicorporel avec troubles du langage.", "La famille a remarque une asymerie faciale soudaine et une impossibilite de lever le bras pendant le repas."],
        "examen": ["Hemiplegie brachio-faciale droite proportionnelle. Aphasie de Broca (motrice). NIHSS evalue a 12. Pas de trouble de la vigilance.", "Deficit sensitivo-moteur de l'hemicorps gauche. Hemianopsie laterale homonyme. Deviation conjuguee de la tete et des yeux."],
        "paraclinique": ["Scanner cerebral en urgence: pas d'hemorragie (elimine un AVC hemorragique), signe de l'artere sylvienne hyperdense. Anglo-TDM: occlusion M1.", "IRM cerebrale en sequence diffusion: hypersignal de territoire jonctionnel. Mismatch FLAIR positif. Avis neurovasculaire pour thrombectomie."],
        "atcd": ["Fibrillation atriale (non anticoagulee)", "Diabete", "AIT dans le passe"],
        "ttt": ["Aucun traitement", "Kardegic (faible dose)"]
    },
    "J15.9": {
        "motifs": ["Toux et fievre", "Point de cote en respirant et frissons", "Infection pulmonaire", "Crache jaune/vert avec fievre"],
        "triage": ["Temperature 39C. Toux grasse. Saturation 92%. A vu le medecin de garde hier.", "Febrile. Toux purulente. Asthenie importante. FR a 22/min."],
        "anamnese": ["Tableau aigu evoluant depuis 3-4 jours associant fievre a frissons, toux productive avec expectorations purulentes et douleur basi-thoracique unilaterale.", "Alteration de l'etat general avec syndrome infectieux net, myalgies et toux devenant de plus en plus encombrante."],
        "examen": ["Syndrome de condensation pulmonaire de la base droite: matite a la percussion, augmentation des vibrations vocales, et foyer de rales crepitants localises.", "Auscultation: crepitants en foyer au lobe inferieur gauche. Reste de l'auscultation normale. Pas de signe de lutte respiratoire severe."],
        "paraclinique": ["Radiographie thoracique face/profil: foyer d'opacite alveolaire systematisee du LIG avec bronchogramme aerien. Hyperleucocytose a PNN (14G/L). CRP a 150 mg/L.", "NFS: polynucleose neutrophile. Procalcitonine elevee. Hemocultures prelevees avant antibiotherapie (Amoxicilline)."],
        "atcd": ["Tabagisme", "BPCO legere"],
        "ttt": ["Ventoline si besoin", "Paracetamol"]
    },
    "J18.9": {
        "motifs": ["Toux persistante", "Grosse bronchite", "Infection des poumons", "Fievre et gene respiratoire"],
        "triage": ["Patient febrile toussant beaucoup. Sat OK. Metatheque.", "Suspicion pneumopathie. Toux + crachats depuis 5 jours. TA normale."],
        "anamnese": ["Toux initialement seche devenue grasse, associee a un febricule, persistant malgre un traitement symptomatique.", "Tableau trainant d'infection des voies aeriennes inferieures."],
        "examen": ["Rales sibilants epars et quelques sous-crepitants diffus. Foyers mal systematises.", "Auscultation encombree aux deux bases. Febrile a 38.5."],
        "paraclinique": ["Radio thorax avec infiltration interstitielle diffuse ou petits foyers alveolaires non systematises. Biologie inflammatoire moderee.", "CRP a 60. Radio pulmonaire d'interpretation difficile, syndrome bronchique."],
        "atcd": ["Asthme dans l'enfance"],
        "ttt": ["Sirops contre la toux", "Corticoides inhales"]
    },
    "J44.0": {
        "motifs": ["Decompensation BPCO", "Crise de BPCO", "N'arrive plus a souffler", "Toux augmentee chez insuffisante respi"],
        "triage": ["Tirage intercostal. Sat 85% habituelle selon le patient, aujourd'hui a 81%. Mise sous VNI.", "Exacerbation BPCO. Encombrement majeur. FR 28."],
        "anamnese": ["Patient tabagique severe connu pour BPCO stade III, presentant une majoration de sa dyspnee habituelle, de son volume et de la purulence de ses crachats (criteres d'Anthonisen).", "Majoration de la dyspnee depuis 48h, toux tres purulente, impossibilite de faire 10 metres."],
        "examen": ["Distension thoracique en tonneau. Expiration prolongee. Auscultation: murmure vesiculaire diminue de facon bilaterale, quelques sibilants et ronchis expiratoires.", "Signes de lutte moderes, cyanose des levres. Hyper-sonorite a la percussion. Ronchis encombrants diffus."],
        "paraclinique": ["Gaz du sang en air ambiant: hypoxemie (PaO2 55), hypercapnie (PaCO2 50), pH compense (7.36). Radio thorax: hyperclarte et aplatissement des coupoles, pas de foyer aigu.", "NFS et CRP pour rechercher une surinfection. GDS: acidose respiratoire debutante."],
        "atcd": ["BPCO post-tabagique", "Oxygenotherapie a domicile", "Syndrome d'apnee du sommeil"],
        "ttt": ["Spiriva", "Symbicort", "O2 a domicile"]
    },
    "J45.0": {
        "motifs": ["Crise d'asthme", "Siffle beaucoup en respirant", "Allergie et respiration courte", "Inhalation de fumee, asthme"],
        "triage": ["Patiente jeune, siffle (wheezing). Sat 94%. Aerosols de ventoline en cours.", "Crise d'asthme severe. Difficulte a parler. FR a 30."],
        "anamnese": ["Episode aigu de dyspnee expiratoire sifflante, apparu suite a une exposition a un allergene (chat/poussiere) ou effort.", "Patiente asthmatique connue, traitement de fond mal suivi. Utilisation de plus de 10 bouffees de Beta-2-mimetiques ce jour sans soulagement."],
        "examen": ["Frein expiratoire evident. Rales sibilants diffus et bilateraux a l'auscultation (wheezing). Thorax distendu.", "Sibilants sonores audibles a l'oreille. Pas de cyanose. Debit expiratoire de pointe (DEP) effondre a 150 L/min."],
        "paraclinique": ["GDS si signe de gravite, souvent normaux au debut. Radio thorax souvent normale ou distension, sert a eliminer un pneumothorax de complication.", "Amelioration rapide sous aerosols de bronchodilatateurs. Biologie generalement sans anomalie."],
        "atcd": ["Asthme allergique", "Rhinite allergique", "Eczema atopique"],
        "ttt": ["Ventoline (Salbutamol)", "Seretide", "Aerius"]
    },
    "K35.9": {
        "motifs": ["Douleur fosse iliaque droite", "Mal au ventre en bas a droite", "Suspicion appendicite", "Douleur FID et nausees"],
        "triage": ["Dlr abdo. Plie la jambe droite. Febricule a 38C. Score douleur 7/10.", "Patiente jeune, algique abdo droite. Pas de trouble gyneco selon elle."],
        "anamnese": ["Douleur abdominale debutant en peri-ombilical puis se localisant et s'accentuant en fosse iliaque droite, associee a de discretes nausees et un febricule.", "Douleur d'apparition progressive depuis 24h, continue, max en FID, sans trouble du transit franc."],
        "examen": ["Abdomen: defense nette en fosse iliaque droite (point de Mac Burney positif). Douleur a la decompression (signe de Blumberg) et signe de Rovsing positif.", "Psoitis present. Toucher rectal: douleur laterodroite. Reste de l'abdomen souple."],
        "paraclinique": ["Hyperleucocytose moderee (12G/L) et CRP legerement ascensionnee (30 mg/L).", "Echographie (ou Scanner) abdominale: appendice epaissi > 8mm, non compressible, avec infiltration de la graisse meso-appendiculaire. Avis chirurgical."],
        "atcd": ["Aucun antecedent notable", "Appendicectomie dans la famille"],
        "ttt": ["Aucun", "Pilule contraceptive"]
    },
    "K52.9": {
         "motifs": ["Colite", "Douleur abdominale et diarrhee sanglante", "Maux de ventre intenses, diarrhees", "Crise aux intestins"],
         "triage": ["Douleur abdo diffuse. Nombreuses selles liquides. Tensions normales.", "Episode de diarrhees profuses et crampes. Pas de sang visible. Asthenie."],
         "anamnese": ["Crampes abdominales diffuses evoluant par salves, suivies de debacles diarrheiques. Notion de consommation d'un repas suspect.", "Douleurs coliques depuis 3 jours avec alternance diarrhee/constipation. Pas de rectorragie evidente."],
         "examen": ["Abdomen globalement meteorise, sensible sur le trajet colique (cadre colique). Pas de defense, pas de contracture.", "Bruits hydro-aeriques tres augmentes. Sensibilite diffuse au palper profond. Ampoule rectale vide."],
         "paraclinique": ["Coproculture en cours. Biologie standard: pas de syndrome inflammatoire severe. Scanner non indique en premiere intention.", "Bilan sanguin avec ionogramme normal. Calprotectine fecale prevue si persistance."],
         "atcd": ["Intolerance au lactose", "Maladie de Crohn", "Troubles fonctionnels intestinaux"],
         "ttt": ["Meteospasmyl", "Imodium", "Probiotiques"]
    },
    "K80.0": {
         "motifs": ["Crise de vesicule", "Forte douleur sous les cotes a droite", "Colique hepatique", "Douleur hypochondre droit irradiant epaule"],
         "triage": ["Douleur HCD 8/10. Nausees. Afebrile. Voie veineuse en place avec antalgiques.", "Forte douleur a droite. Patiente tres inconfortable. FC 90, TA 130/80."],
         "anamnese": ["Douleur brutale, post-prandiale (apres un repas riche), localisee a l'hypochondre droit, irradiant en bretelle vers l'epaule droite, avec nausees.", "Crise douloureuse intense, bloquant l'inspiration profonde, evoluant depuis quelques heures."],
         "examen": ["Signe de Murphy positif (inhibition douloureuse de l'inspiration profonde lors de la palpation sous-costale droite). Pas de defense localisee.", "Abdomen souple par ailleurs. Pas d'ictere conjonctival (elimine une angiocholite clinique a ce stade)."],
         "paraclinique": ["Bilan hepatique: transaminases, PAL, GGT normales (ou minime elevation). Pas d'hyperleucocytose.", "Echographie hepato-biliaire: vesicule biliaire multi-lithiasique, paroi fine, pas de dilatation de la VBP. Lithiase vesiculaire symptomatique."],
         "atcd": ["Surpoids", "Lithiase vesiculaire connue", "Grossesse recente"],
         "ttt": ["Antalgiques", "AINS"]
    },
    "K85.0": {
         "motifs": ["Douleur transfixiante au ventre", "Pancreatite aigue", "Mal au ventre apres l'alcool", "Douleur epigastrique intense"],
         "triage": ["Douleur epigastrique en barre 9/10. Patient agite. TA a 150/90. T a 37.8.", "Douleur transfixiante. Position en chien de fusil soulage un peu. Urgence."],
         "anamnese": ["Douleur epigastrique brutale, d'intensite maximale d'emblee, transfixiante (irradiant dans le dos), associee a des vomissements importants. Consommation recente d'alcool (ou ATCD de lithiase).", "Crise algique abdominale majeure, non calmee par les antalgiques simples. Attitude antalgique typique en anteflexion."],
         "examen": ["Sensibilite epigastrique marquee a la palpation. Meteorisme abdominal. Pas de contracture parietale severe au debut.", "Gene abdominale diffuse. Abolition ou diminution des bruits hydro-aeriques (ileos paralytique). Pas de signe de Cullen ou Grey-Turner."],
         "paraclinique": ["Lipasemie > 3 fois la normale (confirme le diagnostic de pancreatite aigue). CRP souvent elevee.", "Scanner abdominal avec injection (apres 48h): pancreas globuleux, infiltration de la graisse peri-pancreatique, recherche de necrose. Score de Balthazar calcule."],
         "atcd": ["Ethylisme chronique", "Lithiase biliaire", "Hypertriglyceridemie"],
         "ttt": ["Aspirine", "Omeprazole"]
    },
    "G40.9": {
         "motifs": ["Crise d'epilepsie", "A convulsionne", "Perte de connaissance et tremblements", "Crise comitiale"],
         "triage": ["Patient post-critique. Somnolent. GCS 12. Apporte par pompiers. Constantes RAS.", "Crise tonico-clonique observee par la famille. Morsure de langue. Confusion actuelle."],
         "anamnese": ["Episode brutal de perte de contact, suivi de mouvements tonico-cloniques generalises ayant dure environ 3 minutes. Morsure laterale de langue et perte d'urines rapportees.", "Notion de secousses rythmiques des quatre membres. Le patient ne se souvient de rien (amnesie post-critique)."],
         "examen": ["Phase post-critique (stertor, obnubilation). Examen neurologique (quand patient reveille) est sans deficit sensitivo-moteur. Reflexes normaux.", "Obnubilation resolutive. Morsure du bord lateral de la langue confirmee. Signe de Babinski bilateral (physiologique en post-critique immediat)."],
         "paraclinique": ["Biologie standard, iono complet, glycemie capillaire (pour eliminer une hypoglycemie), alcoolemie, toxiques urinaires. TDM cerebral si premiere crise.", "EEG en differe programme. Dosage du taux sanguin de l'antiepileptique (Keppra ou Depakine) si patient connu."],
         "atcd": ["Epilepsie connue", "Traumatisme cranien ancien", "Tumeur cerebrale operee"],
         "ttt": ["Keppra", "Lamictal", "Depakine (en rupture)"]
    },
    "G45.0": {
         "motifs": ["A perdu la vue d'un oeil puis c'est revenu", "Faiblesse du bras qui a disparu", "AIT", "Malaise avec trouble parole temporaire"],
         "triage": ["Suspicion AIT. Asymptomatique actuellement. Deficit moteur gauche resolutif en 15 min.", "Episode de dysarthrie fugace a domicile. Examen neuro actuel strict normal."],
         "anamnese": ["Apparition brutale d'un deficit neurologique focalise (ex: hemiparesie, amaurose fugace, aphasie) ayant dure quelques minutes avec recuperation totale sans sequelle.", "Le patient decrit une lourdeur du bras droit et une difficulte a articuler, entierement resoluee spontanement avant l'arrivee aux urgences."],
         "examen": ["Examen neurologique strictement normal (AIT par definition). Force musculaire 5/5, ROT symetriques, paires craniennes integres.", "Aucun deficit clinique residuel. Auscultation des carotides: possible souffle cervical. Rythme cardiaque regulier a l'auscultation."],
         "paraclinique": ["IRM cerebrale de diffusion en urgence (pour eliminer un AVC constitue). Echo-Doppler des TSAo (recherche de stenose carotidienne). ECG (recherche FA).", "Score ABCD2 pour evaluer le risque de recidive. Biologie normale."],
         "atcd": ["Diabete", "Tabac", "Hypercholesterolemie", "Souffle carotidien"],
         "ttt": ["Kardegic 75", "Tahor 40"]
    },
    "S06.0": {
        "motifs": ["A tape la tete", "Trauma cranien avec perte de connaissance", "Chute sur la tete", "Coup de poing au crane"],
        "triage": ["Trauma cranien. PC initiale breve rapportee. GCS 15 actuel. Pupilles symetriques.", "Chute de sa hauteur. Hematome cranien. Vomissements x1. Constantes stables."],
        "anamnese": ["Notion de choc direct sur le crane suivi d'une perte de connaissance tres breve (< 5 min). Periode d'amnesie peri-traumatique. Quelques nausees.", "Patient victime d'un traumatisme cranien ferme. Se plaint de cephalees frontales sans autre symptome neuro."],
        "examen": ["Patient alerte et oriente, Glasgow Total a 15 (E4V5M6). Pas de deficit neurologique focal. Pupilles isocores et reactives. Hematome sous-cutane du cuir chevelu.", "Pas d'embarrure palpable. Examen des paires craniennes sans anomalie. Reflexes osteotendineux symetriques."],
        "paraclinique": ["Scanner cerebral sans injection de contraste (TDM): aucune anomalie (ni hematome sous-dural, ni epidural, ni contusion). Diagnostic: commotion cerebrale simple.", "Surveillance neuro en UHCD. Biologie inutile. Repos."],
        "atcd": ["Aucun", "Osteoporose"],
        "ttt": ["Doliprane", "Anti-hypertenseurs"]
    },
    "S22.4": {
         "motifs": ["Douleur cotes apres chute", "Trauma costal", "Choc poitrine, a du mal a respirer", "Fracture de cote suspectee"],
         "triage": ["Dlr basi-thoracique droite. Chute escabeau. SpO2 96%. Dlr a la palpation.", "Douleur respi suite traumatisme. Pas de detresse respi."],
         "anamnese": ["Choc direct sur la paroi thoracique laterale. Plainte de douleur exquise, pointue, tres augmentee par l'inspiration profonde, la toux et les mouvements.", "Chute a velo sur le flanc. Douleur parietale bloquant la respiration profonde."],
         "examen": ["Douleur tres localisee a la palpation d'un arc costal. Exquisite. Compression antero-posterieure douloureuse. Auscultation pulmonaire symetrique, claire.", "Pas de matite declive, pas d'emphyseme sous-cutane, tympanisme normal (elimine complications pleurales immediates)."],
         "paraclinique": ["Radiographie de gril costal: trait de fracture non deplace sur le 5eme arc costal. Pas de pneumothorax ni d'epanchement pleural a la radio thorax face.", "Traitement purement antalgique. Radio pour confirmation et eliminer les complications."],
         "atcd": ["Aucun", "Osteoporose"],
         "ttt": ["Aucun"]
    },
    "S42.0": {
         "motifs": ["Chute sur l'epaule", "Douleur epaule, fracture clavicule", "Trauma epaule gauche", "Deformation clavicule"],
         "triage": ["Soutient son bras. Deformation visible de la clavicule. Douleur 6/10.", "A chute sur le moignon de l'epaule. Impotence fonctionnelle du MS droit."],
         "anamnese": ["Choc direct sur le moignon de l'epaule lors d'une chute sportive. Impotence fonctionnelle totale du membre superieur affecte. Le patient soutient son coude avec l'autre main (attitude des traumatises du membre superieur).", "Douleur violente et deformation immediatement visible apres une chute a moto."],
         "examen": ["Palpation douloureuse avec saillie osseuse au tiers moyen de la clavicule, ecchymose en regard. Recherche de complications: pouls distal percU, sensibilite du membre conservee, pas d'atteinte du plexus brachial.", "Mobilite articulaire de l'epaule impossible a cause de la douleur. Pas de complication cutanee (fracture fermee)."],
         "paraclinique": ["Radiographie de l'epaule/clavicule de face: fracture du 1/3 moyen de la clavicule avec leger deplacement. Pose d'anneaux claviculaires ou coude-au-corps.", "Imagerie standard suffit. Chirurgie orthopedique non indiquee en urgence (sauf grand deplacement)."],
         "atcd": ["Aucun notable"],
         "ttt": ["Aucun", "Vitamine D"]
    },
    "S52.5": {
         "motifs": ["Chute sur la main", "Douleur poignet", "Fracture poignet Pouteau-Colles", "Trauma poignet, deformation"],
         "triage": ["Deformation poignet droit en dos de fourchette. Chute de sa hauteur. Impotence fonctionnelle.", "Poignet tres douloureux, udime important. Bagues retirees au triage."],
         "anamnese": ["Mecanisme classique de chute sur la main en extension (hyperextension du poignet). Douleur violente immediate et impotence fonctionnelle de la main et du poignet.", "Le patient s'est rattrape sur ses mains lors d'une chute dans les escaliers. Sensation de craquement."],
         "examen": ["Deformation typique en 'dos de fourchette' de profil, et en 'baionnette' de face. Udime du carpe. Douleur exquise de la styloide radiale.", "Test de la sensibilite pulpaire normal. Pouls radial bien frappe (pas de compression vasculaire ou nerveuse patente aigue)."],
         "paraclinique": ["Radiographie du poignet face/profil: fracture de l'extremite inferieure du radius avec bascule posterieure (Pouteau-Colles). Arrachement eventuel de la styloide ulnaire.", "Necessite de reduction sous ALR ou AG et immobilisation par platre manchette brachio-ante-brachiale."],
         "atcd": ["Osteoporose (post-menopausique)", "Chutes a repetition"],
         "ttt": ["Kardegic", "Calcium"]
    },
    "S72.0": {
         "motifs": ["Chute, n'arrive plus a se lever", "Suspicion fracture col du femur", "Trauma hanche, raccourcissement jambe", "Personne agee tombee"],
         "triage": ["Patiente agee, brancardee. Raccourcissement et rotation externe membre inf droit. Grosse dlr hanche.", "Chute mecanique domicile. Impotence absolue MI gauche."],
         "anamnese": ["Chute mecanique de sa hauteur chez une personne agee. Impossibilite de se relever. Douleur localisee au pli de l'aine ou trochanter.", "Apporte par les pompiers apres avoir ete retrouve au sol. Plainte d'une douleur aigue de la hanche."],
         "examen": ["Attitude vicieuse tres caracteristique: raccourcissement, rotation externe et adduction du membre inferieur atteint. Impotence fonctionnelle totale.", "Palpation douloureuse du pli de l'aine. Examen vasculo-nerveux distal normal. Pas de deficit sentivio-moteur distal."],
         "paraclinique": ["Radiographie bassin de face, hanche pathologique de face et faux profil de Lequesne: trait de fracture du col femoral (Garden III ou IV).", "Bilan pre-operatoire complet (NFS, Hemostase, ECG) preleve. Avis orthopedie pour prothese ou osteosynthese."],
         "atcd": ["Osteoporose", "Troubles cognitifs", "Prothese genou controlateral"],
         "ttt": ["Previscan", "Eliquis", "Antidepresseurs"]
    },
    "S82.6": {
         "motifs": ["Torsion cheville", "Douleur malleole", "Fracture cheville apres sport", "A tordu le pied"],
         "triage": ["Entorse/Fracture cheville gauche. Grosse malleole externe. Ne peut pas appuyer.", "Trauma cheville. Applique glace. Dlr 7/10."],
         "anamnese": ["Traumatisme en inversion ou eversion forcee de la cheville lors de la pratique sportive. Craquement percU. Impossibilite de reprise de l'appui (critere d'Ottawa positif).", "Faux pas sur un trottoir, douleur vive malleolaire externe, apparition rapide d'un gros udime."],
         "examen": ["Udime important peri-malleolaire (en 'oeuf de pigeon'). Palpation exquise de la pointe ou de la face posterieure de la malleole externe.", "Recherche de complication: pas d'ouverture cutanee, pouls pedieux et tibial posterieur palpes. Syndesmose apparemment integre cliniquement."],
         "paraclinique": ["Radiographie cheville face et profil: trait de fracture uni-malleolaire externe (trans-ligamentaire, type Weber B). Pas de luxation associee.", "Mise en place d'une botte platre ou resine apres avis de l'orthopediste si non chirurgical (ou chirurgie selon deplacement)."],
         "atcd": ["Entorses a repetition"],
         "ttt": ["Aucun", "AINS parfois"]
    },
    "F10.0": {
         "motifs": ["Ivresse aigue", "Patient alcoolise sur la voie publique", "Intoxication ethylique", "Agitation et alcool"],
         "triage": ["Amene par la police. Haleine ethylique tres forte. Agite. Tensions OK.", "Dort sur le brancard. Ethylisme aigu. GCS 13. A surveiller."],
         "anamnese": ["Decouvert sur la voie publique par les forces de l'ordre ou les pompiers dans un etat d'ebriete manifeste. Ingestion massive de boissons alcoolisees.", "Contexte de consommation excessive d'alcool rapportee par l'entourage. Le patient est peu collaborant."],
         "examen": ["Dysarthrie, ataxie, nystagmus multidirectionnel. Haleine sentant l'alcool. Humeur instable, allant de l'euphorie a l'agressivite.", "Signes neuro toxiques de l'ivresse. Examen des autres fonctions normal (eliminer une hypoglycemie ou un trauma cranien associe)."],
         "paraclinique": ["Alcoolemie sanguine positive (souvent > 2 g/L). Glycemie capillaire normale. Reste du bilan biologique sans particularite, sauf macrocytose ou perturbation du bilan hepatique ancienne.", "Surveillance en UHCD avec hydratation et apport de Vitamines B1/B6. Repos en chambre calme."],
         "atcd": ["Alcoolisme chronique", "Depression"],
         "ttt": ["Seresta", "Aotal", "Vitamines B"]
    },
    "F41.0": {
         "motifs": ["Crise d'angoisse", "Sensation d'etouffer, panique", "A peur de mourir", "Palpitations liees au stress"],
         "triage": ["Patiente angoissee, pleure, tremble. Constantes normales. ECG d'entree normal.", "Crise de panique. Hyperventilation. SpO2 100%."],
         "anamnese": ["Attaque de panique soudaine, debutant sans declencheur clair, caracterisee par une peur intense, une sensation de mort imminente et une oppression thoracique.", "La patiente rapporte avoir eu l'impression qu'elle allait s'evanouir et devenir folle. Les symptomes ont culmine en 10 minutes."],
         "examen": ["Hyperventilation, tachycardie sinusale a 110 bpm liee au stress, tremblements fins des extremites. Pas de signe d'insuffisance respiratoire.", "Examen cardiopulmonaire strictement normal. Spasmophilie possible (signe de Chvostek parfois positif par alcalose respiratoire)."],
         "paraclinique": ["ECG systematique devant la plainte thoracique: rythme sinusal normal. Troponines negatives. D-Dimeres negatifs (elimine EP).", "Aucun examen de biologie lourd necessaire. Reassurance et administration eventuelle d'une benzodiazepine (Xanax, Valium) a faible dose."],
         "atcd": ["Troubles anxieux generalises", "Spasmophilie"],
         "ttt": ["Xanax", "Lexomil", "Paroxetine"]
    },
    "E10.0": {
         "motifs": ["Diabete decompense", "Acidocetose", "Haleine de pomme, nausees", "Patient diabetique confus"],
         "triage": ["Diabete type 1 connu. Dextro High (hors limite). Haleine acetonique. Polypnee. Salle de dechocage.", "Asthenie majeure, soif intense, urines +++. Nausees importantes."],
         "anamnese": ["Apparition d'un syndrome cardinal (polyurie, polydipsie, amaigrissement) evoluant depuis quelques jours, complete de douleurs abdominales et nausees.", "Rupture d'approvisionnement en insuline chez un patient DT1. Tableau aigu de deshydratation intra et extra-cellulaire."],
         "examen": ["Respiration ample et bruyante de Kussmaul (compensation de l'acidose). Haleine caracteristique (odeur d'acetone ou de pomme reinette). Pli cutane, secheresse muqueuse.", "Tachycardie, hypotension orthostatique. Abdomen parfois pseudo-chirurgical (sensible diffusement sans vraie defense)."],
         "paraclinique": ["Glycemie capillaire tres elevee (> 3 g/L). BU: glycosurie massive et cetonurie forte (+++ ou ++++).", "Gaz du sang: acidose metabolique (pH < 7.30, Bicarbonates bas). Iono: hypokaliemie relative (a corriger). Transfert reanimation ou soins continus."],
         "atcd": ["Diabete de type 1", "Maladie auto-immune"],
         "ttt": ["Insuline lente (Lantus)", "Insuline rapide (Novorapid)"]
    },
    "E11.9": {
         "motifs": ["Bilan diabete type 2", "Hyperglycemie asymptomatique", "Dextro eleve en routine", "Fatigue chez diabetique"],
         "triage": ["Adresse par MT pour glycemie a 4g/L. Totalement asymptomatique. Pas de cetone.", "Diabetique type 2. Asthenie. Constantes stables."],
         "anamnese": ["Decouverte fortuite ou suivi d'une hyperglycemie chronique. Pas de signe d'acidocetose ni de syndrome hyperosmolaire franc.", "Le patient a oublie son traitement oral depuis une semaine. Se sent juste un peu fatigue et boit plus que d'habitude."],
         "examen": ["Examen clinique normal. Pas de deshydratation majeure. Auscultation normale. Sensibilite des pieds (test au monofilament) conservee ou alteree (neuropathie chronique).", "Patient eupneique, pas de douleur. Constantes rassurantes. L'examen ne trouve aucun foyer infectieux declenchant."],
         "paraclinique": ["Hyperglycemie veineuse confirmee (ex: 3.5 g/L). Pas de corps cetoniques dans les urines. Ionogramme sanguin et fonction renale corrects.", "Hemoglobine glyquee (HbA1c) souvent tres elevee (> 9%). Adaptation du traitement antidiabetique oral ou passage a l'insuline basale."],
         "atcd": ["Diabete de type 2", "Syndrome metabolique", "Obesite"],
         "ttt": ["Metformine", "Gliclazide", "Sitagliptine"]
    },
    "E86": {
         "motifs": ["Deshydratation severe", "Personne agee qui ne boit plus", "Coup de chaleur et perte de liquide", "Vertiges, muqueuse seche"],
         "triage": ["Deshydratation. Pli cutane majeur. Perte de 3kg. TA limite basse.", "Canicule. Patiente agee desorientee. Langue tres seche."],
         "anamnese": ["Contexte de forte chaleur, de reduction des apports hydriques ou de pertes excessives (diarrhee, sueurs). Sensation de soif, faiblesse musculaire, vertiges orthostatiques.", "Personne agee retrouvee au sol, n'ayant pas bu depuis 48h. Plainte de secheresse buccale intense et asthenie profonde."],
         "examen": ["Signes de deshydratation extracellulaire: pli cutane persistant, hypotension arterielle, tachycardie. Signes intracellulaires: secheresse des muqueuses, soif ardente, troubles neuro moderes (confusion).", "Yeux excaves (cernes). Baisse de la turgescence cutanee. Auscultation sans particularite. Pas de foyer infectieux evident."],
         "paraclinique": ["Iono: hypernatremie frequente (traduit la deshydratation intra-cellulaire) ou normonatremie. Insuffisance renale fonctionnelle (uree et creatinine elevees, ratio uree/creat eleve).", "Hemoconcentration (protidemie et hematocrite eleves). Perfusion de solutes cristalloides (NaCl 0.9%)."],
         "atcd": ["Demence (oublie de boire)", "Diuretiques au long cours"],
         "ttt": ["Lasilix (suspendu)", "Antihypertenseurs (suspendus)"]
    },
    "N10": {
         "motifs": ["Pyelonephrite", "Fievre et douleur aux reins", "Infection urinaire haute", "Brulures urinaires et frissons"],
         "triage": ["Douleur fosse lombaire droite, febrile a 39. BU positive. Suspi PNA.", "Fievre, frissons. Douleur dos d'un cote. Patiente algique."],
         "anamnese": ["Debut brutal associant syndrome infectieux (fievre > 38.5, frissons) et signes fonctionnels urinaires (brulures mictionnelles, pollakiurie).", "Douleur lombaire unilaterale, pesante, sourde, d'apparition recente, avec antecedent de cystite il y a une semaine mal soignee."],
         "examen": ["Examen de l'abdomen souple, mais presence d'une douleur exquise a la palpation de la fosse lombaire (signe de Giordano positif). Pas de contracture.", "Empatement de la loge renale parfois percU. Reste de l'examen sans particularite. Hemodynamique stable."],
         "paraclinique": ["BU (Bandelette Urinaire) tres positive aux leucocytes et nitrites. ECBU preleve avant antibiotherapie. Prise de sang: hyperleucocytose, CRP Augmentee.", "Echographie renale (souvent differee si tableau typique sans signe de gravite) pour eliminer un obstacle (PNA obstructive). Antibiotherapie probabiliste."],
         "atcd": ["Infections urinaires a repetition", "Grossesse en cours (facteur favorisant)"],
         "ttt": ["Fosfomycine (il y a qq jours)", "Contraception"]
    },
    "N20.0": {
         "motifs": ["Colique nephretique", "Douleur atroce au rein", "Mal au dos en coup de poignard", "Calcul renal"],
         "triage": ["Patient tres agite, ne tient pas en place. Douleur lombo-abdominale insupportable. Pas de fievre.", "Colique nephretique. Douleur tres vive au flanc. Urgence antalgique."],
         "anamnese": ["Douleur lombo-abdominale unilaterale a debut brutal, d'intensite majeure, irradiant vers les organes genitaux externes. Pas de position antalgique (le patient est agite 'frenetique').", "Episode de colique nephretique typique. Le patient se tord de douleur. Pas de fievre ni de frissons."],
         "examen": ["Douleur tres vive a la palpation de la fosse lombaire et sur le trajet de l'uretere. Abdomen globalement souple, pas de vraie defense chirurgicale.", "Touchers pelviens normaux. Pas de globe vesical. Constantes normales en dehors d'une tachycardie due a la douleur."],
         "paraclinique": ["BU: presence d'une hematurie microscopique. Pas de nitrites ni de leucocytes (elimine infection).", "Scanner abdomino-pelvien sans injection (low dose) montre un calcul ureteral responsable d'une dilatation des cavites pyelocalicielles. Traitement par AINS (Ketoprofene)."],
         "atcd": ["Coliques nephretiques par le passe", "Goutte (calculs uriques)"],
         "ttt": ["Allopurinol", "Spasfon"]
    },
    "N39.0": {
         "motifs": ["Cystite", "Brle quand j'urine", "Infection urinaire", "Envie frequente de faire pipi"],
         "triage": ["Brulures mictionnelles depuis 2 jours. Patiente afebrile. BU en cours.", "Pollakiurie et dysurie. Pas de douleur lombaire. Apyrexie."],
         "anamnese": ["Symptomatologie purement vesicale: pollakiurie, imperiosites, brulures lors de la miction (dysurie), et parfois urines troubles ou malodorantes.", "Gene sus-pubienne et envies tres frequentes d'uriner. Pas de fievre, pas de douleur lombaire, pas de nausees."],
         "examen": ["Examen clinique globalement normal. Sensibilite a la palpation de la region sus-pubienne (hypogastre). Fosses lombaires souples et indolores.", "Afebrile. Le reste de l'examen abdominal est sans anomalie. Bon etat general."],
         "paraclinique": ["BU positive (Leucocytes +, Nitrites +). Diagnostic de cystite aigue simple clinique et bandelette. Pas d'ECBU ni de prise de sang necessaires sauf si recidive.", "Prescription d'antibiotique dose unique (Fosfomycine-Trometamol) et conseils d'hydratation. Retour a domicile immediat."],
         "atcd": ["Cystites occasionnelles"],
         "ttt": ["Aucun"]
    },
    "H66.9": {
         "motifs": ["Otite", "Forte douleur a l'oreille", "Mal aux oreilles", "Oreille bouchee et douloureuse"],
         "triage": ["Dlr oreille droite. Febricule 38. OMA probable.", "Grosse douleur auriculaire et baisse de l'audition de ce cote."],
         "anamnese": ["Otalgie pulsatile d'intensite croissante, souvent precedee d'un episode de rhinopharyngite. Sensation d'oreille bouchee (hypoacousie) et febricule.", "Douleur d'une oreille empechant de dormir. Pas de vertige majeur, pas de paralysie faciale."],
         "examen": ["Otoscopie: tympan tres congestif (rouge), bombe, avec disparition du cone lumineux. Pas de perforation visible ni d'otorrhee franche.", "Palpation mastoidienne indolore. Examen de l'oropharynx: legere rhinopharyngite associee. Ganglions cervicaux reactifs."],
         "paraclinique": ["Aucun examen complementaire necessaire. Diagnostic clinique d'Otite Moyenne Aigue (OMA) congestive ou purulente.", "Prescription d'antalgiques et eventuellement d'antibiotherapie selon l'aspect purulent du tympan et l'age."],
         "atcd": ["Rhinopharyngites frequentes"],
         "ttt": ["Serum physiologique", "Doliprane"]
    },
    "J03.9": {
         "motifs": ["Angine", "Mal a la gorge intense", "Difficulte a avaler", "Gorge tres rouge et fievre"],
         "triage": ["Odynophagie importante. Febrile 38.5. Examen de gorge a faire.", "Mal de gorge, ganglions. Test Trod angine a prevoir."],
         "anamnese": ["Douleur de gorge intense (odynophagie) majoree par la deglutition, accompagnee d'un syndrome infectieux (fievre, asthenie, frissons).", "Le patient ne peut plus s'alimenter solidement tant la deglutition est douloureuse. Presence d'adenopathies cervicales douloureuses."],
         "examen": ["Examen oropharynge (abaisse-langue): amygdales tres augmentees de volume (hypertrophiees), hyperhemiees (rouges) avec souvent des enduits pultaces blancs.", "Luette udimatiee. Palpation d'adenopathies sous-angulo-maxillaires sensibles. Auscultation pulmonaire libre."],
         "paraclinique": ["Test Rapide d'Orientation Diagnostique (TROD) Streptocoque A: souvent realise pour distinguer angine virale d'angine bacterienne.", "Biologie inutile. Si Trod positif: antibiotherapie (Amoxicilline). Si negatif: traitement symptomatique exclusif."],
         "atcd": ["Amygdalectomie (non)"],
         "ttt": ["Pastilles pour la gorge", "Paracetamol"]
    },
    "J01.9": {
         "motifs": ["Sinusite", "Douleur au visage, nez bouche", "Mal a la tete derriere les yeux", "Rhume qui a degenere"],
         "triage": ["Cephalees frontales, nez pris. Tensions normales. Suspicion sinusite.", "Douleur sous l'oeil gauche max quand penche la tete en avant. Metatheque."],
         "anamnese": ["Suite a un episode viral des voies aeriennes superieures (rhume), apparition d'une douleur maxillaire unilaterale, pulsatile, accrue par l'anteflexion de la tete (signe du lacet).", "Rhinorrhee purulente, obstruction nasale unilaterale, avec pesanteur faciale et febricule evoluant depuis plusieurs jours."],
         "examen": ["Douleur provoquee a la pression du point sinusal (maxillaire ou frontal). Rhinoscopie anterieure montre des secretions purulentes dans le meat moyen.", "Pas d'udime peri-orbitaire, pas de trouble visuel (elimine une complication grave). Examen neuro normal."],
         "paraclinique": ["Diagnostic clinique. La radiographie des sinus est aujourd'hui obsolete et inutile.", "Antibiothérapie si critères de sinusite bactérienne aiguë purulente (Augmentin) et lavage de nez au sérum physiologique."],
         "atcd": ["Polypose naso-sinusienne", "Rhinite allergique"],
         "ttt": ["Corticoides locaux", "Antihistaminiques"]
    },
    "L02.9": {
         "motifs": ["Abces", "Boule rouge et douloureuse sur la peau", "Furoncle infecte", "Collection de pus cutanee"],
         "triage": ["Grosse voussure fluctuante a la jambe. Douleur inflammatoire. Pas de fievre.", "Abces sous-cutane fessier. Tres douloureux. Pret pour incision."],
         "anamnese": ["Apparition progressive d'une tumefaction cutanee tres douloureuse, chaude, rouge, d'evolution aigue, limitant les mouvements par la douleur.", "Patient signale l'evolution d'un bouton qui s'est infecte, Augmente de volume et devenu tres indure puis fluctuant."],
         "examen": ["Tumorefaction erythemateuse, chaude, extremement sensible a la palpation. Presence d'une fluctuation centrale claire (la collection purulente est mure).", "Adenopathie satellite inflammatoire parfois palpee. Pas d'extension de type cellulite ou dermo-hypodermite severe. Afebrile."],
         "paraclinique": ["Indication a un geste chirurgical local: anesthesie locale, incision au bistouri, evacuation de pus franc, mechage de la cavite.", "Prelevement bacteriologique du pus. Pas de bilan sanguin ni d'antibiotherapie per os systematique (sauf terrain a risque)."],
         "atcd": ["Diabete", "Infections cutanees recidivantes", "Immunodepression"],
         "ttt": ["Antiseptiques locaux"]
    },
    "L03.0": {
         "motifs": ["ErysipEle", "Jambe tres rouge, gonflee et fievre", "Cellulite de la jambe", "Infection cutanee etendue"],
         "triage": ["Grosse jambe rouge aigue (GJRA). Febrile a 39C. Tensions stables. Dermo-hypodermite bacterienne non necrosante.", "Placard inflammatoire du mollet. Frissons ce matin."],
         "anamnese": ["Debut brutal avec fievre elevee (39-40C), frissons, puis apparition secondaire d'un placard erythemateux douloureux et udimateux de la jambe unilateral.", "Notion de porte d'entree retrouvee (intertrigo mycosique inter-orteils ou plaie minime). Douleur cutanee cuisante."],
         "examen": ["Placard cutane inflammatoire (rouge, chaud, douloureux, gonfle) du membre inferieur, bien delimite (bourrelet peripherique inconstant).", "Palpation d'une adenopathie inguinale satellite homolateirale inflammatoire. Pas de crepitation sous-cutane ni d'anesthesie cutanee (signes de gravite de fasciite elimines)."],
         "paraclinique": ["Hyperleucocytose a PNN franche. CRP tres elevee. Les hemocultures sont rarement positives.", "Traitement par antibiotherapie active sur le Streptocoque (Amoxicilline ou Penicilline). Repos jambe surelevee. Traitement de la porte d'entree."],
         "atcd": ["Insuffisance veineuse", "LymphUdime", "Diabete", "Obesite"],
         "ttt": ["Bas de contention", "Anticoagulants si risque"]
    },
    "T78.3": {
         "motifs": ["Reaction allergique majeure", "Angioudime", "Gonflement visage et levres apres piqure", "Choc anaphylactique debutant"],
         "triage": ["Allergie/Urticaire + udime de Quincke. Siffle un peu. Voie veineuse posee en urgence (Cortico + Adrenaline pret).", "A mange des arachides. Levres et langue gonflent. FR 22."],
         "anamnese": ["Survenue brutale (quelques minutes apres contact avec un allergene connu ou morsure d'insecte) de prurit, eruption cutanee, et difficulte respiratoire.", "Sensation de boule dans la gorge, gene inspiratoire majeure et gonflement du visage d'apparition tres rapide."],
         "examen": ["Urticaire geante diffuse tres prurigineuse. Udime facial et labial marquant (angioudime). Stridor inspiratoire par udime larynge.", "Tachycardie, baisse possible de la TA (choc anaphylactique). Auscultation pulmonaire: parfois sibilants (bronchospasme). Urgence extreme."],
         "paraclinique": ["Prise en charge clinique immediate: Adrenaline intra-musculaire, corticoides IV, anti-histaminiques IV. Pas le temps de la biologie.", "Surveillance stricte en box de dechocage. Prescription d'un stylo d'adrenaline (Anapen/Epipen) pour la sortie."],
         "atcd": ["Allergie arachide/fruits a coque", "Allergie venin de guepe", "Asthme"],
         "ttt": ["Stylo d'Adrenaline auto-injectable", "Zyrtec", "Aerius"]
    }
}

PREVALENCE_WEIGHTS = {
    "A09.0": 4, "A41.9": 1,
    "I10": 8, "I21.0": 3, "I48": 3, "I50.0": 2, "I63.9": 3,
    "J15.9": 5, "J18.9": 6, "J44.0": 3, "J45.0": 3,
    "K35.9": 3, "K52.9": 4, "K80.0": 3, "K85.0": 1,
    "G40.9": 2, "G45.0": 2,
    "S06.0": 2, "S22.4": 3, "S42.0": 3, "S52.5": 5, "S72.0": 4, "S82.6": 5,
    "F10.0": 4, "F41.0": 5,
    "E10.0": 1, "E11.9": 6, "E86": 4,
    "N10": 3, "N20.0": 4, "N39.0": 7,
    "H66.9": 3, "J03.9": 5, "J01.9": 4,
    "L02.9": 2, "L03.0": 2, "T78.3": 1,
}

CODE_AGE_RANGES = {
    "A09.0":  (1, 70), "A41.9": (50, 90),
    "I10":   (35, 85), "I21.0": (45, 85), "I48": (50, 85),
    "I50.0": (55, 90), "I63.9": (55, 90),
    "J15.9": (1, 85),  "J18.9": (1, 85),  "J44.0": (50, 85), "J45.0": (3, 45),
    "K35.9": (10, 40), "K52.9": (15, 60), "K80.0": (30, 70), "K85.0": (35, 65),
    "G40.9": (5, 60),  "G45.0": (50, 85),
    "S06.0": (15, 65), "S22.4": (30, 80), "S42.0": (15, 50),
    "S52.5": (40, 85), "S72.0": (60, 95), "S82.6": (15, 50),
    "F10.0": (25, 60), "F41.0": (18, 50),
    "E10.0": (10, 40), "E11.9": (40, 85), "E86": (60, 95),
    "N10":   (18, 55), "N20.0": (25, 65), "N39.0": (18, 80),
    "H66.9": (1, 12),  "J03.9": (3, 30),  "J01.9": (20, 60),
    "L02.9": (25, 65), "L03.0": (40, 80), "T78.3": (5, 50),
}


PHRASES_INTRO = [
    "Patient vu ce jour aux urgences.",
    "Consultation aux urgences pour",
    "Prise en charge dans le box pour evaluation:",
    "L'histoire de la maladie revele:",
    "A l'admission, on note:",
]

PHRASES_LIAISON = [
    "Concernant l'examen clinique:",
    "Sur le plan physique,",
    "A l'examen ce jour,",
]

PHRASES_BIO = [
    "Au niveau des examens complementaires:",
    "Le bilan paraclinique montre:",
    "La biologie et l'imagerie concluent a:",
]

ABREVIATIONS = {
    "douleur": ["dlr"],
    "traitement": ["ttt"],
    "antecedents": ["atcd"],
    "pression arterielle": ["TA"],
    "temperature": ["T", "T°"],
    "examen": ["exam"],
    "patient": ["pat"],
    "urgences": ["urg"],
}


def inject_abbreviations(text, prob=0.3):
    words = text.split()
    for i, w in enumerate(words):
        clean = w.lower().strip(".,:;()")
        if clean in ABREVIATIONS and random.random() < prob:
            new = random.choice(ABREVIATIONS[clean])
            if w[0].isupper():
                new = new.capitalize()
            words[i] = w.replace(clean, new, 1)
    return " ".join(words)


def generate_text_observation(profile):
    parts = []
    parts.append(random.choice(PHRASES_INTRO))
    parts.append(random.choice(profile["anamnese"]))
    parts.append(random.choice(PHRASES_LIAISON))
    parts.append(random.choice(profile["examen"]))
    if random.random() > 0.1:
        parts.append(random.choice(PHRASES_BIO))
        parts.append(random.choice(profile["paraclinique"]))
    text = " ".join(parts)
    text = inject_abbreviations(text, prob=0.3)
    return text


def generate_row(patient_id):
    weighted = list(PREVALENCE_WEIGHTS.keys())
    weights = [PREVALENCE_WEIGHTS[c] for c in weighted]
    code_cim = random.choices(weighted, weights=weights, k=1)[0]
    profile = CIM_PROFILES[code_cim]

    age_min, age_max = CODE_AGE_RANGES[code_cim]
    age = random.randint(age_min, age_max)
    sexe = random.choice(["M", "F"])

    motif_visite = random.choice(profile["motifs"])
    notes_triage = random.choice(profile["triage"])
    texte_observation = generate_text_observation(profile)

    if random.random() < 0.3:
        antecedents = ""
    else:
        nb = random.randint(1, min(2, len(profile["atcd"])))
        antecedents = ", ".join(random.sample(profile["atcd"], nb))

    if random.random() < 0.4:
        traitement_en_cours = ""
    else:
        nb = random.randint(1, min(2, len(profile["ttt"])))
        traitement_en_cours = ", ".join(random.sample(profile["ttt"], nb))

    return [
        patient_id, age, sexe, motif_visite, notes_triage,
        texte_observation, antecedents, traitement_en_cours, code_cim,
    ]


def main():
    random.seed(42)
    num_rows = 30000
    filename = "dataset_nlp_cim10_30k.csv"

    headers = [
        "patient_id", "age", "sexe", "motif_visite", "notes_triage",
        "texte_observation", "antecedents", "traitement_en_cours", "code_cim",
    ]

    print(f"Generating {num_rows} NLP rows...")
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for i in range(1, num_rows + 1):
            w.writerow(generate_row(i))
    print(f"Termine : {filename}")


if __name__ == "__main__":
    main()
